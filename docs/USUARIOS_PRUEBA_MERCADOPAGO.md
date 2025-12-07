# Cómo Usar Usuarios de Prueba de Mercado Pago

## El Problema

Cuando usas credenciales `APP_USR-` (aunque sean de prueba), Mercado Pago requiere que uses **usuarios de prueba** de Mercado Pago, no tarjetas de prueba genéricas.

## Solución: Crear Usuarios de Prueba

### Paso 1: Crear Usuario de Prueba

1. Ve a: https://www.mercadopago.cl/developers/panel/app
2. En el menú lateral, busca **"Usuarios de prueba"** o **"Test users"**
3. Crea un nuevo usuario de prueba
4. Anota el email y contraseña del usuario de prueba

### Paso 2: Usar el Usuario de Prueba

1. **Inicia sesión** en Mercado Pago con el usuario de prueba (no con tu cuenta real)
2. **Agrega una tarjeta de prueba** desde el panel del usuario de prueba
3. **Usa esa tarjeta** en tu aplicación

### Paso 3: Tarjetas de Prueba para Usuarios de Prueba

Con usuarios de prueba, puedes usar estas tarjetas:

**Para Aprobación Inmediata:**
- Número: `5031 7557 3453 0604`
- CVV: `123`
- Fecha: Cualquier fecha futura
- Nombre: El nombre del usuario de prueba

**Para Rechazo:**
- Número: `5031 4332 1540 6351`
- CVV: `123`
- Fecha: Cualquier fecha futura

## Alternativa: Obtener Credenciales TEST-

Si prefieres usar sandbox real:

1. Ve a: https://www.mercadopago.cl/developers/panel/app
2. Crea una **nueva aplicación** o selecciona una existente
3. Busca **"Credenciales de prueba"** o **"Test credentials"**
4. Si aparecen credenciales que empiezan con `TEST-`, úsalas con `MERCADOPAGO_ENVIRONMENT=sandbox`

## Nota Importante

Las credenciales `APP_USR-` que tienes son válidas, pero:
- ✅ Funcionan en `MERCADOPAGO_ENVIRONMENT=production`
- ✅ Requieren usuarios de prueba de Mercado Pago (no tarjetas genéricas)
- ❌ No funcionan con tarjetas de prueba genéricas (documento "Otro", número "123456789")

## Recursos

- [Documentación de Usuarios de Prueba](https://www.mercadopago.cl/developers/es/docs/checkout-api/testing)
- [Panel de Desarrolladores](https://www.mercadopago.cl/developers/panel/app)

