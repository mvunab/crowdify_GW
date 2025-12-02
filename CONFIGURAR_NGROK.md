# 🔧 Configurar ngrok - Paso a Paso

## ⚠️ ngrok Requiere Autenticación

Las versiones recientes de ngrok requieren una cuenta gratuita y un authtoken.

## 📋 Pasos para Configurar ngrok

### Paso 1: Crear Cuenta en ngrok (Gratis)

1. Ve a: **https://dashboard.ngrok.com/signup**
2. Crea una cuenta (es gratis)
3. Puedes usar tu email o cuenta de Google/GitHub

### Paso 2: Obtener tu Authtoken

1. Después de crear la cuenta, ve a: **https://dashboard.ngrok.com/get-started/your-authtoken**
2. Copia tu **authtoken** (es una cadena larga de caracteres)

### Paso 3: Configurar el Authtoken

Abre una terminal y ejecuta:

```bash
ngrok config add-authtoken TU_AUTHTOKEN_AQUI
```

Reemplaza `TU_AUTHTOKEN_AQUI` con el token que copiaste.

**Ejemplo:**
```bash
ngrok config add-authtoken 2abc123def456ghi789jkl012mno345pqr678
```

### Paso 4: Iniciar ngrok

Una vez configurado el authtoken, puedes iniciar ngrok:

```bash
ngrok http 8000
```

Verás algo como:
```
Forwarding   https://abc123.ngrok.io -> http://localhost:8000
```

### Paso 5: Copiar la URL

Copia la URL HTTPS que aparece (ej: `https://abc123.ngrok.io`)

### Paso 6: Usar en Mercado Pago

En el panel de Mercado Pago, configura:

```
URL para prueba: https://TU-URL-NGROK.ngrok.io/api/v1/purchases/webhook
```

## ✅ Resumen Rápido

1. Crear cuenta: https://dashboard.ngrok.com/signup
2. Obtener authtoken: https://dashboard.ngrok.com/get-started/your-authtoken
3. Configurar: `ngrok config add-authtoken TU_TOKEN`
4. Iniciar: `ngrok http 8000`
5. Copiar URL y usar en Mercado Pago

## 💡 Nota

- La cuenta gratuita de ngrok es suficiente para desarrollo
- La URL cambia cada vez que reinicias ngrok (gratis)
- Si necesitas una URL fija, necesitas ngrok Pro (de pago)


