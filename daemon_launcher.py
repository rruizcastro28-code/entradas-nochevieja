#!/usr/bin/env python3
"""
Lanzador en Segundo Plano Real (Desacoplado de Terminal).
Usa setsid / start_new_session para que el servidor y el túnel sigan vivos
aunque cierres el Terminal por completo.
"""

import os
import sys
import subprocess
import time
import re
import signal

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLOUDFLARED_BIN = os.path.join(BASE_DIR, "cloudflared")
SERVER_PY = os.path.join(BASE_DIR, "server.py")
TUNNEL_LOG = os.path.join(BASE_DIR, "tunnel.log")
SERVER_LOG = os.path.join(BASE_DIR, "server.log")
ENLACE_TXT = os.path.join(BASE_DIR, "TU_ENLACE.txt")
PORT_FILE = os.path.join(BASE_DIR, ".active_port")

def kill_previous():
    subprocess.run(["pkill", "-f", "server.py"], stderr=subprocess.DEVNULL)
    subprocess.run(["pkill", "-f", "cloudflared"], stderr=subprocess.DEVNULL)
    for f in [TUNNEL_LOG, SERVER_LOG, PORT_FILE]:
        if os.path.exists(f):
            try:
                os.remove(f)
            except Exception:
                pass
    time.sleep(1)

def main():
    print("=================================================================")
    print("🚀 ARRANCANDO EN SEGUNDO PLANO PERMANENTE")
    print("=================================================================")
    print("1. Limpiando procesos anteriores...")
    kill_previous()

    print("2. Iniciando servidor web (desacoplado)...")
    with open(SERVER_LOG, "w") as s_log:
        server_proc = subprocess.Popen(
            [sys.executable, SERVER_PY, "8000"],
            cwd=BASE_DIR,
            stdin=subprocess.DEVNULL,
            stdout=s_log,
            stderr=subprocess.STDOUT,
            start_new_session=True  # DESACOPLE TOTAL DEL TERMINAL
        )

    time.sleep(1.2)
    active_port = "8000"
    if os.path.exists(PORT_FILE):
        try:
            with open(PORT_FILE) as f:
                active_port = f.read().strip()
        except Exception:
            pass

    print(f"3. Conectando Cloudflare Tunnel al puerto {active_port}...")
    tunnel_proc = subprocess.Popen(
        [CLOUDFLARED_BIN, "tunnel", "--url", f"http://127.0.0.1:{active_port}", "--logfile", TUNNEL_LOG],
        cwd=BASE_DIR,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True  # DESACOPLE TOTAL DEL TERMINAL
    )

    print("4. Esperando tu enlace seguro mundial (espera unos segundos)...")
    url_pattern = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")
    public_url = None

    for _ in range(30):
        time.sleep(0.8)
        if os.path.exists(TUNNEL_LOG):
            try:
                with open(TUNNEL_LOG, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    match = url_pattern.search(content)
                    if match:
                        public_url = match.group(0)
                        break
            except Exception:
                pass
        sys.stdout.write(".")
        sys.stdout.flush()

    print()

    if not public_url:
        print("⚠️ Hubo una demora al conectar con Cloudflare. Revisa tu internet y vuelve a intentar.")
        sys.exit(1)

    taquilla_url = f"{public_url}/?pin=2026"
    scanner_url = f"{public_url}/scanner?pin=puerta"

    # Escribir archivo TU_ENLACE.txt
    with open(ENLACE_TXT, "w", encoding="utf-8") as f:
        f.write(f"""=================================================================
🍾 ENLACES OFICIALES - CAP ANY SENSE CASA 2026
=================================================================

👉 TU PANEL DE TAQUILLA (Para ti y organizadores):
   {taquilla_url}

👉 ENLACE PARA LOS PORTEROS (Para el personal de seguridad):
   {scanner_url}

=================================================================
✅ LA APLICACIÓN YA ESTÁ CORRIENDO EN SEGUNDO PLANO DE TU MAC.
PUEDES CERRAR LA VENTANA DE TERMINAL POR COMPLETO.

Los enlaces seguirán funcionando mientras tu Mac esté encendido.
Para apagar la aplicación cuando termine el evento, ejecuta:
./detener.sh
=================================================================
""")

    print("=" * 65)
    print("🎉 ¡SISTEMA ACTIVO EN SEGUNDO PLANO!")
    print("=" * 65)
    print(f"👉 TU TAQUILLA:")
    print(f"   {taquilla_url}")
    print()
    print(f"👉 ESCÁNER PORTEROS:")
    print(f"   {scanner_url}")
    print("=" * 65)
    print("✅ YA PUEDES CERRAR ESTA VENTANA DE TERMINAL.")
    print("   El servidor sigue funcionando en segundo plano de tu Mac.")
    print("=" * 65)

    # Abrir el archivo en pantalla
    subprocess.run(["open", ENLACE_TXT], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

if __name__ == "__main__":
    main()
