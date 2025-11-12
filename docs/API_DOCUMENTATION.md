# Documentación de la API - Crowdify GW

## Información General

- **Base URL**: `http://localhost:8000` (desarrollo) | `https://api.crodify.com` (producción)
- **Versión de API**: v1
- **Prefijo de rutas**: `/api/v1`
- **Autenticación**: Bearer Token (JWT)
- **Formato de respuesta**: JSON

## Autenticación

La API utiliza JWT (JSON Web Tokens) para autenticación. Incluye el token en el header de cada petición:

```
Authorization: Bearer <tu_token_jwt>
```

### Roles de Usuario

- `user`: Usuario estándar (puede comprar tickets, ver sus propios tickets)
- `admin`: Administrador (acceso completo)
- `scanner`: Escáner de tickets (puede validar tickets)
- `coordinator`: Coordinador de eventos

---

## 📋 Tabla de Contenidos

1. [Health Checks](#health-checks)
2. [Eventos (Events)](#eventos-events)
3. [Compra de Tickets (Purchases)](#compra-de-tickets-purchases)
4. [Tickets](#tickets)
5. [Validación de Tickets](#validación-de-tickets)
6. [Notificaciones](#notificaciones)
7. [Administración (Admin)](#administración-admin)

---

## Health Checks

### GET /health

Health check básico del servicio.

**Autenticación**: No requerida

**Ejemplo de Request**:

```bash
curl -X GET http://localhost:8000/health
```

**Ejemplo de Response**:

```json
{
  "status": "ok",
  "service": "crodify-api"
}
```

---

### GET /ready

Verifica que el servicio está listo y puede conectarse a sus dependencias (DB, Redis).

**Autenticación**: No requerida

**Ejemplo de Request**:

```bash
curl -X GET http://localhost:8000/ready
```

**Ejemplo de Response (Success)**:

```json
{
  "status": "ready",
  "database": "connected",
  "redis": "connected"
}
```

**Ejemplo de Response (Error)**:

```json
{
  "status": "not ready",
  "error": "Database connection failed"
}
```

---

## Eventos (Events)

### GET /api/v1/events

Lista todos los eventos con filtros opcionales.

**Autenticación**: Opcional (público)

**Query Parameters**:

- `category` (string, opcional): Categoría del evento
- `search` (string, opcional): Búsqueda por nombre o ubicación
- `date_from` (datetime, opcional): Fecha desde (formato ISO 8601)
- `date_to` (datetime, opcional): Fecha hasta (formato ISO 8601)
- `limit` (int, opcional): Número máximo de resultados (default: 50, max: 100)
- `offset` (int, opcional): Offset para paginación (default: 0)

**Ejemplo de Request**:

```bash
curl -X GET "http://localhost:8000/api/v1/events?limit=10&category=concierto&search=rock"
```

**Ejemplo de Response**:

```json
[
  {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "organizer_id": "987e6543-e21c-12d3-a456-426614174000",
    "name": "Festival de Rock 2025",
    "location_text": "Estadio Nacional, Santiago",
    "point_location": "-33.4489,-70.6693",
    "starts_at": "2025-12-15T20:00:00Z",
    "ends_at": "2025-12-15T23:59:00Z",
    "capacity_total": 5000,
    "capacity_available": 3500,
    "allow_children": true,
    "category": "concierto",
    "description": "El mejor festival de rock del año",
    "image_url": "https://storage.example.com/events/rock2025.jpg",
    "created_at": "2025-11-01T10:00:00Z",
    "updated_at": "2025-11-10T15:30:00Z"
  }
]
```

---

### GET /api/v1/events/{event_id}

Obtiene los detalles de un evento específico.

**Autenticación**: Opcional (público)

**Path Parameters**:

- `event_id` (string, requerido): ID del evento (UUID)

**Ejemplo de Request**:

```bash
curl -X GET http://localhost:8000/api/v1/events/123e4567-e89b-12d3-a456-426614174000
```

**Ejemplo de Response**:

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "organizer_id": "987e6543-e21c-12d3-a456-426614174000",
  "name": "Festival de Rock 2025",
  "location_text": "Estadio Nacional, Santiago",
  "point_location": "-33.4489,-70.6693",
  "starts_at": "2025-12-15T20:00:00Z",
  "ends_at": "2025-12-15T23:59:00Z",
  "capacity_total": 5000,
  "capacity_available": 3500,
  "allow_children": true,
  "category": "concierto",
  "description": "El mejor festival de rock del año",
  "image_url": "https://storage.example.com/events/rock2025.jpg",
  "created_at": "2025-11-01T10:00:00Z",
  "updated_at": "2025-11-10T15:30:00Z"
}
```

**Códigos de Error**:

- `404 Not Found`: Evento no encontrado

---

### POST /api/v1/events

Crea un nuevo evento.

**Autenticación**: Requerida (rol `admin`)

**Request Body**:

```json
{
  "organizer_id": "987e6543-e21c-12d3-a456-426614174000",
  "name": "Festival de Rock 2025",
  "location_text": "Estadio Nacional, Santiago",
  "starts_at": "2025-12-15T20:00:00Z",
  "ends_at": "2025-12-15T23:59:00Z",
  "capacity_total": 5000,
  "allow_children": true
}
```

**Ejemplo de Request**:

```bash
curl -X POST http://localhost:8000/api/v1/events \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "organizer_id": "987e6543-e21c-12d3-a456-426614174000",
    "name": "Festival de Rock 2025",
    "location_text": "Estadio Nacional, Santiago",
    "starts_at": "2025-12-15T20:00:00Z",
    "ends_at": "2025-12-15T23:59:00Z",
    "capacity_total": 5000,
    "allow_children": true
  }'
```

**Ejemplo de Response**:

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "organizer_id": "987e6543-e21c-12d3-a456-426614174000",
  "name": "Festival de Rock 2025",
  "location_text": "Estadio Nacional, Santiago",
  "starts_at": "2025-12-15T20:00:00Z",
  "ends_at": "2025-12-15T23:59:00Z",
  "capacity_total": 5000,
  "capacity_available": 5000,
  "allow_children": true,
  "created_at": "2025-11-11T10:00:00Z"
}
```

**Códigos de Error**:

- `400 Bad Request`: Datos inválidos
- `403 Forbidden`: Usuario no tiene permisos de administrador

---

### PUT /api/v1/events/{event_id}

Actualiza un evento existente.

**Autenticación**: Requerida (rol `admin` o ser el organizador del evento)

**Path Parameters**:

- `event_id` (string, requerido): ID del evento (UUID)

**Request Body** (todos los campos son opcionales):

```json
{
  "name": "Festival de Rock 2025 - ACTUALIZADO",
  "location_text": "Estadio Nacional, Santiago",
  "starts_at": "2025-12-15T20:00:00Z",
  "ends_at": "2025-12-15T23:59:00Z",
  "capacity_total": 6000,
  "capacity_available": 4000,
  "allow_children": true
}
```

**Ejemplo de Request**:

```bash
curl -X PUT http://localhost:8000/api/v1/events/123e4567-e89b-12d3-a456-426614174000 \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Festival de Rock 2025 - ACTUALIZADO",
    "capacity_total": 6000
  }'
```

**Ejemplo de Response**:

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "organizer_id": "987e6543-e21c-12d3-a456-426614174000",
  "name": "Festival de Rock 2025 - ACTUALIZADO",
  "location_text": "Estadio Nacional, Santiago",
  "starts_at": "2025-12-15T20:00:00Z",
  "ends_at": "2025-12-15T23:59:00Z",
  "capacity_total": 6000,
  "capacity_available": 4000,
  "allow_children": true,
  "created_at": "2025-11-01T10:00:00Z"
}
```

**Códigos de Error**:

- `400 Bad Request`: Datos inválidos
- `403 Forbidden`: Usuario no tiene permisos
- `404 Not Found`: Evento no encontrado

---

### DELETE /api/v1/events/{event_id}

Elimina un evento.

**Autenticación**: Requerida (rol `admin` o ser el organizador del evento)

**Path Parameters**:

- `event_id` (string, requerido): ID del evento (UUID)

**Ejemplo de Request**:

```bash
curl -X DELETE http://localhost:8000/api/v1/events/123e4567-e89b-12d3-a456-426614174000 \
  -H "Authorization: Bearer <token>"
```

**Response**: `204 No Content` (sin body)

**Códigos de Error**:

- `400 Bad Request`: No se puede eliminar el evento (ej: tiene tickets vendidos)
- `403 Forbidden`: Usuario no tiene permisos
- `404 Not Found`: Evento no encontrado

---

## Compra de Tickets (Purchases)

### POST /api/v1/purchases

Crea una orden de compra y genera un link de pago de Mercado Pago.

**Autenticación**: Requerida (rol `user` o superior)

**Request Body**:

```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "event_id": "123e4567-e89b-12d3-a456-426614174000",
  "attendees": [
    {
      "name": "Juan Pérez",
      "email": "juan@example.com",
      "document_type": "RUT",
      "document_number": "12345678-9",
      "is_child": false
    },
    {
      "name": "María Pérez",
      "email": "maria@example.com",
      "document_type": "RUT",
      "document_number": "98765432-1",
      "is_child": true,
      "child_details": {
        "birth_date": "2018-05-15T00:00:00Z",
        "allergies": "Ninguna",
        "special_needs": null,
        "emergency_contact_name": "Juan Pérez",
        "emergency_contact_phone": "+56912345678",
        "medications": [
          {
            "name": "Ibuprofeno",
            "frequency": "Cada 8 horas si hay dolor",
            "notes": "Solo si es necesario"
          }
        ]
      }
    }
  ],
  "selected_services": {
    "abc-service-id": 2
  },
  "idempotency_key": "unique-key-12345"
}
```

**Campos del Request**:

- `user_id` (string, requerido): ID del usuario que compra
- `event_id` (string, requerido): ID del evento
- `attendees` (array, requerido): Lista de asistentes
  - `name` (string, requerido): Nombre completo
  - `email` (string, opcional): Email del asistente
  - `document_type` (string, requerido): Tipo de documento (RUT, PASSPORT, DNI, etc)
  - `document_number` (string, requerido): Número de documento
  - `is_child` (boolean, default: false): Si es un niño
  - `child_details` (object, opcional): Detalles del niño (requerido si `is_child` es true)
    - `birth_date` (datetime, opcional): Fecha de nacimiento
    - `allergies` (string, opcional): Alergias
    - `special_needs` (string, opcional): Necesidades especiales
    - `emergency_contact_name` (string, opcional): Nombre del contacto de emergencia
    - `emergency_contact_phone` (string, opcional): Teléfono de emergencia
    - `medications` (array, opcional): Lista de medicamentos
      - `name` (string): Nombre del medicamento
      - `frequency` (string): Frecuencia de administración
      - `notes` (string): Observaciones
- `selected_services` (object, opcional): Servicios adicionales seleccionados {serviceId: quantity}
- `idempotency_key` (string, opcional): Clave para evitar compras duplicadas

**Ejemplo de Request**:

```bash
curl -X POST http://localhost:8000/api/v1/purchases \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "event_id": "123e4567-e89b-12d3-a456-426614174000",
    "attendees": [
      {
        "name": "Juan Pérez",
        "email": "juan@example.com",
        "document_type": "RUT",
        "document_number": "12345678-9",
        "is_child": false
      }
    ]
  }'
```

**Ejemplo de Response**:

```json
{
  "order_id": "789e1234-e89b-12d3-a456-426614174000",
  "payment_link": "https://www.mercadopago.cl/checkout/v1/redirect?pref_id=123456789-abc-def",
  "status": "pending"
}
```

**Flujo de Compra**:

1. Cliente envía request con datos de asistentes
2. Backend crea orden con estado `pending` y reserva capacidad
3. Backend crea preferencia de pago en Mercado Pago
4. Se devuelve `payment_link` al cliente
5. Cliente redirige a usuario a `payment_link`
6. Usuario paga en Mercado Pago
7. Mercado Pago envía webhook a `/api/v1/purchases/webhook`
8. Backend genera tickets y envía emails

**Códigos de Error**:

- `400 Bad Request`: Datos inválidos, capacidad insuficiente
- `403 Forbidden`: Usuario no puede crear órdenes para otros usuarios
- `500 Internal Server Error`: Error procesando compra o creando preferencia de pago

---

### POST /api/v1/purchases/webhook

Webhook para recibir notificaciones de pago de Mercado Pago.

**Autenticación**: No requerida (Mercado Pago valida internamente)

**Nota**: Este endpoint es llamado automáticamente por Mercado Pago cuando hay actualizaciones en el pago.

**Request Body (ejemplo de Mercado Pago)**:

```json
{
  "action": "payment.updated",
  "api_version": "v1",
  "data": {
    "id": "1234567890"
  },
  "date_created": "2025-11-11T10:00:00Z",
  "id": 123456789,
  "live_mode": true,
  "type": "payment",
  "user_id": "123456"
}
```

**Response**:

```json
{
  "status": "ok"
}
```

**Posibles valores de status**:

- `ok`: Webhook procesado correctamente
- `ignored`: Webhook recibido pero ignorado (no es de interés)
- `error`: Error al procesar webhook

**Nota Importante**: Este endpoint siempre retorna 200 OK para evitar reintentos innecesarios de Mercado Pago.

---

### GET /api/v1/purchases/{order_id}/status

Obtiene el estado de una orden de compra.

**Autenticación**: Requerida (rol `user` o superior, debe ser propietario de la orden o admin)

**Path Parameters**:

- `order_id` (string, requerido): ID de la orden (UUID)

**Ejemplo de Request**:

```bash
curl -X GET http://localhost:8000/api/v1/purchases/789e1234-e89b-12d3-a456-426614174000/status \
  -H "Authorization: Bearer <token>"
```

**Ejemplo de Response**:

```json
{
  "order_id": "789e1234-e89b-12d3-a456-426614174000",
  "status": "completed",
  "total": 45000.0,
  "currency": "CLP",
  "payment_provider": "mercadopago",
  "payment_reference": "1234567890",
  "created_at": "2025-11-11T10:00:00Z",
  "paid_at": "2025-11-11T10:05:30Z"
}
```

**Estados de Orden**:

- `pending`: Orden creada, esperando pago
- `processing`: Pago recibido, procesando tickets
- `completed`: Orden completada, tickets generados
- `cancelled`: Orden cancelada
- `refunded`: Orden reembolsada

**Códigos de Error**:

- `403 Forbidden`: Usuario no tiene acceso a esta orden
- `404 Not Found`: Orden no encontrada

---

## Tickets

### GET /api/v1/tickets/user/{user_id}

Obtiene todos los tickets de un usuario.

**Autenticación**: Requerida (usuario debe ser propietario o admin/coordinator)

**Path Parameters**:

- `user_id` (string, requerido): ID del usuario (UUID)

**Ejemplo de Request**:

```bash
curl -X GET http://localhost:8000/api/v1/tickets/user/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer <token>"
```

**Ejemplo de Response**:

```json
[
  {
    "id": "111e2222-e89b-12d3-a456-426614174000",
    "event_id": "123e4567-e89b-12d3-a456-426614174000",
    "holder_first_name": "Juan",
    "holder_last_name": "Pérez",
    "holder_document_type": "RUT",
    "holder_document_number": "12345678-9",
    "is_child": false,
    "qr_signature": "abc123def456ghi789jkl",
    "status": "issued",
    "issued_at": "2025-11-11T10:05:30Z",
    "used_at": null
  },
  {
    "id": "222e3333-e89b-12d3-a456-426614174000",
    "event_id": "123e4567-e89b-12d3-a456-426614174000",
    "holder_first_name": "María",
    "holder_last_name": "Pérez",
    "holder_document_type": "RUT",
    "holder_document_number": "98765432-1",
    "is_child": true,
    "qr_signature": "xyz987uvw654rst321",
    "status": "issued",
    "issued_at": "2025-11-11T10:05:30Z",
    "used_at": null
  }
]
```

**Estados de Ticket**:

- `issued`: Ticket emitido, no usado
- `validated`: Ticket validado (primer escaneo)
- `used`: Ticket usado (entrada completada)
- `cancelled`: Ticket cancelado

**Códigos de Error**:

- `403 Forbidden`: Usuario no puede ver tickets de otros usuarios
- `404 Not Found`: Usuario no tiene tickets

---

### GET /api/v1/tickets/{ticket_id}

Obtiene información detallada de un ticket específico.

**Autenticación**: Requerida (rol `scanner`, `admin`, o `coordinator`)

**Path Parameters**:

- `ticket_id` (string, requerido): ID del ticket (UUID)

**Ejemplo de Request**:

```bash
curl -X GET http://localhost:8000/api/v1/tickets/111e2222-e89b-12d3-a456-426614174000 \
  -H "Authorization: Bearer <token>"
```

**Ejemplo de Response**:

```json
{
  "id": "111e2222-e89b-12d3-a456-426614174000",
  "event_id": "123e4567-e89b-12d3-a456-426614174000",
  "holder_first_name": "Juan",
  "holder_last_name": "Pérez",
  "holder_document_type": "RUT",
  "holder_document_number": "12345678-9",
  "is_child": false,
  "status": "issued",
  "issued_at": "2025-11-11T10:05:30Z",
  "used_at": null
}
```

**Códigos de Error**:

- `403 Forbidden`: Usuario no tiene permisos para ver tickets
- `404 Not Found`: Ticket no encontrado

---

## Validación de Tickets

### POST /api/v1/tickets/validate

Valida un ticket mediante su código QR.

**Autenticación**: Requerida (rol `scanner`, `admin`, o `coordinator`)

**Request Body**:

```json
{
  "qr_signature": "abc123def456ghi789jkl",
  "inspector_id": "scanner-user-id-uuid",
  "event_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

**Campos del Request**:

- `qr_signature` (string, requerido): Firma QR del ticket
- `inspector_id` (string, requerido): ID del usuario que está validando
- `event_id` (string, opcional): ID del evento (para validación adicional)

**Ejemplo de Request**:

```bash
curl -X POST http://localhost:8000/api/v1/tickets/validate \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "qr_signature": "abc123def456ghi789jkl",
    "inspector_id": "scanner-user-id-uuid",
    "event_id": "123e4567-e89b-12d3-a456-426614174000"
  }'
```

**Ejemplo de Response (Válido)**:

```json
{
  "valid": true,
  "ticket_id": "111e2222-e89b-12d3-a456-426614174000",
  "event_id": "123e4567-e89b-12d3-a456-426614174000",
  "attendee_name": "Juan Pérez",
  "message": "Ticket validado correctamente"
}
```

**Ejemplo de Response (Inválido)**:

```json
{
  "valid": false,
  "ticket_id": null,
  "event_id": null,
  "attendee_name": null,
  "message": "Ticket ya fue utilizado"
}
```

**Posibles mensajes de validación**:

- `"Ticket validado correctamente"`: Primera validación exitosa
- `"Ticket ya fue utilizado"`: Ticket ya fue usado anteriormente
- `"Ticket no encontrado"`: QR signature no existe
- `"Ticket cancelado"`: Ticket fue cancelado
- `"Ticket no pertenece a este evento"`: El ticket es de otro evento

**Códigos de Error**:

- `403 Forbidden`: Usuario no tiene permisos de scanner

---

## Notificaciones

### POST /api/v1/notifications/test-email

Endpoint de prueba para enviar emails.

**Autenticación**: Requerida (rol `admin`)

**Query Parameters**:

- `to_email` (string, requerido): Email de destino

**Ejemplo de Request**:

```bash
curl -X POST "http://localhost:8000/api/v1/notifications/test-email?to_email=test@example.com" \
  -H "Authorization: Bearer <token>"
```

**Ejemplo de Response**:

```json
{
  "status": "sent",
  "message": "Email enviado a test@example.com"
}
```

**Códigos de Error**:

- `403 Forbidden`: Usuario no tiene permisos de administrador
- `500 Internal Server Error`: Error enviando email

---

## Administración (Admin)

Todos los endpoints administrativos requieren autenticación con rol `admin` y están bajo el prefijo `/api/v1/admin`.

### GET /api/v1/admin/organizer

Obtiene información del organizador asociado al usuario admin actual.

**Autenticación**: Requerida (rol `admin`)

**Ejemplo de Request**:

```bash
curl -X GET http://localhost:8000/api/v1/admin/organizer \
  -H "Authorization: Bearer <token>"
```

**Ejemplo de Response**:

```json
{
  "id": "org-uuid-123",
  "org_name": "Mi Organización de Eventos",
  "contact_email": "contacto@miorg.com",
  "contact_phone": "+56912345678",
  "user_id": "user-uuid-456",
  "created_at": "2025-01-01T10:00:00Z",
  "updated_at": "2025-11-01T15:30:00Z"
}
```

**Códigos de Error**:

- `404 Not Found`: No se encontró organizador asociado al usuario

---

### GET /api/v1/admin/scanners

Lista todos los usuarios con rol `scanner`.

**Autenticación**: Requerida (rol `admin`)

**Ejemplo de Request**:

```bash
curl -X GET http://localhost:8000/api/v1/admin/scanners \
  -H "Authorization: Bearer <token>"
```

**Ejemplo de Response**:

```json
{
  "scanners": [
    {
      "id": "scanner-uuid-1",
      "email": "scanner1@ejemplo.com",
      "first_name": "Juan",
      "last_name": "Pérez",
      "role": "scanner",
      "created_at": "2025-03-15T10:00:00Z"
    },
    {
      "id": "scanner-uuid-2",
      "email": "scanner2@ejemplo.com",
      "first_name": "María",
      "last_name": "González",
      "role": "scanner",
      "created_at": "2025-04-20T14:30:00Z"
    }
  ]
}
```

---

### GET /api/v1/admin/users

Lista usuarios por rol (por defecto: `user`).

**Autenticación**: Requerida (rol `admin`)

**Query Parameters**:

- `role` (string, opcional): Rol a filtrar (default: `user`)

**Ejemplo de Request**:

```bash
curl -X GET "http://localhost:8000/api/v1/admin/users?role=user" \
  -H "Authorization: Bearer <token>"
```

**Ejemplo de Response**:

```json
{
  "users": [
    {
      "id": "user-uuid-1",
      "email": "usuario1@ejemplo.com",
      "first_name": "Pedro",
      "last_name": "Ramírez",
      "role": "user",
      "created_at": "2025-05-10T08:00:00Z"
    },
    {
      "id": "user-uuid-2",
      "email": "usuario2@ejemplo.com",
      "first_name": "Ana",
      "last_name": "López",
      "role": "user",
      "created_at": "2025-06-05T11:20:00Z"
    }
  ]
}
```

---

### PUT /api/v1/admin/users/{user_id}/role

Cambia el rol de un usuario (por ejemplo, de `user` a `scanner`).

**Autenticación**: Requerida (rol `admin`)

**Path Parameters**:

- `user_id` (string, requerido): ID del usuario (UUID)

**Request Body**:

```json
{
  "role": "scanner"
}
```

**Roles válidos**: `user`, `scanner`, `coordinator`, `admin`

**Ejemplo de Request**:

```bash
curl -X PUT http://localhost:8000/api/v1/admin/users/user-uuid-1/role \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "role": "scanner"
  }'
```

**Ejemplo de Response**:

```json
{
  "id": "user-uuid-1",
  "email": "usuario1@ejemplo.com",
  "first_name": "Pedro",
  "last_name": "Ramírez",
  "role": "scanner",
  "created_at": "2025-05-10T08:00:00Z"
}
```

**Validaciones**:

- ✅ Solo admin puede cambiar roles
- ✅ Roles válidos: `user`, `scanner`, `coordinator`, `admin`
- ❌ No se puede cambiar el propio rol (evitar perder acceso admin)

**Códigos de Error**:

- `400 Bad Request`: Rol inválido o intento de cambiar propio rol
- `404 Not Found`: Usuario no encontrado

---

### POST /api/v1/admin/scanners

Crea un nuevo usuario con rol `scanner`.

**Autenticación**: Requerida (rol `admin`)

**Request Body**:

```json
{
  "email": "nuevo.scanner@ejemplo.com",
  "first_name": "Carlos",
  "last_name": "Martínez",
  "password": "contraseña-segura-123"
}
```

**Validaciones**:

- Email debe ser único
- Password mínimo 8 caracteres
- first_name y last_name requeridos

**Ejemplo de Request**:

```bash
curl -X POST http://localhost:8000/api/v1/admin/scanners \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "nuevo.scanner@ejemplo.com",
    "first_name": "Carlos",
    "last_name": "Martínez",
    "password": "contraseña-segura-123"
  }'
```

**Ejemplo de Response**:

```json
{
  "id": "scanner-uuid-new",
  "email": "nuevo.scanner@ejemplo.com",
  "first_name": "Carlos",
  "last_name": "Martínez",
  "role": "scanner",
  "created_at": "2025-11-11T16:00:00Z"
}
```

**Nota**: Actualmente solo crea el usuario en la base de datos. Para crear en Supabase Auth se requiere configuración adicional del Admin API.

**Códigos de Error**:

- `400 Bad Request`: Email ya existe o contraseña muy corta

---

### DELETE /api/v1/admin/scanners/{scanner_id}

Remueve rol `scanner` de un usuario (lo degrada a `user`).

**Autenticación**: Requerida (rol `admin`)

**Path Parameters**:

- `scanner_id` (string, requerido): ID del scanner (UUID)

**Ejemplo de Request**:

```bash
curl -X DELETE http://localhost:8000/api/v1/admin/scanners/scanner-uuid-1 \
  -H "Authorization: Bearer <token>"
```

**Ejemplo de Response**:

```json
{
  "message": "Scanner role removed successfully",
  "user_id": "scanner-uuid-1"
}
```

**Nota**: No elimina el usuario completamente, solo cambia su rol a `user`.

**Códigos de Error**:

- `400 Bad Request`: Usuario no tiene rol scanner
- `404 Not Found`: Scanner no encontrado

---

### GET /api/v1/admin/stats

Obtiene estadísticas del dashboard para el organizador.

**Autenticación**: Requerida (rol `admin`)

**Query Parameters**:

- `date_from` (datetime, opcional): Filtrar desde fecha (ISO 8601)
- `date_to` (datetime, opcional): Filtrar hasta fecha (ISO 8601)

**Ejemplo de Request**:

```bash
curl -X GET "http://localhost:8000/api/v1/admin/stats?date_from=2025-01-01T00:00:00Z&date_to=2025-12-31T23:59:59Z" \
  -H "Authorization: Bearer <token>"
```

**Ejemplo de Response**:

```json
{
  "total_events": 15,
  "active_events": 8,
  "total_tickets_sold": 452,
  "total_revenue": 12500000.0,
  "currency": "CLP",
  "period": {
    "from_date": "2025-01-01T00:00:00Z",
    "to_date": "2025-12-31T23:59:59Z"
  }
}
```

**Métricas Incluidas**:

- `total_events`: Total de eventos del organizador (en el período)
- `active_events`: Eventos con `starts_at >= NOW()`
- `total_tickets_sold`: Tickets con estado `issued`, `validated` o `used`
- `total_revenue`: Suma de orders `completed` relacionadas con eventos del organizador

---

### GET /api/v1/admin/events

Lista eventos del organizador con estadísticas de ventas.

**Autenticación**: Requerida (rol `admin`)

**Query Parameters**:

- `status` (string, opcional): Filtro de estado
  - `upcoming`: Eventos futuros (`starts_at > NOW()`)
  - `ongoing`: Eventos en curso
  - `past`: Eventos pasados
  - `all`: Todos los eventos (default)
- `sort` (string, opcional): Ordenamiento
  - `starts_at_asc`: Por fecha de inicio ascendente
  - `starts_at_desc`: Por fecha de inicio descendente (default)
  - `revenue_desc`: Por ingresos descendente

**Ejemplo de Request**:

```bash
curl -X GET "http://localhost:8000/api/v1/admin/events?status=upcoming&sort=starts_at_asc" \
  -H "Authorization: Bearer <token>"
```

**Ejemplo de Response**:

```json
{
  "events": [
    {
      "id": "event-uuid-1",
      "name": "Concierto Rock 2025",
      "location_text": "Estadio Nacional, Santiago",
      "point_location": "-33.4489,-70.6693",
      "starts_at": "2025-12-15T20:00:00Z",
      "ends_at": "2025-12-15T23:59:00Z",
      "capacity_total": 1000,
      "capacity_available": 350,
      "category": "musica",
      "image_url": "https://example.com/image.jpg",
      "organizer": {
        "id": "org-uuid-123",
        "org_name": "Mi Organización"
      },
      "ticket_types": [
        {
          "id": "tt-uuid-1",
          "name": "General",
          "price": 25000.0,
          "is_child": false
        },
        {
          "id": "tt-uuid-2",
          "name": "Niños",
          "price": 15000.0,
          "is_child": true
        }
      ],
      "stats": {
        "tickets_sold": 650,
        "tickets_remaining": 350,
        "revenue": 16250000.0,
        "sales_percentage": 65.0,
        "services_stats": [
          {
            "id": "service-uuid-1",
            "name": "Estacionamiento",
            "service_type": "parking",
            "stock": 100,
            "sold": 45,
            "remaining": 55
          }
        ]
      }
    }
  ]
}
```

**Diferencia con GET /api/v1/events**:

- Este endpoint retorna SOLO eventos del organizador actual
- Incluye estadísticas detalladas de ventas
- Incluye información de ticket_types
- Incluye estadísticas de servicios adicionales

---

### GET /api/v1/admin/events/{event_id}/tickets

Lista todos los tickets de un evento específico con detalles completos.

**Autenticación**: Requerida (rol `admin` o `coordinator`)

**Path Parameters**:

- `event_id` (string, requerido): ID del evento (UUID)

**Query Parameters**:

- `status` (string, opcional): Filtrar por estado (`issued`, `validated`, `used`, `cancelled`)
- `is_child` (boolean, opcional): Filtrar por tipo (true = niños, false = adultos)
- `include_child_details` (boolean, opcional): Incluir detalles completos de niños (default: true)
- `search` (string, opcional): Buscar por nombre o documento

**Ejemplo de Request**:

```bash
curl -X GET "http://localhost:8000/api/v1/admin/events/event-uuid-1/tickets?status=issued&is_child=false" \
  -H "Authorization: Bearer <token>"
```

**Ejemplo de Response**:

```json
{
  "event": {
    "id": "event-uuid-1",
    "name": "Concierto Rock 2025"
  },
  "tickets": [
    {
      "id": "ticket-uuid-1",
      "holder_first_name": "Juan",
      "holder_last_name": "Pérez",
      "holder_document_type": "rut",
      "holder_document_number": "12345678-9",
      "is_child": false,
      "status": "issued",
      "qr_signature": "abc123def456...",
      "issued_at": "2025-11-10T15:30:00Z",
      "validated_at": null,
      "used_at": null,
      "order_item": {
        "order_id": "order-uuid-1",
        "order": {
          "user": {
            "email": "comprador@ejemplo.com",
            "first_name": "María",
            "last_name": "González"
          }
        }
      },
      "child_details": null
    },
    {
      "id": "ticket-uuid-2",
      "holder_first_name": "Pedrito",
      "holder_last_name": "Pérez",
      "holder_document_type": "rut",
      "holder_document_number": "23456789-0",
      "is_child": true,
      "status": "issued",
      "qr_signature": "xyz789uvw456...",
      "issued_at": "2025-11-10T15:30:00Z",
      "validated_at": null,
      "used_at": null,
      "order_item": {
        "order_id": "order-uuid-1",
        "order": {
          "user": {
            "email": "comprador@ejemplo.com",
            "first_name": "María",
            "last_name": "González"
          }
        }
      },
      "child_details": {
        "nombre": "Pedrito Pérez",
        "rut": "23456789-0",
        "tipo_documento": "rut",
        "fecha_nacimiento": "2015-05-20",
        "edad": 10,
        "correo": null,
        "toma_medicamento": true,
        "es_alergico": false,
        "detalle_alergias": null,
        "nombre_contacto_emergencia": "María González",
        "parentesco_contacto_emergencia": "Madre",
        "numero_emergencia": "+56912345678",
        "pais_telefono": "CL",
        "iglesia": "Iglesia Central",
        "tiene_necesidad_especial": false,
        "detalle_necesidad_especial": null,
        "medicamentos": [
          {
            "nombre_medicamento": "Ibuprofeno",
            "frecuencia": "Cada 8 horas",
            "observaciones": "Solo si tiene fiebre"
          }
        ]
      }
    }
  ],
  "summary": {
    "total": 650,
    "adults": 550,
    "children": 100,
    "by_status": {
      "issued": 600,
      "validated": 40,
      "used": 10,
      "cancelled": 0
    }
  }
}
```

**Uso**:
Este endpoint es ideal para:

- Ver todos los asistentes confirmados de un evento
- Revisar detalles médicos de niños
- Generar listas de asistencia
- Verificar estado de tickets vendidos

---

### GET /api/v1/admin/events/{event_id}/tickets/children/export

Exporta datos de niños en formato JSON optimizado para generar Excel en frontend.

**Autenticación**: Requerida (rol `admin` o `coordinator`)

**Path Parameters**:

- `event_id` (string, requerido): ID del evento (UUID)

**Ejemplo de Request**:

```bash
curl -X GET http://localhost:8000/api/v1/admin/events/event-uuid-1/tickets/children/export \
  -H "Authorization: Bearer <token>"
```

**Ejemplo de Response**:

```json
{
  "event": {
    "id": "event-uuid-1",
    "name": "Campamento Verano 2025"
  },
  "children": [
    {
      "ticket_id": "ticket-uuid-2",
      "nombre": "Pedrito Pérez",
      "rut": "23456789-0",
      "tipo_documento": "rut",
      "fecha_nacimiento": "2015-05-20",
      "edad": 10,
      "correo": null,
      "toma_medicamento": true,
      "es_alergico": false,
      "detalle_alergias": null,
      "nombre_contacto_emergencia": "María González",
      "parentesco_contacto_emergencia": "Madre",
      "numero_emergencia": "+56912345678",
      "pais_telefono": "CL",
      "iglesia": "Iglesia Central",
      "tiene_necesidad_especial": false,
      "detalle_necesidad_especial": null,
      "medicamentos": [
        {
          "nombre_medicamento": "Ibuprofeno",
          "frecuencia": "Cada 8 horas",
          "observaciones": "Solo si tiene fiebre"
        }
      ],
      "ticket_status": "issued",
      "comprador": {
        "nombre": "María González",
        "email": "comprador@ejemplo.com"
      }
    }
  ]
}
```

**Uso**:
Este endpoint es ideal para:

- Exportar lista de niños a Excel/CSV
- Imprimir listas con información médica
- Coordinadores que necesitan información completa de niños
- Generar reportes de asistencia

---

## Modelos de Datos

### Event (Evento)

```typescript
interface Event {
  id: string; // UUID
  organizer_id: string; // UUID del organizador
  name: string; // Nombre del evento
  location_text: string | null; // Ubicación en texto
  point_location: string | null; // Coordenadas "lat,lng"
  starts_at: string; // ISO 8601 datetime
  ends_at: string | null; // ISO 8601 datetime
  capacity_total: number; // Capacidad total
  capacity_available: number; // Capacidad disponible
  allow_children: boolean; // Permite niños
  category: string; // Categoría del evento
  description: string | null; // Descripción
  image_url: string | null; // URL de imagen
  created_at: string; // ISO 8601 datetime
  updated_at: string | null; // ISO 8601 datetime
}
```

### Order (Orden de Compra)

```typescript
interface Order {
  id: string; // UUID
  user_id: string; // UUID del usuario
  subtotal: number; // Subtotal en CLP
  discount_total: number; // Descuentos aplicados
  total: number; // Total a pagar
  commission_total: number; // Total de comisiones
  currency: string; // "CLP"
  status: OrderStatus; // Estado de la orden
  payment_provider: string | null; // "mercadopago"
  payment_reference: string | null; // ID de pago en MP
  idempotency_key: string | null; // Clave de idempotencia
  created_at: string; // ISO 8601 datetime
  updated_at: string; // ISO 8601 datetime
  paid_at: string | null; // ISO 8601 datetime
}

type OrderStatus =
  | "pending" // Esperando pago
  | "processing" // Procesando pago
  | "completed" // Completada
  | "cancelled" // Cancelada
  | "refunded"; // Reembolsada
```

### Ticket

```typescript
interface Ticket {
  id: string; // UUID
  order_item_id: string; // UUID del item de orden
  event_id: string; // UUID del evento
  holder_first_name: string; // Nombre del titular
  holder_last_name: string; // Apellido del titular
  holder_document_type: string | null; // Tipo de documento
  holder_document_number: string | null; // Número de documento
  is_child: boolean; // Es un niño
  qr_signature: string; // Firma QR única
  pdf_object_key: string | null; // Ruta del PDF en MinIO
  status: TicketStatus; // Estado del ticket
  issued_at: string; // ISO 8601 datetime
  validated_at: string | null; // ISO 8601 datetime
  used_at: string | null; // ISO 8601 datetime
  scanned_by: string | null; // UUID del escáner
  created_at: string; // ISO 8601 datetime
  updated_at: string; // ISO 8601 datetime
}

type TicketStatus =
  | "issued" // Emitido
  | "validated" // Validado (primer escaneo)
  | "used" // Usado (entrada completada)
  | "cancelled"; // Cancelado
```

### TicketChildDetail (Detalles de Ticket de Niño)

**Nota**: Los campos están en español para mantener compatibilidad con Supabase.

```typescript
interface TicketChildDetail {
  id: string; // UUID
  ticket_id: string; // UUID del ticket
  nombre: string; // Nombre del niño
  rut: string; // RUT o documento
  correo: string | null; // Email
  fecha_nacimiento: string; // Fecha (ISO 8601 date)
  edad: number; // Edad calculada
  tipo_documento: string; // "rut", "dni_ar", etc.
  toma_medicamento: boolean; // Toma medicamentos
  es_alergico: boolean; // Tiene alergias
  detalle_alergias: string | null; // Detalles de alergias
  tiene_necesidad_especial: boolean; // Necesidades especiales
  detalle_necesidad_especial: string | null; // Detalles
  numero_emergencia: string; // Teléfono de emergencia
  pais_telefono: string; // Código de país (ej: "CL")
  nombre_contacto_emergencia: string | null; // Nombre contacto
  parentesco_contacto_emergencia: string | null; // Parentesco
  iglesia: string | null; // Iglesia (opcional)
  created_at: string; // ISO 8601 datetime
  updated_at: string; // ISO 8601 datetime
}
```

---

## Códigos de Estado HTTP

### Códigos de Éxito

- `200 OK`: Petición exitosa
- `201 Created`: Recurso creado exitosamente
- `204 No Content`: Petición exitosa sin contenido en respuesta

### Códigos de Error del Cliente

- `400 Bad Request`: Datos inválidos o faltantes
- `401 Unauthorized`: Token inválido o ausente
- `403 Forbidden`: Sin permisos para realizar la acción
- `404 Not Found`: Recurso no encontrado

### Códigos de Error del Servidor

- `500 Internal Server Error`: Error interno del servidor
- `503 Service Unavailable`: Servicio temporalmente no disponible

---

## Paginación

Los endpoints que retornan listas (como `/api/v1/events`) soportan paginación mediante:

- `limit`: Número de resultados por página (default: 50, max: 100)
- `offset`: Número de resultados a omitir (default: 0)

**Ejemplo**:

```bash
GET /api/v1/events?limit=20&offset=40
```

Esto retornará los resultados 41-60.

---

## Rate Limiting

La API implementa rate limiting para prevenir abuso:

- **Global**: Límite aplicado a todas las peticiones
- **Por IP**: Se trackean peticiones por dirección IP
- **Por Usuario**: Se trackean peticiones por token de usuario autenticado

Si excedes el límite, recibirás un código `429 Too Many Requests`.

---

## Webhooks

### Mercado Pago Webhook

La API recibe notificaciones automáticas de Mercado Pago en:

```
POST /api/v1/purchases/webhook
```

Este endpoint procesa:

- Pagos aprobados → Genera tickets y envía emails
- Pagos rechazados → Cancela orden y libera capacidad
- Pagos reembolsados → Marca orden como reembolsada

**Nota**: No es necesario implementar este endpoint en el frontend, es solo para comunicación servidor-a-servidor.

---

## Notas Importantes

### Idempotencia

Para la compra de tickets, usa el campo `idempotency_key` para prevenir compras duplicadas. Si envías la misma clave dos veces, obtendrás la misma respuesta sin crear una segunda orden.

### Capacidad de Eventos

La capacidad se gestiona automáticamente:

1. Al crear una orden, se **reserva** capacidad
2. Si el pago es exitoso, la reserva se **confirma**
3. Si el pago falla o expira, la capacidad se **libera**

### Manejo de Fechas

Todas las fechas están en formato ISO 8601 (UTC):

```
2025-11-11T10:00:00Z
```

### UUIDs

Todos los IDs en la API son UUIDs v4 en formato string:

```
"123e4567-e89b-12d3-a456-426614174000"
```

---

## Documentación Interactiva

Puedes explorar la API de forma interactiva en:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

Estas interfaces permiten probar todos los endpoints directamente desde el navegador.

---

## Soporte

Para preguntas o problemas con la API:

- **Email**: soporte@crodify.com
- **Logs**: Consulta los logs del backend con `docker compose logs -f backend`
- **Estado del servicio**: Usa los endpoints `/health` y `/ready` para verificar el estado

---

## Changelog

### v1.1.0 (2025-11-11)

- ✅ **Nuevos endpoints administrativos** (10 endpoints):
  - `GET /api/v1/admin/organizer` - Información del organizador
  - `GET /api/v1/admin/scanners` - Listar scanners
  - `GET /api/v1/admin/users` - Listar usuarios por rol
  - `PUT /api/v1/admin/users/{id}/role` - Cambiar rol de usuario
  - `POST /api/v1/admin/scanners` - Crear scanner
  - `DELETE /api/v1/admin/scanners/{id}` - Remover scanner
  - `GET /api/v1/admin/stats` - Estadísticas del dashboard
  - `GET /api/v1/admin/events` - Eventos con estadísticas
  - `GET /api/v1/admin/events/{id}/tickets` - Tickets con detalles completos
  - `GET /api/v1/admin/events/{id}/tickets/children/export` - Exportar datos de niños
- ✅ Servicios admin completamente funcionales
- ✅ Migración de lógica de adminService y ticketsAdminService del frontend

### v1.0.0 (2025-11-11)

- Release inicial de la API
- Endpoints de eventos, compras, tickets y validación
- Integración con Mercado Pago
- Sistema de notificaciones por email
