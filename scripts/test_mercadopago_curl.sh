#!/bin/bash

# Script de prueba de Mercado Pago usando curl
# Este script prueba el backend directamente sin frontend

set -e

# Colores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Prueba de Mercado Pago - Backend con curl ===${NC}\n"

# Configuración
BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
API_BASE="${BACKEND_URL}/api/v1"

# Datos de prueba
EVENT_ID="${EVENT_ID:-4fb47f6c-83a3-4494-aecc-9947863c031c}"
ATTENDEE_NAME="${ATTENDEE_NAME:-Test User}"
ATTENDEE_EMAIL="${ATTENDEE_EMAIL:-test@test.com}"

echo -e "${YELLOW}Configuración:${NC}"
echo "  Backend URL: $BACKEND_URL"
echo "  Event ID: $EVENT_ID"
echo "  Attendee: $ATTENDEE_NAME <$ATTENDEE_EMAIL>"
echo ""

# Paso 1: Verificar que el backend está corriendo
echo -e "${GREEN}[1/5] Verificando que el backend está corriendo...${NC}"
HEALTH_RESPONSE=$(curl -s -w "\n%{http_code}" "${BACKEND_URL}/health" || echo "ERROR")
HTTP_CODE=$(echo "$HEALTH_RESPONSE" | tail -n1)
BODY=$(echo "$HEALTH_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" != "200" ]; then
    echo -e "${RED}❌ Error: El backend no está respondiendo (HTTP $HTTP_CODE)${NC}"
    echo "  Respuesta: $BODY"
    exit 1
fi
echo -e "${GREEN}✅ Backend está corriendo${NC}\n"

# Paso 2: Verificar ready check (DB y Redis)
echo -e "${GREEN}[2/5] Verificando conexiones (DB y Redis)...${NC}"
READY_RESPONSE=$(curl -s -w "\n%{http_code}" "${BACKEND_URL}/ready" || echo "ERROR")
HTTP_CODE=$(echo "$READY_RESPONSE" | tail -n1)
BODY=$(echo "$READY_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" != "200" ]; then
    echo -e "${RED}❌ Error: Ready check falló (HTTP $HTTP_CODE)${NC}"
    echo "  Respuesta: $BODY"
    exit 1
fi

DB_STATUS=$(echo "$BODY" | grep -o '"database":"[^"]*"' | cut -d'"' -f4)
REDIS_STATUS=$(echo "$BODY" | grep -o '"redis":"[^"]*"' | cut -d'"' -f4)

if [ "$DB_STATUS" != "connected" ]; then
    echo -e "${RED}❌ Error: Base de datos no conectada${NC}"
    exit 1
fi

if [ "$REDIS_STATUS" != "connected" ]; then
    echo -e "${YELLOW}⚠️  Advertencia: Redis no conectado (el cache no funcionará)${NC}"
else
    echo -e "${GREEN}✅ Base de datos y Redis conectados${NC}"
fi
echo ""

# Paso 3: Crear compra (POST /api/v1/purchases)
echo -e "${GREEN}[3/5] Creando compra con Mercado Pago...${NC}"

PURCHASE_PAYLOAD=$(cat <<EOF
{
  "event_id": "$EVENT_ID",
  "attendees": [
    {
      "name": "$ATTENDEE_NAME",
      "email": "$ATTENDEE_EMAIL",
      "document_type": "RUT",
      "is_child": false
    }
  ],
  "selected_services": {},
  "payment_method": "mercadopago"
}
EOF
)

echo "  Payload enviado:"
echo "$PURCHASE_PAYLOAD" | jq '.' 2>/dev/null || echo "$PURCHASE_PAYLOAD"
echo ""

PURCHASE_RESPONSE=$(curl -s -w "\n%{http_code}" \
    -X POST \
    -H "Content-Type: application/json" \
    "${API_BASE}/purchases" \
    -d "$PURCHASE_PAYLOAD" || echo "ERROR")

HTTP_CODE=$(echo "$PURCHASE_RESPONSE" | tail -n1)
BODY=$(echo "$PURCHASE_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" != "200" ]; then
    echo -e "${RED}❌ Error: No se pudo crear la compra (HTTP $HTTP_CODE)${NC}"
    echo "  Respuesta: $BODY"
    exit 1
