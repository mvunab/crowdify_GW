# 🔧 Configuración de Payku con Ngrok

## Pasos para probar el flujo completo con webhooks

### 1. Iniciar ngrok

Abre una nueva terminal y ejecuta:

```bash
ngrok http 8000
```

Esto te dará una URL como: `https://xxxx-xxxx-xxxx.ngrok-free.dev`

### 2. Actualizar .env del backend

Agrega o actualiza en `crowdify_GW/.env`:

```env
NGROK_URL=https://xxxx-xxxx-xxxx.ngrok-free.dev
```

**⚠️ IMPORTANTE:** Reemplaza `xxxx-xxxx-xxxx` con tu URL real de ngrok.

### 3. Reiniciar el backend

Después de actualizar el `.env`, reinicia el backend para que cargue la nueva configuración.

### 4. Verificar la configuración

Cuando crees una nueva orden, deberías ver en los logs del backend:

```
[DEBUG Payku]   - urlnotify: https://xxxx-xxxx-xxxx.ngrok-free.dev/api/v1/purchases/payku-webhook
```

### 5. Probar el flujo completo

1. **Crear una orden** desde el frontend
2. **Pagar en Payku** usando las tarjetas de prueba
3. **Verificar que el webhook llegue** automáticamente:
   - Revisa los logs del backend
   - Deberías ver: `🔔 [WEBHOOK PAYKU] Webhook recibido!`
   - La orden debería actualizarse automáticamente a `completed`
   - Los tickets deberían generarse automáticamente

### 6. Verificar en Payku

En el panel de Payku (https://des.payku.cl para sandbox), puedes ver:
- Las transacciones creadas
- El estado de los webhooks enviados
- Si hubo algún error al enviar el webhook

## 🔍 Troubleshooting

### El webhook no llega

1. **Verifica que ngrok esté corriendo:**
   ```bash
   curl https://xxxx-xxxx-xxxx.ngrok-free.dev/api/v1/purchases/payku-webhook
   ```
   Debería responder (aunque sea un error 405, significa que la URL es accesible)

2. **Verifica los logs de ngrok:**
   - En la terminal de ngrok deberías ver las peticiones entrantes
   - Si no ves nada, Payku no está pudiendo alcanzar tu servidor

3. **Verifica la URL del webhook:**
   - Revisa los logs del backend al crear la orden
   - La URL debe ser HTTPS (ngrok siempre usa HTTPS)

### El webhook llega pero falla

1. **Revisa los logs del backend:**
   - Busca errores en el procesamiento del webhook
   - Verifica que la orden exista en la base de datos

2. **Verifica el formato del webhook:**
   - Payku envía datos en formato JSON
   - Revisa que el endpoint esté parseando correctamente

## 📝 Notas

- **Desarrollo local:** Puedes usar el endpoint de verificación manual si ngrok no está disponible
- **Producción:** Necesitarás una URL pública real (no ngrok) configurada en Payku
- **Sandbox vs Producción:** Asegúrate de usar tokens de sandbox para pruebas

