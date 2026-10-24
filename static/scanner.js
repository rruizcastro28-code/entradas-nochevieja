/**
 * Door scanner script for Fiesta Fin de Año.
 * Runs camera scan with jsQR, provides audio and visual feedback.
 * Supports: Live camera, Native camera snapshot, and Hardware laser barcode guns.
 */

let video = document.getElementById("video");
let canvasElement = document.getElementById("qr-canvas");
let canvas = canvasElement.getContext("2d");
let isScanning = true;
let currentFacingMode = "environment";
let currentStream = null;
let soundEnabled = true;
let autoResumeTimeout = null;

// Web Audio synthesizer for door sound effects
let audioCtx = null;
function initAudio() {
  if (!audioCtx) {
    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  }
}

function playSuccessSound() {
  if (!soundEnabled) return;
  try {
    initAudio();
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.type = "sine";
    osc.frequency.setValueAtTime(587.33, audioCtx.currentTime); // D5
    osc.frequency.exponentialRampToValueAtTime(880, audioCtx.currentTime + 0.15); // A5
    gain.gain.setValueAtTime(0.3, audioCtx.currentTime);
    gain.gain.linearRampToValueAtTime(0, audioCtx.currentTime + 0.3);
    osc.connect(gain);
    gain.connect(audioCtx.destination);
    osc.start();
    osc.stop(audioCtx.currentTime + 0.3);
  } catch (e) {
    console.error("Audio error", e);
  }
}

function playErrorSound() {
  if (!soundEnabled) return;
  try {
    initAudio();
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.type = "sawtooth";
    osc.frequency.setValueAtTime(140, audioCtx.currentTime);
    osc.frequency.setValueAtTime(110, audioCtx.currentTime + 0.15);
    gain.gain.setValueAtTime(0.4, audioCtx.currentTime);
    gain.gain.linearRampToValueAtTime(0, audioCtx.currentTime + 0.4);
    osc.connect(gain);
    gain.connect(audioCtx.destination);
    osc.start();
    osc.stop(audioCtx.currentTime + 0.4);
  } catch (e) {
    console.error("Audio error", e);
  }
}

function toggleAudio() {
  soundEnabled = !soundEnabled;
  document.getElementById("btnAudio").innerText = soundEnabled ? "🔊 ON" : "🔇 OFF";
}

// Start Live Camera Feed
function startCamera() {
  const helpBox = document.getElementById("cameraHelpBox");
  const helpTitle = document.getElementById("camHelpTitle");
  const helpMsg = document.getElementById("camHelpMsg");

  // Check if browser supports WebRTC in current security context
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    console.warn("navigator.mediaDevices not available on this origin");
    if (helpBox) {
      helpBox.style.display = "block";
      helpTitle.innerText = "Cámara en directo restringida";
      helpMsg.innerHTML = "Tu navegador requiere una <strong>conexión HTTPS</strong> para el vídeo continuo en red local.<br><br>👉 Pulsa el botón verde <strong>'Tomar Foto del QR'</strong> para escanear al instante con tu cámara nativa, o usa la casilla de DNI.";
    }
    return;
  }

  if (currentStream) {
    currentStream.getTracks().forEach(track => track.stop());
  }

  const constraints = {
    video: {
      facingMode: currentFacingMode,
      width: { ideal: 1280 },
      height: { ideal: 720 }
    }
  };

  navigator.mediaDevices.getUserMedia(constraints)
    .then(stream => {
      if (helpBox) helpBox.style.display = "none";
      currentStream = stream;
      video.srcObject = stream;
      video.setAttribute("playsinline", true);
      video.play();
      isScanning = true;
      requestAnimationFrame(scanTick);
    })
    .catch(err => {
      console.warn("Camera access error with constraints, retrying simple video:", err);
      navigator.mediaDevices.getUserMedia({ video: true })
        .then(stream => {
          if (helpBox) helpBox.style.display = "none";
          currentStream = stream;
          video.srcObject = stream;
          video.setAttribute("playsinline", true);
          video.play();
          isScanning = true;
          requestAnimationFrame(scanTick);
        })
        .catch(finalErr => {
          console.error("Final camera error:", finalErr);
          if (helpBox) {
            helpBox.style.display = "block";
            helpTitle.innerText = "Permiso de Cámara Denegado";
            helpMsg.innerHTML = "El navegador no tiene permiso para abrir la cámara web.<br><br>💡 Usa el botón <strong>'Tomar Foto del QR'</strong> o escribe el DNI abajo.";
          }
        });
    });
}

