# 🔐 Sistema de Login y Autenticación - Crowdify Backend

## 📋 Resumen Ejecutivo

**Este backend NO tiene endpoints de login/registro propios.** El sistema de autenticación funciona de la siguiente manera:

1. **Frontend maneja login/registro** usando **Supabase Auth**
2. **Backend valida tokens JWT** que vienen del frontend
3. **Soporta dos tipos de tokens**: Tokens de Supabase Auth y tokens propios del backend

---

## 🏗️ Arquitectura del Sistema de Autenticación

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│   Frontend  │────────▶│ Supabase Auth│────────▶│   Backend   │
│  (React/    │  Login  │  (Servicio   │  Token  │  (FastAPI)  │
│   Next.js)  │  /Reg   │   Externo)   │  JWT    │             │
└─────────────┘         └──────────────┘         └─────────────┘
                              │
                              │ Valida token
                              ▼
                        ┌──────────────┐
                        │   Redis      │
                        │   (Cache)    │
                        └──────────────┘
```

---

## 🔄 Flujo Completo de Autenticación

### 1. **Registro/Login (Frontend → Supabase)**

El usuario se registra o inicia sesión desde el **frontend** usando Supabase:

```javascript
// En el frontend (React/Next.js)
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY)

// REGISTRO
const { data, error } = await supabase.auth.signUp({
  email: 'usuario@example.com',
  password: 'password123'
})

// LOGIN
const { data, error } = await supabase.auth.signInWithPassword({
  email: 'usuario@example.com',
  password: 'password123'
})

// Obtener token después del login
const { data: { session } } = await supabase.auth.getSession()
const token = session?.access_token  // Este es el token JWT
```

### 2. **Envío de Token al Backend**

El frontend envía el token en cada request:

```javascript
// Ejemplo: Llamar a la API del backend
fetch('http://localhost:8000/api/v1/events', {
  headers: {
    'Authorization': `Bearer ${token}`  // Token de Supabase
  }
})
```

### 3. **Validación en el Backend**

El backend valida el token automáticamente:

```python
# En shared/auth/jwt_handler.py
async def verify_token(token: str):
    # Detecta si es token de Supabase o token propio
    if 'supabase.co/auth' in issuer:
        # Valida con Supabase Auth API
        return await verify_supabase_token(token)
    else:
        # Valida token propio del backend
        return decode_token(token)
```

### 4. **Cache en Redis**

Los tokens validados se cachean en Redis por 10 minutos para mejorar performance:

```python
# En shared/auth/supabase_validator.py
cache_key = f'jwt:validated:{token_hash}'
cached_payload = await redis_client.get(cache_key)
if cached_payload:
    return json.loads(cached_payload)  # Fast path - sin llamar a Supabase
```

---

## 🔍 Cómo Funciona la Validación

### Validación de Tokens de Supabase

1. **Extrae el issuer** del token (sin verificar)
2. **Si es token de Supabase** (`supabase.co/auth`):
   - Llama a `{SUPABASE_URL}/auth/v1/user` con el token
   - Supabase valida el token y devuelve datos del usuario
   - Extrae `user_id`, `email`, `role` del payload
3. **Cachea el resultado** en Redis por 10 minutos
4. **Retorna payload** con información del usuario

### Validación de Tokens Propios

1. **Si NO es token de Supabase**:
   - Valida el token localmente usando `JWT_SECRET`
   - Extrae `user_id`, `email`, `role` del payload
   - Retorna payload con información del usuario

---

## 🛡️ Protección de Endpoints

### Dependencies de FastAPI

El backend usa **dependencies** de FastAPI para proteger endpoints:

```python
# Endpoint público (no requiere token)
@router.get("/events")
async def list_events():
    return events

# Endpoint protegido (requiere token de cualquier usuario)
@router.post("/purchases")
async def create_purchase(
    current_user: Dict = Depends(get_current_user)  # ← Valida token
):
    user_id = current_user['user_id']
    # ... lógica de compra

# Endpoint solo para admin
@router.post("/events")
async def create_event(
    current_user: Dict = Depends(get_current_admin)  # ← Valida token + rol admin
):
    # ... lógica de creación
