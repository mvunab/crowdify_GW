# Guía de Configuración - Variables de Entorno

## Variables que ya tienes (Frontend)

Ya tienes estas variables del frontend:
- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_ANON_KEY`

## Variables necesarias para el Backend

### 1. Base de Datos (PostgreSQL)

**Opción A: Usar PostgreSQL de Supabase (Recomendado para empezar)**

En el dashboard de Supabase:
1. Ve a **Settings** → **Database**
2. Busca **Connection string** → **URI**
3. Copia la URL que tiene este formato:
   ```
   postgresql://postgres:[PASSWORD]@db.olyicxwxyxwtiandtbcg.supabase.co:5432/postgres
   ```

**Opción B: PostgreSQL local (con Docker Compose)**

Si usas `docker-compose.yml`, PostgreSQL se crea automáticamente:
```env
DATABASE_URL=postgresql://crodify:crodify@postgres:5432/crodify
```

**Para obtener la contraseña de Supabase:**
1. Ve a **Settings** → **Database**
2. Busca **Database password** o haz clic en **Reset database password**
3. La contraseña se muestra solo una vez, guárdala bien

---

### 2. Redis

**Opción A: Redis local (con Docker Compose)**

Si usas `docker-compose.yml`, Redis se crea automáticamente:
```env
REDIS_URL=redis://redis:6379/0
REDIS_PASSWORD=
```

**Opción B: Redis de Supabase (si está disponible)**

Algunos proyectos de Supabase tienen Redis. Revisa en **Settings** → **Add-ons**

---

### 3. JWT Secret Key

**Genera una clave secreta aleatoria:**

```bash
# En Linux/Mac
openssl rand -hex 32

# En Windows (PowerShell)
[System.Web.Security.Membership]::GeneratePassword(32, 0)

# O usa Python
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Usa el resultado como:
```env
JWT_SECRET_KEY=tu-clave-generada-aqui
```

⚠️ **IMPORTANTE**: Cambia esto en producción por una clave segura y aleatoria.

---

### 4. Supabase Service Key (Para migración)

**Para leer/escribir desde el backend durante la migración:**

1. Ve a **Settings** → **API**
2. Busca **service_role key** (NO la anon key)
3. Es una clave secreta que tiene permisos completos
4. **NUNCA la expongas en el frontend**

```env
SUPABASE_URL=https://olyicxwxyxwtiandtbcg.supabase.co
SUPABASE_ANON_KEY=tu-anon-key-aqui
SUPABASE_SERVICE_KEY=tu-service-role-key-aqui
```

---

### 5. Mercado Pago (Para pagos)

**Paso a paso:**

1. **Crear cuenta:**
   - Ve a https://www.mercadopago.com.ar
   - Crea una cuenta o inicia sesión

2. **Crear aplicación:**
   - Ve a https://www.mercadopago.com.ar/developers/panel
   - Click en **"Crear nueva aplicación"**
   - Completa el formulario
   - Selecciona **"Integración de pagos"**

3. **Obtener Access Token:**
   - En la aplicación creada, busca **"Credenciales de producción"** o **"Credenciales de prueba"**
   - Para desarrollo, usa las **Credenciales de prueba**
   - Copia el **Access Token**

```env
MERCADOPAGO_ACCESS_TOKEN=APP_USR-1234567890-abcdefghijklmnopqrstuvwxyz1234567890
MERCADOPAGO_WEBHOOK_SECRET=tu-webhook-secret-si-lo-configuras
```

**Para desarrollo**, puedes dejar estos vacíos temporalmente y el sistema fallará gracefully.

---

### 6. SendGrid (Para emails)

**Paso a paso:**

1. **Crear cuenta:**
   - Ve a https://signup.sendgrid.com/
   - Crea una cuenta gratuita (permite 100 emails/día)

2. **Verificar dominio (opcional):**
   - Para producción necesitas verificar tu dominio
   - Para desarrollo puedes usar el email de verificación

