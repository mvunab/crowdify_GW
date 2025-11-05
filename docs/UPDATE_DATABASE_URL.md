# Actualizar DATABASE_URL

El pooler de Supabase puede tener restricciones. Cambia la URL en `backend/.env`:

## Cambio necesario:

**ANTES (pooler - puede tener problemas):**
```
DATABASE_URL=postgresql://postgres.olyicxwxyxwtiandtbcg:Kdc154515@aws-1-us-east-2.pooler.supabase.com:5432/postgres
```

**DESPUÉS (conexión directa - recomendado):**
```
DATABASE_URL=postgresql://postgres.olyicxwxyxwtiandtbcg:Kdc154515@aws-1-us-east-2.connect.supabase.com:5432/postgres
```

O si tienes la conexión directa en el dashboard:
```
DATABASE_URL=postgresql://postgres.olyicxwxyxwtiandtbcg:Kdc154515@db.olyicxwxyxwtiandtbcg.supabase.co:5432/postgres
```

## Para obtener la conexión directa:

1. Ve a Supabase Dashboard → Settings → Database
2. Busca "Connection string" 
3. Selecciona "Direct connection" (no "Connection pooling")
4. Copia la URL y reemplaza en `.env`

## Después del cambio:

```bash
docker restart backend-backend-1
```

Luego prueba:
```bash
curl http://localhost:8000/api/v1/events?limit=5
```

