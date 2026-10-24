"""
Email notification service for Fiesta Fin de Año tickets.
Sends HTML tickets with embedded QR code via standard SMTP with fallback to preview/simulation.
"""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import parseaddr, formataddr
import logging

def format_ticket_email_html(ticket, settings, base_url):
    ticket_url = f"{base_url}/ticket/{ticket['code']}"
    
    event_name = settings.get("event_name", "Gran Fiesta Fin de Año 2026")
    event_date = settings.get("event_date", "31 de Diciembre de 2026")
    event_time = settings.get("event_time", "A partir de las 23:30 h")
    event_venue = settings.get("event_venue", "Sala Privada")
    poster_url = settings.get("poster_url", "").strip()
    
    poster_html = ""
    if poster_url:
        full_poster_url = poster_url if poster_url.startswith("http") else f"{base_url}{poster_url}"
        poster_html = f'<div style="width: 100%; max-height: 240px; overflow: hidden; background: #000; text-align: center;"><img src="{full_poster_url}" alt="Cartel Oficial" style="width: 100%; max-height: 240px; object-fit: cover; display: block;"></div>'
    
    qr_image_url = f"https://api.qrserver.com/v1/create-qr-code/?size=240x240&data={ticket['code']}"

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Tu Entrada - {event_name}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #0b0f19; color: #f3f4f6; margin: 0; padding: 20px; }}
  .card {{ max-width: 520px; margin: 0 auto; background: #111827; border: 1px solid #374151; border-radius: 18px; overflow: hidden; box-shadow: 0 15px 35px rgba(0,0,0,0.6); }}
  .header {{ background: linear-gradient(135deg, #1f2937, #111827); padding: 25px 20px; text-align: center; color: #fff; border-bottom: 2px dashed #f59e0b; }}
  .header h1 {{ margin: 0; font-size: 22px; text-transform: uppercase; letter-spacing: 1.5px; color: #ffffff; }}
  .header p {{ margin: 6px 0 0 0; color: #fbbf24; font-size: 14px; font-weight: 600; }}
  .ticket-badge {{ display: inline-block; background: rgba(245, 158, 11, 0.2); border: 1px solid #f59e0b; color: #fef08a; padding: 5px 14px; border-radius: 20px; font-weight: bold; margin-top: 10px; font-size: 14px; letter-spacing: 1px; }}
  .content {{ padding: 24px; }}
  .details-box {{ background: #1a2233; border: 1px solid #2d3748; border-radius: 14px; padding: 18px; margin-bottom: 20px; }}
  .detail-row {{ margin-bottom: 12px; }}
  .detail-row:last-child {{ margin-bottom: 0; }}
  .label {{ font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; color: #9ca3af; font-weight: 600; }}
  .value {{ font-size: 16px; font-weight: bold; color: #f9fafb; margin-top: 2px; }}
  .dni-highlight {{ color: #fbbf24; font-size: 19px; font-family: monospace; letter-spacing: 1px; }}
  
  .qr-box {{ background: #ffffff; padding: 18px; border-radius: 16px; text-align: center; margin: 20px auto; max-width: 250px; box-shadow: 0 4px 15px rgba(0,0,0,0.4); }}
  .qr-box img {{ display: block; margin: 0 auto; width: 220px; height: 220px; }}
  .qr-code-text {{ color: #111827; font-size: 11px; font-family: monospace; font-weight: bold; margin-top: 8px; letter-spacing: 1px; }}
  
  .btn-container {{ text-align: center; margin: 22px 0 10px 0; }}
  .btn {{ display: inline-block; background: linear-gradient(135deg, #f59e0b, #d97706); color: #000000; text-decoration: none; padding: 13px 26px; border-radius: 10px; font-weight: 800; font-size: 15px; text-transform: uppercase; letter-spacing: 0.5px; }}
  .security-box {{ background: rgba(239, 68, 68, 0.08); border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 12px; padding: 14px; margin-top: 22px; text-align: left; }}
  .security-box strong {{ color: #ffffff; display: block; margin-bottom: 4px; font-size: 12px; }}
  .security-box p {{ margin: 0; font-size: 11px; line-height: 1.5; color: #fca5a5; }}
  .footer {{ text-align: center; font-size: 11px; color: #6b7280; padding: 18px; border-top: 1px solid #1f2937; }}
</style>
</head>
<body>
  <div class="card">
    {poster_html}
    <div class="header">
      <h1>🍾 {event_name}</h1>
      <p>📅 {event_date} • ⏰ {event_time}</p>
      <div class="ticket-badge">ENTRADA NOMINAL Nº #{ticket['ticket_number']:03d}</div>
    </div>
    
    <div class="content">
      <div class="details-box">
        <div class="detail-row">
          <div class="label">Titular de la Entrada</div>
          <div class="value">{ticket['name']} {ticket['surname']}</div>
        </div>
        <div class="detail-row">
          <div class="label">DNI / Documento de Identidad (Nominal)</div>
          <div class="value dni-highlight">{ticket['dni']}</div>
        </div>
        <div class="detail-row">
          <div class="label">Lugar del Evento</div>
          <div class="value">{event_venue}</div>
        </div>
        {f'<div class="detail-row"><div class="label">Observaciones</div><div class="value" style="font-size:13px; color:#d1d5db;">{ticket["notes"]}</div></div>' if ticket.get("notes") else ""}
      </div>
      
      <!-- CÓDIGO QR DIRECTAMENTE VISIBLE EN EL EMAIL -->
      <div class="qr-box">
        <img src="{qr_image_url}" alt="Código QR de Acceso">
        <div class="qr-code-text">{ticket['code']}</div>
      </div>
      <p style="text-align: center; font-size: 12px; color: #9ca3af; margin: 4px 0 16px 0;">
        Presenta este código QR desde tu correo en la puerta del evento.
      </p>

      <div class="btn-container">
        <a href="{ticket_url}" class="btn" target="_blank">📱 Ver Entrada Digital Completa</a>
      </div>
      
      <div class="security-box">
        <strong>⚠️ AVISO IMPORTANTE DE SEGURIDAD EN PUERTA:</strong>
        <p>
          1. Esta entrada es <strong>estrictamente nominal e intransferible</strong>.<br>
          2. En la puerta será <strong>obligatorio mostrar el DNI físico original</strong> del titular.<br>
          3. Cada código QR sólo permite un único escaneo de acceso.
        </p>
      </div>
    </div>
    
    <div class="footer">
      Organización de {event_name} • Entrada Nº #{ticket['ticket_number']:03d}
    </div>
  </div>
</body>
</html>"""
    return html


def connect_smtp(smtp_host, smtp_port, smtp_user, smtp_pass):
    """
    Connects to SMTP supporting both SSL (port 465) and STARTTLS (port 587/25).
    Cleans credentials and strips internal spaces from Google App Passwords.
    """
    clean_user = smtp_user.strip()
    clean_pass = smtp_pass.strip().replace(" ", "")

    if smtp_port == 465:
        server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=14)
    else:
        server = smtplib.SMTP(smtp_host, smtp_port, timeout=14)
        server.ehlo()
        try:
            server.starttls()
            server.ehlo()
        except Exception:
            pass

    if clean_user and clean_pass:
        server.login(clean_user, clean_pass)

    return server


def send_ticket_email(ticket, settings, base_url):
    """
    Sends the ticket with QR directly to the buyer's email address.
    Correctly resolves display name and envelope sender to prevent RFC syntax errors.
    """
    smtp_host = settings.get("smtp_host", "").strip()
    smtp_port = int(settings.get("smtp_port", "587") or "587")
    smtp_user = settings.get("smtp_user", "").strip()
    smtp_pass = settings.get("smtp_pass", "").strip()
    raw_from = settings.get("smtp_from", "").strip()
    
    event_name = settings.get("event_name", "Gran Fiesta Fin de Año 2026")
    subject = f"🍾 Tu Entrada para {event_name} (Nº #{ticket['ticket_number']:03d}) - {ticket['name']} {ticket['surname']}"
    
    html_content = format_ticket_email_html(ticket, settings, base_url)
    
    if not smtp_host or not smtp_user:
        return (False, "Servidor SMTP no configurado. Puedes configurarlo en ⚙️ Configuración para envíos automáticos.")
        
    try:
        # Robustly resolve From display name and RFC envelope email
        if "@" not in raw_from:
            # User provided a name like 'COL.LECTIU ARESTA'
            display_name = raw_from if raw_from else event_name
            envelope_from = smtp_user
        else:
            name_part, addr_part = parseaddr(raw_from)
            display_name = name_part if name_part else event_name
            envelope_from = addr_part if addr_part else smtp_user

        formatted_from = formataddr((display_name, envelope_from))

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = formatted_from
        msg["To"] = ticket["email"]
        
        text_content = f"""Hola {ticket['name']},\n\nAquí tienes tu entrada oficial para {event_name}.\n\nNº Entrada: #{ticket['ticket_number']:03d}\nTitular: {ticket['name']} {ticket['surname']}\nDNI: {ticket['dni']}\nCódigo QR: {base_url}/ticket/{ticket['code']}\n\nRecuerda presentar tu DNI físico en la puerta.\n\nOrganización."""
        
        msg.attach(MIMEText(text_content, "plain", "utf-8"))
        msg.attach(MIMEText(html_content, "html", "utf-8"))
        
        server = connect_smtp(smtp_host, smtp_port, smtp_user, smtp_pass)
        server.sendmail(envelope_from, [ticket["email"]], msg.as_string())
        server.quit()
        
        return (True, f"Email enviado con éxito a {ticket['email']}")
    except smtplib.SMTPAuthenticationError as auth_err:
        logging.error(f"Error de autenticación SMTP: {auth_err}")
        return (False, "Google rechazó la contraseña. En Gmail es obligatorio activar la 'Verificación en dos pasos' y generar una 'Contraseña de aplicación' de 16 letras en myaccount.google.com/apppasswords")
    except smtplib.SMTPSenderRefused as send_err:
        logging.error(f"Remitente rechazado: {send_err}")
        return (False, f"El servidor rechazó el remitente: {send_err}")
    except Exception as e:
        logging.error(f"Error al enviar email: {e}")
        return (False, f"Error al conectar con el servidor de correo: {str(e)}")


def send_test_email(recipient_email, settings, base_url):
    """
    Sends a test verification email to confirm the organizer's SMTP credentials.
    """
    test_ticket = {
        "id": 0,
        "ticket_number": 1,
        "code": "NYE-PRUEBA-001",
        "name": "Prueba",
        "surname": "Organizador",
        "dni": "00000000T",
        "email": recipient_email,
        "notes": "Entrada de prueba del sistema de correo"
    }
    return send_ticket_email(test_ticket, settings, base_url)
