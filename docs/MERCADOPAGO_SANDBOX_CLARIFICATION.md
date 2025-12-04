# Aclaración: Mercado Pago Sandbox y Localhost

## ❓ Pregunta: ¿Se puede probar Mercado Pago en localhost?

**Respuesta corta:** El checkout de Mercado Pago **NO se ejecuta en localhost**. Siempre se ejecuta en los servidores de Mercado Pago.

---

## 🔍 ¿Qué es el Sandbox de Mercado Pago?

El **Sandbox** es el ambiente de **pruebas** de Mercado Pago. Es un servidor real de Mercado Pago, pero configurado para pruebas:

- **URL del Sandbox:** `https://sandbox.mercadopago.cl`
- **URL de Producción:** `https://www.mercadopago.cl`

**Ambos se ejecutan en los servidores de Mercado Pago, NO en tu máquina local.**

---

## ✅ ¿Qué SÍ se ejecuta en localhost?

### 1. Tu Backend (FastAPI)
- **URL:** `http://localhost:8000`
- **Función:** 
  - Crea preferencias de pago en Mercado Pago
  - Recibe webhooks de Mercado Pago
  - Procesa respuestas de pago

### 2. Tu Frontend (React)
- **URL:** `http://localhost:3000`
- **Función:**
  - Muestra información del evento
  - Redirige al usuario al checkout de Mercado Pago
  - Maneja respuestas después del pago

### 3. ngrok (Opcional, para HTTPS)
- **URL:** `https://tu-url.ngrok-free.dev`
- **Función:**
  - Expone tu localhost con HTTPS
  - Necesario para `back_urls` y webhooks

---

## ❌ ¿Qué NO se ejecuta en localhost?

### El Checkout de Mercado Pago
- **NO se ejecuta en:** `http://localhost:3000` o `http://localhost:8000`
- **SÍ se ejecuta en:** `https://sandbox.mercadopago.cl` (sandbox) o `https://www.mercadopago.cl` (producción)

**El checkout es un servicio externo que siempre se ejecuta en los servidores de Mercado Pago.**

---

## 🔄 Flujo Completo de una Compra

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Usuario en localhost:3000 (tu frontend)                 │
│    - Ve el evento                                           │
│    - Hace clic en "Comprar"                                 │
└────────────────────┬──────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Frontend llama a localhost:8000/api/v1/purchases         │
│    (tu backend)                                              │
└────────────────────┬──────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Backend crea preferencia en Mercado Pago API            │
│    - Llama a api.mercadolibre.com/preferences               │
│    - Mercado Pago crea la preferencia                      │
│    - Retorna preference_id y payment_link                   │
└────────────────────┬──────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Backend retorna payment_link al frontend                 │
│    payment_link = "https://sandbox.mercadopago.cl/..."      │
└────────────────────┬──────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. Frontend redirige al usuario a:                         │
│    https://sandbox.mercadopago.cl/checkout/v1/redirect?... │
│    ⚠️ ESTO SE EJECUTA EN LOS SERVIDORES DE MERCADO PAGO     │
└────────────────────┬──────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. Usuario completa el pago en sandbox.mercadopago.cl       │
│    - Ingresa datos de tarjeta                                │
│    - Mercado Pago procesa el pago                           │
│    - Mercado Pago valida la tarjeta                         │
└────────────────────┬──────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 7. Mercado Pago redirige de vuelta a tu aplicación:        │
│    https://tu-ngrok-url.ngrok-free.dev/compra-exitosa      │
│    (con parámetros: payment_id, status, etc.)               │
└────────────────────┬──────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 8. Frontend procesa la respuesta                           │
│    - Verifica el estado del pago                            │
│    - Muestra mensaje de éxito/error                         │
└─────────────────────────────────────────────────────────────┘
```

---

## 🧪 Cómo Probar el Checkout

### Opción 1: Probar el payment_link directamente

1. **Obtén un payment_link:**
   ```bash
   cd /Users/matiasvargasmarin/Desktop/crowdify/crowdify_GW
   ./scripts/test_payment_link.sh
   ```

2. **Copia el payment_link que se muestra**

3. **Abre el link en Chrome o Firefox (NO Brave):**
   - El link será algo como: `https://sandbox.mercadopago.cl/checkout/v1/redirect?pref_id=...`
   - **Este link se ejecuta en los servidores de Mercado Pago, no en localhost**

4. **Completa el pago con tarjeta de prueba:**
   - Número: `4168 8188 4444 7115`
   - CVV: `123`
   - Fecha: Cualquier fecha futura (ej: 12/25)
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

5. **Intenta comprar un ticket:**
   - El frontend redirigirá a `sandbox.mercadopago.cl`
   - Completa el pago ahí
   - Mercado Pago redirigirá de vuelta a tu aplicación

---

## ⚠️ Problema Actual: Brave Browser

### El Error que Estás Viendo

Cuando intentas completar el pago en el checkout de Mercado Pago (que se ejecuta en `sandbox.mercadopago.cl`), Brave Browser bloquea los scripts necesarios para crear el token de la tarjeta.

**Esto NO es un problema del backend ni del frontend.** Es un problema del navegador.

### Solución

1. **Usa Chrome o Firefox para pruebas:**
   - Chrome: Funciona perfectamente
   - Firefox: Funciona perfectamente
   - Brave: Bloquea scripts de Mercado Pago

2. **O configura Brave para permitir scripts:**
   - Desactiva Brave Shield para `sandbox.mercadopago.cl`
   - Permite cookies de terceros
   - Permite scripts de `*.mercadopago.cl` y `*.mercadolibre.com`

---

## ✅ Verificación: Backend Funcionando

Las pruebas con `curl` confirman que el backend funciona perfectamente:

```bash
./scripts/test_mercadopago_curl.sh
```

**Resultado:**
- ✅ Backend funcionando correctamente
- ✅ Compra creada exitosamente
- ✅ Payment link generado correctamente
- ✅ Back URLs guardadas con HTTPS
- ✅ Preferencia verificada en Mercado Pago

**Conclusión:** El backend está funcionando. El problema es del navegador (Brave).

---

## 📝 Resumen

| Componente | ¿Dónde se ejecuta? | ¿Se puede probar en localhost? |
|------------|-------------------|-------------------------------|
| Tu Backend | `localhost:8000` | ✅ Sí |
| Tu Frontend | `localhost:3000` | ✅ Sí |
| Checkout de Mercado Pago | `sandbox.mercadopago.cl` | ❌ No (siempre en servidores de MP) |
| API de Mercado Pago | `api.mercadolibre.com` | ❌ No (siempre en servidores de MP) |

**El checkout de Mercado Pago es un servicio externo que siempre se ejecuta en los servidores de Mercado Pago, no en tu máquina local.**

---

**Última actualización:** 2025-12-04