function toggleCamera() {
  currentFacingMode = (currentFacingMode === "environment") ? "user" : "environment";
  startCamera();
}

// Frame scanning loop
function scanTick() {
  if (!isScanning) return;

  if (video.readyState === video.HAVE_ENOUGH_DATA) {
    canvasElement.height = video.videoHeight;
    canvasElement.width = video.videoWidth;
    canvas.drawImage(video, 0, 0, canvasElement.width, canvasElement.height);

    const imageData = canvas.getImageData(0, 0, canvasElement.width, canvasElement.height);
    const code = jsQR(imageData.data, imageData.width, imageData.height, {
      inversionAttempts: "dontInvert"
    });

    if (code && code.data && code.data.trim() !== "") {
      onCodeDetected(code.data.trim());
      return;
    }
  }

  requestAnimationFrame(scanTick);
}

// Handle Photo Snapshot (Alternative scanner that works 100% on any mobile phone & HTTP)
function handleFileScan(input) {
  if (!input.files || !input.files[0]) return;
  const file = input.files[0];
  const reader = new FileReader();
  reader.onload = function(e) {
    const img = new Image();
    img.onload = function() {
      canvasElement.width = img.width;
      canvasElement.height = img.height;
      canvas.drawImage(img, 0, 0);
      const imageData = canvas.getImageData(0, 0, img.width, img.height);
      const code = jsQR(imageData.data, imageData.width, imageData.height, {
        inversionAttempts: "dontInvert"
      });
      if (code && code.data && code.data.trim() !== "") {
        onCodeDetected(code.data.trim());
      } else {
        alert("⚠️ No se pudo leer el código QR en la foto. Intenta enfocar más de cerca y con buena iluminación.");
      }
    };
    img.src = e.target.result;
  };
  reader.readAsDataURL(file);
}

// When a QR code is detected (by camera or photo)
function onCodeDetected(codeStr) {
  isScanning = false;
  validateCode(codeStr);
}

// Call API to validate
async function validateCode(codeStr) {
  try {
    const res = await fetch("/api/validate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code: codeStr })
    });
    const data = await res.json();
    showResult(data);
  } catch (err) {
    showResult({
      status: "ERROR",
      message: "Error de conexión con el servidor. Comprueba la red.",
      ticket: null
    });
  }
}

// Display full screen result
function showResult(data) {
  const overlay = document.getElementById("resultOverlay");
  const badge = document.getElementById("resBadge");
  const tNum = document.getElementById("resTicketNum");
  const name = document.getElementById("resName");
  const dni = document.getElementById("resDni");
  const extra = document.getElementById("resExtra");

  overlay.className = "result-overlay"; // reset classes

  if (data.status === "VALID") {
    // SUCCESS
    overlay.classList.add("result-valid");
    badge.innerHTML = "✅ ACCESO PERMITIDO";
    tNum.innerText = `ENTRADA #${String(data.ticket.ticket_number).padStart(3, "0")}`;
    name.innerText = `${data.ticket.name} ${data.ticket.surname}`;
    dni.innerText = data.ticket.dni;
    extra.innerHTML = `
      <div style="color: #6ee7b7; font-weight: bold; margin-bottom: 4px;">¡Válida! Primera vez registrada</div>
      <div>Cobrado: ${data.ticket.price}€ (${data.ticket.payment_method})</div>
      ${data.ticket.notes ? `<div style="color: #fbbf24; margin-top: 4px;">📝 ${data.ticket.notes}</div>` : ""}
    `;
    playSuccessSound();
    if (navigator.vibrate) navigator.vibrate(150);
  } else if (data.status === "ALREADY_USED") {
    // FRAUD / DUPLICATE
    overlay.classList.add("result-used");
    badge.innerHTML = "❌ ¡ALERTA! ENTRADA YA USADA";
    tNum.innerText = `ENTRADA #${String(data.ticket.ticket_number).padStart(3, "0")}`;
    name.innerText = `${data.ticket.name} ${data.ticket.surname}`;
    dni.innerText = data.ticket.dni;
    extra.innerHTML = `
      <div style="color: #fca5a5; font-weight: 800; font-size: 14px;">
        ⚠️ YA FUE ESCANEADA PREVIAMENTE A LAS: ${data.ticket.used_at || "hora previa"}
      </div>
      <div style="margin-top: 6px; color: #fff;">¡No permitir acceso con duplicado!</div>
    `;
    playErrorSound();
    if (navigator.vibrate) navigator.vibrate([200, 100, 200]);
  } else {
    // INVALID / NOT FOUND / CANCELLED
    overlay.classList.add("result-error");
    badge.innerHTML = "❌ ENTRADA INVÁLIDA";
    tNum.innerText = "NO AUTORIZADO";
    name.innerText = data.ticket ? `${data.ticket.name} ${data.ticket.surname}` : "Desconocido";
    dni.innerText = data.ticket ? data.ticket.dni : "---";
    extra.innerHTML = `<div style="color: #fca5a5; font-weight: bold;">${data.message}</div>`;
    playErrorSound();
    if (navigator.vibrate) navigator.vibrate([300, 100, 300]);
  }

  overlay.style.display = "flex";
  updateStats();

  // Auto resume after 3.8 seconds
  clearTimeout(autoResumeTimeout);
  autoResumeTimeout = setTimeout(() => {
    resumeScanning();
  }, 3800);
}

