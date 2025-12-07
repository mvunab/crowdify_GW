# Cómo Solucionar `cc_rejected_high_risk` en Mercado Pago

## ¿Qué significa este error?

`cc_rejected_high_risk` significa que el sistema antifraude de Mercado Pago ha detectado un alto riesgo en la transacción y la ha rechazado automáticamente. 

**Mensaje específico del panel**: "Te protegimos de un pago sospechoso. Recomiéndale a tu cliente que pague con el medio de pago y dispositivo que suele usar para compras online."

Esto indica que Mercado Pago detectó un patrón sospechoso, posiblemente:
- Dispositivo nuevo o no reconocido
- Patrón de compra diferente al habitual del usuario
- Ubicación o IP diferente a la usual
- Datos que no coinciden con el historial del usuario

## Soluciones Inmediatas (Código)

### ✅ Ya Implementado

1. **Device ID**: Ya estamos enviando el `device_id` de Mercado Pago en el header `X-meli-session-id`
2. **Datos del Payer**: Ya enviamos nombre, email e identificación
3. **Additional Info**: Ya enviamos información de los items
4. **Statement Descriptor**: Ahora enviamos "TICKETS EVENTO" para que el cargo sea reconocible

## Soluciones en Mercado Pago (Panel)

### 1. Verificar el Rechazo Específico