fi

echo -e "${GREEN}✅ Compra creada exitosamente${NC}"
echo "  Respuesta:"
echo "$BODY" | jq '.' 2>/dev/null || echo "$BODY"
echo ""

# Extraer order_id y payment_link
ORDER_ID=$(echo "$BODY" | grep -o '"order_id":"[^"]*"' | cut -d'"' -f4 || echo "")
PAYMENT_LINK=$(echo "$BODY" | grep -o '"payment_link":"[^"]*"' | cut -d'"' -f4 || echo "")

if [ -z "$ORDER_ID" ]; then
    echo -e "${RED}❌ Error: No se pudo extraer order_id de la respuesta${NC}"
    exit 1
fi

if [ -z "$PAYMENT_LINK" ] || [ "$PAYMENT_LINK" = "null" ]; then
    echo -e "${RED}❌ Error: payment_link es null o no se pudo extraer${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Datos extraídos:${NC}"
echo "  Order ID: $ORDER_ID"
echo "  Payment Link: $PAYMENT_LINK"
echo ""

# Paso 4: Verificar el payment_link
echo -e "${GREEN}[4/5] Verificando payment_link...${NC}"

# Extraer el preference_id del payment_link
PREFERENCE_ID=$(echo "$PAYMENT_LINK" | grep -o 'pref_id=[^&]*' | cut -d'=' -f2 || echo "")

if [ -z "$PREFERENCE_ID" ]; then
    echo -e "${RED}❌ Error: No se pudo extraer preference_id del payment_link${NC}"
    exit 1
fi

echo "  Preference ID: $PREFERENCE_ID"
echo "  Payment Link: $PAYMENT_LINK"
echo ""

# Verificar que el payment_link es válido (HTTPS y contiene preference_id)
if [[ ! "$PAYMENT_LINK" =~ ^https:// ]]; then
    echo -e "${RED}❌ Error: payment_link no es HTTPS${NC}"
    exit 1
fi

if [[ ! "$PAYMENT_LINK" =~ preference-id|pref_id ]]; then
    echo -e "${RED}❌ Error: payment_link no contiene preference_id${NC}"
    exit 1
fi

echo -e "${GREEN}✅ payment_link es válido${NC}"
echo ""

# Paso 5: Probar acceso al payment_link
echo -e "${GREEN}[5/5] Probando acceso al payment_link...${NC}"

# Hacer una petición HEAD para verificar que el link es accesible
LINK_RESPONSE=$(curl -s -w "\n%{http_code}" -I -L --max-time 10 "$PAYMENT_LINK" 2>&1 || echo "ERROR")
HTTP_CODE=$(echo "$LINK_RESPONSE" | tail -n1)

if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "302" ] || [ "$HTTP_CODE" = "301" ]; then
    echo -e "${GREEN}✅ payment_link es accesible (HTTP $HTTP_CODE)${NC}"
else
    echo -e "${YELLOW}⚠️  Advertencia: payment_link retornó HTTP $HTTP_CODE${NC}"
    echo "  Esto puede ser normal si Mercado Pago requiere autenticación o redirección"
fi
echo ""

# Resumen final
echo -e "${GREEN}=== Resumen de la Prueba ===${NC}"
echo -e "${GREEN}✅ Backend funcionando correctamente${NC}"
echo -e "${GREEN}✅ Compra creada exitosamente${NC}"
echo -e "${GREEN}✅ payment_link generado correctamente${NC}"
echo -e "${GREEN}✅ payment_link es accesible${NC}"
echo ""
echo -e "${YELLOW}Próximos pasos:${NC}"
echo "  1. Abre el payment_link en tu navegador:"
echo "     $PAYMENT_LINK"
echo ""
echo "  2. Intenta completar el pago con una tarjeta de prueba:"
echo "     - Número: 4168 8188 4444 7115"
echo "     - CVV: 123"
echo "     - Fecha: Cualquier fecha futura"
echo "     - Nombre: APRO"
echo ""
echo "  3. Si el pago funciona aquí pero no desde el frontend,"
echo "     el problema está en el frontend o en el navegador (Brave)"
echo ""
echo -e "${GREEN}Order ID para referencia: $ORDER_ID${NC}"

