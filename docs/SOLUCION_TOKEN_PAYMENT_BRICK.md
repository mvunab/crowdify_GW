# Solución: Error "Unauthorized use of live credentials" con Payment Brick

## 🔴 Problema

Cuando intentas crear un pago usando **Payment Brick** en sandbox con un token `APP_USR-`, recibes el error:

```
Unauthorized use of live credentials
```

## 🔍 Causa

Aunque Mercado Pago puede proporcionar tokens `APP_USR-` como "credenciales de prueba", cuando usas **Payment Brick** en el entorno sandbox, Mercado Pago **REQUIERE específicamente un token que empiece con `TEST-`**.

**Importante:**
- ✅ Los tokens `APP_USR-` **SÍ funcionan** para crear preferencias en sandbox
- ❌ Los tokens `APP_USR-` **NO funcionan** para crear pagos con Payment Brick en sandbox
- ✅ Para Payment Brick en sandbox, necesitas un token `TEST-`

## ✅ Solución

### Paso 1: Obtener un Token TEST-

1. Ve al panel de desarrolladores de Mercado Pago:
   ```
   https://www.mercadopago.com/developers/panel/app
   ```

2. Selecciona tu aplicación

3. Ve a la sección **"Credenciales de prueba"** (no "Credenciales de producción")

4. Busca el campo **"Access Token"** que empiece con `TEST-`

5. Copia ese token completo

### Paso 2: Actualizar el archivo .env

En tu archivo `.env` del backend (`C:\Users\Andres\Documents\MATIAS PROJECTS\crowdify_GW\.env`), actualiza:

```env
# Cambia esto:
MERCADOPAGO_ACCESS_TOKEN=APP_USR-8730015517513045-111209-...

# Por esto (el token TEST- que obtuviste):
MERCADOPAGO_ACCESS_TOKEN=TEST-tu-token-de-prueba-aqui

# Asegúrate de que el entorno esté en sandbox:
MERCADOPAGO_ENVIRONMENT=sandbox
```

### Paso 3: Reiniciar el Backend

Después de actualizar el `.env`, reinicia tu servidor FastAPI para que cargue las nuevas credenciales.

## 📝 Notas Importantes

### ¿Por qué dos tipos de tokens?

- **Tokens `APP_USR-`**: Funcionan para crear preferencias y algunos flujos en sandbox, pero **NO** para Payment Brick en sandbox
- **Tokens `TEST-`**: Funcionan para **todo** en sandbox, incluyendo Payment Brick

### ¿Qué pasa con las Public Keys?

Las Public Keys (`APP_USR-5548d6e2-...`) que te dieron **SÍ funcionan** para el frontend. No necesitas cambiarlas.

Solo necesitas cambiar el **Access Token** en el backend.

## 🔄 Verificación

Después de actualizar el token, intenta crear un pago nuevamente. El error debería desaparecer.

Si aún tienes problemas, verifica:

1. ✅ El token empieza con `TEST-`
2. ✅ `MERCADOPAGO_ENVIRONMENT=sandbox` en el `.env`
3. ✅ Reiniciaste el servidor después de cambiar el `.env`
4. ✅ Estás usando el token correcto (no el de producción)

## 🆘 Si no encuentras el token TEST-

Si en el panel de Mercado Pago no ves un token `TEST-` en "Credenciales de prueba", es posible que:

1. Necesites generar nuevas credenciales de prueba
2. Tu aplicación no tenga habilitadas las credenciales de prueba
3. Necesites contactar con el soporte de Mercado Pago

En ese caso, puedes:
- Usar el flujo de Checkout Pro (redirección) en lugar de Payment Brick, que sí funciona con tokens `APP_USR-` en sandbox
- O solicitar a Mercado Pago que te proporcione un token `TEST-` específicamente

## 📚 Referencias

- [Documentación de Mercado Pago - Credenciales](https://www.mercadopago.com/developers/es/docs/checkout-api/additional-content/credentials)
- [Documentación de Payment Brick](https://www.mercadopago.com/developers/es/docs/checkout-bricks/payment-brick/introduction)