function resumeScanning() {
  clearTimeout(autoResumeTimeout);
  const overlay = document.getElementById("resultOverlay");
  overlay.style.display = "none";
  isScanning = true;
  if (currentStream) {
    requestAnimationFrame(scanTick);
  }
}

// Manual form submission
function handleManualSubmit(e) {
  e.preventDefault();
  const input = document.getElementById("manualInput");
  const val = input.value.trim();
  if (!val) return;
  input.value = "";
  input.blur();
  isScanning = false;
  validateCode(val);
}

// Hardware Barcode Scanner (Pistola lectora láser / PDA) Support
// Industrial scanners type input rapidly like a keyboard and send 'Enter'
let scannerBuffer = "";
let lastKeyTime = Date.now();

window.addEventListener("keydown", (e) => {
  // If user is intentionally typing in the manual input, let standard typing work
  if (e.target.id === "manualInput") return;

  const now = Date.now();
  if (now - lastKeyTime > 150) {
    scannerBuffer = "";
  }
  lastKeyTime = now;

  if (e.key === "Enter") {
    if (scannerBuffer.length >= 3) {
      e.preventDefault();
      onCodeDetected(scannerBuffer.trim());
      scannerBuffer = "";
    }
  } else if (e.key.length === 1) {
    scannerBuffer += e.key;
  }
});

// Periodically update capacity
async function updateStats() {
  try {
    const res = await fetch("/api/stats");
    const data = await res.json();
    document.getElementById("statCheckedIn").innerText = `${data.checked_in} / ${data.max_capacity}`;
  } catch (e) {}
}

function checkDoorAccess() {
  const pin = typeof EXPECTED_DOOR_PIN !== 'undefined' ? EXPECTED_DOOR_PIN : "puerta";
  const params = new URLSearchParams(window.location.search);
  const pinParam = params.get("pin");
  if (pinParam === pin) {
    sessionStorage.setItem("door_auth", pin);
    const lock = document.getElementById("doorLockScreen");
    if (lock) lock.style.display = "none";
    return true;
  }
  if (sessionStorage.getItem("door_auth") === pin) {
    const lock = document.getElementById("doorLockScreen");
    if (lock) lock.style.display = "none";
    return true;
  }
  const lock = document.getElementById("doorLockScreen");
  if (lock) lock.style.display = "flex";
  return false;
}

function handleDoorPinSubmit(e) {
  e.preventDefault();
  const pin = typeof EXPECTED_DOOR_PIN !== 'undefined' ? EXPECTED_DOOR_PIN : "puerta";
  const input = document.getElementById("doorPinInput");
  const val = input.value.trim();
  if (val === pin) {
    sessionStorage.setItem("door_auth", pin);
    document.getElementById("doorLockScreen").style.display = "none";
    startCamera();
  } else {
    document.getElementById("doorPinError").style.display = "block";
    input.value = "";
    input.focus();
  }
}

window.addEventListener("DOMContentLoaded", () => {
  if (checkDoorAccess()) {
    startCamera();
  }
  updateStats();
  setInterval(updateStats, 15000);
});
