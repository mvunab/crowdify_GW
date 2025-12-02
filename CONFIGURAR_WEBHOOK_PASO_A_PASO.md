# 🔔 Configurar Webhook - Paso a Paso Visual

## ❌ Problema Actual

Tienes configurado:
```
URL para prueba: https://localhost:3000/
```

**Esto NO funciona** porque:
- ❌ `localhost` no es accesible desde internet
- ❌ El puerto es 3000, pero tu backend está en **8000**
- ❌ Mercado Pago necesita una URL HTTPS pública

## ✅ Solución: Usar ngrok

### Paso 1: Instalar ngrok (si no lo tienes)

**Opción A: Descarga Manual**
1. Ve a: https://ngrok.com/download
2. Descarga para Windows
3. Extrae `ngrok.exe` a una carpeta (ej: `C:\ngrok\`)

**Opción B: Con winget (Windows 10/11)**
```powershell
winget install ngrok
```

### Paso 2: Iniciar ngrok

Abre una **nueva terminal** (no cierres esta) y ejecuta:

```bash
ngrok http 8000
```

Verás algo como:
```
Forwarding   https://abc123.ngrok.io -> http://localhost:8000
```

**⚠️ IMPORTANTE**: Mantén esta terminal abierta mientras trabajas.

### Paso 3: Copiar la URL de ngrok

Copia la URL HTTPS que aparece (ej: `https://abc123.ngrok.io`)

### Paso 4: Configurar en Mercado Pago

1. En el panel de Mercado Pago, ve a **Webhooks > Configurar notificaciones**
2. Pestaña: **Modo de prueba** (ya la tienes seleccionada ✅)
3. **URL para prueba**: Reemplaza `https://localhost:3000/` con:
   ```
   https://TU-URL-NGROK.ngrok.io/api/v1/purchases/webhook
   ```
   
   **Ejemplo:**
   ```
   https://abc123.ngrok.io/api/v1/purchases/webhook
   ```
   
   ⚠️ **IMPORTANTE**: 
   - Reemplaza `TU-URL-NGROK` con la URL que copiaste de ngrok
   - Debe terminar en `/api/v1/purchases/webhook` (no solo `/`)
   - Debe ser HTTPS (ngrok lo proporciona automáticamente)

4. **Eventos**: Mantén seleccionado **Order (Mercado Pago)** ✅

5. **Clave secreta**: Ya la tienes generada ✅

6. Click en **Guardar configuración**

### Paso 5: Agregar Clave Secreta al .env

1. Copia la **Clave secreta** que muestra Mercado Pago
2. Abre tu archivo `.env` en la raíz del proyecto
3. Agrega esta línea:

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

## ✅ Verificar que Funciona

### Opción 1: Simular Notificación

En el panel de Mercado Pago, haz click en **"Simular notificación"** para probar.

### Opción 2: Hacer Compra de Prueba

1. Crea una compra de prueba
2. Completa el pago en Mercado Pago (sandbox)
3. Revisa los logs del backend:

```bash
docker-compose logs -f backend | grep webhook
```

Deberías ver:
```
✅ Webhook verificado correctamente
```

## 📋 Resumen de Configuración Correcta

```
Panel Mercado Pago:
├── Modo de prueba ✅
├── URL: https://abc123.ngrok.io/api/v1/purchases/webhook ✅
├── Evento: Order (Mercado Pago) ✅
└── Clave secreta: (copiada al .env) ✅
```

## ⚠️ Notas Importantes

1. **ngrok debe estar corriendo**: Mantén la terminal de ngrok abierta
2. **URL cambia**: Cada vez que reinicias ngrok, la URL cambia
3. **Actualizar URL**: Si reinicias ngrok, debes actualizar la URL en Mercado Pago
4. **Puerto correcto**: Tu backend está en puerto **8000**, no 3000

## 🐛 Troubleshooting

### "Revisa la URL que ingresaste"

- Verifica que la URL sea HTTPS (no HTTP)
- Verifica que termine en `/api/v1/purchases/webhook`
- Verifica que ngrok esté corriendo

### "Webhook no se recibe"

1. Verifica que ngrok esté corriendo:
   - Debe mostrar "Forwarding https://xxx.ngrok.io -> http://localhost:8000"

2. Prueba la URL manualmente:
   ```bash
   curl https://tu-url-ngrok.ngrok.io/api/v1/purchases/webhook
   ```
   Debe retornar 405 (Method Not Allowed), no 404

3. Verifica que el backend esté corriendo:
   ```bash
   docker-compose ps backend
   ```


