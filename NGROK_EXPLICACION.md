# 🔍 ¿Para qué sirve ngrok y cuándo lo necesitas?

## ❓ ¿Qué es ngrok?

**ngrok** es una herramienta que expone tu servidor local (localhost) a internet con HTTPS.

### Ejemplo:
```
Sin ngrok:
  Tu backend: http://localhost:8000  ← Solo accesible desde tu computadora
  Mercado Pago: ❌ No puede enviar webhooks aquí

Con ngrok:
  Tu backend: http://localhost:8000
  ngrok crea: https://abc123.ngrok.io → http://localhost:8000
  Mercado Pago: ✅ Puede enviar webhooks a https://abc123.ngrok.io
```

---

## ✅ ¿Cuándo SÍ necesitas ngrok?

### Escenario 1: Desarrollo Local
- Tu backend está en `localhost:8000` (solo accesible desde tu máquina)
- Mercado Pago necesita enviar webhooks desde internet
- **Solución:** Usa ngrok para exponer tu localhost

### Escenario 2: Testing de Webhooks
- Quieres probar webhooks sin desplegar a producción
- **Solución:** Usa ngrok temporalmente

---

## ❌ ¿Cuándo NO necesitas ngrok?

### Escenario 1: Producción con URL Pública
- Tu backend está en `https://api.tudominio.com` (accesible desde internet)
- **Solución:** Configura directamente la URL de producción en Mercado Pago

### Escenario 2: Backend en la Nube
- Tu backend está en Digital Ocean, AWS, etc. con URL pública
- **Solución:** No necesitas ngrok, usa la URL pública directamente

---

## 🔍 ¿Cómo saber si lo necesitas?

### Pregúntate:
1. **¿Dónde está corriendo tu backend?**
   - ✅ `localhost:8000` → **SÍ necesitas ngrok** (si quieres webhooks)
   - ✅ `https://api.tudominio.com` → **NO necesitas ngrok**

2. **¿Mercado Pago puede alcanzar tu backend desde internet?**
   - Prueba: Abre `https://tu-backend-url.com/api/v1/purchases/webhook` en tu navegador
   - Si NO se abre → Necesitas ngrok o una URL pública

---

## 🛠️ Configuración Actual en tu Código

Tu código ya está preparado para ambos casos:

```python
# Si tienes NGROK_URL configurado, lo usa
# Si no, usa localhost:8000 (pero Mercado Pago no podrá alcanzarlo)
self.webhook_base_url = settings.NGROK_URL or os.getenv("NGROK_URL") or self.base_url.replace(':5173', ':8000')
```

### Opción 1: Desarrollo Local (con ngrok)
```env
NGROK_URL=https://abc123.ngrok.io
```

### Opción 2: Producción (sin ngrok)
```env
# No configures NGROK_URL
# En su lugar, configura APP_BASE_URL con tu URL de producción
APP_BASE_URL=https://api.tudominio.com
```

---

## 💡 Recomendación

### Si estás en desarrollo local:
1. **Instala ngrok** (solo una vez):
   ```bash
   # macOS
   brew install ngrok
   
   # O descarga de: https://ngrok.com/download
   ```

2. **Inicia ngrok** (cada vez que trabajes):
   ```bash
   ngrok http 8000
   ```

3. **Copia la URL HTTPS** que te da (ej: `https://abc123.ngrok.io`)

4. **Agrega al .env**:
   ```env
   NGROK_URL=https://abc123.ngrok.io
   ```

5. **Reinicia el backend**

### Si estás en producción:
- **NO uses ngrok**
- Configura directamente la URL de producción en Mercado Pago
- Ejemplo: `https://api.tudominio.com/api/v1/purchases/webhook`

---

## ⚠️ Importante

- **ngrok gratuito:** La URL cambia cada vez que reinicias ngrok
- **ngrok Pro:** Puedes tener una URL fija (requiere cuenta de pago)
- **Solo para desarrollo:** En producción, usa siempre una URL real

---

## 🎯 Resumen

| Situación | ¿Necesitas ngrok? |
|-----------|-------------------|
| Backend en `localhost:8000` | ✅ SÍ (para webhooks) |
| Backend en `https://api.tudominio.com` | ❌ NO |
| Backend en Digital Ocean/AWS con URL pública | ❌ NO |
| Solo probando localmente | ✅ SÍ (temporalmente) |

**En tu caso:** Si estás desarrollando localmente y quieres recibir webhooks, **SÍ necesitas ngrok**.

