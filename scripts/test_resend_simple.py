"""Script simple para probar Resend con tu API key"""
import os
import sys

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Tu API key de Resend
RESEND_API_KEY = "re_PF5tV5xd_PVRsETbW1NgBLTFNxnXVnu9y"

def test_resend_simple():
    """Prueba simple de Resend usando el ejemplo oficial"""
    try:
        import resend
        
        # Configurar API key
        resend.api_key = RESEND_API_KEY
        
        print("📧 Enviando email de prueba con Resend...")
        print(f"   From: onboarding@resend.dev")
        print(f"   To: dctalk12345@gmail.com")
        print()
        
        # Enviar email usando el ejemplo oficial
        result = resend.Emails.send({
            "from": "onboarding@resend.dev",
            "to": "dctalk12345@gmail.com",
            "subject": "Hello World from Crodify",
            "html": "<p>Congrats on sending your <strong>first email</strong> from Crodify!</p><p>Este es un email de prueba desde el backend.</p>"
        })
        
        if result.get("error"):
            print(f"❌ Error: {result['error']}")
            return False
        
        print(f"✅ Email enviado exitosamente!")
        print(f"   Email ID: {result.get('id', 'N/A')}")
        print(f"   📬 Revisa tu correo: dctalk12345@gmail.com")
        print(f"   📊 Dashboard: https://resend.com/emails")
        return True
        
    except ImportError:
        print("❌ Error: resend no está instalado")
        print("   Instala con: pip install resend")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_resend_simple()
    sys.exit(0 if success else 1)

