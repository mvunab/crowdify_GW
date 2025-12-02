"""
Script para configurar las variables de Mercado Pago en el archivo .env
Ejecuta: python scripts/setup_mercadopago_env.py
"""
import os
from pathlib import Path

def setup_mercadopago_env():
    """Configura las variables de Mercado Pago en el archivo .env"""
    
    root_dir = Path(__file__).parent.parent
    env_file = root_dir / ".env"
    
    # Credenciales proporcionadas
    MERCADOPAGO_ACCESS_TOKEN = "APP_USR-8730015517513045-111209-d3077ef6a256cb4c7599e03efb12bd44-2984124186"
    MERCADOPAGO_PUBLIC_KEY = "APP_USR-5548d6e2-1b1c-445f-a4f1-d6e551426a24"
    MERCADOPAGO_USER_ID = "2972046318"
    MERCADOPAGO_APP_ID = "3707112352713547"
    
    print("🔧 Configurando variables de Mercado Pago en .env...\n")
    
    # Leer archivo .env existente o crear uno nuevo
    env_content = ""
    if env_file.exists():
        env_content = env_file.read_text(encoding='utf-8')
        print("✅ Archivo .env encontrado, actualizando...\n")
    else:
        print("📝 Creando nuevo archivo .env...\n")
    
    # Variables a configurar/actualizar
    variables = {
        "MERCADOPAGO_ACCESS_TOKEN": MERCADOPAGO_ACCESS_TOKEN,
        "MERCADOPAGO_PUBLIC_KEY": MERCADOPAGO_PUBLIC_KEY,
        "MERCADOPAGO_ENVIRONMENT": "sandbox",  # Cambiar a "production" cuando esté listo
        "APP_BASE_URL": "http://localhost:5173",
    }
    
    # Actualizar o agregar variables
    lines = env_content.split('\n')
    updated_lines = []
    variables_found = set()
    
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped or line_stripped.startswith('#'):
            updated_lines.append(line)
            continue
        
        # Verificar si la línea contiene alguna de nuestras variables
        updated = False
        for var_name, var_value in variables.items():
            if line_stripped.startswith(f"{var_name}="):
                updated_lines.append(f"{var_name}={var_value}")
                variables_found.add(var_name)
                updated = True
                print(f"  ✅ Actualizado: {var_name}")
                break
        
        if not updated:
            updated_lines.append(line)
    
    # Agregar variables que no se encontraron
    for var_name, var_value in variables.items():
        if var_name not in variables_found:
            updated_lines.append(f"{var_name}={var_value}")
            print(f"  ➕ Agregado: {var_name}")
    
    # Agregar comentarios informativos si no existen
    if "MERCADOPAGO" not in env_content:
        updated_lines.insert(0, "\n# Mercado Pago Configuration")
        updated_lines.insert(1, "# Application ID: 3707112352713547")
        updated_lines.insert(2, "# User ID: 2972046318")
        updated_lines.insert(3, "# Environment: sandbox (cambiar a 'production' para producción)")
    
    # Escribir archivo actualizado
    env_file.write_text('\n'.join(updated_lines), encoding='utf-8')
    
    print("\n✅ Configuración completada!")
    print(f"   Archivo: {env_file}")
    print("\n📋 Variables configuradas:")
    print(f"   - MERCADOPAGO_ACCESS_TOKEN: {MERCADOPAGO_ACCESS_TOKEN[:30]}...")
    print(f"   - MERCADOPAGO_PUBLIC_KEY: {MERCADOPAGO_PUBLIC_KEY[:30]}...")
    print(f"   - MERCADOPAGO_ENVIRONMENT: sandbox")
    print(f"   - APP_BASE_URL: http://localhost:5173")
    print("\n⚠️  IMPORTANTE:")
    print("   - Estas credenciales empiezan con 'APP_USR-' (no 'TEST-')")
    print("   - Verifica si son credenciales de prueba o producción")
    print("   - Para desarrollo, normalmente se usan credenciales que empiezan con 'TEST-'")
    print("\n🧪 Próximo paso: Ejecuta 'python test_mercadopago.py' para verificar la conexión")

if __name__ == "__main__":
    setup_mercadopago_env()


