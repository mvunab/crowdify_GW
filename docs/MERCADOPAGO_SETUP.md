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

Mercado Pago proporciona tarjetas de prueba para simular pagos **sin necesidad de que el usuario tenga cuenta de Mercado Pago**.

### ⚠️ Importante: Pagos sin Cuenta (Guest Checkout)

El sistema está configurado para permitir pagos sin cuenta de Mercado Pago. Esto significa que:

1. **No es necesario** que el usuario tenga cuenta de Mercado Pago
2. El usuario puede pagar como **invitado** ingresando solo los datos de su tarjeta
3. En el checkout, el usuario puede elegir "Pagar sin cuenta" o simplemente ingresar los datos de la tarjeta

### Tarjetas de Prueba (Chile - MLC) - Recomendadas para este proyecto

Como el sistema usa CLP (pesos chilenos), usa estas tarjetas:

#### ✅ Tarjeta Aprobada (Visa)
- **Número**: `4168 8188 4444 7115`
- **CVV**: `123`
- **Fecha de vencimiento**: Cualquier fecha futura (ej: 11/30)
- **Nombre del titular**: `APRO` (o cualquier nombre)
- **Email**: Cualquier email de prueba (ej: `test_user_123@testuser.com`)

#### ✅ Tarjeta Aprobada (Mastercard)
- **Número**: `5416 7526 0258 2580`
- **CVV**: `123`
- **Fecha de vencimiento**: Cualquier fecha futura (ej: 11/30)
- **Nombre del titular**: `APRO` (o cualquier nombre)
- **Email**: Cualquier email de prueba

#### ✅ Tarjeta Aprobada (Alternativa - Visa)
- **Número**: `5031 7557 3453 0604`
- **CVV**: `123`
- **Fecha de vencimiento**: Cualquier fecha futura (ej: 12/25)
- **Nombre del titular**: `APRO` (o cualquier nombre)
- **Email**: Cualquier email de prueba

#### ❌ Tarjeta Rechazada
- **Número**: `5031 4332 1540 6351`
- **CVV**: `123`
- **Fecha de vencimiento**: Cualquier fecha futura
- **Nombre del titular**: `OTHE` (o cualquier nombre)
- **Email**: Cualquier email de prueba

#### 🔄 Tarjeta Pendiente
- **Número**: `5031 7557 3453 0604`
- **CVV**: `123`
- **Fecha de vencimiento**: Cualquier fecha futura
- **Nombre del titular**: `CONT` (o cualquier nombre)
- **Email**: Cualquier email de prueba

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

### 📋 Flujo de Prueba sin Cuenta

1. **Crear preferencia** en tu backend (FastAPI) - ✅ Ya configurado
2. **Abrir el checkout** en el frontend usando el `payment_link` o `preference_id`
3. **⚠️ IMPORTANTE - Desactivar bloqueadores:**
   - **Antes de probar**, desactiva bloqueadores de anuncios (AdBlock, uBlock, etc.)
   - O usa modo incógnito (sin extensiones)
   - Los bloqueadores impiden la tokenización de la tarjeta
4. **En el formulario de pago**:
   - **NO** inicies sesión en Mercado Pago
   - Simplemente ingresa los datos de la tarjeta de prueba
   - Usa cualquier email de prueba (ej: `test_user_123@testuser.com`)
   - Usa cualquier nombre (ej: `APRO` o `Test User`)
5. **Completar el pago** - Mercado Pago procesará el pago sin requerir cuenta
6. **Redirección automática** - El usuario será redirigido a `back_urls.success` si el pago es aprobado

### 🔍 Verificar que Funciona

Si las tarjetas de prueba no funcionan, verifica:

1. ✅ Estás usando credenciales de **sandbox** (no producción)
2. ✅ El `MERCADOPAGO_ENVIRONMENT` está configurado como `sandbox`
3. ✅ La preferencia tiene `payment_methods` configurado correctamente (ya está en el código)
4. ✅ No estás excluyendo métodos de pago que permitan guest checkout
5. ✅ Estás usando las tarjetas de prueba correctas para tu país

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

### ⚠️ Error: "ERR_BLOCKED_BY_CLIENT" - Errores en Consola al Abrir Checkout

