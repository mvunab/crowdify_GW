# Flujo de Compra Anónima - Verificación y Correcciones

## ✅ Correcciones Realizadas

### 1. **usePurchaseCallback - Compras Anónimas**
- **Problema**: El hook requería usuario autenticado para verificar el estado del pago
- **Solución**: Modificado para permitir verificación sin usuario usando solo el `order_id`
- **Archivo**: `crodify/src/hooks/usePurchaseCallback.ts`

### 2. **Endpoint de Estado - Acceso a Órdenes Anónimas**
- **Problema**: El endpoint `/api/v1/purchases/{order_id}/status` requería autenticación incluso para órdenes anónimas
- **Solución**: Modificado para permitir acceso sin autenticación a órdenes anónimas (sin `user_id`)
- **Archivo**: `crowdify_GW/services/ticket_purchase/routes/purchase.py`

### 3. **auto_return - Solo HTTPS**
- **Problema**: `auto_return` causaba error `invalid_auto_return` en desarrollo local (HTTP)
- **Solución**: Configurado para usar `auto_return` solo cuando `base_url` es HTTPS
- **Archivo**: `crowdify_GW/services/ticket_purchase/services/mercado_pago_service.py`

### 4. **payment_methods - Guest Checkout**
- **Problema**: No estaba explícitamente configurado para permitir pagos sin cuenta
- **Solución**: Agregada configuración `payment_methods` sin exclusiones
- **Archivo**: `crowdify_GW/services/ticket_purchase/services/mercado_pago_service.py`

## ⚠️ Configuraciones Necesarias

### 1. **APP_BASE_URL en Backend**

**IMPORTANTE**: Verifica que `APP_BASE_URL` en el backend apunte al puerto correcto del frontend.

En el archivo `.env` del backend (`crowdify_GW/.env`):

```env
# Si el frontend corre en http://localhost:3000
APP_BASE_URL=http://localhost:3000

# Si el frontend corre en http://localhost:5173 (Vite por defecto)
APP_BASE_URL=http://localhost:5173
```

**Verificar puerto del frontend:**
- Revisa los logs del frontend al iniciar
- O verifica en `crodify/vite.config.ts` o `crodify/package.json`

### 2. **Variables de Entorno de Mercado Pago**

Asegúrate de tener configurado en `crowdify_GW/.env`:

```env
MERCADOPAGO_ACCESS_TOKEN=tu-token-de-sandbox
MERCADOPAGO_PUBLIC_KEY=tu-public-key
MERCADOPAGO_ENVIRONMENT=sandbox
APP_BASE_URL=http://localhost:3000  # O el puerto que uses
```

## 📋 Flujo Completo de Compra Anónima

### Paso 1: Usuario inicia compra
1. Usuario selecciona evento y asistentes
2. **NO** está autenticado (compra anónima)
3. Completa datos de asistentes (nombre, email, documento)
4. Selecciona método de pago: Mercado Pago

### Paso 2: Backend crea orden y preferencia
1. Frontend envía `POST /api/v1/purchases` **sin** `user_id`
2. Backend crea orden con `user_id = NULL` (anónima)
3. Backend crea preferencia en Mercado Pago con:
   - `back_urls` apuntando a `{APP_BASE_URL}/compra-exitosa`, etc.
   - `payment_methods` sin exclusiones (permite guest checkout)
   - `auto_return` solo si `APP_BASE_URL` es HTTPS
   - `payer` con email y nombre del primer asistente

### Paso 3: Usuario paga en Mercado Pago
1. Frontend redirige a `payment_link` de Mercado Pago
2. Usuario **NO** inicia sesión en Mercado Pago
3. Usuario ingresa datos de tarjeta de prueba:
   - Número: `5031 7557 3453 0604` (Chile - Aprobada)
   - CVV: `123`
   - Fecha: Cualquier fecha futura
   - Nombre: `APRO` (o cualquier nombre)
   - Email: Cualquier email de prueba (ej: `test_user_123@testuser.com`)

