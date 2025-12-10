# 🚀 Resend - Inicio Rápido

## ✅ Estado Actual

- ✅ Resend instalado correctamente
- ✅ API Key configurada
- ⚠️ **RESEND_FROM_EMAIL necesita corrección**

## 🔧 Corrección Necesaria

En tu archivo `.env` del backend, asegúrate de tener:

```env
RESEND_API_KEY=re_PF5tV5xd_PVRsETbW1NgBLTFNxnXVnu9y
RESEND_FROM_EMAIL=onboarding@resend.dev
```

**Importante:** 
- Para **desarrollo/pruebas**: usa `onboarding@resend.dev` (email de prueba de Resend)
- Para **producción**: usa tu dominio verificado (ej: `tickets@tudominio.com`)

## 📝 Pasos para Corregir

1. **Edita tu `.env`** en `C:\Users\Andres\Documents\MATIAS PROJECTS\crowdify_GW\.env`

2. **Asegúrate de tener**:
   ```env
   RESEND_FROM_EMAIL=onboarding@resend.dev
   ```

3. **Reinicia el contenedor backend**:
   ```bash
   docker-compose restart backend
   ```

4. **Prueba de nuevo**:
   ```bash
   docker-compose exec backend python scripts/test_resend_docker.py
   ```

## 🧪 Probar Envío de Email

Una vez corregido, puedes probar:

### Opción 1: Script de prueba
```bash
docker-compose exec backend python scripts/test_resend_docker.py
```

### Opción 2: Endpoint de prueba (requiere admin)
```bash
POST http://localhost:8000/api/v1/notifications/test-email?to_email=tu-email@example.com
```

### Opción 3: Realizar una compra
- Completa una compra de tickets
- Los emails se enviarán automáticamente cuando se generen los tickets

## 📊 Ver Emails Enviados

- **Dashboard de Resend**: https://resend.com/emails
- Verás todos los emails enviados con su estado (enviado, entregado, rebotado)

## 🎯 Próximos Pasos

1. ✅ Corregir `RESEND_FROM_EMAIL` a `onboarding@resend.dev`
2. ✅ Reiniciar backend
3. ✅ Probar envío
4. ✅ Verificar en dashboard de Resend

## 📚 Más Información

- [Documentación completa de Resend](./RESEND_SETUP.md)
- [Dashboard de Resend](https://resend.com/emails)

