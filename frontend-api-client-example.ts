/**
 * Ejemplo de Cliente API para Frontend
 * 
 * Este es un ejemplo de cómo integrar el backend de Crodify en tu frontend React/TypeScript
 * 
 * Instrucciones:
 * 1. Copia este archivo a tu proyecto frontend
 * 2. Ajusta las importaciones según tu setup (ej: supabase client)
 * 3. Usa este cliente en tus componentes
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

// Tipos TypeScript
interface Event {
  id: string
  organizer_id: string
  name: string
  location_text?: string | null
  point_location?: string | null
  starts_at: string
  ends_at?: string | null
  capacity_total: number
  capacity_available: number
  allow_children: boolean
  category?: string
  description?: string | null
  image_url?: string | null
  created_at: string
  updated_at?: string | null
}

interface AttendeeData {
  name: string
  email?: string | null
  document_type: string
  document_number: string
  is_child: boolean
  child_details?: {
    birth_date?: string
    allergies?: string | null
    special_needs?: string | null
    emergency_contact_name?: string | null
    emergency_contact_phone?: string | null
    medications?: Array<{
      name: string
      frequency: string
      notes?: string | null
    }>
  } | null
}

interface PurchaseRequest {
  user_id: string
  event_id: string
  attendees: AttendeeData[]
  selected_services?: Record<string, number>
  idempotency_key?: string | null
}

interface PurchaseResponse {
  order_id: string
  payment_link: string
  status: string
}

interface OrderStatus {
  order_id: string
  status: string
  total: number
  currency: string
  payment_provider?: string | null
  payment_reference?: string | null
  created_at: string
  paid_at?: string | null
}

interface Ticket {
  id: string
  order_item_id: string
  event_id: string
  holder_first_name: string
  holder_last_name: string
  holder_document_type?: string | null
  holder_document_number?: string | null
  is_child: boolean
  qr_signature: string
  pdf_object_key?: string | null
  status: string
  issued_at: string
  validated_at?: string | null
  used_at?: string | null
  created_at: string
  updated_at: string
}

interface EventFilters {
  category?: string
  search?: string
  date_from?: string
  date_to?: string
  limit?: number
  offset?: number
}

// Cliente API
class CrodifyApiClient {
  private async getToken(): Promise<string | null> {
    // TODO: Implementar obtención de token desde Supabase Auth
    // Ejemplo:
    // const { data: { session } } = await supabase.auth.getSession()
    // return session?.access_token || null
    
    // Por ahora, retornar null (solo para endpoints públicos)
    return null
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const token = await this.getToken()
    
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    }

    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers,
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ 
        detail: response.statusText 
      }))
      throw new Error(error.detail || `HTTP ${response.status}`)
    }

    // Si es 204 No Content, retornar void
    if (response.status === 204) {
      return undefined as T
    }

    return response.json()
  }

  // ========== Health Checks ==========
  
  async health() {
    return this.request<{ status: string; service: string }>('/health')
  }

  async ready() {
    return this.request<{ 
      status: string
      database: string
      redis: string
    }>('/ready')
  }

  // ========== Eventos ==========

  async getEvents(filters?: EventFilters): Promise<Event[]> {
    const params = new URLSearchParams()
    
    if (filters?.category) params.append('category', filters.category)
    if (filters?.search) params.append('search', filters.search)
    if (filters?.date_from) params.append('date_from', filters.date_from)
    if (filters?.date_to) params.append('date_to', filters.date_to)
    if (filters?.limit) params.append('limit', filters.limit.toString())
    if (filters?.offset) params.append('offset', filters.offset.toString())
    
    const query = params.toString()
    return this.request<Event[]>(`/api/v1/events${query ? `?${query}` : ''}`)
  }

  async getEvent(eventId: string): Promise<Event> {
    return this.request<Event>(`/api/v1/events/${eventId}`)
  }

  async createEvent(eventData: Partial<Event>): Promise<Event> {
    return this.request<Event>('/api/v1/events', {
      method: 'POST',
      body: JSON.stringify(eventData),
    })
  }

  async updateEvent(eventId: string, eventData: Partial<Event>): Promise<Event> {
    return this.request<Event>(`/api/v1/events/${eventId}`, {
      method: 'PUT',
      body: JSON.stringify(eventData),
    })
  }

  async deleteEvent(eventId: string): Promise<void> {
    return this.request<void>(`/api/v1/events/${eventId}`, {
      method: 'DELETE',
    })
  }

  // ========== Compras ==========

  async createPurchase(data: PurchaseRequest): Promise<PurchaseResponse> {
    return this.request<PurchaseResponse>('/api/v1/purchases', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async getOrderStatus(orderId: string): Promise<OrderStatus> {
    return this.request<OrderStatus>(`/api/v1/purchases/${orderId}/status`)
  }

  // ========== Tickets ==========

  async getUserTickets(userId: string): Promise<Ticket[]> {
    return this.request<Ticket[]>(`/api/v1/tickets/user/${userId}`)
  }

  async getTicket(ticketId: string): Promise<Ticket> {
    return this.request<Ticket>(`/api/v1/tickets/${ticketId}`)
  }

  async validateTicket(
    qrSignature: string,
    inspectorId: string,
    eventId?: string
  ): Promise<{
    valid: boolean
    ticket_id?: string
    event_id?: string
    attendee_name?: string
    message?: string
  }> {
    return this.request('/api/v1/tickets/validate', {
      method: 'POST',
      body: JSON.stringify({
        qr_signature: qrSignature,
        inspector_id: inspectorId,
        event_id: eventId,
      }),
    })
  }
}

// Exportar instancia singleton
export const api = new CrodifyApiClient()

// Exportar tipos
export type {
  Event,
  AttendeeData,
  PurchaseRequest,
  PurchaseResponse,
  OrderStatus,
  Ticket,
  EventFilters,
}

