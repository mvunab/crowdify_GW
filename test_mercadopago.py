"""
Script de prueba para verificar la configuración de Mercado Pago
Ejecuta: python test_mercadopago.py
"""
import os
import sys
from pathlib import Path

# Agregar el directorio raíz al path
root_dir = Path(__file__).parent
sys.path.insert(0, str(root_dir))

from dotenv import load_dotenv
import mercadopago

# Cargar variables de entorno
load_dotenv()

def test_mercadopago_config():
    """Prueba la configuración de Mercado Pago"""
    print("🔍 Verificando configuración de Mercado Pago...\n")
    
    # Verificar que existe el archivo .env
    env_file = root_dir / ".env"
    if not env_file.exists():
        print("⚠️  No se encontró el archivo .env")
        print("   Crea un archivo .env en la raíz del proyecto con las variables de Mercado Pago")
        print("   Consulta docs/MERCADOPAGO_SETUP.md para más información\n")
        return False
    
    print("✅ Archivo .env encontrado\n")
    
    # Verificar variables de entorno
    access_token = os.getenv("MERCADOPAGO_ACCESS_TOKEN")
    public_key = os.getenv("MERCADOPAGO_PUBLIC_KEY")
    environment = os.getenv("MERCADOPAGO_ENVIRONMENT", "sandbox")
    
    if not access_token:
        print("❌ MERCADOPAGO_ACCESS_TOKEN no configurado")
        print("   Agrega esta variable a tu archivo .env\n")
        return False
    
    if not access_token.startswith("TEST-") and environment == "sandbox":
        print("⚠️  ADVERTENCIA: El Access Token no parece ser de prueba (no empieza con TEST-)")
        print("   Para desarrollo, usa credenciales de prueba que empiecen con TEST-\n")
    
    print(f"✅ MERCADOPAGO_ACCESS_TOKEN configurado")
    print(f"   Token: {access_token[:20]}...{access_token[-10:]}\n")
    
    if public_key:
        print(f"✅ MERCADOPAGO_PUBLIC_KEY configurado")
        print(f"   Key: {public_key[:20]}...{public_key[-10:]}\n")
    else:
        print("⚠️  MERCADOPAGO_PUBLIC_KEY no configurado (opcional para backend)\n")
    
    print(f"✅ MERCADOPAGO_ENVIRONMENT: {environment}\n")
    
    # Probar conexión con SDK
    print("🔌 Probando conexión con Mercado Pago...\n")
    
    try:
        sdk = mercadopago.SDK(access_token)
        
        # Intentar obtener información del usuario
        result = sdk.user().get()
        
        if result["status"] == 200:
            user_data = result["response"]
            print("✅ Conexión exitosa con Mercado Pago!")
            print(f"   Usuario: {user_data.get('nickname', 'N/A')}")
            print(f"   Email: {user_data.get('email', 'N/A')}")
            print(f"   País: {user_data.get('country_id', 'N/A')}")
            print(f"   Ambiente: {'Sandbox' if access_token.startswith('TEST-') else 'Producción'}\n")
            return True
        else:
            print(f"❌ Error en la conexión: {result.get('message', 'Desconocido')}")
            print(f"   Status: {result.get('status')}\n")
            return False
            
    except Exception as e:
        print(f"❌ Error al conectar con Mercado Pago: {str(e)}\n")
        print("   Posibles causas:")
        print("   - Access Token inválido o expirado")
        print("   - Problemas de conexión a internet")
        print("   - SDK de Mercado Pago no instalado (pip install mercadopago)\n")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("  TEST DE CONFIGURACIÓN DE MERCADO PAGO")
    print("=" * 60)
    print()
    
    success = test_mercadopago_config()
    
    print("=" * 60)
    if success:
        print("✅ Configuración correcta. Puedes continuar con la integración.")
    else:
        print("❌ Hay problemas con la configuración. Revisa los errores arriba.")
        print("   Consulta docs/MERCADOPAGO_SETUP.md para ayuda detallada.")
    print("=" * 60)


