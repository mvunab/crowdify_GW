# 🔍 Guía de Debugging - Webhook Mercado Pago

## Problema: El estado siempre es "pending"

Esta guía te ayudará a identificar por qué el webhook no está actualizando el estado de la orden.

---

## 📋 Checklist de Verificación

### 1. Verificar que el Webhook está Configurado

**En Mercado Pago:**
1. Ve a: https://www.mercadopago.com/developers/panel/app
2. Selecciona tu aplicación
3. Ve a **Webhooks > Configurar notificaciones**
4. Verifica que haya un webhook configurado
5. **IMPORTANTE**: Verifica que esté en la pestaña correcta:
   - **Modo test** ← Si estás usando sandbox/pruebas
   - **Modo productivo** ← Si estás en producción

**URL del webhook debe ser:**
```
https://tu-url.ngrok.io/api/v1/purchases/webhook
```

---

### 2. Verificar Variables de Entorno

Ejecuta el script de debugging:

```bash
cd crowdify_GW
python scripts/debug_webhook.py
```

O verifica manualmente en tu `.env`:

```env
# Requerido
MERCADOPAGO_ACCESS_TOKEN=tu-access-token

# Opcional pero recomendado
MERCADOPAGO_WEBHOOK_SECRET=tu-webhook-secret

# Necesario para desarrollo local
NGROK_URL=https://tu-url.ngrok.io
```

---

### 3. Verificar que ngrok está Corriendo (si usas desarrollo local)

```bash
# Debe mostrar algo como:
# Forwarding   https://abc123.ngrok.io -> http://localhost:8000
```

Si no está corriendo:
```bash
ngrok http 8000
```

**⚠️ IMPORTANTE**: Mantén ngrok corriendo mientras pruebas.

---

### 4. Verificar que el Backend está Accesible

Prueba la URL del webhook:

```bash
curl -X POST https://tu-url.ngrok.io/api/v1/purchases/webhook \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'
```

**Resultado esperado:**
- Si retorna `{"status": "ignored"}` o `{"status": "ok"}` → ✅ El endpoint funciona
- Si retorna `404` → ❌ El endpoint no existe o la URL está mal
- Si retorna error de conexión → ❌ ngrok no está corriendo o la URL está mal

---

### 5. Verificar Logs del Backend

**Mientras haces un pago, revisa los logs:**

```bash
# Si usas Docker
docker-compose logs -f backend | grep -E "WEBHOOK|webhook"

# O todos los logs
docker-compose logs -f backend
```

**Busca estos mensajes:**

✅ **Si el webhook está llegando:**
```
🔔 [WEBHOOK] Webhook recibido!
🔔 [WEBHOOK] Headers - x-signature: True, x-request-id: ...
🔔 [WEBHOOK] Body: {...}
🔔 [WEBHOOK] Procesando webhook...
🔔 [WEBHOOK] Tipo: order, Estado recibido: ...
```

❌ **Si NO ves estos mensajes:**
- El webhook no está llegando al backend
- Verifica que ngrok esté corriendo
- Verifica que la URL en Mercado Pago sea correcta

---

### 6. Verificar Estado de una Orden Específica

```bash
cd crowdify_GW
python scripts/debug_webhook.py <order_id>
```

Ejemplo:
```bash
python scripts/debug_webhook.py a95ee80b-49a4-4b31-b75b-d7fb25bc4933
```

Esto mostrará:
- Estado actual de la orden
- Si tiene tickets generados
- Fechas de creación y pago

---

### 7. Verificar en Mercado Pago - Historial de Notificaciones

1. Ve a: https://www.mercadopago.com/developers/panel/app
2. Selecciona tu aplicación
3. Ve a **Webhooks > Historial de notificaciones**
4. Busca notificaciones recientes

**Qué buscar:**
- ✅ **Enviado exitosamente**: El webhook se envió correctamente
- ❌ **Error de entrega**: El webhook no pudo llegar al backend
- ⏳ **Pendiente**: El webhook está en cola

