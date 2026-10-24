/**
 * Main application script for Point of Sale & Attendees Dashboard.
 */

let allTickets = [];
let currentStats = {};

// Load data on page load
document.addEventListener("DOMContentLoaded", () => {
  checkAdminAccess();
  loadStats();
  loadTickets();
});

function checkAdminAccess() {
  const pin = typeof EXPECTED_ADMIN_PIN !== 'undefined' ? EXPECTED_ADMIN_PIN : "2026";
  const params = new URLSearchParams(window.location.search);
  const pinParam = params.get("pin");
  if (pinParam === pin) {
    sessionStorage.setItem("admin_auth", pin);
    const lock = document.getElementById("adminLockScreen");
    if (lock) lock.style.display = "none";
    return true;
  }
  if (sessionStorage.getItem("admin_auth") === pin) {
    const lock = document.getElementById("adminLockScreen");
    if (lock) lock.style.display = "none";
    return true;
  }
  const lock = document.getElementById("adminLockScreen");
  if (lock) lock.style.display = "flex";
  return false;
}

function handlePinSubmit(e) {
  e.preventDefault();
  const pin = typeof EXPECTED_ADMIN_PIN !== 'undefined' ? EXPECTED_ADMIN_PIN : "2026";
  const input = document.getElementById("adminPinInput");
  const val = input.value.trim();
  if (val === pin) {
    sessionStorage.setItem("admin_auth", pin);
    document.getElementById("adminLockScreen").style.display = "none";
  } else {
    document.getElementById("pinErrorMsg").style.display = "block";
    input.value = "";
    input.focus();
  }
}

function copyDoorLink() {
  const pin = typeof EXPECTED_DOOR_PIN !== 'undefined' ? EXPECTED_DOOR_PIN : "puerta";
  const url = `${window.location.origin}/scanner?pin=${encodeURIComponent(pin)}`;
  navigator.clipboard.writeText(url).then(() => {
    alert("📱 ¡Enlace para los porteros copiado!\n\nPuedes enviárselo por WhatsApp a los controladores de acceso:\n\n" + url);
  });
}

function copyAdminLink() {
  const pin = typeof EXPECTED_ADMIN_PIN !== 'undefined' ? EXPECTED_ADMIN_PIN : "2026";
  const url = `${window.location.origin}/?pin=${encodeURIComponent(pin)}`;
  navigator.clipboard.writeText(url).then(() => {
    alert("🔗 ¡Enlace de Taquilla copiado!\n\nGuarda este enlace en favoritos para entrar directamente sin escribir el PIN:\n\n" + url);
  });
}

// Fetch stats
async function loadStats() {
  try {
    const res = await fetch("/api/stats");
    const data = await res.json();
    currentStats = data;

    document.getElementById("statSold").innerText = `${data.sold} / ${data.max_capacity}`;
    const pct = data.max_capacity > 0 ? Math.round((data.sold / data.max_capacity) * 100) : 0;
    document.getElementById("statSoldPct").innerText = `${pct}% del aforo cubierto`;
    document.getElementById("statProgressBar").style.width = `${Math.min(100, pct)}%`;

    document.getElementById("statRemaining").innerText = data.remaining;
    document.getElementById("statRevenue").innerText = `${Number(data.total_revenue).toFixed(2)} €`;

    document.getElementById("statCheckedIn").innerText = `${data.checked_in} personas`;
    const checkInPct = data.sold > 0 ? Math.round((data.checked_in / data.sold) * 100) : 0;
    document.getElementById("statCheckedInPct").innerText = `${checkInPct}% de los que compraron`;
  } catch (err) {
    console.error("Error al cargar estadísticas", err);
  }
}

// Fetch tickets
async function loadTickets() {
  const search = document.getElementById("searchFilter").value.trim();
  const status = document.getElementById("statusFilter").value;

  try {
    let url = `/api/tickets?search=${encodeURIComponent(search)}&status=${status}`;
    const res = await fetch(url);
    const data = await res.json();
    allTickets = data;
    renderTicketsTable(data);
  } catch (err) {
    console.error("Error al cargar entradas", err);
  }
}

let searchDebounce = null;
function handleSearch() {
  clearTimeout(searchDebounce);
  searchDebounce = setTimeout(loadTickets, 250);
}

