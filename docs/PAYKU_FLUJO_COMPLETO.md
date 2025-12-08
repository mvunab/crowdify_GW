# 🧪 Flujo Completo de Payku con Ngrok

## ✅ Configuración Actual

- **Ngrok URL:** `https://theistically-nondropsical-ean.ngrok-free.dev`
- **Webhook URL:** `https://theistically-nondropsical-ean.ngrok-free.dev/api/v1/purchases/payku-webhook`
- **Frontend URL (redirects):** `http://localhost:3000`
- **Ambiente:** Sandbox (pruebas)

## 🚀 Pasos para Probar el Flujo Completo

### 1. Asegúrate de que ngrok esté corriendo

En una terminal separada:
```bash
ngrok http 8000
```

Verifica que muestre: `Forwarding https://theistically-nondropsical-ean.ngrok-free.dev -> http://localhost:8000`

### 2. Verifica que el backend esté corriendo

El backend debe estar escuchando en `http://localhost:8000`

### 3. Crea una nueva orden desde el frontend

1. Ve a `http://localhost:3000`
2. Selecciona un evento
3. Completa el formulario de compra
4. Selecciona **"Compra Internacional - Payku"**
5. Haz clic en "Continuar"

### 4. Revisa los logs del backend

Cuando se cree la orden, deberías ver:

```
[DEBUG Payku] Creando transacción con los siguientes datos:
[DEBUG Payku]   - urlreturn: http://localhost:3000/compra-exitosa?order_id=xxx&payment_provider=payku
[DEBUG Payku]   - urlnotify: https://theistically-nondropsical-ean.ngrok-free.dev/api/v1/purchases/payku-webhook
```

**⚠️ IMPORTANTE:** Verifica que `urlnotify` use la URL de ngrok (HTTPS).

### 5. Paga en Payku

1. Serás redirigido a la página de pago de Payku
2. Usa una tarjeta de prueba:
   - **VISA:** `4051 8856 0044 6623`
   - **CVV:** `123`
   - **Fecha:** Cualquier fecha futura
   - **RUT:** `11.111.111-1`
   - **Clave:** `123`

3. Completa el pago

### 6. Verifica el webhook automático

**En los logs del backend deberías ver:**

```
🔔 [WEBHOOK PAYKU] Webhook recibido!
🔔 [WEBHOOK PAYKU] Body: {...}
🔔 [WEBHOOK PAYKU] Webhook procesado: {...}
✅ [WEBHOOK PAYKU] Pago aprobado! Actualizando orden ... a 'completed'
```

**En la terminal de ngrok deberías ver:**

```
POST /api/v1/purchases/payku-webhook    200 OK
```

### 7. Verifica la redirección

Después del pago, Payku te redirigirá a:
```
http://localhost:3000/compra-exitosa?order_id=xxx&payment_provider=payku
```

### 8. Verifica que la orden esté completada

La orden debería estar automáticamente en estado `completed` y los tickets generados.

## 🔍 Troubleshooting

### El webhook no llega

1. **Verifica que ngrok esté corriendo:**
   - Abre http://localhost:4040 (interfaz web de ngrok)
   - Deberías ver las peticiones entrantes

2. **Verifica la URL del webhook en los logs:**
   - Al crear la orden, revisa que `urlnotify` use ngrok
   - Si no, verifica que `NGROK_URL` esté en el `.env`

3. **Verifica que Payku pueda alcanzar ngrok:**
   - En el panel de Payku (https://des.payku.cl), revisa los logs de webhooks
   - Si hay errores, Payku mostrará qué pasó

### El webhook llega pero falla

1. **Revisa los logs del backend:**
   - Busca errores en el procesamiento
   - Verifica que la orden exista

2. **Verifica el formato del webhook:**
   - Payku envía datos en formato JSON
   - Revisa que el endpoint esté parseando correctamente

### La orden no se actualiza

Si el webhook no llega, puedes usar el endpoint de verificación manual:

```bash
curl -X POST http://localhost:8000/api/v1/purchases/{order_id}/verify-payku
```

## 📊 Flujo Esperado

```
1. Usuario crea orden → Backend crea transacción en Payku
2. Backend recibe payment_link → Redirige usuario a Payku
3. Usuario paga en Payku → Payku procesa pago
4. Payku envía webhook → Backend recibe notificación
5. Backend actualiza orden → Genera tickets automáticamente
6. Payku redirige usuario → Frontend muestra compra exitosa
```

## ✅ Checklist de Verificación

- [ ] Ngrok está corriendo y accesible
- [ ] Backend está corriendo en puerto 8000
- [ ] `NGROK_URL` está configurado en `.env`
- [ ] Los logs muestran la URL correcta del webhook
- [ ] El webhook llega después del pago
- [ ] La orden se actualiza automáticamente
- [ ] Los tickets se generan automáticamente
- [ ] El usuario es redirigido correctamente

