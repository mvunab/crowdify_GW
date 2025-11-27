# 🎯 Cómo Obtener Token JWT - Guía Práctica

## 📋 Dos Formas de Obtener el Token

### 1️⃣ **Desde el Frontend (Supabase Auth)** - Producción/Real
### 2️⃣ **Generar Token de Prueba** - Desarrollo/Testing

---

## 🚀 Opción 1: Obtener Token desde Supabase (Frontend)

### Paso 1: Usuario hace Login en el Frontend

```javascript
// En tu frontend (React/Next.js/Vue)
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  'https://olyicxwxyxwtiandtbcg.supabase.co',  // Tu SUPABASE_URL
  'tu-supabase-anon-key'  // Tu SUPABASE_ANON_KEY
)

// LOGIN
const { data, error } = await supabase.auth.signInWithPassword({
  email: 'usuario@example.com',
  password: 'tu-password'
})

if (error) {
  console.error('Error de login:', error)
} else {
  console.log('Login exitoso!')
}
```

### Paso 2: Obtener el Token JWT

```javascript
// Después del login, obtener el token
const { data: { session } } = await supabase.auth.getSession()

if (session) {
  const token = session.access_token  // ← Este es tu token JWT
  console.log('Token JWT:', token)
  
  // Guardar para usar después
  localStorage.setItem('jwt_token', token)
}
```

### Paso 3: Usar el Token en Requests

```javascript
// Obtener token guardado
const token = localStorage.getItem('jwt_token')
// O directamente desde Supabase
const { data: { session } } = await supabase.auth.getSession()
const token = session?.access_token

// Usar en fetch/axios
fetch('http://localhost:8000/api/v1/purchases', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    event_id: '123e4567-e89b-12d3-a456-426614174000',
    user_id: session.user.id,
    attendees: [...]
  })
})
```

### 🔍 Ver Token en la Consola del Navegador

Si ya estás logueado en tu frontend, puedes obtener el token desde la consola:

```javascript
// Abre DevTools (F12) → Console
// Si usas Supabase en el frontend:

// Opción A: Si tienes supabase en window
const { data: { session } } = await supabase.auth.getSession()
console.log('Token:', session?.access_token)

// Opción B: Desde localStorage (si lo guardaste)
localStorage.getItem('jwt_token')

// Opción C: Inspeccionar el token en Network tab
// 1. Abre DevTools → Network
// 2. Haz una request a tu API
// 3. Ve a Headers → Request Headers
// 4. Busca "Authorization: Bearer ..."
```

---

## 🧪 Opción 2: Generar Token de Prueba (Desarrollo)

### Método Rápido (Recomendado para Testing)

```bash
# Generar token de admin
python3 scripts/generate_token.py \
  --user-id "550e8400-e29b-41d4-a716-446655440000" \
  --email "admin@test.com" \
  --role admin
```

**Salida:**
```
Token generado:
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI1NTBlODQwMC1lMjliLTQxZDQtYTcxNi00NDY2NTU0NDAwMDAiLCJ1c2VyX2lkIjoiNTUwZTg0MDAtZTI5Yi00MWQ0LWE3MTYtNDQ2NjU1NDQwMDAwIiwiZW1haWwiOiJhZG1pbkB0ZXN0LmNvbSIsInJvbGUiOiJhZG1pbiIsImlhdCI6MTc2NDE4ODcxMX0.n0hgHz9rgMmcc_iiDpM01BCeRDpkD1KPvL_CpYIuxOU
```

### Guardar Token en Variable

```bash
# Guardar token en variable de entorno
export TOKEN=$(python3 scripts/generate_token.py \
  --user-id "550e8400-e29b-41d4-a716-446655440000" \
  --role admin | grep "Token generado" -A 1 | tail -1)

# Verificar
echo $TOKEN

# Usar
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/events
```

### Generar Tokens con Diferentes Roles

```bash
# Usuario normal
python3 scripts/generate_token.py \
  --user-id "111e1111-e11b-11d1-a111-111111111111" \
  --email "user@test.com" \
  --role user

# Admin
python3 scripts/generate_token.py \
  --user-id "222e2222-e22b-22d2-a222-222222222222" \
  --email "admin@test.com" \
  --role admin

# Scanner
python3 scripts/generate_token.py \
  --user-id "333e3333-e33b-33d3-a333-333333333333" \
  --email "scanner@test.com" \
  --role scanner

# Coordinator
python3 scripts/generate_token.py \
  --user-id "444e4444-e44b-44d4-a444-444444444444" \
  --email "coordinator@test.com" \
  --role coordinator
```

---

## 🔧 Si usas Docker

```bash
# Generar token desde dentro del contenedor
docker compose exec backend poetry run python scripts/generate_token.py \
  --user-id "550e8400-e29b-41d4-a716-446655440000" \
  --role admin
```

---

## 📝 Ejemplo Completo: Obtener y Usar Token

### Desde Frontend (JavaScript/TypeScript)