// Render Table
function renderTicketsTable(tickets) {
  const tbody = document.getElementById("ticketsTableBody");
  if (!tickets || tickets.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="7" style="text-align: center; color: var(--text-muted); padding: 30px;">
          No se encontraron entradas registradas.
        </td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = tickets.map(t => {
    let badgeClass = "badge-valida";
    let badgeText = "Válida";
    if (t.status === "USADA") {
      badgeClass = "badge-usada";
      badgeText = `Usada (${t.used_at ? t.used_at.split(" ")[1] : "OK"})`;
    } else if (t.status === "ANULADA") {
      badgeClass = "badge-anulada";
      badgeText = "Anulada";
    }

    const tNum = String(t.ticket_number).padStart(3, "0");

    return `
      <tr>
        <td style="font-family: monospace; font-weight: bold; color: var(--gold-light);">#${tNum}</td>
        <td>
          <div style="font-weight: 700; color: #fff;">${escapeHtml(t.name)} ${escapeHtml(t.surname)}</div>
          ${t.notes ? `<div style="font-size: 11px; color: var(--text-muted);">📝 ${escapeHtml(t.notes)}</div>` : ""}
        </td>
        <td style="font-family: monospace; font-weight: bold; color: #fbbf24;">${escapeHtml(t.dni)}</td>
        <td>
          <div>${escapeHtml(t.email)}</div>
          ${t.phone ? `<div style="font-size: 11px; color: var(--text-muted);">${escapeHtml(t.phone)}</div>` : ""}
        </td>
        <td>
          <div>${Number(t.price).toFixed(2)} €</div>
          <div style="font-size: 10px; color: var(--text-muted); text-transform: uppercase;">${escapeHtml(t.payment_method)}</div>
        </td>
        <td>
          <span class="badge ${badgeClass}">${badgeText}</span>
        </td>
        <td>
          <div class="action-btn-group">
            <a href="/ticket/${t.code}" target="_blank" class="btn-sm" title="Ver entrada">👁️</a>
            <button onclick="copyLink('${t.code}')" class="btn-sm" title="Copiar enlace">🔗</button>
            <button onclick="shareWhatsApp('${t.phone}', '${t.name}', '${t.code}', '${tNum}')" class="btn-sm" title="WhatsApp">📲</button>
            ${t.status === 'USADA' ? 
              `<button onclick="resetStatus(${t.id}, 'VALIDA')" class="btn-sm" title="Revertir a Válida" style="color: #6ee7b7;">↺</button>` : 
              ""}
            ${t.status !== 'ANULADA' ? 
              `<button onclick="cancelTicket(${t.id}, '${tNum}')" class="btn-sm" title="Anular entrada" style="color: #f87171;">✕</button>` : 
              ""}
          </div>
        </td>
      </tr>
    `;
  }).join("");
}

// Check DNI Warning when typing
async function checkDniWarning(val) {
  const dni = val.trim();
  const warningEl = document.getElementById("dniWarning");
  if (dni.length < 5) {
    warningEl.style.display = "none";
    return;
  }

  try {
    const res = await fetch(`/api/check-dni?dni=${encodeURIComponent(dni)}`);
    const data = await res.json();
    if (data.exists && data.tickets.length > 0) {
      const prev = data.tickets[0];
      warningEl.innerHTML = `⚠️ <strong>Aviso:</strong> Este DNI ya tiene la entrada <strong>#${String(prev.ticket_number).padStart(3, "0")}</strong> a nombre de ${prev.name} ${prev.surname}.`;
      warningEl.style.display = "block";
    } else {
      warningEl.style.display = "none";
    }
  } catch (e) {}
}

// Handle POS Form Submit (Emitir entrada)
async function handleCreateTicket(e) {
  e.preventDefault();
  const btn = document.getElementById("btnEmitir");
  btn.disabled = true;
  btn.innerText = "⏳ Emitiendo entrada...";

  const payload = {
    name: document.getElementById("inputName").value.trim(),
    surname: document.getElementById("inputSurname").value.trim(),
    dni: document.getElementById("inputDni").value.trim().toUpperCase(),
    email: document.getElementById("inputEmail").value.trim(),
    phone: document.getElementById("inputPhone").value.trim(),
    price: parseFloat(document.getElementById("inputPrice").value) || 0,
    payment_method: document.getElementById("inputPayment").value,
    notes: document.getElementById("inputNotes").value.trim()
  };

  try {
    const res = await fetch("/api/tickets", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const result = await res.json();

    if (!res.ok) {
      alert("Error: " + (result.message || "No se pudo emitir la entrada"));
      btn.disabled = false;
      btn.innerText = "💾 Emitir y Registrar Entrada";
      return;
    }

    // Success! Reset form
    document.getElementById("posForm").reset();
    document.getElementById("dniWarning").style.display = "none";

    // Refresh table & stats
    loadStats();
    loadTickets();

    // Show success modal
    showSuccessModal(result.ticket, result.email_status);
  } catch (err) {
    alert("Error de conexión al emitir la entrada.");
  } finally {
    btn.disabled = false;
    btn.innerText = "💾 Emitir y Registrar Entrada";
  }
}

// Success Modal Display
function showSuccessModal(ticket, emailStatus) {
  const modal = document.getElementById("successModal");
  const body = document.getElementById("successModalBody");
  const tNum = String(ticket.ticket_number).padStart(3, "0");
  const ticketUrl = `${window.location.origin}/ticket/${ticket.code}`;

  body.innerHTML = `
    <div style="text-align: center; margin-bottom: 20px;">
      <div style="font-size: 14px; text-transform: uppercase; letter-spacing: 1px; color: var(--gold);">Entrada Emitida</div>
      <div style="font-size: 32px; font-weight: 900; color: #fff;">#${tNum}</div>
      <div style="font-size: 18px; font-weight: bold; color: #fff; margin-top: 4px;">${escapeHtml(ticket.name)} ${escapeHtml(ticket.surname)}</div>
      <div style="font-size: 16px; color: var(--gold-light); font-family: monospace;">DNI: ${escapeHtml(ticket.dni)}</div>
    </div>

    <div style="background: #1e293b; border-radius: 12px; padding: 14px; margin-bottom: 18px; font-size: 13px;">
      <div style="margin-bottom: 6px;"><strong>Email destinatario:</strong> ${escapeHtml(ticket.email)}</div>
      <div style="color: ${emailStatus.sent ? '#6ee7b7' : '#fcd34d'};">
        ${emailStatus.sent ? '✅ ' : 'ℹ️ '} ${emailStatus.message}
      </div>
    </div>

    <div style="display: flex; flex-direction: column; gap: 10px;">
      <a href="${ticketUrl}" target="_blank" class="btn-nav btn-nav-primary" style="justify-content: center; padding: 12px; font-size: 15px;">
        👁️ Abrir / Ver Entrada Digital con QR
      </a>
      <button onclick="shareWhatsApp('${ticket.phone}', '${escapeHtml(ticket.name)}', '${ticket.code}', '${tNum}')" class="btn-nav" style="justify-content: center; background: #059669; border: none; padding: 12px; font-size: 15px;">
        📲 Enviar Entrada por WhatsApp
      </button>
      <button onclick="copyToClipboard('${ticketUrl}')" class="btn-nav" style="justify-content: center; padding: 12px;">
        🔗 Copiar Enlace Directo
      </button>
    </div>
  `;

  modal.style.display = "flex";
}

// WhatsApp Share
function shareWhatsApp(phone, name, code, tNum) {
  const url = `${window.location.origin}/ticket/${code}`;
  const text = `¡Hola ${name}! 🍾 Aquí tienes tu entrada oficial (#${tNum}) para la Fiesta de Fin de Año 2026:\n\n👉 ${url}\n\n⚠️ Recuerda: Esta entrada es nominal y está asociada a tu DNI. ¡Es obligatorio presentar tu DNI físico en la puerta!`;
  
  // Clean phone number
  let cleanPhone = (phone || "").replace(/[^0-9]/g, "");
  if (cleanPhone.length === 9) {
    cleanPhone = "34" + cleanPhone; // Default to Spain prefix if 9 digits
  }

  let waUrl = `https://api.whatsapp.com/send?text=${encodeURIComponent(text)}`;
  if (cleanPhone) {
    waUrl = `https://api.whatsapp.com/send?phone=${cleanPhone}&text=${encodeURIComponent(text)}`;
  }

  window.open(waUrl, "_blank");
}

function copyLink(code) {
  const url = `${window.location.origin}/ticket/${code}`;
  copyToClipboard(url);
}

function copyToClipboard(text) {
  navigator.clipboard.writeText(text).then(() => {
    alert("¡Enlace copiado al portapapeles!");
  });
}

// Reset / Cancel Ticket
async function resetStatus(ticketId, newStatus) {
  if (!confirm("¿Deseas volver a marcar esta entrada como VÁLIDA para permitir el acceso de nuevo?")) return;
  try {
    await fetch("/api/reset-status", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ticket_id: ticketId, new_status: newStatus })
    });
    loadStats();
    loadTickets();
  } catch (e) {
    alert("Error al actualizar la entrada.");
  }
}

