"""
Script para corregir la configuración del ambiente de Mercado Pago
Ejecuta: python scripts/fix_mercadopago_environment.py
"""
import os
import sys
from pathlib import Path

# Agregar el directorio raíz al path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from dotenv import load_dotenv, set_key, find_dotenv

def fix_environment():
    """Corrige la configuración del ambiente de Mercado Pago"""
    print("=" * 70)
    print("  CORRECCIÓN DE CONFIGURACIÓN DE MERCADO PAGO")
    print("=" * 70)
    print()
    
    # Cargar variables de entorno
    env_file = find_dotenv()
    if not env_file:
        print("❌ No se encontró archivo .env")
        print("   Crea un archivo .env en la raíz del proyecto")
        return False
    
    load_dotenv(env_file)
    
    access_token = os.getenv("MERCADOPAGO_ACCESS_TOKEN")
    current_env = os.getenv("MERCADOPAGO_ENVIRONMENT", "sandbox")
    
    if not access_token:
        print("❌ MERCADOPAGO_ACCESS_TOKEN no está configurado")
        return False
    
    print(f"📋 Token encontrado: {access_token[:30]}...{access_token[-20:]}")
    print(f"📋 Ambiente actual: {current_env}")
    print()
    
    # Determinar el ambiente correcto basándose en la conexión real
    # Los tokens APP_USR- pueden ser de prueba o producción
    try:
        import mercadopago
        sdk = mercadopago.SDK(access_token)
        user_result = sdk.user().get()
        
        if user_result["status"] == 200:
            user_data = user_result["response"]
            email = user_data.get('email', '')
            nickname = user_data.get('nickname', '')
            is_test_account = 'test' in email.lower() or 'test' in nickname.lower() or 'TESTUSER' in nickname
            
            if is_test_account:
                correct_env = "sandbox"
                token_type = "prueba (sandbox)"
            else:
                correct_env = "production"
                token_type = "producción"
        else:
            # Si no podemos verificar, usar heurística basada en el prefijo
            if access_token.startswith("TEST-"):
                correct_env = "sandbox"
                token_type = "prueba (sandbox)"
            elif access_token.startswith("APP_USR-"):
                # Por defecto, asumir producción si no podemos verificar
                correct_env = "production"
                token_type = "producción (no verificado)"
            else:
                print("⚠️  Formato de token desconocido")
                return False
    except Exception as e:
        print(f"⚠️  No se pudo verificar el tipo de cuenta: {e}")
        # Usar heurística basada en el prefijo
        if access_token.startswith("TEST-"):
            correct_env = "sandbox"
            token_type = "prueba (sandbox)"
        elif access_token.startswith("APP_USR-"):
            correct_env = "production"
            token_type = "producción (no verificado)"
        else:
            print("⚠️  Formato de token desconocido")
            return False
    
    print(f"🔍 Tipo de token detectado: {token_type}")
    print(f"🔍 Ambiente recomendado: {correct_env}")
    print()
    
    if current_env == correct_env:
        print("✅ La configuración ya es correcta!")
        print(f"   MERCADOPAGO_ENVIRONMENT={current_env}")
        return True
    
    print(f"⚠️  Inconsistencia detectada:")
    print(f"   - Token es de {token_type}")
    print(f"   - Ambiente configurado: {current_env}")
    print()
    
    # Preguntar si quiere corregir
    print(f"¿Deseas cambiar MERCADOPAGO_ENVIRONMENT a '{correct_env}'? (s/n): ", end="")
    response = input().strip().lower()
    
    if response in ['s', 'si', 'sí', 'y', 'yes']:
        set_key(env_file, "MERCADOPAGO_ENVIRONMENT", correct_env)
        print()
        print(f"✅ Configuración actualizada!")
        print(f"   MERCADOPAGO_ENVIRONMENT={correct_env}")
        print()
        print("⚠️  IMPORTANTE: Reinicia tu aplicación backend para que los cambios surtan efecto")
        return True
    else:
        print()
        print("ℹ️  No se realizaron cambios")
        print(f"   Para corregir manualmente, edita tu archivo .env y cambia:")
        print(f"   MERCADOPAGO_ENVIRONMENT={correct_env}")
        return False

if __name__ == "__main__":
    success = fix_environment()
    sys.exit(0 if success else 1)

