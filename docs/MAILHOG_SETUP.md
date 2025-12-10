# 📧 Configuración de MailHog para Envío de Emails

## ¿Qué es MailHog?

MailHog es un servidor SMTP de prueba que captura todos los correos electrónicos enviados durante el desarrollo, permitiéndote verlos en una interfaz web sin necesidad de enviarlos realmente.

## 🚀 Configuración

### 1. MailHog ya está configurado en Docker Compose

El servicio de MailHog ya está incluido en `docker-compose.yml`:

```yaml
mailhog:
  image: mailhog/mailhog
  ports:
    - "1025:1025"  # SMTP port
    - "8025:8025"  # Web UI port
```

### 2. Variables de Entorno

Asegúrate de tener estas variables en tu archivo `.env`:

```env
# SMTP Configuration para MailHog
SMTP_HOST=mailhog
SMTP_PORT=1025
SMTP_FROM=tickets@example.local
SMTP_USER=
SMTP_PASSWORD=
SMTP_USE_TLS=false
```

**Nota:** Si estás corriendo el backend fuera de Docker, usa `localhost` en lugar de `mailhog`:

```env
SMTP_HOST=localhost
SMTP_PORT=1025
```

### 3. Iniciar MailHog

Si usas Docker Compose:

```bash
docker-compose up mailhog
```

O inicia todos los servicios:

```bash
docker-compose up
```

MailHog estará disponible en:
- **Interfaz Web:** http://localhost:8025
- **SMTP Server:** localhost:1025

## 📨 Uso del Servicio de Email

### Enviar un Email Simple

```python
from services.notifications.services.email_service import EmailService

service = EmailService()

success = await service.send_email(
    to_email="test@example.com",
    subject="Asunto del Email",
    html_content="<h1>Contenido HTML</h1><p>Este es un email de prueba.</p>",
    text_content="Contenido de texto plano"
)
```

### Enviar Email con Ticket

```python
success = await service.send_ticket_email(
    to_email="usuario@example.com",
    attendee_name="Juan Pérez",
    event_name="Concierto de Rock",
    event_date="26 de Diciembre, 2025",
    event_location="Estadio Nacional",
    ticket_id="TKT-123456",
    qr_code_url="https://example.com/qr.png",  # Opcional
    pdf_attachment=pdf_bytes  # Opcional
)
```

### Enviar Email de Confirmación de Orden

```python
success = await service.send_order_confirmation_email(
    to_email="comprador@example.com",
    buyer_name="María González",
    order_id="ORD-789",
    order_total=50000.0,
    currency="CLP",
    event_name="Festival de Música",
    tickets_count=2
)
```

## 🧪 Probar el Envío de Emails

### 1. Usando el Endpoint de Prueba

```bash
# Requiere autenticación de admin
curl -X POST "http://localhost:8000/api/v1/notifications/test-email?to_email=test@example.com" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 2. Ver Emails en MailHog

1. Abre tu navegador en http://localhost:8025
2. Envía un email desde tu aplicación
3. Verás el email aparecer en la interfaz de MailHog
4. Puedes hacer clic en el email para ver:
   - Remitente y destinatario
   - Asunto
   - Contenido HTML y texto
   - Adjuntos (si los hay)

## 🔧 Configuración para Producción

Para producción, cambia las variables de entorno a un servidor SMTP real:

```env
SMTP_HOST=smtp.gmail.com  # o tu servidor SMTP
SMTP_PORT=587
SMTP_USER=tu-email@gmail.com
SMTP_PASSWORD=tu-contraseña-o-app-password
SMTP_FROM=noreply@tudominio.com
SMTP_USE_TLS=true
```

### Ejemplo con Gmail

1. Genera una "Contraseña de aplicación" en tu cuenta de Google
2. Usa esa contraseña en `SMTP_PASSWORD`
3. Configura:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tu-email@gmail.com
SMTP_PASSWORD=tu-app-password
SMTP_FROM=tu-email@gmail.com
SMTP_USE_TLS=true
```

## 📝 Notas Importantes

- **MailHog solo captura emails, NO los envía realmente**
- En desarrollo, todos los emails se capturan en MailHog
- En producción, asegúrate de configurar un servidor SMTP real
- El servicio de email es asíncrono y no bloquea la aplicación
- Los errores se registran en los logs del backend

## 🐛 Troubleshooting

### MailHog no recibe emails

1. Verifica que MailHog esté corriendo:
   ```bash
   docker-compose ps mailhog
   ```

2. Verifica que el puerto 1025 esté disponible:
   ```bash
   netstat -an | grep 1025
   ```

3. Verifica las variables de entorno:
   ```bash
   docker-compose exec backend env | grep SMTP
   ```

### Error de conexión SMTP

- Si estás fuera de Docker, usa `localhost` en lugar de `mailhog`
- Verifica que el puerto SMTP (1025) esté expuesto
- En producción, verifica credenciales y configuración TLS

## 🔗 Referencias

- [MailHog GitHub](https://github.com/mailhog/MailHog)
- [aiosmtplib Documentation](https://aiosmtplib.readthedocs.io/)