**Síntomas:**
Cuando abres el checkout de Mercado Pago, ves múltiples errores en la consola del navegador:
- `GET https://js-agent.newrelic.com/nr-rum-1.303.0.min.js net::ERR_BLOCKED_BY_CLIENT`
- `POST https://api.mercadolibre.com/tracks net::ERR_BLOCKED_BY_CLIENT`
- `Could not send event id ... Error: [object ProgressEvent]`
- El botón "Continuar" no funciona después de ingresar los datos de la tarjeta
- Error: `TypeError: Cannot read properties of null (reading 'id')`

**Causa:**
Un bloqueador de anuncios o extensión del navegador está bloqueando scripts de tracking/analytics de Mercado Pago. Aunque estos scripts son principalmente para analytics, algunos son necesarios para el funcionamiento del checkout (tokenización de tarjeta, validación, etc.).

**⚠️ IMPORTANTE: Diferenciar Errores Críticos vs. No Críticos**

**Errores NO Críticos (puedes ignorarlos):**
- `404 (Not Found)` en endpoints como `/jms/lgz/background/etid` - Son endpoints internos opcionales de Mercado Pago
- `Mixed Content` warnings - El navegador los maneja automáticamente
- `401 (Unauthorized)` en reCAPTCHA - No afecta el checkout si no usas reCAPTCHA

**Errores CRÍTICOS (debes solucionarlos):**
- `ERR_BLOCKED_BY_CLIENT` en scripts de Mercado Pago - **Estos SÍ pueden bloquear el checkout**
- `TypeError: Cannot read properties of null` - Indica que un script necesario fue bloqueado

**Soluciones Paso a Paso:**

#### 1. **Solución Rápida: Modo Incógnito (Recomendado para Pruebas)**
   - Abre una ventana de incógnito en tu navegador
   - Las extensiones suelen estar desactivadas en este modo
   - Prueba el flujo de pago completo ahí
   - ✅ **Esta es la solución más rápida para verificar que el problema es el bloqueador**

#### 2. **Desactivar Bloqueadores Temporalmente**
   - **Chrome/Edge**: 
     - Click en el icono de la extensión (AdBlock, uBlock, etc.)
     - Selecciona "Pausar en este sitio" o "Desactivar en este sitio"
   - **Firefox**:
     - Click en el icono de la extensión
     - Desactiva para `sandbox.mercadopago.cl`
   - **Safari**:
     - Preferencias → Extensiones → Desactiva bloqueadores temporalmente

#### 3. **Agregar a Lista Blanca (Solución Permanente)**
   Agrega estos dominios a la lista blanca de tu bloqueador:
   ```
   *.mercadopago.com
   *.mercadopago.cl
   *.mercadolibre.com
   *.mercadolibre.cl
   sandbox.mercadopago.cl
   api.mercadolibre.com
   js-agent.newrelic.com
   ```

   **Cómo hacerlo:**
   - **uBlock Origin**: Click en el icono → "Abrir panel" → "Lista blanca" → Agregar dominios
   - **AdBlock**: Click en el icono → "Configuración" → "Lista de sitios permitidos" → Agregar
   - **Privacy Badger**: Click en el icono → "Desactivar en este sitio"

#### 4. **Verificar Configuración del Navegador**
   - **Chrome**: 
     - `chrome://settings/content/ads` → Permitir anuncios en `sandbox.mercadopago.cl`
     - `chrome://settings/content/all` → Buscar `mercadopago` y permitir
   - **Firefox**: 
     - `about:preferences#privacy` → Desactivar bloqueo de contenido para Mercado Pago
   - **Safari**: 
     - Preferencias → Privacidad → Desactivar "Prevenir rastreo entre sitios web" temporalmente

#### 5. **Usar Otro Navegador**
   - Prueba con un navegador sin extensiones instaladas
   - O usa un navegador diferente (Chrome, Firefox, Safari, Edge)
   - Esto confirma si el problema es específico de tu configuración actual

#### 6. **Verificar que el Checkout Funciona**
   Después de aplicar las soluciones:
   1. Abre el checkout de Mercado Pago
   2. Ingresa los datos de la tarjeta de prueba
   3. Verifica que el botón "Continuar" funciona
   4. Si aún no funciona, revisa la consola para ver qué scripts siguen bloqueados

**Nota:** Los errores de `ERR_BLOCKED_BY_CLIENT` son causados por bloqueadores, no por problemas en el código del backend o frontend. Es necesario permitir las peticiones de Mercado Pago para que el checkout funcione correctamente.

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

