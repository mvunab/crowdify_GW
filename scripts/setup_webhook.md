# 🔔 Guía Rápida: Configurar Webhook de Mercado Pago

## Opción 1: Desarrollo Local con ngrok (Recomendado)

### Paso 1: Instalar ngrok

**Windows (con Chocolatey):**
```bash
choco install ngrok
```

**O descargar manualmente:**
1. Ve a https://ngrok.com/download
2. Descarga para Windows
3. Extrae `ngrok.exe` a una carpeta en tu PATH (ej: `C:\Program Files\ngrok\`)

### Paso 2: Iniciar ngrok

Abre una nueva terminal y ejecuta:
```bash
ngrok http 8000
```

Esto te dará una URL como: `https://abc123.ngrok.io`

**⚠️ IMPORTANTE:** Mantén esta terminal abierta mientras trabajas.

### Paso 3: Configurar Webhook en Mercado Pago

1. **Copia la URL de ngrok** (ej: `https://abc123.ngrok.io`)
2. Ve a: https://www.mercadopago.com/developers/panel/app
3. Selecciona tu aplicación
4. Ve a **Webhooks > Configurar notificaciones**
5. Pestaña **Modo productivo** (o **Modo test** si estás en sandbox)
6. URL: `https://abc123.ngrok.io/api/v1/purchases/webhook`
7. Evento: Selecciona **Order (Mercado Pago)**
8. Click en **Guardar configuración**

### Paso 4: Obtener Webhook Secret

1. Después de guardar, Mercado Pago mostrará una **clave secreta**
2. Haz click en **Revelar** para verla
3. **Cópiala** (la necesitarás en el siguiente paso)

### Paso 5: Agregar Secret al .env

Abre tu archivo `.env` y agrega:

```env
MERCADOPAGO_WEBHOOK_SECRET=tu-clave-secreta-aqui
```

### Paso 6: Reiniciar Backend

```bash
docker-compose restart backend
```

## Opción 2: Producción (Si tienes URL pública)

### Paso 1: Configurar Webhook

1. Ve a: https://www.mercadopago.com/developers/panel/app
2. Selecciona tu aplicación
3. Ve a **Webhooks > Configurar notificaciones**
4. Pestaña **Modo productivo**
5. URL: `https://tu-dominio.com/api/v1/purchases/webhook`
6. Evento: **Order (Mercado Pago)**
7. Click en **Guardar configuración**

### Paso 2: Obtener y Configurar Secret

Igual que en la Opción 1, pasos 4-6.

## ✅ Verificar que Funciona

### Opción A: Usar MCP de Mercado Pago

Puedes simular una notificación de prueba usando el MCP.

### Opción B: Hacer una Compra de Prueba

1. Crea una compra de prueba
2. Completa el pago en Mercado Pago
3. Revisa los logs del backend:
   ```bash
   docker-compose logs -f backend | grep webhook
   ```

Deberías ver:
```
✅ Webhook verificado correctamente
```

## 🐛 Troubleshooting

### Webhook no se recibe

1. **Verifica que ngrok esté corriendo:**
   ```bash
   # Debe mostrar "Forwarding https://xxx.ngrok.io -> http://localhost:8000"
   ```

2. **Verifica que el backend esté accesible:**
   ```bash
   curl https://tu-url-ngrok.ngrok.io/api/v1/purchases/webhook
   # Debe retornar 405 (Method Not Allowed) o similar, no 404
   ```

3. **Verifica en Mercado Pago:**
   - Ve a **Webhooks > Historial de notificaciones**
   - Revisa si hay errores de entrega

### Firma no coincide

1. Verifica que `MERCADOPAGO_WEBHOOK_SECRET` esté correcto en `.env`
2. Reinicia el backend después de agregar el secret
3. Revisa los logs para ver el error específico

## 📝 Notas Importantes

- **ngrok gratuito**: La URL cambia cada vez que reinicias ngrok. Si necesitas una URL fija, usa ngrok Pro.
- **Desarrollo vs Producción**: Usa **Modo test** en sandbox y **Modo productivo** en producción.
- **HTTPS requerido**: Mercado Pago solo envía webhooks a URLs HTTPS.


