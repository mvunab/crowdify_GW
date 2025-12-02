# 🔔 Configurar Webhook de Mercado Pago - Guía Rápida

## 📋 Pasos a Seguir

### Paso 1: Instalar ngrok (si no lo tienes)

**Opción A: Descarga Manual (Recomendado)**
1. Ve a: https://ngrok.com/download
2. Descarga la versión para Windows
3. Extrae `ngrok.exe` a una carpeta (ej: `C:\ngrok\`)
4. Agrega esa carpeta a tu PATH o úsalo directamente

**Opción B: Con winget (si tienes Windows 10/11)**
```powershell
winget install ngrok
```

### Paso 2: Iniciar ngrok

Abre una **nueva terminal** y ejecuta:

```bash
ngrok http 8000
```

**⚠️ IMPORTANTE:** Mantén esta terminal abierta. Verás algo como:

```
Forwarding   https://abc123.ngrok.io -> http://localhost:8000
```

**Copia la URL HTTPS** (ej: `https://abc123.ngrok.io`)

### Paso 3: Configurar Webhook en Mercado Pago

1. Ve a: **https://www.mercadopago.com/developers/panel/app**
2. Selecciona tu aplicación
3. En el menú izquierdo: **Webhooks > Configurar notificaciones**
4. **IMPORTANTE**: Hay DOS pestañas:
   - **Modo test** (para desarrollo/sandbox) ← **USA ESTA para desarrollo**
   - **Modo productivo** (para producción)
5. Selecciona la pestaña **Modo test**
6. URL: `https://TU-URL-NGROK.ngrok.io/api/v1/purchases/webhook`
   - Reemplaza `TU-URL-NGROK` con la URL que copiaste de ngrok
7. Evento: Selecciona **Order (Mercado Pago)**
8. Click en **Guardar configuración**

**💡 Nota**: El webhook en "Modo test" solo recibirá notificaciones de pagos de prueba (sandbox). Para producción, configura otro webhook en la pestaña "Modo productivo".

### Paso 4: Obtener Webhook Secret

Después de guardar, Mercado Pago mostrará una **clave secreta**:

1. Haz click en **Revelar** para verla
2. **Copia la clave completa** (es larga, algo como: `abc123def456...`)

### Paso 5: Agregar Secret al .env

Abre tu archivo `.env` en la raíz del proyecto y agrega:

```env
MERCADOPAGO_WEBHOOK_SECRET=tu-clave-secreta-completa-aqui
```

**Ejemplo:**
```env
MERCADOPAGO_WEBHOOK_SECRET=abc123def456ghi789jkl012mno345pqr678stu901vwx234yz
```

### Paso 6: Reiniciar Backend

```bash
docker-compose restart backend
```

### Paso 7: Verificar que Funciona

1. Haz una compra de prueba
2. Completa el pago en Mercado Pago
3. Revisa los logs del backend:

```bash
docker-compose logs -f backend | grep webhook
```

Deberías ver:
```
✅ Webhook verificado correctamente
```

## 🎯 Resumen de URLs

- **URL de ngrok**: `https://abc123.ngrok.io` (cambia cada vez que reinicias ngrok)
- **URL del webhook**: `https://abc123.ngrok.io/api/v1/purchases/webhook`
- **URL en Mercado Pago**: Pega la URL del webhook en el panel

## ⚠️ Notas Importantes

1. **ngrok gratuito**: La URL cambia cada vez que reinicias ngrok
   - Si necesitas una URL fija, considera ngrok Pro o usar una URL de producción

2. **Mantén ngrok corriendo**: 
   - Debes mantener la terminal de ngrok abierta mientras trabajas
   - Si cierras ngrok, el webhook dejará de funcionar

3. **HTTPS requerido**: 
   - Mercado Pago solo envía webhooks a URLs HTTPS
   - ngrok proporciona HTTPS automáticamente

4. **Desarrollo vs Producción**:
   - **Sandbox/Desarrollo**: 
     - Usa la pestaña **Modo test** en Mercado Pago
     - Puedes usar ngrok para la URL
     - Solo recibirá notificaciones de pagos de prueba
   - **Producción**: 
     - Usa la pestaña **Modo productivo** en Mercado Pago
     - Debe ser una URL real (no ngrok)
     - Recibirá notificaciones de pagos reales

## 🐛 Troubleshooting

### "Webhook no se recibe"

1. Verifica que ngrok esté corriendo:
   - Debe mostrar "Forwarding https://xxx.ngrok.io -> http://localhost:8000"

2. Verifica que el backend esté corriendo:
   ```bash
   docker-compose ps backend
   ```

3. Prueba la URL manualmente:
   ```bash
   curl https://tu-url-ngrok.ngrok.io/api/v1/purchases/webhook
   ```
   Debe retornar 405 (Method Not Allowed), no 404

### "Firma no coincide"

1. Verifica que `MERCADOPAGO_WEBHOOK_SECRET` esté correcto en `.env`
2. No debe tener espacios extra
3. Reinicia el backend después de agregar el secret

### "ngrok no se conecta"

1. Verifica que el puerto 8000 esté libre
2. Verifica que el backend esté corriendo en el puerto 8000
3. Prueba con otro puerto si es necesario

## ✅ Checklist

- [ ] ngrok instalado
- [ ] ngrok corriendo en puerto 8000
- [ ] URL de ngrok copiada
- [ ] Webhook configurado en panel de Mercado Pago
- [ ] Webhook Secret copiado
- [ ] `MERCADOPAGO_WEBHOOK_SECRET` agregado al `.env`
- [ ] Backend reiniciado
- [ ] Webhook probado con compra de prueba

## 🚀 Siguiente Paso

Una vez configurado, el webhook funcionará automáticamente:
- Cuando un usuario pague, Mercado Pago notificará a tu backend
- El backend actualizará la orden y generará los tickets automáticamente
- El usuario verá sus tickets al volver a tu app

