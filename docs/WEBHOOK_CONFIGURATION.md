# 🔔 Configuración de Webhooks de Mercado Pago

## Estado Actual

### ✅ Implementado en el Backend

1. **Endpoint Webhook**: `/api/v1/purchases/webhook`
   - Recibe notificaciones POST de Mercado Pago
   - Retorna HTTP 200 para confirmar recepción
   - Procesa actualizaciones de estado de pagos

2. **Verificación de Firma**:
   - Implementada verificación HMAC SHA256
   - Valida `x-signature` header
   - Compara con `MERCADOPAGO_WEBHOOK_SECRET`

3. **Procesamiento de Notificaciones**:
   - Actualiza estado de órdenes
   - Genera tickets cuando el pago es aprobado
   - Maneja errores sin fallar el webhook

### ⚠️ Pendiente: Configuración en Mercado Pago

El webhook **NO está configurado** en el panel de Mercado Pago. Necesitas configurarlo manualmente.

## 📋 Pasos para Configurar el Webhook

### Opción 1: Desarrollo Local (usando ngrok)

1. **Instalar ngrok** (si no lo tienes):
   ```bash
   # Windows (con Chocolatey)
   choco install ngrok
   
   # O descargar de https://ngrok.com/download
   ```

2. **Iniciar ngrok** para exponer tu backend:
   ```bash
   ngrok http 8000
   ```

3. **Copiar la URL HTTPS** que ngrok te da (ej: `https://abc123.ngrok.io`)

4. **Configurar en Mercado Pago**:
   - Ve a [Tus integraciones](https://www.mercadopago.com/developers/panel/app)
   - Selecciona tu aplicación
   - Ve a **Webhooks > Configurar notificaciones**
   - **IMPORTANTE**: Hay DOS pestañas:
     - **Modo test** ← **USA ESTA para desarrollo/sandbox**
     - **Modo productivo** (para producción)
   - Selecciona la pestaña **Modo test**
   - URL: `https://abc123.ngrok.io/api/v1/purchases/webhook`
   - Evento: **Order (Mercado Pago)**
   - Click en **Guardar configuración**
   
   **💡 Nota**: El webhook en "Modo test" solo recibirá notificaciones de pagos de prueba. Para producción, configura otro webhook en "Modo productivo".

5. **Copiar el Webhook Secret**:
   - Después de guardar, Mercado Pago generará una clave secreta
   - Cópiala y agrégala a tu `.env`:
     ```
     MERCADOPAGO_WEBHOOK_SECRET=tu-clave-secreta-aqui
     ```

### Opción 2: Producción

1. **Asegúrate de que tu backend sea accesible públicamente**:
   - Debe tener una URL HTTPS (no HTTP)
   - Ejemplo: `https://api.tudominio.com/api/v1/purchases/webhook`

2. **Configurar en Mercado Pago**:
   - Ve a [Tus integraciones](https://www.mercadopago.com/developers/panel/app)
   - Selecciona tu aplicación
   - Ve a **Webhooks > Configurar notificaciones**
   - Pestaña **Modo productivo**
   - URL: `https://api.tudominio.com/api/v1/purchases/webhook`
   - Evento: **Order (Mercado Pago)**
   - Click en **Guardar configuración**

3. **Agregar Webhook Secret a producción**:
   ```
   MERCADOPAGO_WEBHOOK_SECRET=tu-clave-secreta-de-produccion
   ```

## 🧪 Probar el Webhook

### Usando MCP de Mercado Pago

Puedes usar el MCP de Mercado Pago para simular notificaciones:

```python
# Simular webhook de pago aprobado
simulate_webhook(
    resource_id="tu-payment-id",
    topic="payment",
    callback_env_production=False  # True para producción
)
```

### Verificar Historial

```python
# Ver historial de notificaciones
notifications_history()
```

## 🔒 Seguridad

### Verificación de Firma

El backend ahora valida automáticamente las firmas de los webhooks usando:

1. **Header `x-signature`**: Contiene `ts` (timestamp) y `v1` (firma HMAC)
2. **Header `x-request-id`**: ID único de la petición
3. **Query param `data.id`**: ID del recurso (order/payment)
4. **Webhook Secret**: Clave secreta configurada en Mercado Pago

### Template de Validación

El sistema construye el siguiente template para validar:
```
id:[data.id];request-id:[x-request-id];ts:[ts];
```

Luego calcula HMAC SHA256 con el secret y compara con `v1`.

## 📝 Variables de Entorno Necesarias

```env
# Webhook Secret (obtenido de Mercado Pago después de configurar)
MERCADOPAGO_WEBHOOK_SECRET=tu-clave-secreta-aqui

# URL base (para construir notification_url en preferencias)
APP_BASE_URL=http://localhost:5173  # Desarrollo
# APP_BASE_URL=https://tudominio.com  # Producción
```

## 🐛 Troubleshooting

### Webhook no se recibe

1. **Verifica que la URL sea accesible públicamente**:
   - No uses `localhost` o `127.0.0.1`
   - Usa ngrok para desarrollo local
   - En producción, asegúrate de tener HTTPS

2. **Verifica los logs del backend**:
   ```bash
   docker-compose logs -f backend
   ```

3. **Verifica en Mercado Pago**:
   - Ve a **Webhooks > Historial de notificaciones**
   - Revisa si hay errores de entrega

### Firma no coincide

1. **Verifica que `MERCADOPAGO_WEBHOOK_SECRET` sea correcto**:
   - Debe ser el secret generado por Mercado Pago
   - No debe tener espacios extra

2. **Verifica los logs**:
   - El backend mostrará si la verificación falla
   - Revisa el formato del manifest

### Webhook se recibe pero no procesa

1. **Verifica los logs del backend**:
   ```bash
   docker-compose logs -f backend | grep webhook
   ```

2. **Verifica que el `external_reference` coincida**:
   - Debe ser el `order_id` que enviaste al crear la preferencia
   - Revisa en la base de datos si existe la orden

## 📚 Referencias

- [Documentación de Webhooks de Mercado Pago](https://www.mercadopago.com/developers/es/docs/checkout-api-v2/notifications)
- [Validación de Firma](https://www.mercadopago.com/developers/es/docs/your-integrations/notifications/webhooks)

## ✅ Checklist

- [ ] Backend tiene endpoint `/api/v1/purchases/webhook` ✅
- [ ] Verificación de firma implementada ✅
- [ ] Webhook configurado en panel de Mercado Pago ⚠️
- [ ] `MERCADOPAGO_WEBHOOK_SECRET` configurado en `.env` ⚠️
- [ ] URL del webhook es accesible públicamente ⚠️
- [ ] Probado con notificación de prueba ⚠️

