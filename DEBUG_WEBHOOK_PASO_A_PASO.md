# 🔍 Debugging Webhook - Paso a Paso

## Problema: Estado siempre "pending"

Sigue estos pasos en orden para identificar el problema:

---

## ✅ Paso 1: Verificar Variables de Entorno

Revisa tu archivo `.env` en `crowdify_GW/`:

```bash
cd crowdify_GW
cat .env | grep -E "MERCADOPAGO|NGROK"
```

**Debe tener:**
- ✅ `MERCADOPAGO_ACCESS_TOKEN` (requerido)
- ✅ `NGROK_URL` (si usas desarrollo local)
- ⚠️ `MERCADOPAGO_WEBHOOK_SECRET` (opcional en desarrollo)

**Si falta `NGROK_URL`:**
1. Inicia ngrok: `ngrok http 8000`
2. Copia la URL HTTPS (ej: `https://abc123.ngrok.io`)
3. Agrega a `.env`: `NGROK_URL=https://abc123.ngrok.io`
4. Reinicia el backend

---

## ✅ Paso 2: Verificar que ngrok está Corriendo

```bash
# Debe mostrar algo como:
# Forwarding   https://abc123.ngrok.io -> http://localhost:8000
```

**Si no está corriendo:**
```bash
ngrok http 8000
```

**⚠️ IMPORTANTE**: Mantén esta terminal abierta.

---

## ✅ Paso 3: Verificar Webhook en Mercado Pago

1. Ve a: https://www.mercadopago.com/developers/panel/app
2. Selecciona tu aplicación
3. Ve a **Webhooks > Configurar notificaciones**
4. Verifica:
   - ✅ Hay un webhook configurado
   - ✅ Está en la pestaña **"Modo test"** (si usas sandbox)
   - ✅ La URL es: `https://tu-url-ngrok.io/api/v1/purchases/webhook`
   - ✅ El evento es: **"Order (Mercado Pago)"**

**Si no está configurado:**
- Configúralo siguiendo la guía en `CONFIGURAR_WEBHOOK.md`

---

## ✅ Paso 4: Verificar Historial de Notificaciones

1. En Mercado Pago, ve a **Webhooks > Historial de notificaciones**
2. Busca notificaciones recientes (últimos 30 minutos)
3. Revisa el estado de cada notificación

**Qué buscar:**
- ✅ **"Enviado exitosamente"** → El webhook se envió correctamente
- ❌ **"Error de entrega"** → El webhook no pudo llegar al backend
- ⏳ **"Pendiente"** → El webhook está en cola

**Si ves errores:**
- Verifica que ngrok esté corriendo
- Verifica que la URL sea correcta
- Verifica que el backend esté accesible

---

## ✅ Paso 5: Revisar Logs del Backend

**Mientras haces un pago de prueba, revisa los logs:**

```bash
# Si usas Docker
docker-compose logs -f backend

# O filtrar solo webhooks
docker-compose logs -f backend | grep -E "WEBHOOK|webhook"
```

**Busca estos mensajes:**

### ✅ Si el webhook está llegando:
```
🔔 [WEBHOOK] Webhook recibido!
🔔 [WEBHOOK] Headers - x-signature: True, x-request-id: ...
🔔 [WEBHOOK] Body: {...}
🔔 [WEBHOOK] Tipo: order, Estado recibido: ...
```

### ❌ Si NO ves estos mensajes:
- El webhook no está llegando al backend
- Verifica pasos 1-3

### ⏳ Si ves "Estado recibido: pending":
```
🔔 [WEBHOOK] Tipo: order, Estado recibido: pending
⏳ [WEBHOOK] Estado 'pending' - El pago aún está pendiente
```

**Esto es normal** - El webhook está funcionando, pero el pago realmente está pendiente en Mercado Pago.

---

## ✅ Paso 6: Verificar Estado de una Orden

**Opción A: Desde el frontend**
- Abre la consola del navegador
- Busca logs que digan: `[PurchaseSuccess] Estado de la orden: ...`

**Opción B: Desde el backend (si tienes acceso a la base de datos)**
- Consulta la tabla `orders`
- Busca la orden por `id`
- Revisa el campo `status`

**Opción C: Usar la API**
```bash
curl http://localhost:8000/api/v1/purchases/<order_id>/status
```

---

## 🔍 Diagnóstico Rápido

### Escenario A: No ves logs de webhook

**Problema:** El webhook no está llegando al backend

**Solución:**
1. Verifica que ngrok esté corriendo (Paso 2)
2. Verifica que el webhook esté configurado en Mercado Pago (Paso 3)
3. Verifica que la URL sea correcta
4. Revisa el historial de notificaciones en Mercado Pago (Paso 4)

---

### Escenario B: Ves logs pero estado sigue "pending"

**Problema:** El webhook llega pero el pago realmente está pendiente

**Solución:**
- Esto es normal si el pago aún no se ha completado
- Espera unos minutos y verifica de nuevo
- En sandbox, algunos pagos pueden tardar más

**Si el pago ya se completó pero sigue "pending":**
- Verifica en los logs qué estado está recibiendo el webhook
- Puede que el estado no se esté mapeando correctamente

---

### Escenario C: El webhook llega pero no actualiza la orden

**Problema:** Error al procesar el webhook

**Solución:**
- Revisa los logs completos del backend
- Busca mensajes de error
- Verifica que el `external_reference` coincida con el `order_id`

---

## 📋 Información para Compartir

Si necesitas ayuda, comparte:

1. **Logs del backend** cuando haces un pago:
   ```bash
   docker-compose logs backend | grep -E "WEBHOOK|webhook" | tail -20
   ```

2. **Resultado de verificar variables de entorno:**
   ```bash
   cd crowdify_GW
   cat .env | grep -E "MERCADOPAGO|NGROK"
   ```

3. **Estado del webhook en Mercado Pago:**
   - ¿Está configurado?
   - ¿En qué modo (test/productivo)?
   - ¿Hay notificaciones en el historial?

4. **Estado de ngrok:**
   - ¿Está corriendo?
   - ¿Cuál es la URL?

Con esta información podré ayudarte a identificar exactamente qué está fallando.

