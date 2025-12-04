#!/bin/bash

# Script de diagnóstico para payment links de Mercado Pago
# Este script ayuda a identificar problemas con el checkout

set -e

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== Diagnóstico de Payment Link de Mercado Pago ===${NC}\n"

# Si se proporciona un payment_link como argumento, usarlo
if [ -n "$1" ]; then
    PAYMENT_LINK="$1"
    PREFERENCE_ID=$(echo "$PAYMENT_LINK" | grep -o 'pref_id=[^&]*' | cut -d'=' -f2 || echo "")
else
    # Crear una nueva compra
    echo -e "${YELLOW}Creando nueva compra...${NC}"
    
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
        echo "Respuesta completa: $PURCHASE_RESPONSE"
        exit 1
    fi
    
    PREFERENCE_ID=$(echo "$PAYMENT_LINK" | grep -o 'pref_id=[^&]*' | cut -d'=' -f2 || echo "")
    
    echo -e "${GREEN}✅ Compra creada${NC}"
    echo "  Order ID: $ORDER_ID"
fi

if [ -z "$PREFERENCE_ID" ]; then
    echo -e "${RED}❌ Error: No se pudo extraer preference_id del payment_link${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}=== Información del Payment Link ===${NC}"
echo "  Payment Link: $PAYMENT_LINK"
echo "  Preference ID: $PREFERENCE_ID"
echo ""

# Verificar la preferencia en Mercado Pago
echo -e "${YELLOW}Verificando preferencia en Mercado Pago...${NC}"

VERIFY_RESULT=$(docker compose exec -T backend python -c "
import os
from dotenv import load_dotenv
import mercadopago
import json
import sys

load_dotenv()
sdk = mercadopago.SDK(os.getenv('MERCADOPAGO_ACCESS_TOKEN'))
result = sdk.preference().get('$PREFERENCE_ID')

if result['status'] == 200:
    pref = result['response']
    
    # Información básica
    print('STATUS: OK')
    print(f'PREFERENCE_ID: {pref.get(\"id\")}')
    print(f'STATUS_PREF: {pref.get(\"status\", \"N/A\")}')
    
    # Back URLs
    back_urls = pref.get('back_urls', {})
    has_valid_back_urls = bool(back_urls.get('success') and back_urls.get('failure') and back_urls.get('pending'))
    print(f'BACK_URLS_VALID: {has_valid_back_urls}')
    print(f'BACK_URLS: {json.dumps(back_urls)}')
    
    # Init points
    print(f'SANDBOX_INIT_POINT: {pref.get(\"sandbox_init_point\", \"\")}')
    print(f'INIT_POINT: {pref.get(\"init_point\", \"\")}')
    
    # Items
    items = pref.get('items', [])
    print(f'ITEMS_COUNT: {len(items)}')
    if items:
        total = sum(item.get('quantity', 0) * item.get('unit_price', 0) for item in items)
        print(f'TOTAL_AMOUNT: {total}')
    
    # Payment methods
    payment_methods = pref.get('payment_methods', {})
    excluded_types = payment_methods.get('excluded_payment_types', [])
    excluded_methods = payment_methods.get('excluded_payment_methods', [])
    print(f'EXCLUDED_TYPES: {len(excluded_types)}')
    print(f'EXCLUDED_METHODS: {len(excluded_methods)}')
    
    # Auto return
    auto_return = pref.get('auto_return', 'N/A')
    print(f'AUTO_RETURN: {auto_return}')
    
    # Notification URL
    notification_url = pref.get('notification_url', 'N/A')
    print(f'NOTIFICATION_URL: {notification_url}')
    
    # Verificar si hay errores
    if 'error' in pref:
        print(f'ERROR: {json.dumps(pref[\"error\"])}')
    else:
        print('ERROR: NONE')
        
else:
    print(f'STATUS: ERROR')
    print(f'HTTP_STATUS: {result[\"status\"]}')
    print(f'MESSAGE: {result.get(\"message\", \"Unknown error\")}')
    if 'response' in result:
        print(f'RESPONSE: {json.dumps(result[\"response\"])}')
" 2>&1)

echo "$VERIFY_RESULT" | while IFS= read -r line; do
    if echo "$line" | grep -q "STATUS: OK"; then
        echo -e "${GREEN}✅ Preferencia verificada en Mercado Pago${NC}"
    elif echo "$line" | grep -q "STATUS: ERROR"; then
        echo -e "${RED}❌ Error verificando preferencia${NC}"
    elif echo "$line" | grep -q "BACK_URLS_VALID: True"; then
        echo -e "${GREEN}✅ Back URLs válidas${NC}"
    elif echo "$line" | grep -q "BACK_URLS_VALID: False"; then
        echo -e "${RED}❌ Back URLs inválidas${NC}"
    elif echo "$line" | grep -q "ERROR: NONE"; then
        echo -e "${GREEN}✅ No hay errores en la preferencia${NC}"
    elif echo "$line" | grep -q "ERROR:"; then
        echo -e "${RED}❌ Error en preferencia: $line${NC}"
    fi
done

echo ""
echo -e "${BLUE}=== Detalles de la Preferencia ===${NC}"
echo "$VERIFY_RESULT" | grep -E "(PREFERENCE_ID|STATUS_PREF|BACK_URLS|SANDBOX_INIT_POINT|ITEMS_COUNT|TOTAL_AMOUNT|EXCLUDED|AUTO_RETURN|NOTIFICATION_URL)" | sed 's/^/  /'

echo ""
echo -e "${BLUE}=== Prueba de Acceso al Payment Link ===${NC}"

# Probar acceso con curl (esperamos 403, que es normal)
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -L --max-time 10 "$PAYMENT_LINK" 2>&1 || echo "000")

