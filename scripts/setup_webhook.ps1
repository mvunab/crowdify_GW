# Script para configurar webhook de Mercado Pago
# Uso: .\scripts\setup_webhook.ps1

Write-Host "🔔 Configuración de Webhook de Mercado Pago" -ForegroundColor Cyan
Write-Host ""

# Verificar si ngrok está instalado
Write-Host "1️⃣ Verificando ngrok..." -ForegroundColor Yellow
$ngrokPath = Get-Command ngrok -ErrorAction SilentlyContinue

if (-not $ngrokPath) {
    Write-Host "   ❌ ngrok no está instalado" -ForegroundColor Red
    Write-Host ""
    Write-Host "   Opciones para instalar:" -ForegroundColor Yellow
    Write-Host "   a) Con Chocolatey: choco install ngrok" -ForegroundColor White
    Write-Host "   b) Descargar de: https://ngrok.com/download" -ForegroundColor White
    Write-Host ""
    
    $install = Read-Host "¿Quieres instalar ngrok ahora? (s/n)"
    if ($install -eq "s" -or $install -eq "S") {
        $hasChoco = Get-Command choco -ErrorAction SilentlyContinue
        if ($hasChoco) {
            Write-Host "   Instalando ngrok con Chocolatey..." -ForegroundColor Yellow
            choco install ngrok -y
        } else {
            Write-Host "   Chocolatey no está instalado." -ForegroundColor Red
            Write-Host "   Por favor, descarga ngrok manualmente de: https://ngrok.com/download" -ForegroundColor Yellow
            Write-Host "   Luego ejecuta este script nuevamente." -ForegroundColor Yellow
            exit 1
        }
    } else {
        Write-Host "   Por favor, instala ngrok y ejecuta este script nuevamente." -ForegroundColor Yellow
        exit 1
    }
} else {
    Write-Host "   ✅ ngrok está instalado" -ForegroundColor Green
}

Write-Host ""
Write-Host "2️⃣ Iniciando ngrok en puerto 8000..." -ForegroundColor Yellow
Write-Host "   ⚠️  IMPORTANTE: Mantén esta ventana abierta" -ForegroundColor Yellow
Write-Host "   Presiona Ctrl+C para detener ngrok cuando termines" -ForegroundColor Yellow
Write-Host ""

# Verificar si el puerto 8000 está en uso
$portInUse = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if (-not $portInUse) {
    Write-Host "   ⚠️  El puerto 8000 no está en uso." -ForegroundColor Yellow
    Write-Host "   Asegúrate de que el backend esté corriendo:" -ForegroundColor Yellow
    Write-Host "   docker-compose up -d backend" -ForegroundColor White
    Write-Host ""
}

# Iniciar ngrok en una nueva ventana
Write-Host "   Iniciando ngrok..." -ForegroundColor Yellow
Start-Process ngrok -ArgumentList "http 8000" -WindowStyle Normal

Write-Host ""
Write-Host "3️⃣ Espera 3 segundos para que ngrok inicie..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

# Intentar obtener la URL de ngrok
Write-Host ""
Write-Host "4️⃣ Obteniendo URL de ngrok..." -ForegroundColor Yellow
try {
    $ngrokResponse = Invoke-RestMethod -Uri "http://localhost:4040/api/tunnels" -ErrorAction Stop
    $ngrokUrl = $ngrokResponse.tunnels[0].public_url
    
    if ($ngrokUrl -match "https://") {
        $webhookUrl = "$ngrokUrl/api/v1/purchases/webhook"
        Write-Host "   ✅ URL de ngrok: $ngrokUrl" -ForegroundColor Green
        Write-Host "   ✅ URL del webhook: $webhookUrl" -ForegroundColor Green
        Write-Host ""
        
        # Copiar al portapapeles
        $webhookUrl | Set-Clipboard
        Write-Host "   📋 URL copiada al portapapeles!" -ForegroundColor Cyan
        Write-Host ""
        
        Write-Host "5️⃣ Siguiente paso:" -ForegroundColor Yellow
        Write-Host "   Ve a: https://www.mercadopago.com/developers/panel/app" -ForegroundColor White
        Write-Host "   1. Selecciona tu aplicación" -ForegroundColor White
        Write-Host "   2. Ve a Webhooks > Configurar notificaciones" -ForegroundColor White
        Write-Host "   3. Pega esta URL: $webhookUrl" -ForegroundColor Cyan
        Write-Host "   4. Selecciona evento: Order (Mercado Pago)" -ForegroundColor White
        Write-Host "   5. Guarda y copia el Webhook Secret" -ForegroundColor White
        Write-Host ""
        
        Write-Host "6️⃣ Después de obtener el Webhook Secret:" -ForegroundColor Yellow
        Write-Host "   Agrégalo a tu archivo .env:" -ForegroundColor White
        Write-Host "   MERCADOPAGO_WEBHOOK_SECRET=tu-secret-aqui" -ForegroundColor Cyan
        Write-Host ""
        
        Write-Host "7️⃣ Reinicia el backend:" -ForegroundColor Yellow
        Write-Host "   docker-compose restart backend" -ForegroundColor White
        Write-Host ""
        
    } else {
        Write-Host "   ⚠️  No se pudo obtener la URL HTTPS de ngrok" -ForegroundColor Yellow
        Write-Host "   Verifica manualmente en: http://localhost:4040" -ForegroundColor White
    }
} catch {
    Write-Host "   ⚠️  No se pudo conectar a la API de ngrok" -ForegroundColor Yellow
    Write-Host "   Verifica que ngrok esté corriendo en: http://localhost:4040" -ForegroundColor White
    Write-Host "   La URL del webhook será: https://TU-URL-NGROK.ngrok.io/api/v1/purchases/webhook" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "✅ Script completado. Mantén ngrok corriendo mientras trabajas." -ForegroundColor Green


