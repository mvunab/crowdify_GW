# Configuración de Mercado Pago - Ambiente de Desarrollo

Esta guía te ayudará a configurar Mercado Pago en tu ambiente de desarrollo paso a paso.

## 📋 Requisitos Previos

1. Cuenta de Mercado Pago (o Mercado Libre)
2. Acceso a [Mercado Pago Developers](https://www.mercadopago.com/developers)

## 🚀 Paso 1: Crear una Aplicación en Mercado Pago

1. Ingresa a [Mercado Pago Developers](https://www.mercadopago.com/developers)
2. Haz clic en **Ingresar** (esquina superior derecha)
3. Si no tienes cuenta, créala primero
4. Una vez dentro, haz clic en **Tus integraciones** > **Crear aplicación**

### Configuración de la Aplicación

- **Nombre**: `Crodify - Desarrollo` (o el nombre que prefieras)
- **Tipo de pago**: Selecciona **Pagos online**
- **Plataforma**: Selecciona **Otra plataforma** o **Plataforma propia**
- **URL de la tienda**: `http://localhost:5173` (para desarrollo)

## 🔑 Paso 2: Obtener Credenciales de Prueba

Para desarrollo, necesitas usar **credenciales de prueba (sandbox)**. Esto te permite probar sin realizar pagos reales.

### 2.1 Crear Cuenta de Prueba de Vendedor

1. En **Tus integraciones**, selecciona tu aplicación
2. Ve a **Cuentas de prueba** en el menú lateral
3. Haz clic en **+ Crear cuenta de prueba**
4. Configura:
   - **País**: Selecciona el país donde operarás (ej: Argentina, Chile, etc.)
   - **Descripción**: `Vendedor de prueba - Crodify`
   - **Tipo de cuenta**: **Vendedor**
5. Haz clic en **Crear cuenta de prueba**

### 2.2 Obtener Credenciales de Prueba

1. **Importante**: Abre una ventana de incógnito
2. Ve a [Mercado Pago Developers](https://www.mercadopago.com/developers)
3. Inicia sesión con el usuario de prueba vendedor creado
4. En **Tus integraciones**, crea una nueva aplicación (o selecciona una existente)
5. Ve a **Detalles de la aplicación** > **Credenciales de producción**
6. Aquí encontrarás:
   - **Public Key**: Clave pública (para frontend)
   - **Access Token**: Clave privada (para backend) ⚠️ **MANTÉN ESTA SECRETA**

> **Nota**: Aunque dice "Credenciales de producción", estas son las credenciales de tu usuario de prueba. En producción usarás credenciales diferentes.

## ⚙️ Paso 3: Configurar Variables de Entorno

### 3.1 Opción Automática (Recomendada)

Ejecuta el script de configuración automática:

```bash
cd C:\Users\Andres\Documents\MARINS DEV\crowdify_GW
python scripts/setup_mercadopago_env.py
```

Este script configurará automáticamente todas las variables necesarias en tu archivo `.env`.

### 3.2 Opción Manual: Crear archivo `.env` en el backend

En la raíz del proyecto backend (`crowdify_GW`), crea o edita el archivo `.env`:

```env
# Mercado Pago - Credenciales
MERCADOPAGO_ACCESS_TOKEN=APP_USR-8730015517513045-111209-d3077ef6a256cb4c7599e03efb12bd44-2984124186
MERCADOPAGO_PUBLIC_KEY=APP_USR-5548d6e2-1b1c-445f-a4f1-d6e551426a24
MERCADOPAGO_WEBHOOK_SECRET=
MERCADOPAGO_ENVIRONMENT=sandbox

# URL base de la aplicación (para redirects)
APP_BASE_URL=http://localhost:5173

# Información adicional (para referencia)
# Application ID: 3707112352713547
# User ID: 2972046318
```

### 3.3 Verificar valores

- **MERCADOPAGO_ACCESS_TOKEN**: Access Token de tu aplicación
- **MERCADOPAGO_PUBLIC_KEY**: Public Key de tu aplicación  
- **MERCADOPAGO_WEBHOOK_SECRET**: (Opcional para desarrollo) Puedes dejarlo vacío
- **MERCADOPAGO_ENVIRONMENT**: 
  - `sandbox` para desarrollo/pruebas
  - `production` para producción (solo cuando estés listo)

> **Nota**: Las credenciales proporcionadas empiezan con `APP_USR-`. Si son credenciales de producción, asegúrate de cambiar `MERCADOPAGO_ENVIRONMENT` a `production` cuando estés listo para recibir pagos reales.

## 🔗 Paso 4: Configurar Webhooks (Opcional para Desarrollo)

Los webhooks permiten que Mercado Pago notifique a tu backend cuando hay cambios en los pagos.

### 4.1 Para Desarrollo Local

Para desarrollo local, necesitas exponer tu servidor local. Puedes usar:

- **ngrok**: `ngrok http 8000`
- **localtunnel**: `npx localtunnel --port 8000`

Una vez que tengas la URL pública (ej: `https://abc123.ngrok.io`):

1. Ve a **Tus integraciones** > Tu aplicación > **Webhooks**
2. Configura la URL: `https://abc123.ngrok.io/api/v1/purchases/webhook`
3. Selecciona los eventos: `payment`

### 4.2 Para Desarrollo con Docker

Si usas Docker, asegúrate de que el puerto 8000 esté expuesto y usa ngrok o similar.

## ✅ Paso 5: Verificar la Configuración

### 5.1 Verificar que el SDK esté instalado

```bash
cd C:\Users\Andres\Documents\MARINS DEV\crowdify_GW
pip install -r requirements.txt
```

### 5.2 Probar la conexión

Puedes crear un script de prueba simple:

```python
# test_mercadopago.py
import os
from dotenv import load_dotenv
import mercadopago

load_dotenv()

access_token = os.getenv("MERCADOPAGO_ACCESS_TOKEN")
if not access_token:
    print("❌ MERCADOPAGO_ACCESS_TOKEN no configurado")
    exit(1)

sdk = mercadopago.SDK(access_token)
print("✅ SDK de Mercado Pago inicializado correctamente")

# Probar obtener información de la cuenta
try:
    result = sdk.user().get()
    if result["status"] == 200:
        print(f"✅ Conexión exitosa. Usuario: {result['response'].get('nickname', 'N/A')}")
    else:
        print(f"⚠️ Error: {result.get('message', 'Desconocido')}")
except Exception as e:
    print(f"❌ Error: {e}")
```

Ejecuta:
```bash
python test_mercadopago.py
```

## 🧪 Paso 6: Probar con Tarjetas de Prueba

Mercado Pago proporciona tarjetas de prueba para simular pagos:

### Tarjetas de Prueba (Argentina - MLA)

- **Aprobada**: 
  - Número: `5031 7557 3453 0604`
  - CVV: `123`
  - Fecha: Cualquier fecha futura
  - Nombre: `APRO`

- **Rechazada**: 
  - Número: `5031 4332 1540 6351`
  - CVV: `123`
  - Fecha: Cualquier fecha futura
  - Nombre: `OTHE`

### Tarjetas de Prueba (Chile - MLC)

- **Aprobada**: 
  - Número: `5031 7557 3453 0604`
  - CVV: `123`
  - Fecha: Cualquier fecha futura
  - Nombre: `APRO`

> **Nota**: Las tarjetas de prueba varían según el país. Consulta la [documentación oficial](https://www.mercadopago.com/developers/es/docs/checkout-api/testing) para tu país.

## 📝 Checklist de Configuración

- [ ] Aplicación creada en Mercado Pago Developers
- [ ] Cuenta de prueba de vendedor creada
- [ ] Credenciales de prueba obtenidas (Access Token y Public Key)
- [ ] Archivo `.env` configurado con las credenciales
- [ ] Variables de entorno cargadas correctamente
- [ ] SDK de Mercado Pago instalado
- [ ] Conexión probada exitosamente
- [ ] Webhook configurado (opcional para desarrollo)

## 🔒 Seguridad

⚠️ **IMPORTANTE**:

1. **NUNCA** subas el archivo `.env` a Git
2. **NUNCA** compartas tus credenciales de producción
3. Usa credenciales de prueba (`TEST-`) para desarrollo
4. Las credenciales de producción empiezan diferente (sin `TEST-`)

## 🚀 Siguiente Paso

Una vez configurado el ambiente de desarrollo, puedes:

1. Probar la creación de preferencias de pago
2. Probar el flujo completo de compra
3. Configurar webhooks para recibir notificaciones
4. Integrar con el frontend

## 📚 Recursos Adicionales

- [Documentación Oficial de Mercado Pago](https://www.mercadopago.com/developers/es/docs)
- [SDK de Python](https://github.com/mercadopago/sdk-python)
- [Tarjetas de Prueba por País](https://www.mercadopago.com/developers/es/docs/checkout-api/testing)

## 🆘 Solución de Problemas

### Error: "MERCADOPAGO_ACCESS_TOKEN no configurado"
- Verifica que el archivo `.env` existe en la raíz del proyecto
- Verifica que la variable esté escrita correctamente
- Reinicia el servidor después de cambiar `.env`

### Error: "Invalid access token"
- Verifica que estés usando credenciales de prueba (empiezan con `TEST-`)
- Asegúrate de haber copiado el token completo sin espacios
- Verifica que estés usando el token del usuario de prueba correcto

### Error: "Webhook not received"
- Verifica que la URL del webhook sea accesible públicamente
- Usa ngrok o similar para desarrollo local
- Verifica que el endpoint `/api/v1/purchases/webhook` esté configurado

