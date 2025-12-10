"""Script para probar el envío de emails con Resend"""
import asyncio
import sys
import os

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.notifications.services.email_service import EmailService


async def test_resend():
    """Probar envío de email con Resend"""
    service = EmailService()
    
    print("📧 Probando envío de email con Resend...")
    print(f"   From Email: {service.from_email}")
    print()
    
    if not service.resend_configured:
        print("❌ RESEND_API_KEY no configurado!")
        print("   Agrega RESEND_API_KEY a tu archivo .env")
        print("   Obtén tu API key en: https://resend.com/api-keys")
        return False
    
    # Email de prueba simple
    print("1. Enviando email simple...")
    success = await service.send_email(
        to_email="test@example.com",
        subject="Test Email from Crodify (Resend)",
        html_content="""
        <h1>Email de Prueba</h1>
        <p>Este es un email de prueba enviado desde el backend de Crodify usando <strong>Resend</strong>.</p>
        <p>Si ves este email en el dashboard de Resend, la configuración está funcionando correctamente.</p>
        <p>Visita <a href="https://resend.com/emails">resend.com/emails</a> para ver todos los emails enviados.</p>
        """,
        text_content="Este es un email de prueba enviado desde el backend de Crodify usando Resend."
    )
    
    if success:
        print("   ✅ Email enviado exitosamente!")
        print("   📬 Revisa Resend Dashboard: https://resend.com/emails")
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
    print("📬 Revisa los emails en Resend Dashboard: https://resend.com/emails")
    return True


if __name__ == "__main__":
    try:
        result = asyncio.run(test_resend())
        sys.exit(0 if result else 1)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

