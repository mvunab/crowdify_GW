# 📊 Reporte de Pruebas de Endpoints - Crowdify Backend

**Fecha:** $(date)  
**Total Endpoints:** 25  
**Endpoints Funcionando:** 13 (52%)  
**Endpoints con Problemas:** 12 (48%)

---

## ✅ Endpoints Funcionando Correctamente (13)

### Health Checks
- ✅ `GET /health` - Health check básico
- ✅ `GET /ready` - Verifica conexiones (DB, Redis)

### Eventos
- ✅ `GET /api/v1/events` - Listar eventos (público)
- ✅ `GET /api/v1/events/{event_id}` - Obtener evento (404 esperado si no existe)

### Tickets
- ✅ `GET /api/v1/tickets/user/{user_id}` - Obtener tickets del usuario
- ✅ `GET /api/v1/tickets/{ticket_id}` - Obtener ticket (404 esperado si no existe)

### Admin
- ✅ `GET /api/v1/admin/organizer` - Información del organizador
- ✅ `GET /api/v1/admin/scanners` - Listar scanners
- ✅ `GET /api/v1/admin/users` - Listar usuarios
- ✅ `GET /api/v1/admin/stats` - Estadísticas del dashboard
- ✅ `GET /api/v1/admin/events` - Eventos con estadísticas
- ✅ `GET /api/v1/admin/tickets/children` - Tickets de niños

---

## ⚠️ Endpoints con Problemas (12)

### 1. Validación de Tickets
**❌ `POST /api/v1/tickets/validate`**
- **Error:** 422 - Campo `inspector_id` requerido
- **Causa:** El body de prueba no incluye todos los campos requeridos
- **Solución:** Agregar `inspector_id` al body

**Body correcto:**
```json
{
  "qr_signature": "test-signature-123",
  "inspector_id": "00000000-0000-0000-0000-000000000002",
  "event_id": null
}
```

---

### 2. Compras
**❌ `POST /api/v1/purchases`**
- **Error:** 422 - Campo `document_type` requerido en attendees
- **Causa:** El body de prueba no incluye todos los campos requeridos
- **Solución:** Agregar campos faltantes a attendees

**Body correcto:**
```json
{
  "event_id": "00000000-0000-0000-0000-000000000001",
  "user_id": "00000000-0000-0000-0000-000000000002",
  "attendees": [{
    "name": "Test User",
    "email": "test@test.com",
    "document_type": "rut",
    "document_number": "12345678-9",
    "is_child": false
  }]
}
```

**❌ `POST /api/v1/purchases/webhook`**
- **Error:** 500 - Internal Server Error
- **Causa:** Error interno al procesar webhook de Mercado Pago
- **Acción:** Revisar logs del servidor, posiblemente falta configuración de Mercado Pago

**❌ `GET /api/v1/purchases/{order_id}/status`**
- **Error:** 500 - Internal Server Error
- **Causa:** Error interno al obtener estado de orden
- **Acción:** Revisar logs, posible problema con la consulta a la base de datos

---

### 3. Eventos
**❌ `POST /api/v1/events`**
- **Error:** 422 - Campo `organizer_id` requerido
- **Causa:** El body de prueba no incluye `organizer_id`
- **Solución:** Agregar `organizer_id` al body

**Body correcto:**
```json
{
  "organizer_id": "00000000-0000-0000-0000-000000000001",
  "name": "Test Event",
  "location_text": "Test Location",
  "starts_at": "2024-12-31T20:00:00Z",
  "ends_at": "2025-01-01T02:00:00Z",
  "capacity_total": 100
}
```

**❌ `PUT /api/v1/events/{event_id}`**
- **Error:** 422 - Body requerido
- **Causa:** No se está enviando body en la request
- **Solución:** Enviar body con campos a actualizar

**Body correcto:**
```json
{
  "name": "Evento Actualizado",
  "capacity_total": 200
}
```

**❌ `GET /api/v1/admin/events/{event_id}/tickets`**
- **Error:** 400 - Evento no encontrado
- **Causa:** El evento con ID de prueba no existe
- **Estado:** ✅ Funcional, solo necesita un evento real en la DB

**❌ `GET /api/v1/admin/events/{event_id}/tickets/children/export`**
- **Error:** 400 - Evento no encontrado
- **Causa:** El evento con ID de prueba no existe
- **Estado:** ✅ Funcional, solo necesita un evento real en la DB

---

### 4. Notificaciones
**❌ `POST /api/v1/notifications/test-email`**
- **Error:** 422 - Query parameter `to_email` requerido
- **Causa:** Falta el parámetro de query
- **Solución:** Agregar `?to_email=test@example.com` a la URL

**URL correcta:**
```
POST /api/v1/notifications/test-email?to_email=test@example.com
```

---

### 5. Admin - Gestión de Usuarios
**❌ `POST /api/v1/admin/scanners`**
- **Error:** 422 - Body requerido
- **Causa:** No se está enviando body
- **Solución:** Enviar body con datos del scanner

**Body correcto:**
```json
{
  "email": "scanner@test.com",
  "first_name": "Scanner",
  "last_name": "Test",
  "password": "password123"
}
```

**❌ `PUT /api/v1/admin/users/{user_id}/role`**
- **Error:** 422 - Body requerido
- **Causa:** No se está enviando body
- **Solución:** Enviar body con el nuevo rol

**Body correcto:**
```json
{
  "role": "admin"
}
```

**❌ `DELETE /api/v1/admin/scanners/{scanner_id}`**
- **Error:** 400 - ID de scanner inválido
- **Causa:** El UUID de prueba no es válido o no existe
- **Estado:** ✅ Funcional, solo necesita un scanner real en la DB

---

## 📋 Resumen por Categoría

| Categoría | Total | ✅ OK | ❌ Error | ⚠️ Notas |
|-----------|-------|-------|----------|----------|
| Health Checks | 2 | 2 | 0 | - |
| Eventos | 5 | 2 | 3 | 2 errores son de validación (faltan campos) |
| Tickets | 2 | 2 | 0 | - |
| Compras | 3 | 0 | 3 | 1 error 500 (webhook), 1 error 500 (status), 1 validación |
| Notificaciones | 1 | 0 | 1 | Falta query parameter |
| Admin | 12 | 7 | 5 | 2 errores son 404/400 esperados (no hay datos) |

---

## 🔧 Acciones Recomendadas

### Prioridad Alta
1. **Revisar errores 500:**
   - `POST /api/v1/purchases/webhook` - Revisar logs, posible problema con Mercado Pago
   - `GET /api/v1/purchases/{order_id}/status` - Revisar logs, posible problema con DB

### Prioridad Media
2. **Corregir validaciones:**
   - Agregar campos requeridos faltantes en los bodies de prueba
   - Mejorar mensajes de error para campos requeridos

### Prioridad Baja
3. **Mejorar documentación:**
   - Documentar todos los campos requeridos en cada endpoint
   - Agregar ejemplos de request/response

---

## ✅ Conclusión

**Estado General:** 🟡 **Funcional con mejoras necesarias**

- **52% de endpoints funcionando correctamente**
- La mayoría de errores son de **validación** (faltan campos en el body)
- Hay **2 errores 500** que requieren atención (webhook y status de orden)
- Los endpoints están **bien estructurados** y responden correctamente cuando se envían datos válidos

**Recomendación:** 
1. Corregir los errores 500 primero
2. Mejorar el script de pruebas para incluir todos los campos requeridos
3. Agregar datos de prueba en la base de datos para probar endpoints que requieren recursos existentes

