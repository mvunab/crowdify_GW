# 🔑 Cómo Obtener Bearer Token para Probar el Backend

## Opción 1: Generar Token de Prueba (Desarrollo) ⚡

### Usando el script incluido:

```bash
# Generar token para usuario normal
python3 scripts/generate_token.py --user-id "123e4567-e89b-12d3-a456-426614174000" --email "usuario@example.com" --role user

# Generar token para admin
python3 scripts/generate_token.py --user-id "123e4567-e89b-12d3-a456-426614174000" --email "admin@example.com" --role admin

# Generar token para scanner
python3 scripts/generate_token.py --user-id "123e4567-e89b-12d3-a456-426614174000" --email "scanner@example.com" --role scanner

# Generar token para coordinator
python3 scripts/generate_token.py --user-id "123e4567-e89b-12d3-a456-426614174000" --email "coordinator@example.com" --role coordinator
```

### O usando Poetry:

```bash
# Si estás usando Docker
docker compose exec backend poetry run python scripts/generate_token.py --user-id "123e4567-e89b-12d3-a456-426614174000" --role admin

# Si estás en desarrollo local
poetry run python scripts/generate_token.py --user-id "123e4567-e89b-12d3-a456-426614174000" --role admin
```

### El script te dará algo como:

```
Token generado:
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjNlNDU2Ny1lODliLTEyZDMtYTQ1Ni00MjY2MTQxNzQwMDAiLCJ1c2VyX2lkIjoiMTIzZTQ1NjctZTg5Yi0xMmQzLWE0NTYtNDI2NjE0MTc0MDAwIiwiZW1haWwiOiJhZG1pbkBleGFtcGxlLmNvbSIsInJvbGUiOiJhZG1pbiIsImlhdCI6MTcwMDAwMDAwMH0.xxxxx

Para usar en curl:
curl -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." http://localhost:8000/api/v1/events
```

---

## Opción 2: Usar Token de Supabase (Producción/Real) 🔐

Si tu frontend usa Supabase Auth, puedes obtener el token directamente desde el frontend:

### En el navegador (JavaScript):

```javascript
// Obtener token de Supabase
const { data: { session } } = await supabase.auth.getSession()
const token = session?.access_token

// Usar en fetch
fetch('http://localhost:8000/api/v1/events', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
})
```

### Desde la consola del navegador:

1. Abre tu aplicación frontend
2. Abre DevTools (F12)
3. En la consola, ejecuta:
```javascript
// Si usas Supabase
const { data: { session } } = await supabase.auth.getSession()
console.log('Token:', session?.access_token)
```

---

## 🧪 Probar con el Token

### Usando curl:

```bash
# 1. Obtener token (copia el token generado)
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# 2. Probar endpoint de eventos
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/events

# 3. Probar endpoint de health (no requiere token)
curl http://localhost:8000/health

# 4. Probar endpoint ready (no requiere token)
curl http://localhost:8000/ready
```

### Usando Postman/Insomnia:

1. **Method**: GET (o POST según el endpoint)
2. **URL**: `http://localhost:8000/api/v1/events`
3. **Headers**:
   - Key: `Authorization`
   - Value: `Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`

### Usando httpie:

```bash
http GET http://localhost:8000/api/v1/events Authorization:"Bearer $TOKEN"
```

### Usando Python (requests):

```python
import requests

token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

headers = {
    "Authorization": f"Bearer {token}"
}

response = requests.get("http://localhost:8000/api/v1/events", headers=headers)
print(response.json())
```

---

## 📋 Endpoints que Requieren Token

### ✅ Requieren Autenticación (cualquier rol):
- `POST /api/v1/purchases` - Crear compra
- `GET /api/v1/tickets/user/{user_id}` - Ver tickets del usuario
- `GET /api/v1/tickets/{ticket_id}` - Ver ticket específico

### 🔒 Requieren Rol Admin:
- `POST /api/v1/events` - Crear evento
- `PUT /api/v1/events/{event_id}` - Actualizar evento
- `DELETE /api/v1/events/{event_id}` - Eliminar evento
- `GET /api/v1/admin/*` - Todos los endpoints de admin

### 📱 Requieren Rol Scanner:
- `POST /api/v1/tickets/validate` - Validar ticket QR

### 🌐 Públicos (no requieren token):
- `GET /health` - Health check
- `GET /ready` - Ready check
- `GET /api/v1/events` - Listar eventos (público)
- `GET /api/v1/events/{event_id}` - Ver evento (público)

---

## 🔍 Verificar que el Token Funciona

```bash
# 1. Verificar health (debe funcionar sin token)
curl http://localhost:8000/health
# Respuesta esperada: {"status":"ok","service":"crodify-api"}

# 2. Verificar ready (debe funcionar sin token)
curl http://localhost:8000/ready
# Respuesta esperada: {"status":"ready","database":"connected","redis":"connected"}

# 3. Probar endpoint público
curl http://localhost:8000/api/v1/events
# Debe devolver lista de eventos (puede estar vacía)

# 4. Probar endpoint protegido CON token
TOKEN="tu_token_aqui"
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/tickets/user/123e4567-e89b-12d3-a456-426614174000

# 5. Probar endpoint protegido SIN token (debe fallar)
curl http://localhost:8000/api/v1/tickets/user/123e4567-e89b-12d3-a456-426614174000
# Respuesta esperada: {"detail":"Not authenticated"}
```

---

## ⚙️ Configuración del Token

El token usa el `JWT_SECRET` definido en tu `.env`:

```env
JWT_SECRET=dev-secret  # Por defecto en desarrollo
```

**⚠️ IMPORTANTE**: En producción, cambia este valor por uno seguro:

```bash
# Generar secret seguro
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## 🐛 Troubleshooting

### Error: "Token inválido o expirado"
- Verifica que el token no haya expirado (tokens duran 30 minutos por defecto)
- Verifica que el `JWT_SECRET` en `.env` coincida con el usado para generar el token
- Regenera el token

### Error: "Se requieren permisos de administrador"
- Genera un token con `--role admin`
- Verifica que el token tenga el rol correcto

### Error: "Not authenticated"
- Verifica que estés enviando el header `Authorization: Bearer <token>`
- Verifica que no haya espacios extra en el token
- Verifica que el backend esté corriendo

---

## 📝 Ejemplo Completo

```bash
# 1. Generar token de admin
python3 scripts/generate_token.py \
  --user-id "550e8400-e29b-41d4-a716-446655440000" \
  --email "admin@test.com" \
  --role admin

# 2. Copiar el token generado
export TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# 3. Probar crear un evento
curl -X POST http://localhost:8000/api/v1/events \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Evento de Prueba",
    "location_text": "Santiago, Chile",
    "starts_at": "2024-12-31T20:00:00Z",
    "ends_at": "2025-01-01T02:00:00Z",
    "capacity_total": 100
  }'
```

---

## 💡 Tip: Guardar Token en Variable

```bash
# En tu terminal, guarda el token en una variable
export TOKEN=$(python3 scripts/generate_token.py --user-id "123e4567-e89b-12d3-a456-426614174000" --role admin | grep -A 1 "Token generado" | tail -1)

# Ahora puedes usarlo fácilmente
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/events
```