### Error: "Mixed Content" (HTTP/HTTPS)
- Estos son warnings del navegador, no errores críticos
- Mercado Pago maneja automáticamente la actualización de HTTP a HTTPS
- No afectan el funcionamiento del checkout

### 📋 Guía de Errores Específicos en Consola

Cuando abres el checkout de Mercado Pago, es normal ver varios errores en la consola. Esta guía te ayuda a entender cuáles son críticos y cuáles puedes ignorar:

#### ✅ Errores que PUEDES IGNORAR (No críticos)

1. **`404 (Not Found)` en endpoints de Mercado Pago:**
   ```
   GET https://sandbox.mercadopago.cl/jms/lgz/background/etid 404 (Not Found)
   GET https://sandbox.mercadopago.cl/jms/lgz/background/session/... 404 (Not Found)
   ```
   - **Qué son**: Endpoints internos de tracking/analytics de Mercado Pago
   - **Por qué aparecen**: Son opcionales y no siempre están disponibles
   - **Acción**: Puedes ignorarlos, no afectan el checkout

2. **`Mixed Content` warnings:**
   ```
   Mixed Content: The page at 'https://sandbox.mercadopago.cl/...' was loaded over HTTPS, 
   but requested an insecure element 'http://www.mercadolibre.com/...'
   ```
   - **Qué son**: Advertencias sobre recursos HTTP en páginas HTTPS
   - **Por qué aparecen**: Mercado Pago usa algunos recursos HTTP antiguos
   - **Acción**: El navegador los actualiza automáticamente a HTTPS, puedes ignorarlos

3. **`401 (Unauthorized)` en reCAPTCHA:**
   ```
   POST https://www.google.com/recaptcha/enterprise/pat?k=... 401 (Unauthorized)
   ```
   - **Qué es**: Error de autenticación con reCAPTCHA de Google
   - **Por qué aparece**: reCAPTCHA no está configurado o no es necesario
   - **Acción**: Puedes ignorarlo si no usas reCAPTCHA en tu checkout

#### ❌ Errores CRÍTICOS (Debes solucionarlos)

1. **`ERR_BLOCKED_BY_CLIENT` en scripts de Mercado Pago:**
   ```
   GET https://js-agent.newrelic.com/nr-rum-1.303.0.min.js net::ERR_BLOCKED_BY_CLIENT
   POST https://api.mercadolibre.com/tracks net::ERR_BLOCKED_BY_CLIENT
   ```
   - **Qué es**: Un bloqueador está bloqueando scripts necesarios
   - **Por qué es crítico**: Algunos scripts son necesarios para tokenizar la tarjeta
   - **Síntoma**: El botón "Continuar" no funciona después de ingresar datos de tarjeta
   - **Acción**: Ver sección "Error: ERR_BLOCKED_BY_CLIENT" arriba

2. **`TypeError: Cannot read properties of null (reading 'id')`:**
   ```
   TypeError: Cannot read properties of null (reading 'id')
   ```
   - **Qué es**: Un script bloqueado impidió la inicialización de un objeto
   - **Por qué es crítico**: Indica que un componente crítico no se cargó
   - **Causa común**: Bloqueador bloqueó un script necesario
   - **Acción**: Desactiva bloqueadores y prueba de nuevo

3. **`Could not send event id ... Error: [object ProgressEvent]`:**
   ```
   Could not send event id 118b6e9a-cf52-4a25-9665-43c171c83a22. Error: [object ProgressEvent]
   ```
   - **Qué es**: No se pudo enviar un evento de tracking
   - **Por qué puede ser crítico**: Si es parte del flujo de tokenización, puede bloquear el checkout
   - **Causa común**: Bloqueador o problema de red
   - **Acción**: Verifica bloqueadores y conexión a internet

#### 🔍 Cómo Verificar si el Problema es Crítico

1. **Abre el checkout de Mercado Pago**
2. **Ingresa los datos de la tarjeta de prueba**
3. **Intenta hacer clic en "Continuar"**
4. **Si el botón NO funciona** → El problema es crítico, sigue las soluciones arriba
5. **Si el botón SÍ funciona** → Los errores son solo warnings, puedes ignorarlos

#### 💡 Recomendación

Para pruebas de desarrollo, usa **modo incógnito** sin extensiones. Esto elimina la mayoría de los errores y te permite verificar que el checkout funciona correctamente.

