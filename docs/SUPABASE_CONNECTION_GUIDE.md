# Guía de Conexión a Supabase - Sin Pagar

## ✅ Solución Gratuita: Session Pooler

Supabase ofrece **3 tipos de conexión**:

### 1. **Connection Pooler** (Puerto 5432) - ⚠️ Problemas
- ❌ Puede tener restricciones de schema
- ❌ No siempre compatible con todas las operaciones
- ✅ Gratuito pero limitado

### 2. **Session Pooler** (Puerto 6543) - ✅ RECOMENDADO
- ✅ Compatible con IPv4 (gratis)
- ✅ Funciona mejor con SQLAlchemy
- ✅ Sin restricciones de schema
- ✅ **GRATUITO** - No necesitas pagar

### 3. **Direct Connection** (Puerto 5432)
- ✅ Funciona perfecto
- ❌ Requiere IPv6 o IPv4 add-on (pago)
- ❌ No compatible con IPv4 sin pagar

## 🔧 Configuración Recomendada

**Usa Session Pooler (puerto 6543):**

```env
DATABASE_URL=postgresql://postgres.olyicxwxyxwtiandtbcg:Kdc154515@aws-1-us-east-2.pooler.supabase.com:6543/postgres
```

**Cambio clave:** Solo cambia el puerto de `5432` a `6543`

## 📋 Pasos para Actualizar

1. **Edita `backend/.env`:**
   ```env
   # Cambia de:
   DATABASE_URL=postgresql://postgres.olyicxwxyxwtiandtbcg:Kdc154515@aws-1-us-east-2.pooler.supabase.com:5432/postgres
   
   # A:
   DATABASE_URL=postgresql://postgres.olyicxwxyxwtiandtbcg:Kdc154515@aws-1-us-east-2.pooler.supabase.com:6543/postgres
   ```

2. **Reinicia el contenedor:**
   ```bash
   docker restart backend-backend-1
   ```

3. **Prueba:**
   ```bash
   curl http://localhost:8000/api/v1/events?limit=5
   ```

## 🔍 Diferencia entre Poolers

| Característica | Connection Pooler (5432) | Session Pooler (6543) |
|----------------|--------------------------|----------------------|
| Compatibilidad | Limitada | Excelente |
| IPv4 | ✅ Sí | ✅ Sí |
| Schema restrictions | ⚠️ A veces | ✅ No |
| Recomendado para ORMs | ❌ No | ✅ Sí |
| Costo | Gratis | Gratis |

## 💡 Por qué Session Pooler es mejor

- **Session-based**: Mantiene el contexto de la sesión (schemas, variables, etc.)
- **Mejor para ORMs**: SQLAlchemy funciona mejor con este tipo de pooler
- **Sin restricciones**: Puede acceder a todas las tablas sin problemas
- **Gratuito**: No necesitas pagar nada

## 🚫 Cuándo necesitarías pagar

Solo necesitarías pagar el **IPv4 add-on** si:
- Quieres usar la conexión directa (puerto 5432, sin pooler)
- Tu red solo soporta IPv4
- Pero **NO es necesario** - Session Pooler es suficiente y gratis

