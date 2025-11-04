# Backend API - Crodify

## URL Base
```
http://localhost:8000
```

## Autenticación
- Método: JWT Token en header `Authorization: Bearer <token>`
- Obtener token desde Supabase Auth: `session?.access_token`
- Roles: `user`, `admin`, `scanner`, `coordinator`

## Endpoints

### Eventos (Públicos)
- `GET /api/v1/events?category=musica&limit=10` - Listar eventos
- `GET /api/v1/events/{event_id}` - Detalle de evento

### Compras (Requiere: `user`)
- `POST /api/v1/purchases` - Crear orden de compra
  ```json
  {
    "user_id": "uuid",
    "event_id": "uuid",
    "attendees": [
      {
        "name": "Juan Pérez",
        "email": "juan@example.com",
        "document_type": "RUT",
        "document_number": "12345678-9",
        "is_child": false,
        "child_details": null
      }
    ],
    "selected_services": {},
    "idempotency_key": null
  }
  ```
  Response: `{ "order_id": "uuid", "payment_link": "https://...", "status": "pending" }`

- `GET /api/v1/purchases/{order_id}/status` - Estado de orden
  Response: `{ "order_id": "uuid", "status": "completed", "total": 25000, ... }`
  Status: `pending`, `processing`, `completed`, `cancelled`, `refunded`

### Tickets (Requiere: `user`)
- `GET /api/v1/tickets/user/{user_id}` - Tickets del usuario
  Response: Array de tickets con `qr_signature`, `status`, `holder_first_name`, etc.

### Validación (Requiere: `scanner`)
- `POST /api/v1/tickets/validate` - Validar ticket QR
  ```json
  {
    "qr_signature": "abc123...",
    "inspector_id": "uuid",
    "event_id": "uuid"
  }
  ```

## Configuración
```env
VITE_API_BASE_URL=http://localhost:8000
```

## Flujo de Compra
1. Usuario selecciona evento → `GET /api/v1/events/{id}`
2. Usuario completa datos → `POST /api/v1/purchases`
3. Redirigir a `payment_link` de respuesta
4. Después de pago, verificar → `GET /api/v1/purchases/{order_id}/status`
5. Si `status === "completed"` → `GET /api/v1/tickets/user/{user_id}`

## Errores
Formato: `{ "detail": "mensaje" }`
Códigos: 200 OK, 400 Bad Request, 401 Unauthorized, 403 Forbidden, 404 Not Found, 500 Error

## Swagger
http://localhost:8000/docs

