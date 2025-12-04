#!/bin/bash

# Script para actualizar NGROK_URL y APP_BASE_URL en .env

if [ -z "$1" ]; then
    echo "Uso: ./update_ngrok_url.sh https://xxxx-xxxx-xxxx.ngrok-free.app"
    echo ""
    echo "Para obtener la URL de ngrok:"
    echo "1. Inicia ngrok: ngrok http 3000"
    echo "2. Copia la URL HTTPS que aparece"
    echo "3. Ejecuta este script con esa URL"
    exit 1
fi

NGROK_URL="$1"

cd "$(dirname "$0")"

# Actualizar NGROK_URL
if grep -q "^NGROK_URL=" .env; then
    sed -i.bak "s|^NGROK_URL=.*|NGROK_URL=$NGROK_URL|" .env
    echo "✅ NGROK_URL actualizado a: $NGROK_URL"
else
    echo "NGROK_URL=$NGROK_URL" >> .env
    echo "✅ NGROK_URL agregado: $NGROK_URL"
fi

# Actualizar APP_BASE_URL
if grep -q "^APP_BASE_URL=" .env; then
    sed -i.bak "s|^APP_BASE_URL=.*|APP_BASE_URL=$NGROK_URL|" .env
    echo "✅ APP_BASE_URL actualizado a: $NGROK_URL"
else
    echo "APP_BASE_URL=$NGROK_URL" >> .env
    echo "✅ APP_BASE_URL agregado: $NGROK_URL"
fi

echo ""
echo "✅ Configuración actualizada. Reinicia el backend para aplicar los cambios:"
echo "   docker compose restart backend"

