#!/bin/bash
# Script para detener todos los servidores y túneles en ejecución
echo "Deteniendo procesos anteriores..."
pkill -f "server.py" 2>/dev/null
pkill -f "cloudflared" 2>/dev/null
pkill -f "public_tunnel.py" 2>/dev/null
sleep 1
echo "✅ Procesos detenidos. Los puertos han quedado liberados."