if [ "$HTTP_CODE" = "403" ]; then
    echo -e "${YELLOW}⚠️  HTTP 403 - Esto es NORMAL${NC}"
    echo "  Mercado Pago bloquea el acceso directo con curl"
    echo "  Debes abrir el link en un navegador real"
elif [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "302" ] || [ "$HTTP_CODE" = "301" ]; then
    echo -e "${GREEN}✅ Payment link es accesible (HTTP $HTTP_CODE)${NC}"
else
    echo -e "${RED}❌ Error accediendo al payment link (HTTP $HTTP_CODE)${NC}"
    echo "  Esto puede indicar un problema con la preferencia"
fi

echo ""
echo -e "${BLUE}=== Instrucciones para Probar ===${NC}"
echo ""
echo -e "${YELLOW}1. Copia este payment_link:${NC}"
echo "   $PAYMENT_LINK"
echo ""
echo -e "${YELLOW}2. IMPORTANTE - Abre en Chrome o Firefox (NO Brave):${NC}"
echo "   - Brave bloquea scripts de Mercado Pago"
echo "   - Chrome/Firefox funcionan correctamente"
echo ""
echo -e "${YELLOW}3. Si ves un error en el navegador, copia el mensaje exacto${NC}"
echo "   - Abre las herramientas de desarrollador (F12)"
echo "   - Revisa la consola para ver errores"
echo "   - Revisa la pestaña Network para ver peticiones fallidas"
echo ""
echo -e "${YELLOW}4. Tarjeta de prueba para completar el pago:${NC}"
echo "   - Número: 4168 8188 4444 7115"
echo "   - CVV: 123"
echo "   - Fecha: Cualquier fecha futura (ej: 12/25)"
echo "   - Nombre: APRO"
echo "   - Email: test@test.com"
echo ""
echo -e "${YELLOW}5. Si el error persiste:${NC}"
echo "   - Verifica que ngrok esté corriendo"
echo "   - Verifica que NGROK_URL esté configurado en .env"
echo "   - Revisa los logs del backend: docker compose logs backend"
echo ""

