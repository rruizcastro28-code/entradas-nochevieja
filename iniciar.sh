#!/bin/bash
# Script de inicio rápido para la taquilla y control de acceso de Nochevieja
cd "$(dirname "$0")"

echo "=========================================================="
echo "🍾 INICIANDO SISTEMA DE ENTRADAS - FIESTA FIN DE AÑO 🍾"
echo "=========================================================="

python3 server.py 8000 "$@"
