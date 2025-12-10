"""Script para probar la generación de QR code"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.notifications.services.email_service import EmailService

def test_qr_generation():
    """Probar generación de QR"""
    service = EmailService()
    
    # QR signature de prueba
    test_qr_signature = "test1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
    
    print("🧪 Probando generación de QR code...")
    print(f"   QR Signature: {test_qr_signature[:30]}...")
    print()
    
    # Generar QR
    qr_base64 = service._generate_qr_image_base64(test_qr_signature)
    
    if qr_base64:
        print(f"✅ QR generado exitosamente!")
        print(f"   Tamaño base64: {len(qr_base64)} caracteres")
        print(f"   Primeros 50 caracteres: {qr_base64[:50]}...")
        print()
        print("📝 Para verificar, puedes:")
        print("   1. Copiar el base64 completo")
        print("   2. Pegarlo en: https://base64.guru/converter/decode/image")
        print("   3. O usar: data:image/png;base64,{qr_base64} en un HTML")
        return True
    else:
        print("❌ Error generando QR code")
        return False

if __name__ == "__main__":
    success = test_qr_generation()
    sys.exit(0 if success else 1)