### ⚠️ Error Persiste Incluso Sin Bloqueadores

**Síntomas:**
- Los errores `ERR_BLOCKED_BY_CLIENT` persisten incluso en modo incógnito
- El botón "Continuar" no funciona después de ingresar datos de tarjeta
- El checkout de Mercado Pago se carga pero no permite completar el pago

**Posibles Causas:**

1. **Problema con las Credenciales de Sandbox:**
   - Verifica que estés usando credenciales de **sandbox** (no producción)
   - Verifica que `MERCADOPAGO_ENVIRONMENT=sandbox` en tu `.env`
   - Verifica que el `MERCADOPAGO_ACCESS_TOKEN` sea válido y no esté expirado

2. **Problema con la Configuración de la Preferencia:**
   - Verifica los logs del backend para ver qué datos se están enviando a Mercado Pago
   - Verifica que la preferencia se esté creando correctamente (status 201)
   - Verifica que el `payment_link` se esté generando correctamente

3. **Problema con el Ambiente de Sandbox de Mercado Pago:**
   - El ambiente de sandbox de Mercado Pago puede tener problemas temporales
   - Intenta crear una nueva preferencia después de unos minutos
   - Verifica el estado del servicio de Mercado Pago en su página de estado

4. **Problema con el Formato del `payment_link`:**
   - Verifica que el `payment_link` tenga el formato correcto: `https://sandbox.mercadopago.cl/checkout/v1/redirect?pref_id=...`
   - Verifica que el `pref_id` en la URL sea válido

**Soluciones:**

1. **Verificar Credenciales:**
   ```bash
   # En el backend, verifica los logs cuando se crea una preferencia
   docker compose logs backend --tail=100 | grep -E "(preference|MercadoPago|ERROR)"
   ```

2. **Verificar la Preferencia Directamente:**
   - Abre el `payment_link` en una nueva pestaña
   - Verifica que el checkout se carga correctamente
   - Intenta ingresar los datos de la tarjeta de prueba
   - Si el checkout no se carga, el problema está en la preferencia

3. **Crear una Preferencia de Prueba Manualmente:**
   - Usa la API de Mercado Pago directamente para crear una preferencia de prueba
   - Compara la respuesta con la que genera tu backend
   - Verifica si hay diferencias en la configuración

4. **Contactar Soporte de Mercado Pago:**
   - Si el problema persiste, podría ser un problema con tu cuenta de sandbox
   - Contacta al soporte de Mercado Pago con los detalles del problema
   - Incluye los logs del backend y los errores de la consola del navegador

**Verificación Rápida:**

1. **Verifica que el backend esté generando el `payment_link` correctamente:**
   ```bash
   docker compose logs backend --tail=50 | grep "payment_link"
   ```

2. **Abre el `payment_link` directamente en el navegador:**
   - Copia el `payment_link` de los logs
   - Ábrelo en una nueva pestaña
   - Verifica si el checkout se carga correctamente

3. **Prueba con una tarjeta de prueba diferente:**
   - Usa una tarjeta de prueba diferente (Visa, Mastercard, etc.)
   - Verifica si el problema es específico de una tarjeta

**Nota:** Si el problema persiste incluso después de verificar todo lo anterior, podría ser un problema temporal con el servicio de Mercado Pago. Intenta de nuevo después de unos minutos o contacta al soporte de Mercado Pago.

### ⚠️ Error: `back_urls` Vacías en la Preferencia

**Síntomas:**
- El backend envía `back_urls` correctas pero Mercado Pago las guarda vacías
- En los logs del backend ves: `back_urls config: {'failure': '', 'pending': '', 'success': ''}`
- El checkout se carga pero puede tener problemas con la redirección después del pago

**Causa:**
Mercado Pago rechaza URLs HTTP (`http://localhost:3000`) en el ambiente de sandbox. Cuando envías `back_urls` con URLs HTTP, Mercado Pago las rechaza silenciosamente y las guarda como vacías.

**Solución:**

1. **Usar ngrok para HTTPS (Recomendado para Desarrollo):**
   ```bash
   # Instalar ngrok si no lo tienes
   brew install ngrok  # macOS
   # o descarga desde https://ngrok.com/
   
   # Iniciar ngrok apuntando al frontend
   ngrok http 3000
   ```
   
   Luego configura en tu `.env`:
   ```env
   NGROK_URL=https://xxxx-xxxx-xxxx.ngrok-free.app
   APP_BASE_URL=https://xxxx-xxxx-xxxx.ngrok-free.app
   ```

