#!/bin/bash

# Script para probar el payment_link directamente
# Este script verifica que el payment_link de Mercado Pago funciona

set -e

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== Prueba de Payment Link de Mercado Pago ===${NC}\n"

# Si se proporciona un payment_link como argumento, usarlo
if [ -n "$1" ]; then
    PAYMENT_LINK="$1"
else
    # Crear una nueva compra y obtener el payment_link
    echo -e "${YELLOW}Creando nueva compra para obtener payment_link...${NC}"
    
    BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
    API_BASE="${BACKEND_URL}/api/v1"
    EVENT_ID="${EVENT_ID:-4fb47f6c-83a3-4494-aecc-9947863c031c}"
    
    PURCHASE_PAYLOAD=$(cat <<EOF
{
  "event_id": "$EVENT_ID",
  "attendees": [
    {
      "name": "Test User",
      "email": "test@test.com",
      "document_type": "RUT",
      "is_child": false
    }
  ],
  "selected_services": {},
  "payment_method": "mercadopago"
}
EOF
)
    
    PURCHASE_RESPONSE=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        "${API_BASE}/purchases" \
        -d "$PURCHASE_PAYLOAD")
    
    PAYMENT_LINK=$(echo "$PURCHASE_RESPONSE" | grep -o '"payment_link":"[^"]*"' | cut -d'"' -f4 || echo "")
    ORDER_ID=$(echo "$PURCHASE_RESPONSE" | grep -o '"order_id":"[^"]*"' | cut -d'"' -f4 || echo "")
    
    if [ -z "$PAYMENT_LINK" ] || [ "$PAYMENT_LINK" = "null" ]; then
        echo -e "${RED}❌ Error: No se pudo obtener payment_link${NC}"
        echo "Respuesta: $PURCHASE_RESPONSE"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Compra creada${NC}"
    echo "  Order ID: $ORDER_ID"
fi

echo -e "${GREEN}Payment Link:${NC}"
echo "  $PAYMENT_LINK"
echo ""

# Extraer preference_id
PREFERENCE_ID=$(echo "$PAYMENT_LINK" | grep -o 'pref_id=[^&]*' | cut -d'=' -f2 || echo "")

if [ -z "$PREFERENCE_ID" ]; then
    echo -e "${RED}❌ Error: No se pudo extraer preference_id${NC}"
    exit 1
fi

echo -e "${GREEN}Preference ID:${NC}"
echo "  $PREFERENCE_ID"
echo ""

# Verificar la preferencia en Mercado Pago
echo -e "${YELLOW}Verificando preferencia en Mercado Pago...${NC}"

VERIFY_RESULT=$(docker compose exec -T backend python -c "
import os
from dotenv import load_dotenv
import mercadopago
import json

load_dotenv()
sdk = mercadopago.SDK(os.getenv('MERCADOPAGO_ACCESS_TOKEN'))
result = sdk.preference().get('$PREFERENCE_ID')

if result['status'] == 200:
    pref = result['response']
    back_urls = pref.get('back_urls', {})
    has_valid_back_urls = bool(back_urls.get('success') and back_urls.get('failure') and back_urls.get('pending'))
    
    print('STATUS: OK')
    print(f'BACK_URLS_VALID: {has_valid_back_urls}')
    print(f'BACK_URLS: {json.dumps(back_urls)}')
    print(f'SANDBOX_INIT_POINT: {pref.get(\"sandbox_init_point\", \"\")}')
else:
    print(f'STATUS: ERROR')
    print(f'MESSAGE: {result.get(\"message\", \"Unknown error\")}')
" 2>&1)

if echo "$VERIFY_RESULT" | grep -q "STATUS: OK"; then
    echo -e "${GREEN}✅ Preferencia verificada en Mercado Pago${NC}"
    
    if echo "$VERIFY_RESULT" | grep -q "BACK_URLS_VALID: True"; then
        echo -e "${GREEN}✅ Back URLs válidas${NC}"
    else
        echo -e "${RED}❌ Back URLs inválidas${NC}"
    fi
    
    echo "$VERIFY_RESULT" | grep "BACK_URLS:" | sed 's/BACK_URLS: //' | python3 -m json.tool 2>/dev/null || echo "$VERIFY_RESULT" | grep "BACK_URLS:"
else
    echo -e "${RED}❌ Error verificando preferencia${NC}"
    echo "$VERIFY_RESULT"
fi

echo ""

# Instrucciones para probar
echo -e "${BLUE}=== Instrucciones para Probar ===${NC}"
echo ""
echo -e "${YELLOW}1. Abre el payment_link en tu navegador:${NC}"
echo "   $PAYMENT_LINK"
echo ""
echo -e "${YELLOW}2. IMPORTANTE - Usa Chrome o Firefox (NO Brave):${NC}"
echo "   - Brave bloquea scripts de Mercado Pago"
echo "   - Chrome/Firefox no tienen este problema"
echo ""
echo -e "${YELLOW}3. Intenta completar el pago con tarjeta de prueba:${NC}"
echo "   - Número: 4168 8188 4444 7115"
echo "   - CVV: 123"
echo "   - Fecha: Cualquier fecha futura (ej: 12/25)"
echo "   - Nombre: APRO"
echo "   - Email: test@test.com"
echo ""
echo -e "${YELLOW}4. Si funciona en Chrome/Firefox:${NC}"
echo "   - Confirma que el problema es específico de Brave"
echo "   - Sigue la guía de configuración de Brave"
echo ""
echo -e "${YELLOW}5. Si NO funciona en Chrome/Firefox:${NC}"
echo "   - Verifica los logs del backend"
echo "   - Contacta soporte de Mercado Pago"
echo ""

