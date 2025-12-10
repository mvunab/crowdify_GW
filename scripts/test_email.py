"""Script para probar el envío de emails con MailHog"""
import asyncio
import sys
import os

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.notifications.services.email_service import EmailService


async def test_email():
    """Probar envío de email"""
    service = EmailService()
    
    print("📧 Probando envío de email con MailHog...")
    print(f"   SMTP Host: {service.smtp_host}")
    print(f"   SMTP Port: {service.smtp_port}")
    print(f"   From: {service.smtp_from}")
    print()
    
    # Email de prueba simple
    print("1. Enviando email simple...")
    success = await service.send_email(
        to_email="test@example.com",
        subject="Test Email from Crodify",
        html_content="""
        <h1>Email de Prueba</h1>
        <p>Este es un email de prueba enviado desde el backend de Crodify.</p>
        <p>Si ves este email en MailHog, la configuración está funcionando correctamente.</p>
        """,
        text_content="Este es un email de prueba enviado desde el backend de Crodify."
    )
    
    if success:
        print("   ✅ Email enviado exitosamente!")
        print("   📬 Revisa MailHog en http://localhost:8025")
    else:
        print("   ❌ Error al enviar email")
        return False
    
    print()
    
    # Email con ticket
    print("2. Enviando email con ticket...")
    success = await service.send_ticket_email(
        to_email="usuario@example.com",
        attendee_name="Juan Pérez",
        event_name="Concierto de Prueba",
        event_date="26 de Diciembre, 2025",
        event_location="Estadio Nacional",
        ticket_id="TKT-TEST-123"
    )
    
    if success:
        print("   ✅ Email con ticket enviado exitosamente!")
    else:
        print("   ❌ Error al enviar email con ticket")
        return False
    
    print()
    print("✅ Todas las pruebas completadas!")
    print("📬 Revisa los emails en MailHog: http://localhost:8025")
    return True


if __name__ == "__main__":
    try:
        result = asyncio.run(test_email())
        sys.exit(0 if result else 1)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

