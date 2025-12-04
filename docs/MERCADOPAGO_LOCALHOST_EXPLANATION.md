# Mercado Pago: ¿Se puede probar en localhost?

## ❌ No, el checkout de Mercado Pago NO se ejecuta en localhost

**Importante:** El checkout de Mercado Pago **siempre** se ejecuta en los servidores de Mercado Pago, no en tu máquina local.

### ¿Dónde se ejecuta el checkout?

- **Sandbox (Pruebas):** `https://sandbox.mercadopago.cl`
- **Producción:** `https://www.mercadopago.cl`

### ¿Qué SÍ se ejecuta en localhost?

✅ **Tu backend (FastAPI):** `http://localhost:8000`
- Crea las preferencias de pago
- Recibe webhooks de Mercado Pago
- Procesa las respuestas de pago

✅ **Tu frontend (React):** `http://localhost:3000`
- Muestra la información del evento
- Redirige al usuario al checkout de Mercado Pago
- Maneja las respuestas después del pago

❌ **El checkout de Mercado Pago:** NO se ejecuta en localhost
- Se ejecuta en los servidores de Mercado Pago
- Tu aplicación solo redirige al usuario a ese checkout

---

## 🔄 Flujo Completo

```
1. Usuario en localhost:3000 (tu frontend)
   ↓
2. Usuario hace clic en "Comprar"
   ↓
3. Frontend llama a localhost:8000/api/v1/purchases (tu backend)
   ↓
4. Backend crea preferencia en Mercado Pago API
   ↓
5. Backend retorna payment_link (URL de Mercado Pago)
   ↓
6. Frontend redirige al usuario a:
   https://sandbox.mercadopago.cl/checkout/v1/redirect?pref_id=...
   ↓
7. Usuario completa el pago en los servidores de Mercado Pago
   ↓
8. Mercado Pago redirige de vuelta a tu aplicación:
   https://tu-ngrok-url.ngrok-free.dev/compra-exitosa
   ↓
9. Tu frontend procesa la respuesta
```

---

## 🧪 Cómo Probar el Checkout

### Opción 1: Abrir el payment_link directamente

1. **Obtén un payment_link:**
   ```bash
   cd /Users/matiasvargasmarin/Desktop/crowdify/crowdify_GW
   ./scripts/test_payment_link.sh
   ```

2. **Copia el payment_link que se muestra**

3. **Abre el link en Chrome o Firefox (NO Brave):**
   - Brave bloquea scripts de Mercado Pago
   - Chrome/Firefox funcionan correctamente

4. **Completa el pago con tarjeta de prueba:**
   - Número: `4168 8188 4444 7115`
   - CVV: `123`
   - Fecha: Cualquier fecha futura
   - Nombre: `APRO`
   - Email: `test@test.com`

### Opción 2: Probar desde tu frontend

1. **Asegúrate de que ngrok esté corriendo:**
   ```bash
   ngrok http 3000
   ```

2. **Actualiza NGROK_URL en .env:**
   ```bash
   ./update_ngrok_url.sh https://tu-url.ngrok-free.dev
   ```

3. **Reinicia el backend:**
   ```bash
   docker compose restart backend
   ```

4. **Abre tu frontend en Chrome/Firefox:**
   - `http://localhost:3000`
   - NO uses Brave (bloquea scripts de Mercado Pago)

5. **Intenta comprar un ticket**

---

## ⚠️ Problemas Comunes

### Error: `ERR_BLOCKED_BY_CLIENT`

**Causa:** Brave Browser bloquea scripts de Mercado Pago

**Solución:**
1. Usa Chrome o Firefox para pruebas
2. O configura Brave para permitir scripts de Mercado Pago:
   - Desactiva Brave Shield para `sandbox.mercadopago.cl`
   - Permite cookies de terceros
   - Permite scripts de `*.mercadopago.cl` y `*.mercadolibre.com`

### Error: `payment_link` es null

**Causa:** El backend no pudo crear la preferencia

**Solución:**
1. Verifica que `MERCADOPAGO_ACCESS_TOKEN` esté configurado en `.env`
2. Verifica los logs del backend:
   ```bash
   docker compose logs backend | grep MercadoPago
   ```
3. Ejecuta la prueba con curl:
   ```bash
   ./scripts/test_mercadopago_curl.sh
   ```

### Error: `back_urls` vacías

**Causa:** Mercado Pago rechaza URLs HTTP

**Solución:**
1. Usa ngrok para obtener una URL HTTPS
2. Configura `NGROK_URL` en `.env`
3. El backend usará automáticamente `NGROK_URL` para `back_urls`

---

## ✅ Verificación

### Verificar que el backend funciona:

```bash
# Prueba con curl
./scripts/test_mercadopago_curl.sh

# Deberías ver:
# ✅ Backend funcionando correctamente
# ✅ Compra creada exitosamente
# ✅ payment_link generado correctamente
```

### Verificar que el payment_link funciona:

```bash
# Obtener un payment_link
./scripts/test_payment_link.sh

# Abrir el link en Chrome/Firefox
# Intentar completar el pago con tarjeta de prueba
```

---

## 📝 Resumen

- ❌ **NO puedes ejecutar el checkout de Mercado Pago en localhost**
- ✅ **SÍ puedes probar tu backend en localhost**
- ✅ **SÍ puedes probar tu frontend en localhost**
- ✅ **El checkout se ejecuta en los servidores de Mercado Pago**
- ✅ **Puedes probar el checkout abriendo el payment_link en un navegador**

**El checkout de Mercado Pago es un servicio externo que se ejecuta en los servidores de Mercado Pago, no en tu máquina local.**

---

**Última actualización:** 2025-12-04