2. **Verificar que las back_urls se guardaron:**
   ```bash
   docker compose logs backend --tail=100 | grep -E "(back_urls|WARNING MercadoPago)"
   ```
   
   Si ves el warning `Las back_urls NO se guardaron correctamente`, significa que Mercado Pago las rechazó.

3. **Alternativa: Omitir back_urls (No recomendado):**
   - El checkout funcionará pero no habrá redirección automática después del pago
   - El usuario tendrá que volver manualmente a tu aplicación
   - Solo útil para pruebas rápidas

**Nota:** Las `back_urls` vacías no impiden que el checkout funcione, pero sí impiden la redirección automática después del pago. El usuario puede completar el pago, pero tendrá que volver manualmente a tu aplicación.

### ⚠️ Error: `ERR_BLOCKED_BY_CLIENT` Persiste Incluso Sin Bloqueadores

**Síntomas:**
- `ERR_BLOCKED_BY_CLIENT` en `api.mercadolibre.com/tracks`
- `TypeError: Cannot read properties of null (reading 'id')`
- El botón "Continuar" no funciona después de ingresar datos de tarjeta
- El error persiste incluso en modo incógnito y otros navegadores

**Causas Posibles:**

1. **Bloqueador a Nivel del Sistema:**
   - Firewall o antivirus bloqueando conexiones
   - Proxy corporativo bloqueando ciertos dominios
   - Configuración de red bloqueando `api.mercadolibre.com`

2. **Configuración del Navegador:**
   - Políticas de seguridad estrictas
   - Configuración de privacidad que bloquea trackers
   - Modo de privacidad estricto activado

3. **Problema con el Ambiente de Sandbox:**
   - El ambiente de sandbox de Mercado Pago puede tener problemas temporales
   - Algunos scripts de tracking pueden no estar disponibles

**Soluciones:**

1. **Verificar Configuración de Red:**
   ```bash
   # Verificar que puedes acceder a api.mercadolibre.com
   curl -I https://api.mercadolibre.com/tracks
   ```

2. **Desactivar Firewall/Antivirus Temporalmente:**
   - Desactiva temporalmente el firewall o antivirus
   - Prueba el flujo de pago
   - Si funciona, configura excepciones para `*.mercadolibre.com` y `*.mercadopago.com`

3. **Usar un Navegador Diferente:**
   - Prueba con Chrome, Firefox, Safari, Edge
   - Algunos navegadores tienen configuraciones de privacidad más estrictas

4. **Verificar Políticas de Privacidad del Navegador:**
   - Chrome: `chrome://settings/privacy` → Verificar configuración de "No rastrear"
   - Firefox: `about:preferences#privacy` → Verificar configuración de protección contra rastreo
   - Safari: Preferencias → Privacidad → Verificar configuración

5. **Contactar Soporte de Mercado Pago:**
   - Si el problema persiste, podría ser un problema con el ambiente de sandbox
   - Contacta al soporte con los detalles del error
   - Incluye capturas de pantalla de la consola del navegador

**Nota:** Los errores `ERR_BLOCKED_BY_CLIENT` en `api.mercadolibre.com/tracks` son principalmente de tracking/analytics. Aunque pueden causar problemas, el checkout debería funcionar si los scripts principales de Mercado Pago se cargan correctamente. Si el botón "Continuar" no funciona, el problema es más crítico y requiere atención.

### ⚠️ Error: `createCardToken` Falla - `ERR_BLOCKED_BY_CLIENT` en `api.mercadolibre.com/tracks`

**Síntomas:**
- Error: `Could not send event id ... Error: [object ProgressEvent]` en `createCardToken`
- `POST https://api.mercadolibre.com/tracks net::ERR_BLOCKED_BY_CLIENT`
- `TypeError: Cannot read properties of null (reading 'id')`
- El botón "Continuar" no funciona después de ingresar datos de tarjeta
- El error persiste incluso en modo incógnito

**Causa:**
Un bloqueador está bloqueando los scripts de tracking de Mercado Pago (`api.mercadolibre.com/tracks`). Aunque estos scripts son principalmente para analytics, **Mercado Pago los usa también para crear el token de la tarjeta**. Si están bloqueados, el checkout no puede procesar el pago.

