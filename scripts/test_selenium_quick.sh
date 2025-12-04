#!/bin/bash

# Script rápido para ejecutar la prueba de Selenium

echo "🧪 Ejecutando prueba automatizada de Mercado Pago con Selenium..."
echo ""

cd /Users/matiasvargasmarin/Desktop/crowdify/crowdify_GW

# Verificar que Python y Selenium estén disponibles
if ! python3 -c "import selenium" 2>/dev/null; then
    echo "❌ Selenium no está instalado"
    echo "   Instala con: pip install selenium"
    exit 1
fi

# Ejecutar el script
python3 scripts/test_mercadopago_selenium.py "$@"

