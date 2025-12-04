# Historia de Usuario: Sistema de Productos para Niños

## 📋 Descripción General

Como **usuario** (autenticado o visitante), quiero poder **comprar productos para niños** asociados a un evento, de manera similar a como se compran productos en el cine, donde puedo comprar cualquier producto sin necesidad de tener una entrada al evento, respetando el formulario actual para niños.

## 🎯 Objetivos

1. Permitir la compra de productos para niños independientemente de la compra de entradas
2. Mantener el formulario actual de datos de niños
3. Permitir compras múltiples de productos/entradas de niños
4. Gestionar stock independiente para productos de niños
5. Permitir compras como visitante (sin autenticación)

## 📊 Requisitos Funcionales

### RF1: Productos Suscritos a Entradas
- Cada entrada puede tener múltiples productos asociados (productos para niños)
- Los productos pueden ser de tipo `child_product` o `child_ticket`
- Los productos pueden comprarse independientemente de las entradas

### RF2: Compra Independiente de Productos
- Un usuario puede comprar productos sin tener una entrada al evento
- Similar al modelo de cine: compras lo que quieras, cuando quieras
- Los productos tienen su propio stock y precio

### RF3: Formulario de Niños
- Mantener el formulario actual de datos de niños (`TicketChildDetail`)
- Aplicar el formulario cuando se compra un producto de tipo `child_ticket` o `child_product`
- Validar todos los campos requeridos del formulario

### RF4: Compra Múltiple
- Un usuario puede comprar múltiples productos/entradas de niños en una sola transacción
- No hay límite de cantidad (excepto por stock disponible)
- Cada producto/entrada requiere completar el formulario de niño

### RF5: Stock Independiente
- Los productos de niños tienen su propio stock (`stock` y `stock_available`)
- El stock se gestiona independientemente del stock de entradas generales
- Se debe validar stock antes de permitir la compra

### RF6: Compra como Visitante
- Endpoint público para compras sin autenticación
- Requiere datos de contacto del comprador (nombre, email, teléfono)
- Los tickets/productos se asocian al comprador visitante

## 🗄️ Modelo de Datos

### Modificaciones a Modelos Existentes

#### EventService (Ya existe, necesita ajustes)
```python
class EventService(Base):
    __tablename__ = "event_services"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Numeric(12, 2), nullable=False, server_default="0")
    stock = Column(Integer, nullable=False, server_default="0")
    stock_available = Column(Integer, nullable=False, server_default="0")
    service_type = Column(String, nullable=False, server_default="general")
    # Tipos: general, food, parking, child_ticket, child_product
    
    # Para productos de niños
    requires_child_form = Column(Boolean, nullable=False, server_default="false")
    # Si requiere formulario de niño (child_ticket siempre lo requiere)
    
    min_age = Column(Integer, nullable=True)
    max_age = Column(Integer, nullable=True)
    
    # Relación con ticket_type (si es child_ticket)
    ticket_type_id = Column(UUID(as_uuid=True), ForeignKey("ticket_types.id"), nullable=True)
    # Si es null, es un producto independiente
```

#### Nuevo Modelo: OrderServiceItem (Ya existe, verificar)
```python
class OrderServiceItem(Base):
    __tablename__ = "order_service_items"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False)
    service_id = Column(UUID(as_uuid=True), ForeignKey("event_services.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(12, 2), nullable=False)
    final_price = Column(Numeric(12, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relaciones
    order = relationship("Order", back_populates="order_service_items")
    service = relationship("EventService", back_populates="order_service_items")
    child_details = relationship("OrderServiceItemChildDetail", back_populates="order_service_item", cascade="all, delete-orphan")
```

#### Nuevo Modelo: OrderServiceItemChildDetail
```python
class OrderServiceItemChildDetail(Base):
    """
    Detalles de niño para productos/servicios comprados
    Similar a TicketChildDetail pero para productos
    """
    __tablename__ = "order_service_item_child_details"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_service_item_id = Column(UUID(as_uuid=True), ForeignKey("order_service_items.id"), nullable=False)
    
    # Campos del formulario de niño (mismos que TicketChildDetail)
    nombre = Column(String, nullable=False)
    rut = Column(String, nullable=False)
    correo = Column(String, nullable=True)
    fecha_nacimiento = Column(Date, nullable=False)
    edad = Column(Integer, nullable=False)
    tipo_documento = Column(String, nullable=True, server_default="rut")
    
    toma_medicamento = Column(Boolean, nullable=False, server_default="false")
    es_alergico = Column(Boolean, nullable=False, server_default="false")
    detalle_alergias = Column(Text, nullable=True)
    
    tiene_necesidad_especial = Column(Boolean, nullable=False, server_default="false")
    detalle_necesidad_especial = Column(Text, nullable=True)
    
    numero_emergencia = Column(String, nullable=False)
    pais_telefono = Column(String, nullable=True, server_default="CL")
    nombre_contacto_emergencia = Column(String, nullable=True)
    parentesco_contacto_emergencia = Column(String, nullable=True)
    
    iglesia = Column(String, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relaciones
    order_service_item = relationship("OrderServiceItem", back_populates="child_details")
    medications = relationship("OrderServiceItemChildMedication", back_populates="child_detail", cascade="all, delete-orphan")
```