```

### Dependencies Disponibles

1. **`get_current_user`**: Requiere token válido (cualquier usuario)
2. **`get_current_admin`**: Requiere token + rol `admin`
3. **`get_current_scanner`**: Requiere token + rol `scanner` o `admin`
4. **`get_current_admin_or_coordinator`**: Requiere token + rol `admin` o `coordinator`
5. **`get_optional_user`**: Token opcional (para endpoints públicos que pueden personalizarse)

---

## 👥 Roles de Usuario

El sistema soporta 4 roles:

| Rol | Descripción | Endpoints Accesibles |
|-----|-------------|---------------------|
| **user** | Usuario estándar | Comprar tickets, ver sus tickets |
| **admin** | Administrador | Todos los endpoints + panel admin |
| **scanner** | Validador de tickets | Validar tickets QR |
| **coordinator** | Coordinador | Gestionar eventos, ver estadísticas |

### Cómo se Asigna el Rol

El rol viene del token JWT:

- **Tokens de Supabase**: El rol está en `user_metadata.role` o `app_metadata.role`
- **Tokens propios**: El rol está directamente en el payload del token

```python
# En shared/auth/dependencies.py
role = payload.get('app_metadata', {}).get('role', 'user')  # Default: 'user'
```

---

## 🚫 Lo que NO tiene este Backend

### ❌ No hay endpoints de:
- `POST /api/v1/auth/login` - No existe
- `POST /api/v1/auth/register` - No existe
- `POST /api/v1/auth/logout` - No existe
- `POST /api/v1/auth/refresh` - No existe

### ✅ En su lugar:
- El frontend usa **Supabase Auth** para login/registro
- El backend solo **valida tokens** que vienen del frontend

---

## 🔧 Configuración Necesaria

### Variables de Entorno

```env
# Supabase (para validar tokens)
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# JWT (para tokens propios del backend)
JWT_SECRET_KEY=dev-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# Redis (para cache de tokens)
REDIS_URL=redis://redis:6379/0
```

---

## 📝 Ejemplo Completo de Flujo

### 1. Usuario se registra en el frontend:

```javascript
// Frontend
const { data, error } = await supabase.auth.signUp({
  email: 'nuevo@example.com',
  password: 'password123'
})

// Supabase crea el usuario en auth.users
// Supabase devuelve un token JWT
const token = data.session.access_token
```

### 2. Frontend guarda el token:

```javascript
// El token se guarda automáticamente en Supabase client
// O puedes guardarlo manualmente:
localStorage.setItem('token', token)
```

### 3. Frontend hace request al backend:

```javascript
const token = await supabase.auth.getSession().then(s => s.data.session?.access_token)

fetch('http://localhost:8000/api/v1/purchases', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    event_id: '123e4567-e89b-12d3-a456-426614174000',
    attendees: [...]
  })
})
```

### 4. Backend valida el token:

```python
# En shared/auth/dependencies.py
async def get_current_user(credentials):
    token = credentials.credentials
    payload = await verify_token(token)  # ← Valida con Supabase
    
    if payload is None:
        raise HTTPException(401, "Token inválido")
    
    return {
        'user_id': payload['sub'],
        'email': payload['email'],
        'role': payload.get('app_metadata', {}).get('role', 'user')
    }
```

### 5. Backend procesa la request:

```python
# En services/ticket_purchase/routes/purchase.py
@router.post("/purchases")
async def create_purchase(
    request: PurchaseRequest,
    current_user: Dict = Depends(get_current_user)  # ← Token validado
):
    # current_user['user_id'] contiene el ID del usuario
    # Procesar compra...
```

---

## 🧪 Generar Tokens de Prueba (Desarrollo)

Para desarrollo/testing, puedes generar tokens sin usar Supabase:

```bash
# Generar token de prueba
python3 scripts/generate_token.py \
  --user-id "550e8400-e29b-41d4-a716-446655440000" \
  --email "test@example.com" \
  --role admin

# Usar el token
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/v1/events
```

Estos tokens se validan **localmente** (no llaman a Supabase).

---

## 🔄 Migración desde Supabase

El sistema está diseñado para **convivir con Supabase** durante la migración:

1. **Fase 1**: Frontend usa Supabase Auth, backend valida tokens de Supabase ✅ (Actual)
2. **Fase 2**: Backend puede generar sus propios tokens (ya implementado)
3. **Fase 3**: Frontend migra gradualmente a tokens propios del backend

---

## 🐛 Troubleshooting

### Error: "Token inválido o expirado"

**Causas posibles:**
- Token expirado (tokens de Supabase duran 1 hora por defecto)
- Token no es válido
- `SUPABASE_URL` o `SUPABASE_ANON_KEY` incorrectos
- Redis no está disponible (afecta cache, no la validación)

**Solución:**
```bash
# Verificar variables de entorno
echo $SUPABASE_URL
echo $SUPABASE_ANON_KEY

# Verificar que Redis esté corriendo
curl http://localhost:8000/ready
```

### Error: "Se requieren permisos de administrador"

**Causa:** El usuario no tiene rol `admin` en Supabase.

**Solución:**
1. Ir a Supabase Dashboard → Authentication → Users
2. Editar el usuario
3. En `user_metadata` o `app_metadata`, agregar: `{"role": "admin"}`
4. O usar el endpoint admin para cambiar roles (si está implementado)

---

## 📚 Referencias

- **Supabase Auth Docs**: https://supabase.com/docs/guides/auth
- **JWT Handler**: `shared/auth/jwt_handler.py`
- **Supabase Validator**: `shared/auth/supabase_validator.py`
- **Dependencies**: `shared/auth/dependencies.py`

---

## 💡 Resumen

✅ **Login/Registro**: Se maneja en el **frontend** con Supabase Auth  
✅ **Validación**: El **backend** valida tokens JWT automáticamente  
✅ **Cache**: Tokens validados se cachean en Redis (10 min)  
✅ **Roles**: Soporta 4 roles (user, admin, scanner, coordinator)  
✅ **Flexible**: Soporta tokens de Supabase y tokens propios  

❌ **NO hay endpoints de login/registro en el backend**  
❌ **NO se almacenan contraseñas en el backend** (están en Supabase Auth)

