"""Script para probar Resend desde dentro de Docker"""
import os
import sys
import asyncio

# Agregar el directorio raíz al path
sys.path.insert(0, '/app')

async def test_resend():
    """Probar Resend desde Docker"""
    try:
        from services.notifications.services.email_service import EmailService
        
        service = EmailService()
        
        print("📧 Probando Resend desde Docker...")
        print(f"   API Key configurada: {'Sí' if service.resend_configured else 'No'}")
        print(f"   From Email: {service.from_email}")
        print()
        
        if not service.resend_configured:
            print("❌ RESEND_API_KEY no configurado en el contenedor!")
            print("   Verifica que esté en el .env y que Docker lo haya cargado")
            return False
        
        # Email de prueba
        print("Enviando email de prueba...")
        success = await service.send_email(
            to_email="dctalk12345@gmail.com",
            subject="Test desde Crodify Docker",
            html_content="""
            <h1>✅ Resend funcionando!</h1>
            <p>Este email fue enviado desde el backend de Crodify usando <strong>Resend</strong>.</p>
            <p>Si recibes este email, la configuración está correcta.</p>
            """,
            text_content="Este email fue enviado desde el backend de Crodify usando Resend."
        )
        
        if success:
            print("✅ Email enviado exitosamente!")
            print("📬 Revisa tu correo: dctalk12345@gmail.com")
            print("📊 Dashboard: https://resend.com/emails")
            return True
        else:
            print("❌ Error al enviar email")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_resend())
    sys.exit(0 if result else 1)