#### Nuevo Modelo: OrderServiceItemChildMedication
```python
class OrderServiceItemChildMedication(Base):
    __tablename__ = "order_service_item_child_medications"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    child_detail_id = Column(UUID(as_uuid=True), ForeignKey("order_service_item_child_details.id"), nullable=False)
    nombre = Column(String, nullable=False)
    dosis = Column(String, nullable=True)
    horario = Column(String, nullable=True)
    observaciones = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relaciones
    child_detail = relationship("OrderServiceItemChildDetail", back_populates="medications")
```

#### Modificación a Order
```python
class Order(Base):
    # ... campos existentes ...
    
    # Nuevo campo para compras de visitantes
    guest_email = Column(String, nullable=True)  # Email del visitante
    guest_name = Column(String, nullable=True)  # Nombre del visitante
    guest_phone = Column(String, nullable=True)  # Teléfono del visitante
    is_guest_order = Column(Boolean, nullable=False, server_default="false")
    
    # Relaciones
    order_service_items = relationship("OrderServiceItem", back_populates="order", cascade="all, delete-orphan")
```

## 🔌 Endpoints a Crear/Modificar

### 1. GET /api/v1/events/{event_id}/child-products
**Descripción:** Obtener todos los productos para niños disponibles de un evento

**Autenticación:** No requerida (público)

**Response:**
```json
{
  "products": [
    {
      "id": "uuid",
      "name": "Entrada Niño",
      "description": "Entrada para niños de 5-12 años",
      "price": 5000,
      "stock_available": 50,
      "service_type": "child_ticket",
      "requires_child_form": true,
      "min_age": 5,
      "max_age": 12,
      "ticket_type_id": "uuid" // Si es child_ticket
    },
    {
      "id": "uuid",
      "name": "Combo Niño",
      "description": "Combo especial para niños",
      "price": 8000,
      "stock_available": 30,
      "service_type": "child_product",
      "requires_child_form": true
    }
  ]
}
```

### 2. POST /api/v1/purchases/child-products
**Descripción:** Comprar productos para niños (requiere autenticación)

**Autenticación:** Requerida (JWT)

**Request:**
```json
{
  "event_id": "uuid",
  "products": [
    {
      "service_id": "uuid",
      "quantity": 2,
      "child_details": [
        {
          "nombre": "Juan Pérez",
          "rut": "12345678-9",
          "correo": "juan@example.com",
          "fecha_nacimiento": "2015-05-15",
          "edad": 8,
          "tipo_documento": "rut",
          "toma_medicamento": false,
          "es_alergico": true,
          "detalle_alergias": "Alérgico a maní",
          "tiene_necesidad_especial": false,
          "numero_emergencia": "+56912345678",
          "pais_telefono": "CL",
          "nombre_contacto_emergencia": "María Pérez",
          "parentesco_contacto_emergencia": "Madre",
          "iglesia": "Iglesia Central",
          "medicamentos": [
            {
              "nombre": "Antihistamínico",
              "dosis": "5ml",
              "horario": "Cada 8 horas",
              "observaciones": "Solo si es necesario"
            }
          ]
        },
        {
          "nombre": "Pedro Pérez",
          "rut": "98765432-1",
          // ... resto de campos
        }
      ]
    }
  ],
  "idempotency_key": "optional-key"
}
```

**Response:**
```json
{
  "order_id": "uuid",
  "payment_link": "https://mercadopago.com/...",
  "status": "pending",
  "total": 16000,
  "currency": "CLP"
}
```

### 3. POST /api/v1/purchases/child-products/guest
**Descripción:** Comprar productos para niños como visitante (sin autenticación)

**Autenticación:** No requerida

**Request:**
```json
{
  "event_id": "uuid",
  "buyer": {
    "name": "María González",
    "email": "maria@example.com",
    "phone": "+56912345678"
  },
  "products": [
    {
      "service_id": "uuid",
      "quantity": 1,
      "child_details": [
        {
          // ... mismo formato que arriba
        }
      ]
    }
  ],
  "idempotency_key": "optional-key"
}
```

**Response:**
```json
{
  "order_id": "uuid",
  "payment_link": "https://mercadopago.com/...",
  "status": "pending",
  "total": 5000,
  "currency": "CLP"
}
```

### 4. GET /api/v1/purchases/child-products/{order_id}
**Descripción:** Obtener estado de una compra de productos para niños

