# Fix: Problema con conexión a Supabase

El pooler de Supabase puede tener restricciones. Prueba usar la conexión directa:

## Opción 1: Usar conexión directa (recomendado)

En `backend/.env`, cambia la DATABASE_URL de:
```
DATABASE_URL=postgresql://postgres.olyicxwxyxwtiandtbcg:Kdc154515@aws-1-us-east-2.pooler.supabase.com:5432/postgres
```

A la conexión directa (sin pooler):
```
DATABASE_URL=postgresql://postgres.olyicxwxyxwtiandtbcg:Kdc154515@aws-1-us-east-2.connect.supabase.com:5432/postgres
```

O si tienes la IP directa:
```
DATABASE_URL=postgresql://postgres.olyicxwxyxwtiandtbcg:Kdc154515@db.olyicxwxyxwtiandtbcg.supabase.co:5432/postgres
```

## Opción 2: Verificar permisos del pooler

El pooler puede tener restricciones de schema. Asegúrate de que:
1. El usuario tenga permisos en el schema `public`
2. El pooler esté configurado para usar el schema correcto

## Para obtener la conexión directa:

1. Ve a Supabase Dashboard → Settings → Database
2. Busca "Connection string" → "Direct connection" (no pooler)
3. Usa esa URL en lugar de la del pooler