3. **Crear API Key:**
   - Ve a **Settings** → **API Keys**
   - Click en **"Create API Key"**
   - Dale un nombre (ej: "Crodify Backend")
   - Selecciona **"Full Access"** o **"Restricted Access"** (solo Mail Send)
   - Copia el API Key (solo se muestra una vez)

```env
EMAIL_PROVIDER=sendgrid
EMAIL_API_KEY=SG.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
EMAIL_FROM=noreply@crodify.com  # O tu email verificado
```

**Alternativas gratuitas:**
- **Mailgun**: 5000 emails/mes gratis
- **Mailtrap**: Solo para desarrollo (testing)
- **SMTP local**: Para desarrollo local con MailHog (incluido en docker-compose)

---

## Archivo .env Completo (Ejemplo)

Crea `backend/.env` con esto:

```env
# Database - Usa la connection string de Supabase
DATABASE_URL=postgresql://postgres:TU_PASSWORD@db.olyicxwxyxwtiandtbcg.supabase.co:5432/postgres
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10

# Redis - Local con Docker
REDIS_URL=redis://redis:6379/0
REDIS_PASSWORD=

# Supabase (para migración)
SUPABASE_URL=https://olyicxwxyxwtiandtbcg.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9seWljeHd4eXh3dGlhbmR0YmNnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjE2NzAxMDMsImV4cCI6MjA3NzI0NjEwM30.TeteoABAf6Kf_ZGzo7PwwDXhqxXpAgFj2MPROl3aR94
SUPABASE_SERVICE_KEY=tu-service-role-key-aqui

# JWT - Genera una clave aleatoria
JWT_SECRET_KEY=tu-clave-secreta-generada-aqui
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Mercado Pago - Obtén de tu cuenta
MERCADOPAGO_ACCESS_TOKEN=tu-access-token-aqui
MERCADOPAGO_WEBHOOK_SECRET=

# Email - SendGrid
EMAIL_PROVIDER=sendgrid
EMAIL_API_KEY=tu-api-key-aqui
EMAIL_FROM=noreply@crodify.com

# CORS
CORS_ORIGINS=http://localhost:5173,https://crodify.vercel.app

# App
APP_ENV=development
APP_DEBUG=True
APP_BASE_URL=http://localhost:8000
LOG_LEVEL=INFO
```

---

## Configuración Mínima para Desarrollo

Si solo quieres probar el backend sin pagos ni emails:

```env
# Mínimo necesario
DATABASE_URL=postgresql://postgres:TU_PASSWORD@db.olyicxwxyxwtiandtbcg.supabase.co:5432/postgres
REDIS_URL=redis://redis:6379/0
JWT_SECRET_KEY=dev-secret-key-change-in-production
CORS_ORIGINS=http://localhost:5173
APP_ENV=development
APP_DEBUG=True

# Dejar vacíos (el sistema funcionará pero sin estas features)
MERCADOPAGO_ACCESS_TOKEN=
EMAIL_API_KEY=
```

---

## Verificación

Una vez configurado, verifica que todo funciona:

```bash
# 1. Iniciar servicios
docker-compose up -d

# 2. Verificar health
curl http://localhost:8000/health

# 3. Verificar conexiones
curl http://localhost:8000/ready

# 4. Ver documentación
# Abre http://localhost:8000/docs en tu navegador
```

---

## Prioridades

### 🔴 Crítico (necesario para funcionar):
1. ✅ DATABASE_URL
2. ✅ REDIS_URL (o usa local)
3. ✅ JWT_SECRET_KEY

### 🟡 Importante (para features completas):
4. ✅ MERCADOPAGO_ACCESS_TOKEN (para pagos)
5. ✅ EMAIL_API_KEY (para emails)

### 🟢 Opcional (para migración):
6. ✅ SUPABASE_SERVICE_KEY (solo si quieres leer/escribir a Supabase)

---

## Ayuda

Si tienes problemas:
1. Verifica que todas las variables estén en `backend/.env` (no en `.env.example`)
2. Reinicia los servicios: `docker-compose restart backend`
3. Revisa los logs: `docker-compose logs backend`

