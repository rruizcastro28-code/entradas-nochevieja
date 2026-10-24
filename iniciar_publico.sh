#!/bin/bash
# Script para arrancar la taquilla y escáner con enlace público mundial https://*.trycloudflare.com
cd "$(dirname "$0")"

./detener.sh >/dev/null 2>&1
python3 public_tunnel.py