1. Ve a tu [Panel de Mercado Pago](https://www.mercadopago.cl/developers/panel)
2. Navega a **Pagos** → **Pagos rechazados**
3. Busca el pago con ID `136222937919` (o el ID que corresponda)
4. Revisa la razón específica del rechazo

### 2. Revisar Configuración de Antifraude

1. En el panel, ve a **Configuración** → **Seguridad**
2. Revisa la configuración de **Prevención de Fraudes**
3. Ajusta el nivel de seguridad si es necesario (más bajo = menos rechazos, pero más riesgo)

### 3. Contactar Soporte de Mercado Pago

Si el problema persiste:

1. Ve a [Soporte de Mercado Pago](https://www.mercadopago.cl/developers/support)
2. Explica que estás recibiendo `cc_rejected_high_risk` en pagos legítimos
3. Proporciona:
   - **Número de operación**: `136222937919` (o el ID que corresponda)
   - Fecha y hora: 7 de diciembre - 01:28 hs
   - Monto: $2,000 CLP
   - Medio de pago: VISA Débito Santander terminada en 4208
   - Mensaje: "Te protegimos de un pago sospechoso"
   - Datos del comprador (sin información sensible)

### 4. Acciones Inmediatas Basadas en el Mensaje

El mensaje específico sugiere que el problema es con el **dispositivo o medio de pago**. Acciones recomendadas:

1. **Verificar Device ID**:
   - Asegúrate de que el script de seguridad de Mercado Pago esté cargado correctamente
   - Verifica en la consola del navegador que `MP_DEVICE_SESSION_ID` esté disponible
   - El Device ID debe ser consistente entre intentos

2. **Recomendaciones para el Cliente**:
   - Usar el mismo dispositivo que usa habitualmente para compras online
   - Usar la misma tarjeta que ha usado antes en Mercado Pago
   - Si es la primera vez que usa esta tarjeta, puede ser rechazada por seguridad

3. **Para Pruebas**:
   - Usa tarjetas de prueba primero (no tienen restricciones de antifraude)
   - Si pruebas con tarjetas reales, usa una tarjeta que el usuario ya haya usado antes en Mercado Pago

## Mejoras en los Datos del Comprador

### Verificar que los Datos Coincidan Exactamente

**CRÍTICO**: Los datos del comprador deben coincidir EXACTAMENTE con los datos de la tarjeta:

- ✅ **Nombre**: Debe ser exactamente como aparece en la tarjeta
- ✅ **Email**: Debe ser el email registrado en Mercado Pago (si tiene cuenta)
- ✅ **RUT/DNI**: Debe coincidir con el titular de la tarjeta
- ✅ **Dirección**: Si es posible, incluir dirección de facturación

### Mejoras que Podemos Implementar

1. **Agregar teléfono del comprador** (si está disponible)
2. **Agregar dirección de facturación** (si está disponible)
3. **Validar que el nombre no tenga caracteres especiales** innecesarios

## Soluciones para Tarjetas Reales

### Para Tarjetas de Débito/Crédito Reales

1. **Verificar con el Banco**:
   - Algunos bancos bloquean transacciones en línea por defecto
   - El usuario debe autorizar transacciones en línea con su banco

2. **Usar Tarjetas de Prueba Primero**:
   - Antes de probar con tarjetas reales, verifica que todo funcione con tarjetas de prueba
   - Las tarjetas de prueba no tienen restricciones de antifraude

3. **Construir Historial de Transacciones**:
   - Si tu cuenta es nueva, realiza transacciones pequeñas primero
   - Mercado Pago necesita ver un historial de transacciones exitosas

## Mejoras Adicionales en el Código

### Opción 1: Agregar Teléfono del Payer

Si tienes el teléfono del comprador, podemos agregarlo:

```python
payer_data["phone"] = {
    "area_code": "+56",  # Código de país
    "number": "912345678"  # Número sin espacios ni guiones
}
```

### Opción 2: Agregar Dirección de Facturación

Si tienes la dirección del comprador:

```python
payer_data["address"] = {
    "street_name": "Calle Principal",
    "street_number": 123,
    "zip_code": "1234567"
}
```

### Opción 3: Agregar Shipping en Additional Info

Para productos digitales (tickets), puedes indicar que no hay envío:

```python
additional_info["shipments"] = {
    "receiver_address": {
        "zip_code": "0000000",
        "state_name": "N/A",
        "city_name": "N/A",
        "street_name": "Digital",
        "street_number": 0
    }
}
```

## Diagnóstico del Device ID

### Verificar que el Device ID se Esté Capturando

1. **Abre la consola del navegador** (F12 → Console)
2. **Antes de hacer un pago**, ejecuta en la consola:
   ```javascript
   console.log('Device ID:', window.MP_DEVICE_SESSION_ID);
   ```
3. **Deberías ver** algo como: `armor.044dea17a4601167ac9cee...`
4. **Si es `null` o `undefined`**:
   - Verifica que el script de seguridad esté cargado: `<script src="https://www.mercadopago.com/v2/security.js" view="checkout"></script>`
   - Asegúrate de que el script se cargue ANTES del Payment Brick
   - Verifica que no haya errores de CORS o bloqueos de contenido

### Verificar en los Logs del Backend

Revisa los logs del backend para confirmar que el Device ID se está recibiendo:

```bash
docker-compose logs backend | grep "Device ID"
```

Deberías ver algo como:
```
[DEBUG MercadoPago] Usando API directa para incluir Device ID
[DEBUG MercadoPago]   - Device ID: armor.044dea17a46011...
```

## Verificación de Datos

### Checklist Antes de Probar con Tarjeta Real

- [ ] El nombre del comprador coincide exactamente con la tarjeta
- [ ] El RUT/DNI coincide con el titular de la tarjeta
- [ ] El email es válido y está activo
- [ ] El Device ID se está enviando correctamente (verificar en consola y logs)
- [ ] El `statement_descriptor` es claro y reconocible
- [ ] Los items en `additional_info` tienen información completa
- [ ] No hay intentos de pago duplicados con los mismos datos
- [ ] El cliente está usando un dispositivo que ha usado antes para compras online
- [ ] La tarjeta ha sido usada antes en Mercado Pago (si es posible)

## Soluciones Específicas para "Pago Sospechoso"

Basado en el mensaje del panel: **"Recomiéndale a tu cliente que pague con el medio de pago y dispositivo que suele usar para compras online"**

### Para el Cliente Final

1. **Usar dispositivo conocido**:
   - Si el cliente siempre compra desde su computadora, que use su computadora
   - Si siempre compra desde su celular, que use su celular
   - Evitar usar dispositivos nuevos o públicos

2. **Usar tarjeta conocida**:
   - Si el cliente tiene cuenta en Mercado Pago, usar una tarjeta que ya haya usado antes
   - Si es la primera vez usando esta tarjeta, puede ser rechazada por seguridad

3. **Usar la misma red/WiFi**:
   - Si es posible, usar la misma conexión a internet que usa habitualmente

### Para Desarrollo/Pruebas

1. **Usar tarjetas de prueba**:
   - Las tarjetas de prueba no tienen restricciones de antifraude
   - Usa las tarjetas listadas en `TARJETAS_PRUEBA_CHILE.md`

2. **Construir historial**:
   - Realiza varias transacciones pequeñas exitosas primero
   - Mercado Pago necesita ver un patrón de transacciones legítimas

3. **Verificar Device ID**:
   - Asegúrate de que el Device ID se capture correctamente
   - Verifica en los logs del backend que se esté enviando

## Próximos Pasos

1. ✅ **Ya revisaste el panel de Mercado Pago** - Confirmaste que es "pago sospechoso"
2. **Verifica el Device ID** - Asegúrate de que se esté capturando y enviando correctamente
3. **Prueba con tarjetas de prueba** - Para verificar que todo funcione sin restricciones
4. **Contacta soporte de Mercado Pago** - Si el problema persiste con tarjetas legítimas, proporciona:
   - Número de operación: `136222937919`
   - Mensaje: "Te protegimos de un pago sospechoso"
   - Explica que es un pago legítimo y que el cliente está usando su dispositivo habitual
5. **Construye historial** - Realiza transacciones pequeñas exitosas primero

## Recursos

- [Documentación de Mercado Pago - Mejorar Aprobación](https://www.mercadopago.cl/developers/es/docs/checkout-api/how-tos/improve-payment-approval)
- [Documentación - Razones de Rechazo](https://www.mercadopago.cl/developers/es/docs/checkout-api/how-tos/reasons-for-rejection)
- [Panel de Mercado Pago](https://www.mercadopago.cl/developers/panel)

