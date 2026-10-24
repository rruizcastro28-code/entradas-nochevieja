#!/usr/bin/env python3
"""
Fiesta Fin de Año - Sistema de Venta de Entradas Nominales y Control de Acceso.
Zero-dependency, pure Python 3 web server.
"""

import os
import sys
import json
import socket
import urllib.parse
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import re
import csv
import io

import database
import email_service

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

# Helper class for dot notation in templates
class DictObj:
    def __init__(self, d):
        for k, v in d.items():
            if isinstance(v, dict):
                setattr(self, k, DictObj(v))
            else:
                setattr(self, k, v)
    def __getitem__(self, key):
        return getattr(self, key)
    def get(self, key, default=None):
        return getattr(self, key, default)

def render_template(template_name, context=None):
    if context is None:
        context = {}
    
    # Wrap dicts for attribute access
    wrapped_context = {}
    for k, v in context.items():
        if isinstance(v, dict):
            wrapped_context[k] = DictObj(v)
        else:
            wrapped_context[k] = v

    filepath = os.path.join(TEMPLATES_DIR, template_name)
    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()

    # Process if/elif/else blocks
    pattern = re.compile(r'{%\s*if\s+(.*?)\s*%}(.*?){%\s*endif\s*%}', re.DOTALL)
    
    def eval_if(m):
        cond_str = m.group(1).strip()
        body = m.group(2)
        parts = re.split(r'{%\s*(elif\s+.*?|else)\s*%}', body)
        
        try:
            val = eval(cond_str, {}, wrapped_context)
        except Exception:
            val = False
            
        if val:
            return parts[0]
            
        i = 1
        while i < len(parts):
            tag = parts[i].strip()
            subbody = parts[i+1] if i+1 < len(parts) else ''
            if tag == 'else':
                return subbody
            elif tag.startswith('elif'):
                elif_cond = tag[4:].strip()
                try:
                    if eval(elif_cond, {}, wrapped_context):
                        return subbody
                except Exception:
                    pass
            i += 2
        return ''

    while '{% if' in text:
        new_text = pattern.sub(eval_if, text)
        if new_text == text:
            break
        text = new_text

    # Process variables {{ ... }}
    var_pattern = re.compile(r'{{\s*(.*?)\s*}}')
    def eval_var(m):
        expr = m.group(1).strip()
        if '|format(' in expr:
            try:
                fmt, arg = expr.split('|format(')
                fmt = eval(fmt)
                arg = arg.rstrip(')')
                val = eval(arg, {}, wrapped_context)
                return fmt % val
            except Exception:
                return ''
        try:
            val = eval(expr, {}, wrapped_context)
            return str(val) if val is not None else ''
        except Exception:
            return ''

    return var_pattern.sub(eval_var, text)


class AppRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Clean logging
        sys.stderr.write(f"[{self.log_date_time_string()}] {self.command} {self.path} -> {args[0]}\n")

    def get_base_url(self):
        host = self.headers.get("Host") or "localhost:8000"
        return f"http://{host}"

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def send_html(self, html_str, status=200):
        body = html_str.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # 1. Static Files
        if path.startswith("/static/"):
            filename = os.path.basename(path)
            filepath = os.path.join(STATIC_DIR, filename)
            if os.path.isfile(filepath):
                ext = os.path.splitext(filename)[1].lower()
                mime_map = {
                    ".js": "application/javascript",
                    ".css": "text/css",
                    ".html": "text/html",
                    ".png": "image/png",
                    ".jpg": "image/jpeg",
                    ".svg": "image/svg+xml",
                    ".ico": "image/x-icon"
                }
                mime = mime_map.get(ext, "application/octet-stream")
                with open(filepath, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", mime)
                self.send_header("Content-Length", str(len(content)))
                self.send_header("Cache-Control", "public, max-age=3600")
                self.end_headers()
                self.wfile.write(content)
                return
            else:
                self.send_error(404, "Archivo estático no encontrado")
                return

        # 2. Main Page: Admin / Taquilla
        if path == "/" or path == "/admin":
            settings = database.get_settings()
            html = render_template("index.html", {"settings": settings})
            self.send_html(html)
            return

        # 3. Door Scanner
        if path == "/scanner":
            settings = database.get_settings()
            html = render_template("scanner.html", {"settings": settings})
            self.send_html(html)
            return

        # 4. View Nominal Ticket
        if path.startswith("/ticket/"):
            code_or_id = path[len("/ticket/"):].strip()
            ticket = database.get_ticket_by_code_or_id(code_or_id)
            if not ticket:
                self.send_html("<h1>Entrada no encontrada</h1><p>El código proporcionado no corresponde a ninguna entrada válida.</p>", status=404)
                return
            settings = database.get_settings()
            html = render_template("ticket.html", {"ticket": ticket, "settings": settings})
            self.send_html(html)
            return

        # 5. API: Stats
        if path == "/api/stats":
            stats = database.get_stats()
            self.send_json(stats)
            return

        # 6. API: Get Tickets list
        if path == "/api/tickets":
            search = query.get("search", [""])[0]
            status = query.get("status", ["ALL"])[0]
            tickets = database.get_tickets(search=search, status=status)
            self.send_json(tickets)
            return

        # 7. API: Check DNI
        if path == "/api/check-dni":
            dni = query.get("dni", [""])[0]
            existing = database.check_dni_exists(dni)
            self.send_json({
                "exists": len(existing) > 0,
                "tickets": existing
            })
            return

        # 8. API: Export CSV
        if path == "/api/export-csv":
            tickets = database.get_tickets()
            output = io.StringIO()
            # UTF-8 BOM so Excel opens with proper accents
            output.write('\ufeff')
            writer = csv.writer(output, delimiter=';')
            writer.writerow([
                "Nº Entrada", "Nombre", "Apellidos", "DNI", "Email",
                "Teléfono", "Precio (€)", "Método de Pago", "Estado",
                "Fecha de Emisión", "Hora Acceso Puerta", "Observaciones", "Código Seguro"
            ])
            for t in tickets:
                writer.writerow([
                    f"#{t['ticket_number']:03d}",
                    t['name'],
                    t['surname'],
                    t['dni'],
                    t['email'],
                    t['phone'],
                    f"{t['price']:.2f}",
                    t['payment_method'],
                    t['status'],
                    t['created_at'],
                    t['used_at'] or "",
                    t['notes'],
                    t['code']
                ])
            csv_bytes = output.getvalue().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition", 'attachment; filename="asistentes_nochevieja_2026.csv"')
            self.send_header("Content-Length", str(len(csv_bytes)))
            self.end_headers()
            self.wfile.write(csv_bytes)
            return

        self.send_error(404, "Página no encontrada")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        content_len = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else "{}"
        try:
            body = json.loads(post_data)
        except Exception:
            body = {}

        # 1. API: Create Ticket
        if path == "/api/tickets":
            try:
                name = body.get("name", "").strip()
                surname = body.get("surname", "").strip()
                dni = body.get("dni", "").strip()
                email = body.get("email", "").strip()
                phone = body.get("phone", "").strip()
                price = float(body.get("price", 0.0))
                payment_method = body.get("payment_method", "Efectivo")
                notes = body.get("notes", "").strip()

                if not name or not surname or not dni or not email:
                    self.send_json({"error": True, "message": "Faltan campos obligatorios (Nombre, Apellidos, DNI, Email)"}, status=400)
                    return

                new_ticket = database.create_ticket(
                    name=name,
                    surname=surname,
                    dni=dni,
                    email=email,
                    phone=phone,
                    price=price,
                    payment_method=payment_method,
                    notes=notes
                )

                # Attempt email sending
                settings = database.get_settings()
                base_url = self.get_base_url()
                sent, email_msg = email_service.send_ticket_email(new_ticket, settings, base_url)

                self.send_json({
                    "success": True,
                    "ticket": new_ticket,
                    "email_status": {
                        "sent": sent,
                        "message": email_msg
                    }
                })
            except ValueError as ve:
                self.send_json({"error": True, "message": str(ve)}, status=400)
            except Exception as e:
                self.send_json({"error": True, "message": f"Error al emitir entrada: {str(e)}"}, status=500)
            return

        # 2. API: Validate Door Scan
        if path == "/api/validate":
            code = body.get("code", "").strip()
            if not code:
                self.send_json({"status": "ERROR", "message": "Código vacío", "ticket": None}, status=400)
                return

            status, ticket, msg = database.validate_ticket_scan(code)
            self.send_json({
                "status": status,
                "ticket": ticket,
                "message": msg
            })
            return

        # 3. API: Reset or Cancel Ticket Status
        if path == "/api/reset-status":
            ticket_id = body.get("ticket_id")
            new_status = body.get("new_status", "VALIDA")
            if not ticket_id:
                self.send_json({"error": True, "message": "ID de entrada requerido"}, status=400)
                return
            database.reset_ticket_status(ticket_id, new_status)
            self.send_json({"success": True})
            return

        # 4. API: Update Settings
        if path == "/api/settings":
            database.update_settings(body)
            self.send_json({"success": True})
            return

        # 5. API: Upload Poster Image
        if path == "/api/upload-poster":
            try:
                img_data_str = body.get("image_data", "")
                if not img_data_str:
                    self.send_json({"error": True, "message": "Datos de imagen vacíos"}, status=400)
                    return
                if "," in img_data_str:
                    _, b64_str = img_data_str.split(",", 1)
                else:
                    b64_str = img_data_str
                import base64
                img_bytes = base64.b64decode(b64_str)
                poster_path = os.path.join(STATIC_DIR, "cartel.jpg")
                with open(poster_path, "wb") as f:
                    f.write(img_bytes)
                database.update_settings({"poster_url": "/static/cartel.jpg"})
                self.send_json({"success": True, "poster_url": "/static/cartel.jpg"})
            except Exception as e:
                self.send_json({"error": True, "message": str(e)}, status=500)
            return

        # 6. API: Test Email
        if path == "/api/test-email":
            try:
                recipient = body.get("recipient", "").strip()
                if not recipient:
                    self.send_json({"error": True, "message": "Email de prueba requerido"}, status=400)
                    return
                settings = database.get_settings()
                base_url = self.get_base_url()
                sent, msg = email_service.send_test_email(recipient, settings, base_url)
                self.send_json({"success": sent, "message": msg})
            except Exception as e:
                self.send_json({"error": True, "message": str(e)}, status=500)
            return

        self.send_error(404, "Endpoint no encontrado")


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def generate_ssl_cert(cert_file, key_file):
    import subprocess
    cmd = [
        "openssl", "req", "-x509", "-newkey", "rsa:2048",
        "-keyout", key_file, "-out", cert_file,
        "-days", "365", "-nodes",
        "-subj", "/CN=localhost"
    ]
    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True
    except Exception:
        return False


def main():
    database.init_db()
    # Check environment variable for Cloud hosting (Render, Railway, etc.)
    env_port = os.environ.get("PORT")
    port = int(env_port) if env_port and env_port.isdigit() else 8000
    use_https = "--https" in sys.argv

    for arg in sys.argv[1:]:
        if arg.isdigit():
            port = int(arg)

    ThreadingHTTPServer.allow_reuse_address = True

    # Try binding, with graceful fallback to alternative ports if busy
    server = None
    candidate_ports = [port] + [8080, 8001, 8002, 8888, 9000] if not env_port else [port]
    for p in candidate_ports:
        try:
            server = ThreadingHTTPServer(("0.0.0.0", p), AppRequestHandler)
            port = p
            break
        except OSError as e:
            if p == candidate_ports[-1]:
                print(f"❌ Error al iniciar servidor: {e}")
                sys.exit(1)
            continue

    # Write active port to file for tunnel synchronization
    with open(os.path.join(BASE_DIR, ".active_port"), "w") as f:
        f.write(str(port))

    local_ip = get_local_ip()
    protocol = "http"

    if use_https:
        cert_file = os.path.join(BASE_DIR, "cert.pem")
        key_file = os.path.join(BASE_DIR, "key.pem")
        if not (os.path.exists(cert_file) and os.path.exists(key_file)):
            generate_ssl_cert(cert_file, key_file)
        if os.path.exists(cert_file) and os.path.exists(key_file):
            import ssl
            ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            ctx.load_cert_chain(certfile=cert_file, keyfile=key_file)
            server.socket = ctx.wrap_socket(server.socket, server_side=True)
            protocol = "https"

    print("=" * 65)
    print("🍾 SISTEMA DE ENTRADAS Y CONTROL DE ACCESO - FIN DE AÑO 🍾")
    print("=" * 65)
    print(f"👉 Panel de Taquilla / Ventas:    {protocol}://localhost:{port}/")
    print(f"👉 Escáner de Puerta (Móvil):     {protocol}://{local_ip}:{port}/scanner")
    print("-" * 65)
    print("Dispositivos en la misma red Wi-Fi pueden abrir el escáner")
    print(f"directamente entrando a: {protocol}://{local_ip}:{port}/scanner")
    if not use_https:
        print("💡 Tip: Para activar HTTPS en red local ejecuta: ./iniciar.sh --https")
    print("=" * 65)
    print("Presiona Ctrl+C para detener el servidor.\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")
        server.server_close()


if __name__ == "__main__":
    main()