**Autenticación:** Requerida (o por order_id si es visitante)

**Response:**
```json
{
  "order_id": "uuid",
  "status": "completed",
  "total": 16000,
  "currency": "CLP",
  "payment_provider": "mercadopago",
  "payment_reference": "mp-123456",
  "created_at": "2024-01-15T10:00:00Z",
  "paid_at": "2024-01-15T10:05:00Z",
  "products": [
    {
      "service_id": "uuid",
      "service_name": "Entrada Niño",
      "quantity": 2,
      "unit_price": 5000,
      "final_price": 10000,
      "child_details": [
        // ... detalles de niños
      ]
    }
  ]
}
```

## 🔄 Flujos de Compra

### Flujo 1: Compra Autenticada
1. Usuario autenticado navega al evento
2. Ve lista de productos para niños disponibles
3. Selecciona productos y cantidad
4. Para cada producto que requiere formulario, completa datos del niño
5. Sistema valida stock disponible
6. Sistema crea orden y genera link de pago
7. Usuario completa pago
8. Sistema confirma orden y genera tickets/productos

### Flujo 2: Compra como Visitante
1. Visitante navega al evento (sin login)
2. Ve lista de productos para niños disponibles
3. Selecciona productos y cantidad
4. Completa datos del comprador (nombre, email, teléfono)
5. Para cada producto, completa datos del niño
6. Sistema valida stock disponible
7. Sistema crea orden (sin user_id) y genera link de pago
8. Visitante completa pago
9. Sistema confirma orden y genera tickets/productos
10. Sistema envía email de confirmación al visitante

## ✅ Criterios de Aceptación

### CA1: Productos Independientes
- ✅ Un usuario puede comprar productos sin tener entrada al evento
- ✅ Los productos se muestran en una sección separada
- ✅ El stock de productos es independiente del stock de entradas

### CA2: Formulario de Niños
- ✅ El formulario actual se mantiene intacto
- ✅ Todos los campos requeridos se validan
- ✅ Se pueden agregar múltiples medicamentos
- ✅ El formulario se aplica por cada producto/entrada de niño

### CA3: Compra Múltiple
- ✅ Un usuario puede comprar múltiples productos en una transacción
- ✅ Cada producto puede tener diferentes cantidades
- ✅ Se valida stock para cada producto individualmente

### CA4: Stock Independiente
- ✅ Cada producto tiene su propio stock
- ✅ El stock se decrementa al confirmar la compra
- ✅ Se valida stock antes de permitir la compra
- ✅ Se muestra stock disponible en la lista de productos

### CA5: Compra como Visitante
- ✅ Endpoint público funciona sin autenticación
- ✅ Se requiere información de contacto del comprador
- ✅ Se envía email de confirmación al visitante
- ✅ El visitante puede consultar su orden con el order_id

### CA6: Integración con Pago
- ✅ Se integra con MercadoPago
- ✅ Se genera link de pago único
- ✅ Se maneja webhook de confirmación
- ✅ Se actualiza stock al confirmar pago

## 🛠️ Tareas Técnicas

### Backend
- [ ] Crear migración para nuevos modelos
- [ ] Crear servicio `ChildProductService`
- [ ] Crear endpoints de productos para niños
- [ ] Modificar `PurchaseService` para soportar productos
- [ ] Crear servicio de validación de stock para productos
- [ ] Integrar formulario de niños en compra de productos
- [ ] Crear endpoint de compra como visitante
- [ ] Agregar validaciones de negocio

### Frontend
- [ ] Crear componente de lista de productos para niños
- [ ] Integrar formulario de niños en flujo de compra
- [ ] Crear vista de compra como visitante
- [ ] Agregar validaciones de formulario
- [ ] Mostrar stock disponible
- [ ] Manejar estados de carga y error

### Testing
- [ ] Tests unitarios de servicios
- [ ] Tests de integración de endpoints
- [ ] Tests de validación de stock
- [ ] Tests de formulario de niños
- [ ] Tests de compra como visitante

## 📝 Notas de Implementación

1. **Stock Management**: Usar el mismo sistema de locks distribuidos que se usa para capacidad de eventos
2. **Formulario de Niños**: Reutilizar la lógica existente de `TicketChildDetail`
3. **Pagos**: Reutilizar la integración existente con MercadoPago
4. **Email**: Enviar confirmación tanto a usuarios autenticados como visitantes
5. **Seguridad**: Validar que los visitantes solo puedan ver sus propias órdenes

## 🔗 Relaciones con Otras HUs

- **HU de Entradas Generales**: Los productos pueden comprarse independientemente
- **HU de Formulario de Niños**: Se reutiliza el formulario existente
- **HU de Pagos**: Se integra con el sistema de pagos existente
- **HU de Stock**: Se extiende el sistema de stock para productos