**Soluciones Definitivas:**

1. **Verificar Extensiones del Navegador (Chrome/Edge):**
   ```bash
   # Abre Chrome y ve a:
   chrome://extensions/
   
   # Desactiva TODAS las extensiones temporalmente
   # Especialmente:
   # - AdBlock, uBlock Origin, Privacy Badger
   # - Cualquier extensión de privacidad
   # - Cualquier extensión de seguridad
   ```

2. **Verificar Configuración de Privacidad del Navegador:**
   - **Chrome**: `chrome://settings/privacy` → Desactiva "No rastrear" temporalmente
   - **Firefox**: `about:preferences#privacy` → Desactiva "Protección contra rastreo" temporalmente
   - **Safari**: Preferencias → Privacidad → Desactiva "Prevenir rastreo entre sitios web" temporalmente

3. **Verificar Firewall/Antivirus:**
   - Desactiva temporalmente el firewall o antivirus
   - Verifica que no esté bloqueando `api.mercadolibre.com`
   - Configura excepciones para `*.mercadolibre.com` y `*.mercadopago.com`

4. **Verificar Proxy/VPN:**
   - Si usas un proxy o VPN, desactívalo temporalmente
   - Algunos proxies bloquean scripts de tracking

5. **Usar un Navegador Completamente Limpio:**
   - Descarga un navegador nuevo (Chrome, Firefox, Edge)
   - No instales extensiones
   - Prueba el checkout ahí

6. **Verificar Políticas de Red (Si estás en una red corporativa):**
   - Algunas redes corporativas bloquean scripts de tracking
   - Prueba desde otra red (hotspot del móvil, red doméstica)

7. **Contactar Soporte de Mercado Pago:**
   - Si nada funciona, contacta al soporte de Mercado Pago
   - Explica que `createCardToken` falla por `ERR_BLOCKED_BY_CLIENT`
   - Pregunta si hay una forma de desactivar el tracking o usar una API alternativa

**Verificación Rápida:**

1. Abre las herramientas de desarrollador (F12)
2. Ve a la pestaña "Network" (Red)
3. Intenta crear un pago
4. Busca peticiones a `api.mercadolibre.com/tracks`
5. Si ves `ERR_BLOCKED_BY_CLIENT`, confirma que es un bloqueador

**Nota Importante:** Este es un problema del lado del cliente (navegador), no del backend. El backend está funcionando correctamente (las `back_urls` están configuradas con HTTPS). El problema es que el navegador está bloqueando scripts necesarios para el funcionamiento del checkout.

### ⚠️ Error: Brave Browser Bloqueando Scripts de Mercado Pago

**Síntomas:**
- `ERR_BLOCKED_BY_CLIENT` en `api.mercadolibre.com/tracks`
- `createCardToken` falla
- El botón "Continuar" no funciona
- El error persiste incluso en modo incógnito

**Causa:**
Brave Browser tiene un bloqueador de anuncios y trackers integrado que es muy agresivo. Por defecto, bloquea scripts de tracking, lo que incluye los scripts de Mercado Pago necesarios para crear el token de la tarjeta.

**Soluciones para Brave:**

#### Solución 1: Desactivar Shield Temporalmente (Recomendado para Pruebas)

1. **Abre el checkout de Mercado Pago**
2. **Haz clic en el icono del león (Brave Shield)** en la barra de direcciones
3. **Desactiva "Shields" para este sitio**
4. **Recarga la página**
5. **Intenta el pago de nuevo**

#### Solución 2: Configurar Excepciones en Brave Shield

1. **Abre el checkout de Mercado Pago**
2. **Haz clic en el icono del león (Brave Shield)**
3. **Haz clic en "Configuración avanzada"**
4. **En "Cookies y scripts de seguimiento"**, selecciona "Permitir todos los cookies y scripts de seguimiento"
5. **O agrega excepciones específicas:**
   - `sandbox.mercadopago.cl`
   - `api.mercadolibre.com`
   - `*.mercadopago.com`
   - `*.mercadolibre.com`

#### Solución 3: Configuración Global de Brave (Para Desarrollo)

1. **Abre `brave://settings/shields`**
2. **Desactiva "Bloquear anuncios y seguimiento"** temporalmente
3. **O configura excepciones específicas:**
   - Ve a `brave://settings/shields/filters`
   - Agrega excepciones para los dominios de Mercado Pago

