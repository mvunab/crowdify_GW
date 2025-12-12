# Crowdify API - Guía de Integración Frontend

> **Versión**: 1.2.0  
> **Última actualización**: Diciembre 2025  
> **Contacto técnico**: Backend Team

---

## 📋 Índice

1. [Información General](#información-general)
2. [Autenticación](#autenticación)
3. [Endpoints Públicos](#endpoints-públicos)
4. [Endpoints de Usuario](#endpoints-de-usuario)
5. [Endpoints de Compra](#endpoints-de-compra)
6. [Endpoints de Tickets](#endpoints-de-tickets)
7. [Endpoints de Administración](#endpoints-de-administración)
8. [Modelos TypeScript](#modelos-typescript)
9. [Códigos de Error y Manejo](#códigos-de-error-y-manejo)
10. [Rate Limiting](#rate-limiting)
11. [Ejemplos de Implementación](#ejemplos-de-implementación)

---

## Información General

### URLs Base

| Entorno    | URL                        |
| ---------- | -------------------------- |
| Desarrollo | `http://localhost:8000`    |
| Producción | `https://api.crowdify.com` |

### Headers Requeridos

```typescript
const headers = {
  "Content-Type": "application/json",
  Authorization: `Bearer ${token}`, // Solo para endpoints protegidos
};
```

### Formato de Respuestas

- Todas las respuestas son **JSON**
- Las fechas están en formato **ISO 8601 UTC**: `"2025-12-15T20:00:00Z"`
- Los IDs son **UUID v4**: `"123e4567-e89b-12d3-a456-426614174000"`

---

## Autenticación

### Tipo de Autenticación

**JWT Bearer Token** - Se debe incluir en el header `Authorization`:

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Roles de Usuario

| Rol           | Descripción            | Permisos                                       |
| ------------- | ---------------------- | ---------------------------------------------- |
| `user`        | Usuario estándar       | Comprar tickets, ver sus tickets               |
| `scanner`     | Escáner de tickets     | Validar tickets                                |
| `coordinator` | Coordinador de eventos | Ver tickets de eventos, algunos permisos admin |
| `admin`       | Administrador          | Acceso completo                                |

### Obtención del Token

El token JWT se obtiene desde **Supabase Auth**. El backend valida los tokens de Supabase.

---

## Endpoints Públicos

### Health Check

```http
GET /health
```

**Response:**

```json
{
  "status": "ok",
  "service": "crodify-api"
}
```

### Ready Check (con dependencias)

```http
GET /ready
```

**Response:**

```json
{
  "status": "ready",
  "database": "connected",
  "redis": "connected"
}
```

---

## Endpoints de Eventos

### Listar Eventos

```http
GET /api/v1/events
```

**Auth:** Opcional (público)

**Query Parameters:**

| Parámetro   | Tipo     | Descripción                            |
| ----------- | -------- | -------------------------------------- |
| `category`  | string   | Filtrar por categoría                  |
| `search`    | string   | Buscar por nombre/ubicación            |
| `date_from` | ISO 8601 | Fecha desde                            |
| `date_to`   | ISO 8601 | Fecha hasta                            |
| `limit`     | number   | Máx resultados (default: 50, max: 100) |
| `offset`    | number   | Offset para paginación                 |

**Response:**

```json
[
  {
    "id": "uuid",
    "organizer_id": "uuid",
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

### Obtener Evento por ID

```http
GET /api/v1/events/{event_id}
```

**Auth:** Opcional (público)

**Response:** Mismo formato que el item del listado

---

## Endpoints de Compra

### ⚠️ ENDPOINT PRINCIPAL - Crear Compra

```http
POST /api/v1/purchases
```

**Auth:** Opcional (permite compras anónimas)

**⚡ Rate Limit:** `10 requests/minuto por IP`

**Request Body:**

```typescript
interface PurchaseRequest {
  user_id?: string; // Opcional - UUID del usuario
  event_id: string; // Requerido - UUID del evento
  attendees: AttendeeData[]; // Requerido - Lista de asistentes
  selected_services?: Record<string, number>; // Opcional - {serviceId: quantity}
  idempotency_key?: string; // Opcional - Clave para evitar duplicados
  payment_method?: "mercadopago" | "payku" | "bank_transfer";
  receipt_url?: string; // Solo para bank_transfer
}

interface AttendeeData {
  name: string; // Requerido - Nombre completo
  email: string; // Requerido - Email del asistente
  document_type?: string; // Opcional - "RUT" | "PASSPORT" | "DNI"
  document_number?: string; // Opcional - Número de documento
  is_child: boolean; // Default: false
  child_details?: ChildDetailsData; // Requerido si is_child=true
}

interface ChildDetailsData {
  birth_date?: string; // ISO 8601 date
  allergies?: string;
  special_needs?: string;
  emergency_contact_name?: string;
  emergency_contact_phone?: string;
  medications?: Medication[];
}

interface Medication {
  name: string;
  frequency: string;
  notes?: string;
}
```

**Response:**

```typescript
interface PurchaseResponse {
  order_id: string; // UUID de la orden creada
  payment_link?: string; // URL de pago (Payku/legacy MP)
  preference_id?: string; // ID para MercadoPago Payment Brick
  status: "pending" | "completed" | "failed";
  payment_method?: string;
}
```

**Ejemplo Request:**

```json
{
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
      "is_child": true,
      "child_details": {
        "birth_date": "2018-05-15",
        "allergies": "Ninguna",
        "emergency_contact_name": "Juan Pérez",
        "emergency_contact_phone": "+56912345678"
      }
    }
  ],
  "payment_method": "mercadopago",
  "idempotency_key": "unique-key-12345"
}
```

### Obtener Estado de Orden

```http
GET /api/v1/purchases/{order_id}/status
```

**Auth:** Requerida (propietario o admin)

**Response:**

```typescript
interface OrderStatusResponse {
  order_id: string;
  status: "pending" | "processing" | "completed" | "cancelled" | "refunded";
  total: number;
  currency: string; // "CLP"
  payment_provider?: string;
  payment_reference?: string;
  created_at: string;
  paid_at?: string;
  attendees_data?: AttendeeData[];
  services?: ServiceItem[];
}

interface ServiceItem {
  service_id: string;
  service_name: string;
  quantity: number;
  unit_price: number;
  total_price: number;
}
```

---

## Endpoints de Tickets

### Obtener Tickets del Usuario

```http
GET /api/v1/tickets/user/{user_id}
```

**Auth:** Requerida (propietario o admin/coordinator)

**Response:**

```typescript
interface UserTicket {
  id: string;
  eventId: string;
  id_evento: string; // Alias de compatibilidad
  holder_first_name: string;
  holder_last_name: string;
  attendeeName: string; // Nombre completo
  holder_document_type?: string;
  holder_document_number?: string;
  is_child: boolean;
  qr_signature: string;
  qr_code: string; // Alias de qr_signature
  status: string;
  estado: string; // Status en español
  issued_at?: string;
  used_at?: string;
  purchaseDate?: string;
  event: {
    id: string;
    title: string;
    nombre: string; // Alias de title
    location: string;
    date: string;
    time: string;
    capacity_total: number;
    allow_children: boolean;
  };
}
```

**Mapeo de Estados:**
| Backend | Frontend |
|---------|----------|
| `issued` | `comprado` |
| `validated` | `validado` |
| `used` | `usado` |
| `cancelled` | `cancelado` |

### 🔓 Buscar Tickets por Email (PÚBLICO)

```http
GET /api/v1/tickets/email/{email}
```

**Auth:** No requerida

**Descripción:** Permite buscar tickets sin autenticación usando el email del titular.

**Response:** Array de tickets con formato similar a `/user/{user_id}`

### Obtener Ticket por ID

```http
GET /api/v1/tickets/{ticket_id}
```

**Auth:** Requerida (scanner/admin/coordinator)

### Validar Ticket (QR)

```http
POST /api/v1/tickets/validate
```

**Auth:** Requerida (scanner/admin/coordinator)

**Request:**

```typescript
interface TicketValidationRequest {
  qr_signature: string; // Contenido del QR escaneado
  inspector_id: string; // UUID del scanner
  event_id?: string; // UUID del evento (opcional)
}
```

**Response:**

```typescript
interface TicketValidationResponse {
  valid: boolean;
  ticket_id?: string;
  event_id?: string;
  attendee_name?: string;
  message: string;
}
```

**Posibles mensajes:**

- `"Ticket validado correctamente"`
- `"Ticket ya fue utilizado"`
- `"Ticket no encontrado"`
- `"Ticket cancelado"`
- `"Ticket no pertenece a este evento"`

---

## Endpoints de Administración

> **Todos requieren:** `Authorization: Bearer <admin_token>`

### Dashboard Stats

```http
GET /api/v1/admin/stats
```

**Query Params:** `date_from`, `date_to` (ISO 8601)

**Response:**

```typescript
interface DashboardStats {
  total_events: number;
  active_events: number;
  total_tickets_sold: number;
  total_revenue: number;
  currency: string;
  period: {
    from_date: string;
    to_date: string;
  };
}
```

### Listar Eventos del Organizador

```http
GET /api/v1/admin/events
```

**Query Params:**

- `status`: `upcoming` | `ongoing` | `past` | `all`
- `sort`: `starts_at_asc` | `starts_at_desc` | `revenue_desc`

**Response:** Lista de eventos con estadísticas detalladas

### Listar Tickets de un Evento

```http
GET /api/v1/admin/events/{event_id}/tickets
```

**Query Params:**

- `status`: `issued` | `validated` | `used` | `cancelled`
- `is_child`: `true` | `false`
- `search`: Buscar por nombre/documento
- `include_child_details`: `true` | `false`

### Exportar Datos de Niños

```http
GET /api/v1/admin/events/{event_id}/tickets/children/export
```

**Descripción:** Retorna JSON optimizado para exportar a Excel

### Gestión de Usuarios

```http
GET /api/v1/admin/users?role=user
GET /api/v1/admin/scanners
POST /api/v1/admin/scanners
PUT /api/v1/admin/users/{user_id}/role
DELETE /api/v1/admin/scanners/{scanner_id}
```

### Gestión de Órdenes

```http
GET /api/v1/admin/orders
GET /api/v1/admin/orders/{order_id}
PUT /api/v1/admin/orders/{order_id}/approve    # Aprobar transferencia bancaria
PUT /api/v1/admin/orders/{order_id}/reject     # Rechazar orden
```

---

## Modelos TypeScript

### Tipos Completos para Frontend

```typescript
// ==================== EVENTOS ====================
interface Event {
  id: string;
  organizer_id: string;
  name: string;
  location_text: string | null;
  point_location: string | null;
  starts_at: string;
  ends_at: string | null;
  capacity_total: number;
  capacity_available: number;
  allow_children: boolean;
  category: string;
  description: string | null;
  image_url: string | null;
  created_at: string;
  updated_at: string | null;
}

// ==================== ÓRDENES ====================
type OrderStatus =
  | "pending"
  | "processing"
  | "completed"
  | "cancelled"
  | "refunded";

interface Order {
  id: string;
  user_id: string | null;
  subtotal: number;
  discount_total: number;
  total: number;
  commission_total: number;
  currency: string;
  status: OrderStatus;
  payment_provider: string | null;
  payment_reference: string | null;
  idempotency_key: string | null;
  created_at: string;
  updated_at: string;
  paid_at: string | null;
}

// ==================== TICKETS ====================
type TicketStatus = "issued" | "validated" | "used" | "cancelled";

interface Ticket {
  id: string;
  order_item_id: string;
  event_id: string;
  holder_first_name: string;
  holder_last_name: string;
  holder_email: string;
  holder_document_type: string | null;
  holder_document_number: string | null;
  is_child: boolean;
  qr_signature: string;
  pdf_object_key: string | null;
  status: TicketStatus;
  issued_at: string;
  validated_at: string | null;
  used_at: string | null;
  scanned_by: string | null;
  created_at: string;
  updated_at: string;
}

// ==================== DETALLES DE NIÑOS ====================
interface TicketChildDetail {
  id: string;
  ticket_id: string;
  nombre: string;
  rut: string;
  correo: string | null;
  fecha_nacimiento: string;
  edad: number;
  tipo_documento: string;
  toma_medicamento: boolean;
  es_alergico: boolean;
  detalle_alergias: string | null;
  tiene_necesidad_especial: boolean;
  detalle_necesidad_especial: string | null;
  numero_emergencia: string;
  pais_telefono: string;
  nombre_contacto_emergencia: string | null;
  parentesco_contacto_emergencia: string | null;
  iglesia: string | null;
  medicamentos?: ChildMedication[];
}

interface ChildMedication {
  nombre_medicamento: string;
  frecuencia: string;
  observaciones: string | null;
}

// ==================== COMPRA ====================
interface PurchaseRequest {
  user_id?: string;
  event_id: string;
  attendees: AttendeeData[];
  selected_services?: Record<string, number>;
  idempotency_key?: string;
  payment_method?: "mercadopago" | "payku" | "bank_transfer";
  receipt_url?: string;
}

interface AttendeeData {
  name: string;
  email: string;
  document_type?: string;
  document_number?: string;
  is_child: boolean;
  child_details?: ChildDetailsInput;
}

interface ChildDetailsInput {
  birth_date?: string;
  allergies?: string;
  special_needs?: string;
  emergency_contact_name?: string;
  emergency_contact_phone?: string;
  medications?: MedicationInput[];
}

interface MedicationInput {
  name: string;
  frequency: string;
  notes?: string;
}

interface PurchaseResponse {
  order_id: string;
  payment_link?: string;
  preference_id?: string;
  status: "pending" | "completed" | "failed";
  payment_method?: string;
}
```

---

## Códigos de Error y Manejo

### Códigos HTTP

| Código | Significado    | Acción Frontend                |
| ------ | -------------- | ------------------------------ |
| `200`  | Éxito          | Procesar respuesta             |
| `201`  | Creado         | Procesar respuesta             |
| `400`  | Bad Request    | Mostrar `detail` al usuario    |
| `401`  | No autenticado | Redirigir a login              |
| `403`  | Sin permisos   | Mostrar mensaje de permisos    |
| `404`  | No encontrado  | Mostrar "no encontrado"        |
| `409`  | Conflicto      | Compra duplicada (idempotency) |
| `422`  | Validación     | Mostrar errores de campos      |
| `429`  | Rate Limit     | Ver sección Rate Limiting      |
| `500`  | Error servidor | Mostrar error genérico         |

### Formato de Errores

```typescript
interface APIError {
  detail: string | ValidationError[];
}

interface ValidationError {
  loc: (string | number)[];
  msg: string;
  type: string;
}
```

### Ejemplo de Manejo

```typescript
async function apiCall<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${getToken()}`,
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json();

    switch (response.status) {
      case 401:
        // Redirigir a login
        redirectToLogin();
        break;
      case 429:
        // Rate limit alcanzado
        toast.error("Demasiados intentos. Espera un momento.");
        break;
      case 400:
      case 422:
        // Mostrar error de validación
        toast.error(error.detail);
        break;
      default:
        toast.error("Ha ocurrido un error. Intenta de nuevo.");
    }

    throw new Error(error.detail || "Error desconocido");
  }

  return response.json();
}
```

---

## Rate Limiting

### Límites Actuales

| Endpoint                               | Límite          | Ventana  |
| -------------------------------------- | --------------- | -------- |
| `POST /api/v1/purchases`               | **10 requests** | 1 minuto |
| `POST /api/v1/purchases/webhook`       | 100 requests    | 1 minuto |
| `POST /api/v1/purchases/payku-webhook` | 100 requests    | 1 minuto |

### Respuesta cuando se excede

**HTTP Status:** `429 Too Many Requests`

```json
{
  "error": "Rate limit exceeded: 10 per 1 minute"
}
```

### Manejo Recomendado

```typescript
// En tu servicio de API
async function createPurchase(
  data: PurchaseRequest
): Promise<PurchaseResponse> {
  try {
    const response = await api.post("/api/v1/purchases", data);
    return response.data;
  } catch (error) {
    if (error.response?.status === 429) {
      // Rate limit alcanzado
      toast.warning(
        "Demasiados intentos de compra. Por favor espera un momento antes de intentar de nuevo."
      );

      // Opcional: deshabilitar botón por 60 segundos
      disablePurchaseButton(60000);

      return null;
    }
    throw error;
  }
}
```

### Headers de Rate Limit (en respuesta)

```
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 7
X-RateLimit-Reset: 1702400000
```

---

## Ejemplos de Implementación

### Servicio de API (React/TypeScript)

```typescript
// api/client.ts
import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Interceptor para agregar token
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem("supabase_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Interceptor para manejar errores
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token inválido o expirado
      localStorage.removeItem("supabase_token");
      window.location.href = "/login";
    }
    if (error.response?.status === 429) {
      // Rate limit
      console.warn("Rate limit exceeded");
    }
    return Promise.reject(error);
  }
);

export default apiClient;
```

### Servicio de Eventos

```typescript
// services/eventsService.ts
import apiClient from "../api/client";
import { Event } from "../types";

export const eventsService = {
  async getEvents(params?: {
    category?: string;
    search?: string;
    limit?: number;
    offset?: number;
  }): Promise<Event[]> {
    const response = await apiClient.get("/api/v1/events", { params });
    return response.data;
  },

  async getEventById(eventId: string): Promise<Event> {
    const response = await apiClient.get(`/api/v1/events/${eventId}`);
    return response.data;
  },
};
```

### Servicio de Compras

```typescript
// services/purchaseService.ts
import apiClient from "../api/client";
import {
  PurchaseRequest,
  PurchaseResponse,
  OrderStatusResponse,
} from "../types";

export const purchaseService = {
  async createPurchase(data: PurchaseRequest): Promise<PurchaseResponse> {
    // Generar idempotency key si no se proporciona
    if (!data.idempotency_key) {
      data.idempotency_key = `${data.event_id}-${Date.now()}-${Math.random()
        .toString(36)
        .substr(2, 9)}`;
    }

    const response = await apiClient.post("/api/v1/purchases", data);
    return response.data;
  },

  async getOrderStatus(orderId: string): Promise<OrderStatusResponse> {
    const response = await apiClient.get(`/api/v1/purchases/${orderId}/status`);
    return response.data;
  },
};
```

### Servicio de Tickets

```typescript
// services/ticketsService.ts
import apiClient from "../api/client";
import { UserTicket } from "../types";

export const ticketsService = {
  async getUserTickets(userId: string): Promise<UserTicket[]> {
    const response = await apiClient.get(`/api/v1/tickets/user/${userId}`);
    return response.data;
  },

  async getTicketsByEmail(email: string): Promise<UserTicket[]> {
    // Endpoint público - no requiere auth
    const response = await apiClient.get(
      `/api/v1/tickets/email/${encodeURIComponent(email)}`
    );
    return response.data;
  },

  async validateTicket(
    qrSignature: string,
    inspectorId: string,
    eventId?: string
  ) {
    const response = await apiClient.post("/api/v1/tickets/validate", {
      qr_signature: qrSignature,
      inspector_id: inspectorId,
      event_id: eventId,
    });
    return response.data;
  },
};
```

### Hook de Compra (React)

```typescript
// hooks/usePurchase.ts
import { useState } from "react";
import { purchaseService } from "../services/purchaseService";
import { PurchaseRequest, PurchaseResponse } from "../types";

export function usePurchase() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const createPurchase = async (
    data: PurchaseRequest
  ): Promise<PurchaseResponse | null> => {
    setLoading(true);
    setError(null);

    try {
      const response = await purchaseService.createPurchase(data);

      // Redirigir según método de pago
      if (response.payment_method === "mercadopago" && response.preference_id) {
        // Usar MercadoPago Payment Brick
        // ... inicializar brick con preference_id
      } else if (response.payment_link) {
        // Redirigir a payment_link
        window.location.href = response.payment_link;
      }

      return response;
    } catch (err: any) {
      const message =
        err.response?.data?.detail || "Error al procesar la compra";
      setError(message);
      return null;
    } finally {
      setLoading(false);
    }
  };

  return { createPurchase, loading, error };
}
```

---

## Flujo de Compra Completo

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FLUJO DE COMPRA                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. Usuario selecciona evento y asistentes                          │
│     └── Frontend: formulario de compra                              │
│                                                                     │
│  2. POST /api/v1/purchases                                          │
│     ├── Backend crea Order (status: pending)                        │
│     ├── Backend reserva capacidad                                   │
│     └── Backend crea preferencia de pago                            │
│                                                                     │
│  3. Response: { order_id, preference_id/payment_link }              │
│     └── Frontend guarda order_id para polling                       │
│                                                                     │
│  4. Usuario paga                                                    │
│     ├── MercadoPago: usar Payment Brick con preference_id           │
│     ├── Payku: redirigir a payment_link                            │
│     └── Transferencia: mostrar datos bancarios                      │
│                                                                     │
│  5. Webhook recibido (automático)                                   │
│     ├── POST /api/v1/purchases/webhook (MercadoPago)                │
│     └── POST /api/v1/purchases/payku-webhook (Payku)                │
│                                                                     │
│  6. Backend procesa pago                                            │
│     ├── Actualiza Order (status: completed)                         │
│     ├── Genera tickets con QR                                       │
│     └── Envía email con tickets                                     │
│                                                                     │
│  7. Frontend polling (opcional)                                     │
│     ├── GET /api/v1/purchases/{order_id}/status                     │
│     └── Cuando status=completed, mostrar confirmación               │
│                                                                     │
│  8. Usuario recibe email con tickets PDF                            │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Documentación Interactiva

- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`
- **OpenAPI JSON:** `http://localhost:8000/openapi.json`

---

## Changelog

### v1.2.0 (Diciembre 2025)

- ✅ Rate limiting implementado en endpoint de compras (10/min)
- ✅ Pool de conexiones optimizado para alta concurrencia
- ✅ Soporte para compras anónimas (sin user_id)
- ✅ Webhooks de Payku y MercadoPago
- ✅ Procesamiento de tickets en background (no bloquea respuesta)

### v1.1.0 (Noviembre 2025)

- ✅ Endpoints administrativos completos
- ✅ Exportación de datos de niños
- ✅ Gestión de scanners y usuarios

### v1.0.0 (Noviembre 2025)

- Release inicial
- Endpoints de eventos, compras, tickets
- Integración con MercadoPago
- Notificaciones por email

---

## Contacto

- **Backend Issues:** GitHub Issues
- **Documentación API:** `/docs`
- **Logs de Debug:** `docker compose logs -f backend`