```javascript
// 1. Configurar Supabase
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
)

// 2. Función para obtener token
async function getAuthToken() {
  const { data: { session }, error } = await supabase.auth.getSession()
  
  if (error || !session) {
    // Si no hay sesión, hacer login primero
    const { data: loginData, error: loginError } = await supabase.auth.signInWithPassword({
      email: 'usuario@example.com',
      password: 'password123'
    })
    
    if (loginError) {
      throw new Error('Error de login: ' + loginError.message)
    }
    
    return loginData.session.access_token
  }
  
  return session.access_token
}

// 3. Usar el token
async function callBackendAPI() {
  const token = await getAuthToken()
  
  const response = await fetch('http://localhost:8000/api/v1/purchases', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      event_id: '123e4567-e89b-12d3-a456-426614174000',
      user_id: (await supabase.auth.getUser()).data.user.id,
      attendees: [
        {
          name: 'Juan Pérez',
          email: 'juan@example.com',
          document_type: 'rut',
          document_number: '12345678-9',
          is_child: false
        }
      ]
    })
  })
  
  const data = await response.json()
  return data
}
```

### Desde Terminal (curl)

```bash
# 1. Generar token
TOKEN=$(python3 scripts/generate_token.py \
  --user-id "550e8400-e29b-41d4-a716-446655440000" \
  --role admin | grep "Token generado" -A 1 | tail -1)

# 2. Probar endpoint
curl -X GET \
  -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/events

# 3. Crear evento (requiere admin)
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Evento de Prueba",
    "location_text": "Santiago, Chile",
    "starts_at": "2024-12-31T20:00:00Z",
    "ends_at": "2025-01-01T02:00:00Z",
    "capacity_total": 100
  }' \
  http://localhost:8000/api/v1/events
```

### Desde Python

```python
import requests
import subprocess
import json

# 1. Generar token
result = subprocess.run(
    [
        'python3', 'scripts/generate_token.py',
        '--user-id', '550e8400-e29b-41d4-a716-446655440000',
        '--email', 'admin@test.com',
        '--role', 'admin'
    ],
    capture_output=True,
    text=True
)

# Extraer token de la salida
token = None
for line in result.stdout.split('\n'):
    if line.startswith('eyJ'):  # Los tokens JWT empiezan así
        token = line.strip()
        break

if not token:
    print("Error generando token")
    exit(1)

# 2. Usar token
headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json'
}

# Probar endpoint
response = requests.get(
    'http://localhost:8000/api/v1/events',
    headers=headers
)

print(f"Status: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)}")
```

---

## 🔍 Verificar que el Token Funciona

```bash
# 1. Obtener token
TOKEN="tu-token-aqui"

# 2. Probar health (no requiere token)
curl http://localhost:8000/health

# 3. Probar ready (no requiere token)
curl http://localhost:8000/ready

# 4. Probar endpoint público
curl http://localhost:8000/api/v1/events

# 5. Probar endpoint protegido CON token
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/tickets/user/550e8400-e29b-41d4-a716-446655440000

# 6. Probar endpoint protegido SIN token (debe fallar)
curl http://localhost:8000/api/v1/tickets/user/550e8400-e29b-41d4-a716-446655440000
# Respuesta esperada: {"detail":"Not authenticated"}
```

---

## 🐛 Troubleshooting

### Error: "Token inválido o expirado"

**Causas:**
- Token expirado (tokens de Supabase duran ~1 hora)
- Token corrupto o mal copiado
- `JWT_SECRET` incorrecto (para tokens propios)

**Solución:**
```bash
# Regenerar token
python3 scripts/generate_token.py --user-id "xxx" --role admin

# O desde frontend, refrescar sesión
await supabase.auth.refreshSession()
```

### Error: "Not authenticated"

**Causa:** No estás enviando el token o el formato es incorrecto.

**Solución:**
```bash
# Verificar formato correcto
# ✅ CORRECTO:
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# ❌ INCORRECTO:
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9... (espacios extra)
Authorization: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9... (falta "Bearer ")
```

### No puedo obtener token desde Supabase

**Verificar:**
1. ¿Estás logueado en el frontend?
2. ¿Supabase está configurado correctamente?
3. ¿Las variables de entorno están bien?

```javascript
// Debug en consola del navegador
const { data: { session } } = await supabase.auth.getSession()
console.log('Session:', session)
console.log('Token:', session?.access_token)
```

---

## 📚 Resumen Rápido

### Para Desarrollo/Testing:
```bash
python3 scripts/generate_token.py --user-id "xxx" --role admin
```

### Para Producción:
```javascript
// En el frontend
const { data: { session } } = await supabase.auth.getSession()
const token = session?.access_token
```

### Usar el Token:
```bash
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/events
```

---

## 💡 Tips

1. **Guardar token en variable**: `export TOKEN="..."` para reutilizarlo
2. **Token de Supabase**: Se renueva automáticamente, no necesitas hacer nada
3. **Token de prueba**: Expira según `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` (default: 30 min)
4. **Ver token en Network tab**: DevTools → Network → Headers → Authorization

