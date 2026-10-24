#!/bin/bash
# Arranca el servidor y el túnel en segundo plano para poder cerrar el Terminal
cd "$(dirname "$0")"

echo "=========================================================="
echo "🚀 INICIANDO EN SEGUNDO PLANO (PUEDES CERRAR EL TERMINAL)"
echo "=========================================================="

# 1. Detener procesos anteriores si los hubiera
./detener.sh >/dev/null 2>&1
rm -f tunnel.log server.log .active_port

# 2. Arrancar servidor web local en segundo plano
nohup python3 server.py 8000 > server.log 2>&1 &
sleep 1

# Leer el puerto activo
ACTIVE_PORT=8000
if [ -f .active_port ]; then
  ACTIVE_PORT=$(cat .active_port)
fi

echo "1. Servidor web iniciado en puerto $ACTIVE_PORT."
echo "2. Conectando con la red segura mundial de Cloudflare..."

# 3. Arrancar cloudflared en segundo plano con log directo
nohup ./cloudflared tunnel --url "http://127.0.0.1:$ACTIVE_PORT" --logfile tunnel.log > /dev/null 2>&1 &

# 4. Esperar a que aparezca la URL en tunnel.log
PUBLIC_URL=""
for i in {1..25}; do
  sleep 1
  if [ -f tunnel.log ]; then
    PUBLIC_URL=$(grep -oE "https://[a-zA-Z0-9-]+\.trycloudflare\.com" tunnel.log | head -n 1)
    if [ -n "$PUBLIC_URL" ]; then
      break
    fi
  fi
  printf "."
done
echo ""

if [ -z "$PUBLIC_URL" ]; then
  echo ""
  echo "⚠️ El túnel está tardando un poco más de lo habitual en responder."
  echo "Mostrando últimos registros del túnel:"
  tail -n 10 tunnel.log 2>/dev/null
  echo ""
  echo "👉 Prueba ejecutando en primer plano: ./iniciar_publico.sh"
  exit 1
fi

# 5. Guardar enlaces en TU_ENLACE.txt
cat << EOF > TU_ENLACE.txt
=================================================================
🍾 ENLACES OFICIALES - CAP ANY SENSE CASA 2026
=================================================================

👉 TU PANEL DE TAQUILLA (Para ti y organizadores):
   $PUBLIC_URL/?pin=2026

👉 ENLACE PARA LOS PORTEROS (Para el personal de seguridad):
   $PUBLIC_URL/scanner?pin=puerta

=================================================================
✅ LA APLICACIÓN YA ESTÁ CORRIENDO EN SEGUNDO PLANO.
PUEDES CERRAR LA VENTANA DE TERMINAL.

Para apagar la aplicación cuando termine el evento, ejecuta:
./detener.sh
=================================================================
EOF

echo ""
echo "================================================================="
echo "🎉 ¡LISTO! SISTEMA ACTIVO EN SEGUNDO PLANO"
echo "================================================================="
echo "👉 TU TAQUILLA:"
echo "   $PUBLIC_URL/?pin=2026"
echo ""
echo "👉 ESCÁNER PORTEROS:"
echo "   $PUBLIC_URL/scanner?pin=puerta"
echo "================================================================="
echo "💡 Estos enlaces se han guardado también en el archivo: TU_ENLACE.txt"
echo "💡 YA PUEDES CERRAR ESTA VENTANA DE TERMINAL. No se apagará."
echo "================================================================="

# Abrir el archivo de texto en pantalla para comodidad
open TU_ENLACE.txt 2>/dev/null || true