async function cancelTicket(ticketId, tNum) {
  if (!confirm(`¿Estás seguro de anular la entrada #${tNum}? Se liberará una plaza en el aforo de 499 personas.`)) return;
  try {
    await fetch("/api/reset-status", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ticket_id: ticketId, new_status: "ANULADA" })
    });
    loadStats();
    loadTickets();
  } catch (e) {
    alert("Error al anular la entrada.");
  }
}

// CSV Export
function exportCSV() {
  window.location.href = "/api/export-csv";
}

// Settings Modal
function openSettingsModal() {
  document.getElementById("settingsModal").style.display = "flex";
}

function handlePosterUpload(input) {
  if (!input.files || !input.files[0]) return;
  const file = input.files[0];
  const reader = new FileReader();
  reader.onload = async function(e) {
    const base64Data = e.target.result;
    try {
      const res = await fetch("/api/upload-poster", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image_data: base64Data, filename: file.name })
      });
      const data = await res.json();
      if (data.success) {
        alert("¡Cartel subido y guardado con éxito! Ya se mostrará en todas las entradas.");
        const container = document.getElementById("posterPreviewContainer");
        container.innerHTML = `<img src="${data.poster_url}?t=${Date.now()}" style="max-height: 125px; object-fit: contain; border-radius: 4px;">`;
      } else {
        alert("Error al subir el cartel: " + (data.message || "desconocido"));
      }
    } catch (err) {
      alert("Error de conexión al subir el cartel.");
    }
  };
  reader.readAsDataURL(file);
}

