"""
Script de diagnóstico para verificar el token de Mercado Pago
Ejecuta: python scripts/diagnose_mercadopago_token.py
"""
import os
import sys
from pathlib import Path

# Agregar el directorio raíz al path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from dotenv import load_dotenv
import mercadopago

# Cargar variables de entorno
load_dotenv()

def diagnose_token():
    """Diagnostica problemas con el token de Mercado Pago"""
    print("=" * 70)
    print("  DIAGNÓSTICO DE TOKEN DE MERCADO PAGO")
    print("=" * 70)
    print()
    
    # Obtener token
    access_token = os.getenv("MERCADOPAGO_ACCESS_TOKEN")
    environment = os.getenv("MERCADOPAGO_ENVIRONMENT", "sandbox")
    
    if not access_token:
        print("❌ ERROR: MERCADOPAGO_ACCESS_TOKEN no está configurado")
        print("   Agrega esta variable a tu archivo .env")
        return False
    
    print(f"📋 Token encontrado: {access_token[:30]}...{access_token[-20:]}")
    print(f"📋 Ambiente configurado: {environment}")
    print()
    
    # Verificar formato del token
    print("🔍 Verificando formato del token...")
    if access_token.startswith("TEST-"):
        print("✅ Token de prueba (TEST-) detectado")
        token_type = "sandbox"
    elif access_token.startswith("APP_USR-"):
        print("✅ Token de aplicación (APP_USR-) detectado")
        print("   Nota: Los tokens APP_USR- pueden ser de prueba o producción")
        print("   Se determinará el tipo real al verificar la conexión...")
        token_type = "unknown"  # Se determinará después
    else:
        print("⚠️  ADVERTENCIA: Formato de token desconocido")
        print("   Los tokens válidos deben empezar con 'TEST-' (sandbox) o 'APP_USR-' (producción/prueba)")
        token_type = "unknown"
    print()
    
    # Probar conexión con SDK
    print("🔌 Probando conexión con Mercado Pago...")
    try:
        sdk = mercadopago.SDK(access_token)
        
        # Test 1: Obtener información del usuario
        print("   Test 1: Obteniendo información del usuario...")
        user_result = sdk.user().get()
        
        if user_result["status"] == 200:
            user_data = user_result["response"]
            print("   ✅ Conexión exitosa!")
            print(f"      Usuario: {user_data.get('nickname', 'N/A')}")
            print(f"      Email: {user_data.get('email', 'N/A')}")
            print(f"      País: {user_data.get('country_id', 'N/A')}")
            print(f"      ID: {user_data.get('id', 'N/A')}")
            
            # Determinar si es cuenta de prueba basándose en el email o nickname
            email = user_data.get('email', '')
            nickname = user_data.get('nickname', '')
            is_test_account = 'test' in email.lower() or 'test' in nickname.lower() or 'TESTUSER' in nickname
            
            if is_test_account:
                print(f"      ✅ Tipo: Cuenta de PRUEBA (sandbox)")
                if environment != "sandbox":
                    print(f"      ⚠️  ADVERTENCIA: Es una cuenta de prueba pero MERCADOPAGO_ENVIRONMENT={environment}")
                    print(f"         Considera cambiar a MERCADOPAGO_ENVIRONMENT=sandbox")
            else:
                print(f"      ✅ Tipo: Cuenta de PRODUCCIÓN")
                if environment != "production":
                    print(f"      ⚠️  ADVERTENCIA: Es una cuenta de producción pero MERCADOPAGO_ENVIRONMENT={environment}")
                    print(f"         Considera cambiar a MERCADOPAGO_ENVIRONMENT=production")
        else:
            error_msg = user_result.get('message', 'Error desconocido')
            error_status = user_result.get('status', 'N/A')
            print(f"   ❌ Error en la conexión: {error_msg}")
            print(f"      Status HTTP: {error_status}")
            
            # Analizar el error
            if error_status == 401:
                print()
                print("   🔴 PROBLEMA DETECTADO: Token inválido o expirado (401 Unauthorized)")
                print("      Soluciones:")
                print("      1. Verifica que el token esté correcto en tu archivo .env")
                print("      2. Si el token expiró, obtén uno nuevo desde:")
                print("         https://www.mercadopago.com/developers/panel/app")
                print("      3. Para tokens de producción, verifica que no hayan sido revocados")
            elif error_status == 403:
                print()
                print("   🔴 PROBLEMA DETECTADO: Token sin permisos suficientes (403 Forbidden)")
                print("      Soluciones:")
                print("      1. Verifica los permisos de tu aplicación en Mercado Pago")
                print("      2. Asegúrate de que el token tenga acceso a las APIs necesarias")
            else:
                print()
                print(f"   ⚠️  Error HTTP {error_status}: {error_msg}")
            
            return False
        
        print()
        
        # Test 2: Crear una preferencia de prueba
        print("   Test 2: Creando preferencia de prueba...")
        try:
            test_preference_data = {
                "items": [
                    {
                        "title": "Test Item",
                        "quantity": 1,
                        "currency_id": "CLP",
                        "unit_price": 100.0
                    }
                ],
                "back_urls": {
                    "success": "https://www.mercadopago.com",
                    "failure": "https://www.mercadopago.com",
                    "pending": "https://www.mercadopago.com"
                },
                "auto_return": "approved"
            }
            
            preference_result = sdk.preference().create(test_preference_data)
            
            if preference_result["status"] == 201:
                preference_id = preference_result["response"].get("id")
                print(f"   ✅ Preferencia creada exitosamente: {preference_id}")
                print("   ✅ El token tiene permisos para crear preferencias")
            else:
                error_msg = preference_result.get('message', 'Error desconocido')
                error_response = preference_result.get('response', {})
                print(f"   ❌ Error creando preferencia: {error_msg}")
                
                # Analizar error de preferencia
                if isinstance(error_response, dict):
                    error_cause = error_response.get('cause', [])
                    if error_cause:
                        if isinstance(error_cause, list) and len(error_cause) > 0:
                            print(f"      Causa: {error_cause[0]}")
                        else:
                            print(f"      Causa: {error_cause}")
                
                return False
                
        except Exception as e:
            print(f"   ❌ Excepción al crear preferencia: {str(e)}")
            return False
        
        print()
        print("=" * 70)
        print("✅ DIAGNÓSTICO COMPLETO: El token está funcionando correctamente")
        print("=" * 70)
        return True
        
    except Exception as e:
        print(f"❌ Error crítico al conectar con Mercado Pago: {str(e)}")
        print()
        print("Posibles causas:")
        print("  1. Token inválido o expirado")
        print("  2. Problemas de conexión a internet")
        print("  3. SDK de Mercado Pago no instalado (pip install mercadopago)")
        print("  4. Token revocado o sin permisos")
        print()
        print("Soluciones:")
        print("  1. Verifica tu token en: https://www.mercadopago.com/developers/panel/app")
        print("  2. Obtén un nuevo token si el actual expiró")
        print("  3. Verifica que el SDK esté instalado: pip install mercadopago")
        return False

if __name__ == "__main__":
    success = diagnose_token()
    sys.exit(0 if success else 1)

