#!/usr/bin/env python3
"""
Lanzador del Servidor de Entradas con Enlace Público Seguro (Cloudflare Tunnel).
Genera una URL https://*.trycloudflare.com accesible desde cualquier móvil o PC en el mundo.
"""

import os
import sys
import subprocess
import re
import time
import signal

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLOUDFLARED_BIN = os.path.join(BASE_DIR, "cloudflared")
SERVER_PY = os.path.join(BASE_DIR, "server.py")

def main():
    if not os.path.exists(CLOUDFLARED_BIN):
        print("❌ Error: No se encontró el ejecutable cloudflared en la carpeta.")
        sys.exit(1)

    print("=================================================================")
    print("🍾 INICIANDO SISTEMA CON ENLACE PÚBLICO SEGURO (HTTPS) 🍾")
    print("=================================================================")
    print("1. Arrancando servidor local en puerto 8000...")
    
    server_proc = subprocess.Popen(
        [sys.executable, SERVER_PY, "8000"],
        cwd=BASE_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )

    time.sleep(1.2)
    active_port = "8000"
    port_file = os.path.join(BASE_DIR, ".active_port")
    if os.path.exists(port_file):
        try:
            with open(port_file) as f:
                active_port = f.read().strip()
        except Exception:
            pass

    print(f"2. Generando enlace seguro mundial con Cloudflare Tunnel (puerto {active_port})...")
    log_file = os.path.join(BASE_DIR, "tunnel.log")
    if os.path.exists(log_file):
        os.remove(log_file)

    tunnel_proc = subprocess.Popen(
        [CLOUDFLARED_BIN, "tunnel", "--url", f"http://127.0.0.1:{active_port}", "--logfile", log_file],
        cwd=BASE_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    public_url = None
    url_pattern = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")

    # Check log file until URL is generated
    start_time = time.time()
    while time.time() - start_time < 25:
        time.sleep(0.6)
        if os.path.exists(log_file):
            try:
                with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    match = url_pattern.search(content)
                    if match:
                        public_url = match.group(0)
                        break
            except Exception:
                pass

    if not public_url:
        print("⚠️ No se pudo obtener la URL automáticamente. Revisa tu conexión a internet.")
        server_proc.terminate()
        tunnel_proc.terminate()
        sys.exit(1)

    taquilla_url = f"{public_url}/?pin=2026"
    scanner_url = f"{public_url}/scanner?pin=puerta"

    # Save to TU_ENLACE.txt
    enlace_path = os.path.join(BASE_DIR, "TU_ENLACE.txt")
    with open(enlace_path, "w", encoding="utf-8") as f:
        f.write(f"""=================================================================
🍾 ENLACES OFICIALES - CAP ANY SENSE CASA 2026
=================================================================

👉 TU PANEL DE TAQUILLA (Para ti y organizadores):
   {taquilla_url}

👉 ENLACE PARA LOS PORTEROS (Para el personal de seguridad):
   {scanner_url}

=================================================================
✅ La aplicación está en ejecución.
Para detenerla cuando termine el evento, ejecuta: ./detener.sh
=================================================================
""")

    print("\n" + "=" * 65)
    print("🚀 ¡SISTEMA ONLINE Y ACCESIBLE DESDE CUALQUIER LUGAR DEL MUNDO!")
    print("=" * 65)
    print(f"👉 TU PANEL DE CONTROL (Taquilla / Ventas):")
    print(f"   {taquilla_url}")
    print()
    print(f"👉 ENLACE PARA LOS PORTEROS / SEGURIDAD (Escáner de Puerta):")
    print(f"   {scanner_url}")
    print("=" * 65)
    print("💡 Se ha guardado una copia de tus enlaces en: TU_ENLACE.txt")
    print("Presiona Ctrl+C en cualquier momento para apagar el servidor.\n")

    subprocess.run(["open", enlace_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def shutdown(sig, frame):
        print("\nApagando túnel y servidor...")
        tunnel_proc.terminate()
        server_proc.terminate()
        print("¡Listo! Servidor detenido.")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Keep running and printing logs if needed
    try:
        while True:
            time.sleep(1)
            if server_proc.poll() is not None:
                print("El servidor local se cerró inesperadamente.")
                break
            if tunnel_proc.poll() is not None:
                print("El túnel se cerró inesperadamente.")
                break
    except KeyboardInterrupt:
        shutdown(None, None)

if __name__ == "__main__":
    main()