### Paso 4: Callback de Mercado Pago
1. Mercado Pago redirige a `{APP_BASE_URL}/compra-exitosa?payment_id=xxx&status=approved&external_reference={order_id}`
2. **Webhook** también se ejecuta en paralelo: `POST /api/v1/purchases/webhook`
3. Backend procesa el webhook y actualiza el estado de la orden

### Paso 5: Frontend verifica estado
1. `usePurchaseCallback` detecta parámetros en la URL
2. Extrae `order_id` de `external_reference` o `order_id`
3. Llama a `GET /api/v1/purchases/{order_id}/status` **sin autenticación**
4. Backend permite acceso porque la orden es anónima (`user_id = NULL`)
5. Frontend muestra estado y mensaje de éxito

## 🧪 Pruebas a Realizar

### 1. Verificar Configuración
```bash
# En backend
cd crowdify_GW
cat .env | grep APP_BASE_URL

# Verificar que coincida con el puerto del frontend
```

### 2. Probar Flujo Completo
1. ✅ Iniciar backend: `make up` o `docker compose up`
2. ✅ Iniciar frontend: `npm run dev`
3. ✅ Navegar a un evento sin autenticarse
4. ✅ Completar formulario de compra
5. ✅ Seleccionar Mercado Pago
6. ✅ Verificar que se redirige a Mercado Pago
7. ✅ Usar tarjeta de prueba sin iniciar sesión
8. ✅ Verificar redirección a `/compra-exitosa`
9. ✅ Verificar que se muestra mensaje de éxito

### 3. Verificar Logs
- Backend: Verificar que la preferencia se crea correctamente
- Backend: Verificar que el webhook se procesa
- Frontend: Verificar que `usePurchaseCallback` detecta los parámetros
- Frontend: Verificar que se puede acceder al estado sin autenticación

## 🔍 Posibles Problemas y Soluciones

### Problema 1: `payment_link` es `null`
**Causa**: Error al crear la preferencia (ej: `invalid_auto_return`)
**Solución**: Verificar que `APP_BASE_URL` no use `auto_return` con HTTP

### Problema 2: No se puede verificar estado sin usuario
**Causa**: Endpoint requiere autenticación
**Solución**: Ya corregido - permite acceso a órdenes anónimas

### Problema 3: Redirección a URL incorrecta
**Causa**: `APP_BASE_URL` apunta a puerto incorrecto
**Solución**: Actualizar `APP_BASE_URL` en `.env` del backend

### Problema 4: Tarjeta de prueba no funciona
**Causa**: Credenciales incorrectas o ambiente incorrecto
**Solución**: 
- Verificar `MERCADOPAGO_ENVIRONMENT=sandbox`
- Usar tarjetas de prueba correctas para tu país
- Verificar que el token sea de sandbox

## 📝 Notas Importantes

1. **Compras Anónimas**: Las órdenes sin `user_id` se pueden verificar usando solo el `order_id`
2. **Webhook**: Es crítico para actualizar el estado, pero el callback de URL también funciona
3. **Tarjetas de Prueba**: Varían por país, consulta documentación de Mercado Pago
4. **auto_return**: Solo funciona con HTTPS, en desarrollo local no se usa

## ✅ Checklist Pre-Prueba

- [ ] `APP_BASE_URL` configurado correctamente en backend
- [ ] `MERCADOPAGO_ENVIRONMENT=sandbox` en backend
- [ ] `MERCADOPAGO_ACCESS_TOKEN` configurado (token de sandbox)
- [ ] Backend corriendo y accesible
- [ ] Frontend corriendo en el puerto especificado en `APP_BASE_URL`
- [ ] Rutas `/compra-exitosa`, `/compra-fallida`, `/compra-pendiente` existen en frontend
- [ ] Webhook configurado (opcional para desarrollo local, requiere ngrok)

