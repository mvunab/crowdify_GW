# Solución de Problemas con Token de Mercado Pago

## Problema: Token APP_USR-... inválido o expirado

Si estás recibiendo errores relacionados con el token de Mercado Pago (como `APP_USR-8730015517513045-111209-d3077ef6a256cb4c7599e03efb12bd44-2984124186`), sigue estos pasos:

## 1. Ejecutar Diagnóstico

Primero, ejecuta el script de diagnóstico para identificar el problema exacto:

```bash
python scripts/diagnose_mercadopago_token.py
```

Este script verificará:
- ✅ Si el token está configurado
- ✅ Si el formato del token es correcto
- ✅ Si el token es válido y tiene permisos
- ✅ Si puede crear preferencias de pago

## 2. Problemas Comunes y Soluciones

### Error 401: Token Inválido o Expirado

**Síntomas:**
- Error `401 Unauthorized` al crear preferencias
- Mensaje: "Token inválido o expirado"

**Soluciones:**

1. **Obtener un nuevo Access Token:**
   - Ve a: https://www.mercadopago.com/developers/panel/app
   - Selecciona tu aplicación
   - Copia el **Access Token** (no el Public Key)
   - Actualiza tu archivo `.env`:
     ```env
     MERCADOPAGO_ACCESS_TOKEN=APP_USR-tu-nuevo-token-aqui
     ```

2. **Verificar que el token no haya sido revocado:**
   - Los tokens pueden ser revocados si:
     - Cambiaste la contraseña de tu cuenta
     - Revocaste la autorización de la aplicación
     - Hubo un problema de seguridad

3. **Verificar el ambiente:**
   - Si usas un token de producción (`APP_USR-`), asegúrate de que:
     ```env
     MERCADOPAGO_ENVIRONMENT=production
     ```
   - Si usas un token de prueba (`TEST-`), asegúrate de que:
     ```env
     MERCADOPAGO_ENVIRONMENT=sandbox
     ```

### Error 403: Token Sin Permisos

**Síntomas:**
- Error `403 Forbidden` al crear preferencias
- Mensaje: "Token sin permisos suficientes"

**Soluciones:**

1. **Verificar permisos de la aplicación:**
   - Ve a: https://www.mercadopago.com/developers/panel/app
   - Verifica que tu aplicación tenga los permisos necesarios:
     - ✅ Crear preferencias de pago
     - ✅ Recibir notificaciones (webhooks)
     - ✅ Consultar pagos

2. **Regenerar credenciales:**
   - Si los permisos no están correctos, regenera las credenciales desde el panel

### Token Expirado

Los tokens de Mercado Pago pueden expirar en diferentes situaciones:

- **Tokens OAuth (Authorization Code):** Válidos por 180 días (6 meses)
- **Tokens Client Credentials:** Válidos por 6 horas
- **Tokens pueden ser revocados:** Por cambio de contraseña, revocación manual, etc.

**Solución:**
1. Obtén un nuevo token desde el panel de desarrolladores
2. Actualiza tu archivo `.env`
3. Reinicia tu aplicación backend

## 3. Verificar Configuración

Asegúrate de que tu archivo `.env` tenga la configuración correcta:

```env
# Token de Mercado Pago (REQUERIDO)
MERCADOPAGO_ACCESS_TOKEN=APP_USR-tu-token-aqui

# Public Key (opcional para backend, requerido para frontend)
MERCADOPAGO_PUBLIC_KEY=APP_USR-tu-public-key-aqui

# Ambiente: sandbox o production
MERCADOPAGO_ENVIRONMENT=sandbox

# Webhook Secret (opcional para desarrollo)
MERCADOPAGO_WEBHOOK_SECRET=tu-webhook-secret-aqui
```

## 4. Probar la Conexión

Después de actualizar el token, prueba la conexión:

```bash
python test_mercadopago.py
```

O usa el script de diagnóstico:

```bash
python scripts/diagnose_mercadopago_token.py
```

## 5. Logs del Backend

Si el problema persiste, revisa los logs del backend. El servicio mejorado ahora incluye:

- ✅ Detección automática de tokens inválidos (401)
- ✅ Detección de tokens sin permisos (403)
- ✅ Mensajes de error más descriptivos
- ✅ Logging detallado para diagnóstico

Busca en los logs mensajes como:
```
[ERROR] Token inválido: ... (Status: 401)
[ERROR] Error creando preferencia de Mercado Pago
[ERROR] Token usado: APP_USR-...
```

## 6. Obtener Nuevo Token

### Para Sandbox (Pruebas):
1. Ve a: https://www.mercadopago.com/developers/panel/app
2. Selecciona tu aplicación de prueba
3. Copia el **Access Token** (debe empezar con `TEST-`)
4. Actualiza `.env` con `MERCADOPAGO_ENVIRONMENT=sandbox`

### Para Producción:
1. Ve a: https://www.mercadopago.com/developers/panel/app
2. Selecciona tu aplicación de producción
3. Copia el **Access Token** (debe empezar con `APP_USR-`)
4. Actualiza `.env` con `MERCADOPAGO_ENVIRONMENT=production`

## 7. Contacto con Soporte

Si el problema persiste después de seguir estos pasos:

1. Verifica que tu cuenta de Mercado Pago esté activa
2. Revisa el estado de tu aplicación en el panel de desarrolladores
3. Contacta al soporte de Mercado Pago con:
   - El ID de tu aplicación
   - El tipo de error que recibes
   - Los logs del backend

## Recursos Adicionales

- [Documentación de Mercado Pago](https://www.mercadopago.com/developers/es/docs)
- [Panel de Desarrolladores](https://www.mercadopago.com/developers/panel/app)
- [Guía de Setup](MERCADOPAGO_SETUP.md)