**Si ves errores:**
- Verifica que la URL sea correcta
- Verifica que ngrok esté corriendo
- Verifica que el backend esté accesible

---

## 🔍 Diagnóstico por Escenario

### Escenario 1: No ves logs de webhook

**Síntomas:**
- No aparecen mensajes `🔔 [WEBHOOK]` en los logs
- El estado siempre es "pending"

**Causas posibles:**
1. ❌ Webhook no configurado en Mercado Pago
2. ❌ URL incorrecta en Mercado Pago
3. ❌ ngrok no está corriendo (desarrollo local)
4. ❌ Webhook configurado en "Modo productivo" pero estás usando "Modo test"

**Solución:**
1. Configura el webhook en Mercado Pago (ver paso 1)
2. Asegúrate de usar la pestaña correcta (test vs productivo)
3. Verifica que ngrok esté corriendo
4. Prueba la URL manualmente con curl

---

### Escenario 2: Ves logs pero el estado sigue siendo "pending"

**Síntomas:**
- Aparecen mensajes `🔔 [WEBHOOK]` en los logs
- Pero el estado sigue siendo "pending"

**Causas posibles:**
1. El webhook llega con estado "pending" (el pago realmente está pendiente)
2. El estado no se mapea correctamente
3. Hay un error al procesar el webhook

**Qué revisar en los logs:**
```
🔔 [WEBHOOK] Tipo: order, Estado recibido: pending
⏳ [WEBHOOK] Estado 'pending' - El pago aún está pendiente
```

**Si ves esto:**
- El webhook está funcionando correctamente
- El pago realmente está pendiente en Mercado Pago
- Necesitas esperar a que Mercado Pago procese el pago

**Si ves errores:**
- Revisa el mensaje de error completo
- Verifica que el `external_reference` coincida con el `order_id`

---

### Escenario 3: El webhook llega pero no actualiza la orden

**Síntomas:**
- Ves logs de webhook recibido
- Pero la orden no cambia de estado

**Causas posibles:**
1. El `external_reference` no coincide con el `order_id`
2. La orden no se encuentra en la base de datos
3. Hay un error al actualizar la orden

**Qué revisar en los logs:**
```
🔔 [WEBHOOK] External Reference: xxx, Order ID: yyy
⚠️  Orden xxx no encontrada
```

**Solución:**
- Verifica que el `external_reference` en la preferencia sea el `order_id`
- Verifica que la orden exista en la base de datos

---

## 🛠️ Comandos Útiles

### Ver logs del backend en tiempo real
```bash
docker-compose logs -f backend
```

### Filtrar solo logs de webhook
```bash
docker-compose logs -f backend | grep -E "WEBHOOK|webhook"
```

### Verificar estado de una orden
```bash
cd crowdify_GW
python scripts/debug_webhook.py <order_id>
```

### Listar órdenes recientes
```bash
cd crowdify_GW
python scripts/debug_webhook.py
```

### Probar endpoint del webhook manualmente
```bash
curl -X POST https://tu-url.ngrok.io/api/v1/purchases/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "type": "order",
    "data": {
      "id": "123456789",
      "external_reference": "tu-order-id",
      "status": "processed"
    }
  }'
```

---

## 📝 Pasos para Debuggear Ahora

1. **Ejecuta el script de debugging:**
   ```bash
   cd crowdify_GW
   python scripts/debug_webhook.py
   ```

2. **Revisa los logs del backend mientras haces un pago:**
   ```bash
   docker-compose logs -f backend | grep -E "WEBHOOK|webhook"
   ```

3. **Verifica en Mercado Pago:**
   - Ve a Webhooks > Historial de notificaciones
   - Busca notificaciones recientes

4. **Comparte conmigo:**
   - Los logs que aparecen cuando haces un pago
   - El resultado del script de debugging
   - Si ves notificaciones en el historial de Mercado Pago

Con esa información podré ayudarte a identificar exactamente qué está fallando.