function closeModal(modalId) {
  document.getElementById(modalId).style.display = "none";
}

async function handleSaveSettings(e, reload = true) {
  if (e && e.preventDefault) e.preventDefault();
  const payload = {
    event_name: document.getElementById("confEventName").value,
    event_date: document.getElementById("confEventDate").value,
    event_time: document.getElementById("confEventTime").value,
    event_venue: document.getElementById("confEventVenue").value,
    max_capacity: document.getElementById("confMaxCapacity").value,
    smtp_host: document.getElementById("confSmtpHost").value,
    smtp_port: document.getElementById("confSmtpPort").value,
    smtp_user: document.getElementById("confSmtpUser").value,
    smtp_pass: document.getElementById("confSmtpPass").value,
    smtp_from: document.getElementById("confSmtpFrom").value,
    admin_pin: document.getElementById("confAdminPin") ? document.getElementById("confAdminPin").value.trim() : "2026",
    door_pin: document.getElementById("confDoorPin") ? document.getElementById("confDoorPin").value.trim() : "puerta"
  };

  try {
    const res = await fetch("/api/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (res.ok && reload) {
      alert("Configuración guardada correctamente.");
      closeModal("settingsModal");
      window.location.reload();
    }
  } catch (e) {
    if (reload) alert("Error al guardar la configuración.");
  }
}

async function sendTestEmail() {
  const recipient = document.getElementById("testEmailRecipient").value.trim();
  const resDiv = document.getElementById("testEmailResult");
  if (!recipient) {
    alert("Por favor, escribe un email para recibir la prueba.");
    return;
  }
  
  await handleSaveSettings(null, false);

  resDiv.style.display = "block";
  resDiv.style.color = "#9ca3af";
  resDiv.innerText = "⏳ Enviando correo de prueba con código QR...";

  try {
    const res = await fetch("/api/test-email", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ recipient: recipient })
    });
    const data = await res.json();
    if (data.success) {
      resDiv.style.color = "#6ee7b7";
      resDiv.innerHTML = `✅ <strong>¡Éxito!</strong> ${data.message}. Revisa tu bandeja de entrada.`;
    } else {
      resDiv.style.color = "#f87171";
      resDiv.innerHTML = `❌ <strong>Error:</strong> ${data.message}`;
    }
  } catch (err) {
    resDiv.style.color = "#f87171";
    resDiv.innerText = "Error de conexión con el servidor.";
  }
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
