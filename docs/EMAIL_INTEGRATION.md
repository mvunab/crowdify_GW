# 📧 Integración de Envío de Emails

## ✅ Implementación Completada

El sistema ahora envía automáticamente emails con tickets cuando se completa una compra usando **Resend**.

## 🔄 Servicio de Email: Resend

**Migrado desde MailHog a Resend** para mejor mantenimiento y funcionalidad en desarrollo y producción.

## 🔄 Flujo Automático

### 1. Cuando se Generan Tickets

Cuando una compra se completa y los tickets se generan (método `_generate_tickets` en `purchase_service.py`):

1. ✅ Se generan los tickets en la base de datos
2. ✅ Se actualiza `capacity_available` del evento
3. ✅ **NUEVO:** Se envían emails automáticamente a cada asistente

### 2. Detalles del Envío

- **Agrupación por Email:** Los tickets se agrupan por email del asistente
- **Un Email por Ticket:** Cada ticket se envía en un email separado (fácil de modificar para agrupar)
- **Información Incluida:**
  - Nombre del asistente
  - Nombre del evento
  - Fecha del evento (formateada en español)
  - Ubicación del evento
  - ID del ticket

### 3. Manejo de Errores

- Si el envío de email falla, **NO se bloquea la generación de tickets**
- Los errores se registran en los logs
- Los tickets se generan correctamente aunque el email falle

## 📬 Endpoint de Reenvío

El endpoint `/api/v1/purchases/admin/resend-tickets/{order_id}` ahora:

- ✅ Envía emails reales usando el servicio de email
- ✅ Agrupa tickets por email
- ✅ Retorna estadísticas de envío (exitosos/fallidos)

**Uso:**
```bash
POST /api/v1/purchases/admin/resend-tickets/{order_id}?email=usuario@example.com
```

## 🧪 Pruebas

### 1. Configurar Resend

1. Crea una cuenta en [resend.com](https://resend.com)
2. Obtén tu API key en [resend.com/api-keys](https://resend.com/api-keys)
3. Agrega a tu `.env`:
   ```env
   RESEND_API_KEY=re_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   RESEND_FROM_EMAIL=onboarding@resend.dev
   ```

### 2. Realizar una Compra de Prueba

1. Completa una compra de tickets
2. Cuando el pago se confirme, los tickets se generarán
3. Los emails se enviarán automáticamente usando Resend

### 3. Verificar Emails

- Abre [resend.com/emails](https://resend.com/emails)
- Deberías ver todos los emails enviados
- Cada email contiene:
  - Información del evento
  - Detalles del ticket
  - Nombre del asistente
  - Estado de entrega (enviado, entregado, etc.)

## ⚙️ Configuración

### Variables de Entorno Requeridas

```env
# Resend Configuration (desarrollo y producción)
RESEND_API_KEY=re_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
RESEND_FROM_EMAIL=onboarding@resend.dev  # Para desarrollo
# RESEND_FROM_EMAIL=tickets@tudominio.com  # Para producción (después de verificar dominio)
```

**Obtén tu API key:** [resend.com/api-keys](https://resend.com/api-keys)

## 📝 Notas Importantes

1. **Resend funciona en desarrollo Y producción** - Una sola configuración
2. **En desarrollo**, Resend captura emails automáticamente (ver en dashboard)
3. **En producción**, Resend envía emails reales automáticamente
4. **Los emails se envían asíncronamente** - No bloquean la respuesta del API
5. **Si un email falla**, se registra en los logs pero no afecta la compra
6. **Plan gratuito**: 3,000 emails/mes

## 🔧 Personalización

### Modificar el Contenido del Email

Edita el método `send_ticket_email` en:
- `services/notifications/services/email_service.py`

### Agrupar Múltiples Tickets en un Email

Modifica `_send_ticket_emails` en:
- `services/ticket_purchase/services/purchase_service.py`

Actualmente envía un email por ticket, pero puedes agruparlos por email.

## 🐛 Troubleshooting

### No se reciben emails

1. Verifica que `RESEND_API_KEY` esté configurado:
   ```bash
   docker-compose exec backend env | grep RESEND
   ```

2. Revisa los logs del backend:
   ```bash
   docker-compose logs backend | grep -i email
   ```

3. Verifica en el dashboard de Resend:
   - [resend.com/emails](https://resend.com/emails)

### Error: "RESEND_API_KEY no configurado"

1. Agrega `RESEND_API_KEY` a tu archivo `.env`
2. Reinicia el backend
3. Obtén tu API key en [resend.com/api-keys](https://resend.com/api-keys)

### Error: "Invalid API key"

1. Verifica que la API key sea correcta (debe empezar con `re_`)
2. Asegúrate de que no tenga espacios extra
3. Genera una nueva API key si es necesario

## 📚 Referencias

- [Documentación de Resend](./RESEND_SETUP.md)
- [Servicio de Email](../services/notifications/services/email_service.py)
- [Dashboard de Resend](https://resend.com/emails)
- [Documentación Oficial de Resend](https://resend.com/docs)

