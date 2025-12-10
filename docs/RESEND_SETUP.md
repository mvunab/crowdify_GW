# 📧 Configuración de Resend

## ✅ Migración Completada

El sistema ahora usa **Resend** para envío de emails en desarrollo y producción.

## 🚀 Configuración Inicial

### 1. Crear Cuenta en Resend

1. Visita [resend.com](https://resend.com)
2. Crea una cuenta gratuita
3. Plan gratuito: **3,000 emails/mes**

### 2. Obtener API Key

1. Ve a [API Keys](https://resend.com/api-keys)
2. Haz clic en "Create API Key"
3. Dale un nombre (ej: "Crodify Development")
4. Copia la API key (empieza con `re_`)

### 3. Configurar Variables de Entorno

Agrega a tu archivo `.env`:

```env
# Resend Configuration
RESEND_API_KEY=re_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
RESEND_FROM_EMAIL=onboarding@resend.dev  # Para desarrollo
```

**Nota:** `onboarding@resend.dev` es el email por defecto que Resend proporciona para pruebas. Funciona sin configuración adicional.

## 📧 Para Producción

### 1. Verificar Dominio

1. Ve a [Domains](https://resend.com/domains)
2. Agrega tu dominio (ej: `tudominio.com`)
3. Sigue las instrucciones para verificar DNS
4. Una vez verificado, actualiza `RESEND_FROM_EMAIL`:

```env
RESEND_FROM_EMAIL=tickets@tudominio.com
```

### 2. Configurar DNS

Resend te dará registros DNS para agregar:
- **SPF**: `v=spf1 include:resend.com ~all`
- **DKIM**: Registros específicos que Resend proporciona
- **DMARC**: (Opcional pero recomendado)

## 🧪 Probar el Envío

### 1. Usar el Endpoint de Prueba

```bash
POST /api/v1/notifications/test-email?to_email=tu-email@example.com
```

Requiere autenticación de admin.

### 2. Ver Emails en Resend

1. Ve a [Emails](https://resend.com/emails) en el dashboard
2. Verás todos los emails enviados
3. Puedes ver:
   - Estado (enviado, entregado, rebotado)
   - Contenido del email
   - Logs de entrega

## 📊 Ventajas de Resend

### ✅ Desarrollo
- **Captura automática**: Resend captura emails en desarrollo
- **Dashboard web**: Ver todos los emails en resend.com/emails
- **Sin configuración local**: No necesitas Docker para MailHog

### ✅ Producción
- **Entrega confiable**: 99.9% de entregabilidad
- **Analytics integrado**: Ver aperturas, clics, rebotes
- **Webhooks**: Recibir eventos en tiempo real
- **Templates**: Crear templates reutilizables

## 🔧 Configuración Avanzada

### Variables de Entorno Completas

```env
# Resend (Recomendado)
RESEND_API_KEY=re_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
RESEND_FROM_EMAIL=tickets@tudominio.com

# SMTP Legacy (solo si necesitas usar SMTP)
# SMTP_HOST=smtp.example.com
# SMTP_PORT=587
# SMTP_USER=your-email@example.com
# SMTP_PASSWORD=your-password
# SMTP_USE_TLS=true
```

### En Docker Compose

Las variables se pasan automáticamente desde `.env`:

```yaml
environment:
  RESEND_API_KEY: ${RESEND_API_KEY:-}
  RESEND_FROM_EMAIL: ${RESEND_FROM_EMAIL:-onboarding@resend.dev}
```

## 📝 Uso del Servicio

El servicio funciona igual que antes:

```python
from services.notifications.services.email_service import EmailService

service = EmailService()

# Enviar email simple
success = await service.send_email(
    to_email="usuario@example.com",
    subject="Asunto",
    html_content="<h1>Contenido</h1>"
)

# Enviar email con ticket
success = await service.send_ticket_email(
    to_email="usuario@example.com",
    attendee_name="Juan Pérez",
    event_name="Concierto",
    event_date="26 de Diciembre, 2025",
    event_location="Estadio Nacional",
    ticket_id="TKT-123"
)
```

## 🐛 Troubleshooting

### Error: "RESEND_API_KEY no configurado"

**Solución:**
1. Verifica que `RESEND_API_KEY` esté en tu `.env`
2. Reinicia el backend después de agregar la variable
3. Verifica que el `.env` esté en el directorio correcto

### Error: "Invalid API key"

**Solución:**
1. Verifica que la API key sea correcta (debe empezar con `re_`)
2. Asegúrate de que no tenga espacios extra
3. Genera una nueva API key si es necesario

### Emails no se envían

**Solución:**
1. Revisa los logs del backend para ver errores
2. Verifica en [resend.com/emails](https://resend.com/emails) si aparecen
3. En desarrollo, Resend captura emails automáticamente
4. Verifica que `RESEND_FROM_EMAIL` sea válido

### Dominio no verificado en producción

**Solución:**
1. Ve a [resend.com/domains](https://resend.com/domains)
2. Verifica que los registros DNS estén correctos
3. Usa `onboarding@resend.dev` temporalmente para pruebas

## 📚 Recursos

- [Documentación de Resend](https://resend.com/docs)
- [Python SDK](https://github.com/resendlabs/resend-python)
- [API Reference](https://resend.com/docs/api-reference)
- [Dashboard](https://resend.com/emails)

## 🔄 Migración desde MailHog

Si tenías MailHog configurado:

1. ✅ **Código actualizado**: Ya no usa MailHog
2. ✅ **Docker Compose**: MailHog está comentado
3. ✅ **Variables**: Ahora usa `RESEND_API_KEY`
4. ✅ **Sin cambios en la lógica**: El servicio funciona igual

**No necesitas hacer nada más** - solo agregar `RESEND_API_KEY` a tu `.env`.

