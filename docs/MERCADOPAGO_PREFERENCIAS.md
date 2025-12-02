# Preferencias de Pago Dinámicas - Mercado Pago

## 📋 ¿Por qué son necesarias las preferencias?

**Sí, las preferencias de pago son necesarias** incluso cuando los productos y precios varían constantemente (como en una ticketera).

### ¿Cómo funcionan?

1. **Se crean dinámicamente**: Cada vez que un usuario quiere comprar, se crea una **nueva preferencia** con los items específicos de esa compra.
2. **No son estáticas**: A diferencia de un e-commerce tradicional, no guardas preferencias predefinidas. Cada compra genera su propia preferencia única.
3. **Flexibilidad total**: Puedes incluir diferentes tipos de tickets, servicios adicionales, cantidades variables, etc.

## 🔄 Flujo de una Compra

```
1. Usuario selecciona tickets y servicios
   ↓
2. Frontend envía request con:
   - Attendees (cantidad de tickets)
   - Selected services (servicios adicionales)
   ↓
3. Backend calcula precios:
   - Precio de tickets × cantidad
   - Precio de servicios × cantidad
   - Total
   ↓
4. Backend crea preferencia de pago con:
   - Item 1: "Ticket General - Evento X" (cantidad: 2, precio: $15,000)
   - Item 2: "Servicio VIP" (cantidad: 1, precio: $5,000)
   - Item 3: "Almuerzo" (cantidad: 2, precio: $8,000)
   ↓
5. Mercado Pago genera un link único de pago
   ↓
6. Usuario paga en Mercado Pago
   ↓
7. Webhook notifica al backend
   ↓
8. Backend genera tickets
```

## 💡 Ejemplo Práctico

### Escenario: Compra de 2 tickets + 1 servicio VIP

**Request del frontend:**
```json
{
  "event_id": "abc-123",
  "attendees": [
    {"name": "Juan Pérez", "is_child": false},
    {"name": "María Pérez", "is_child": false}
  ],
  "selected_services": {
    "service-vip-id": 1
  }
}
```

**Backend crea preferencia con:**
```python
items = [
    {
        "title": "Ticket General - Concierto Rock",
        "description": "2 ticket(s) para Concierto Rock",
        "quantity": 2,
        "unit_price": 15000.0
    },
    {
        "title": "Servicio VIP",
        "description": "Servicio VIP - Concierto Rock",
        "quantity": 1,
        "unit_price": 5000.0
    }
]
```

**Total en Mercado Pago:** $35,000 CLP

## ✅ Ventajas de este Enfoque

1. **Flexibilidad**: Cada compra puede tener diferentes items y precios
2. **Transparencia**: El usuario ve exactamente qué está pagando (tickets + servicios por separado)
3. **Escalabilidad**: Funciona con cualquier cantidad de items
4. **Mantenibilidad**: No necesitas predefinir productos en Mercado Pago

## 🔧 Implementación Actual

El código ya está preparado para esto:

### `MercadoPagoService.create_preference()`

Acepta dos modos:

**Modo 1: Múltiples items (recomendado para ticketeras)**
```python
preference = mercado_pago_service.create_preference(
    order_id="order-123",
    currency="CLP",
    items=[
        {"title": "Ticket", "quantity": 2, "unit_price": 15000},
        {"title": "Servicio VIP", "quantity": 1, "unit_price": 5000}
    ]
)
```

**Modo 2: Un solo item (compatibilidad)**
```python
preference = mercado_pago_service.create_preference(
    order_id="order-123",
    title="Tickets - Evento",
    total_amount=35000,
    currency="CLP"
)
```

### `PurchaseService.create_purchase()`

El servicio automáticamente:
1. Calcula precios de tickets según tipo
2. Calcula precios de servicios adicionales
3. Construye la lista de items
4. Crea la preferencia con todos los items

## 📊 Estructura de Items

Cada item en la preferencia tiene:

```python
{
    "title": str,           # Nombre del producto (ej: "Ticket General")
    "description": str,     # Descripción opcional
    "quantity": int,       # Cantidad (ej: 2 tickets)
    "unit_price": float,   # Precio unitario (ej: 15000.0)
    "currency_id": str     # Moneda (ej: "CLP")
}
```

## 🎯 Casos de Uso

### Caso 1: Solo Tickets
```python
items = [
    {
        "title": "Ticket General - Evento X",
        "quantity": 3,
        "unit_price": 20000.0
    }
]
```

### Caso 2: Tickets + Servicios
```python
items = [
    {
        "title": "Ticket General - Evento X",
        "quantity": 2,
        "unit_price": 20000.0
    },
    {
        "title": "Parking",
        "quantity": 1,
        "unit_price": 5000.0
    },
    {
        "title": "Almuerzo",
        "quantity": 2,
        "unit_price": 8000.0
    }
]
```

### Caso 3: Tickets de Diferentes Tipos
Si en el futuro necesitas diferentes tipos de tickets con precios distintos:
```python
items = [
    {
        "title": "Ticket General",
        "quantity": 2,
        "unit_price": 15000.0
    },
    {
        "title": "Ticket VIP",
        "quantity": 1,
        "unit_price": 35000.0
    }
]
```

## 🔍 Verificación

Para verificar que las preferencias se están creando correctamente:

1. **Revisar logs del backend** cuando se crea una compra
2. **Verificar en Mercado Pago**: El link de pago mostrará todos los items
3. **Probar con diferentes combinaciones**: tickets + servicios, solo tickets, etc.

## 📝 Notas Importantes

1. **Cada preferencia es única**: No reutilices preferencias entre compras
2. **External Reference**: El `order_id` se guarda como `external_reference` para identificar la orden cuando llegue el webhook
3. **Expiración**: Las preferencias expiran en 24 horas por defecto
4. **Total calculado automáticamente**: Mercado Pago suma todos los items automáticamente

## 🚀 Próximos Pasos

1. ✅ Preferencias dinámicas implementadas
2. ⏳ Probar con diferentes combinaciones de items
3. ⏳ Verificar que los webhooks funcionen correctamente
4. ⏳ Implementar manejo de errores específicos