#### Solución 4: Usar un Perfil de Navegador Separado

1. **Crea un nuevo perfil en Brave** sin bloqueadores
2. **Usa ese perfil solo para pruebas de desarrollo**
3. **Mantén tu perfil principal con bloqueadores activos**

#### Solución 5: Configurar Brave para Permitir Scripts de Mercado Pago

1. **Abre `brave://settings/shields`**
2. **Haz clic en "Filtros"**
3. **Agrega excepciones para:**
   ```
   sandbox.mercadopago.cl
   api.mercadolibre.com
   *.mercadopago.com
   *.mercadolibre.com
   ```

**Pasos Rápidos (Solución Más Rápida):**

1. Abre el checkout de Mercado Pago
2. Haz clic en el **icono del león (Brave Shield)** en la barra de direcciones
3. **Desactiva "Shields"** para este sitio
4. Recarga la página
5. Intenta el pago

**Nota:** Brave es conocido por tener bloqueadores muy agresivos. Para desarrollo, es recomendable desactivar Shield temporalmente o usar un navegador diferente (Chrome, Firefox) para pruebas de integración de pagos.

### ⚠️ Error: `requestStorageAccessFor: Permission denied` en Brave

**Síntomas:**
- `requestStorageAccessFor: Permission denied`
- `TypeError: Cannot read properties of null (reading 'id')`
- El botón "Continuar" no funciona
- El error persiste incluso después de desactivar Shield

**Causa:**
Brave tiene configuraciones adicionales de privacidad que bloquean el acceso a cookies y storage entre sitios. Mercado Pago necesita acceso a cookies/storage para funcionar correctamente.

**Soluciones Adicionales para Brave:**

#### Solución 1: Permitir Cookies y Storage (Recomendado)

1. **Abre `brave://settings/cookies`**
2. **Desactiva "Bloquear cookies de terceros"** temporalmente
3. **O configura excepciones:**
   - Haz clic en "Agregar" en "Sitios que siempre pueden usar cookies"
   - Agrega: `sandbox.mercadopago.cl`
   - Agrega: `api.mercadolibre.com`

#### Solución 2: Configurar Permisos de Storage

1. **Abre `brave://settings/content/all`**
2. **Busca `sandbox.mercadopago.cl`**
3. **Permite "Cookies" y "JavaScript"**
4. **Permite "Imágenes" y "Scripts"**

#### Solución 3: Desactivar Todas las Protecciones de Privacidad Temporalmente

1. **Abre `brave://settings/privacy`**
2. **Desactiva temporalmente:**
   - "Bloquear anuncios y seguimiento"
   - "Bloquear cookies de terceros"
   - "Bloquear scripts de seguimiento"
3. **Recarga el checkout de Mercado Pago**
4. **Intenta el pago**

#### Solución 4: Usar un Perfil de Navegador Limpio

1. **Crea un nuevo perfil en Brave:**
   - `brave://settings/profiles`
   - Haz clic en "Agregar"
2. **En el nuevo perfil, desactiva todas las protecciones:**
   - Shield desactivado
   - Cookies permitidas
   - JavaScript permitido
3. **Usa este perfil solo para desarrollo**

#### Solución 5: Usar Chrome o Firefox para Pruebas

Si nada funciona, usa Chrome o Firefox para pruebas de integración de pagos:
- Chrome: No tiene bloqueadores integrados por defecto
- Firefox: Tiene bloqueadores opcionales que puedes desactivar fácilmente

**Pasos Rápidos (Solución Más Completa):**

1. **Abre `brave://settings/cookies`**
2. **Desactiva "Bloquear cookies de terceros"**
3. **Abre `brave://settings/shields`**
4. **Desactiva "Bloquear anuncios y seguimiento"**
5. **Abre el checkout de Mercado Pago**
6. **Haz clic en el icono del león y desactiva Shield para este sitio**
7. **Recarga la página (F5)**
8. **Intenta el pago**

**Verificación:**

Después de aplicar las configuraciones:
1. Abre la consola del navegador (F12)
2. Ve a la pestaña "Application" → "Cookies"
3. Verifica que hay cookies de `sandbox.mercadopago.cl`
4. Intenta crear un pago
5. No deberías ver `requestStorageAccessFor: Permission denied`

