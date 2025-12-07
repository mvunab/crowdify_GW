# 🚀 Cómo Iniciar ngrok

## Paso 1: Verificar Instalación

```bash
ngrok version
```

Deberías ver: `ngrok version 3.34.0` (o similar)

## Paso 2: Iniciar ngrok

Abre una **nueva terminal** y ejecuta:

```bash
ngrok http 8000
```

**⚠️ IMPORTANTE:** Mantén esta terminal abierta mientras trabajas.

## Paso 3: Copiar la URL

Verás algo como:

```
Session Status                online
Account                       tu-email@example.com (Plan: Free)
Version                       3.34.0
Region                        United States (us)
Latency                       -
Web Interface                 http://127.0.0.1:4040
Forwarding                    https://abc123.ngrok-free.dev -> http://localhost:8000
```

**Copia la URL HTTPS** (ej: `https://abc123.ngrok-free.dev`)

## Paso 4: Actualizar .env

Abre `crowdify_GW/.env` y actualiza:

```env
NGROK_URL=https://abc123.ngrok-free.dev
```

**⚠️ NOTA:** Si la URL cambia (ngrok gratuito cambia la URL cada vez), actualiza el `.env` y reinicia el backend.

## Paso 5: Reiniciar Backend

```bash
cd crowdify_GW
docker-compose restart backend
```

## ✅ Verificar que Funciona

1. Abre en tu navegador: `https://tu-url-ngrok.ngrok-free.dev/api/health`
2. Deberías ver una respuesta del backend

## 🔍 Si Necesitas Autenticación

Si ngrok te pide autenticación:

1. Ve a: https://dashboard.ngrok.com/signup
2. Crea una cuenta gratuita
3. Obtén tu authtoken
4. Ejecuta: `ngrok config add-authtoken TU_TOKEN`

## 💡 Tips

- **Mantén ngrok corriendo:** No cierres la terminal mientras trabajas
- **URL cambia:** Cada vez que reinicias ngrok, la URL cambia (en plan gratuito)
- **URL fija:** Con ngrok Pro puedes tener una URL fija

