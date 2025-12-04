# Prueba Automatizada de Mercado Pago con Selenium

Este script automatiza la prueba del checkout de Mercado Pago usando Selenium, simulando un navegador real.

## 🎯 ¿Por qué usar Selenium?

- ✅ **Simula un navegador real**: Detecta errores que solo aparecen en el navegador
- ✅ **Captura screenshots**: Guarda imágenes de cada paso para debugging
- ✅ **Detecta errores de consola**: Identifica errores JavaScript que no se ven a simple vista
- ✅ **Automatiza el flujo completo**: Desde crear la compra hasta abrir el checkout
- ✅ **Reproducible**: Puedes ejecutar la misma prueba múltiples veces

## 📋 Requisitos

### 1. Instalar dependencias

```bash
pip install selenium requests python-dotenv
```

O si estás usando el contenedor Docker:

```bash
docker compose exec backend pip install selenium requests
```

### 2. Instalar ChromeDriver

**macOS:**
```bash
brew install chromedriver
```

**Linux:**
```bash
# Descargar desde https://chromedriver.chromium.org/
# O usar el gestor de paquetes de tu distribución
```

**Windows:**
- Descargar desde https://chromedriver.chromium.org/
- Agregar al PATH

## 🚀 Uso

### Opción 1: Crear compra automáticamente y probar

```bash
cd /Users/matiasvargasmarin/Desktop/crowdify/crowdify_GW
python3 scripts/test_mercadopago_selenium.py
```

### Opción 2: Probar un payment_link específico

```bash
python3 scripts/test_mercadopago_selenium.py "https://sandbox.mercadopago.cl/checkout/v1/redirect?pref_id=..."
```

### Opción 3: Modo headless (sin ventana del navegador)

```bash
python3 scripts/test_mercadopago_selenium.py --headless
```

## 📸 Screenshots

Los screenshots se guardan en la carpeta `screenshots/`:

- `01_checkout_loaded.png` - Página inicial del checkout
- `02_form_not_found.png` - Si no se encuentra el formulario
- `03_page_loaded.png` - Página completamente cargada
- `error.png` - Si ocurre un error

## 🔍 Qué detecta el script

1. **Errores de consola del navegador**: Errores JavaScript que aparecen en la consola
2. **Errores visibles en la página**: Mensajes de error que el usuario puede ver
3. **Formulario de pago**: Verifica que el formulario esté presente
4. **URL correcta**: Confirma que estamos en la página de Mercado Pago
5. **Tiempo de carga**: Mide cuánto tarda en cargar la página

## 📊 Ejemplo de salida

```
🧪 Prueba Automatizada de Mercado Pago con Selenium
============================================================

📦 Creando compra...
✅ Compra creada
   Order ID: feb7c0ed-11c5-444d-8a20-8265c936beae
   Payment Link: https://sandbox.mercadopago.cl/checkout/v1/redirect?pref_id=...

🌐 Abriendo payment_link en navegador...
⏳ Esperando a que cargue el checkout...
   📸 Screenshot guardado: screenshots/01_checkout_loaded_20251204_123456.png
✅ No hay errores en la consola
📍 URL actual: https://sandbox.mercadopago.cl/checkout/v1/redirect?pref_id=...

🔍 Buscando formulario de pago...
✅ Encontrado iframe: id='cardNumber'
   📸 Screenshot guardado: screenshots/03_page_loaded_20251204_123456.png
✅ No hay errores visibles en la página

✅ Prueba completada

📝 Resumen:
   - URL: https://sandbox.mercadopago.cl/checkout/v1/redirect?pref_id=...
   - Título: Mercado Pago - Checkout
   - Errores de consola: 0
   - Errores visibles: 0
   - Formulario encontrado: True
```

## ⚠️ Limitaciones

- **No completa el pago automáticamente**: El script solo verifica que el checkout carga correctamente. Completar el pago requiere interacción manual o configuración adicional de Selenium para manejar iframes de Mercado Pago.

- **ChromeDriver debe estar actualizado**: Asegúrate de tener una versión compatible de ChromeDriver con tu versión de Chrome.

- **Modo headless puede tener limitaciones**: Algunos sitios detectan el modo headless y pueden comportarse diferente.

## 🐛 Troubleshooting

### Error: "chromedriver not found"

```bash
# macOS
brew install chromedriver

# Verificar instalación
which chromedriver
chromedriver --version
```

### Error: "selenium not installed"

```bash
pip install selenium
```

### Error: "Connection refused" al crear compra

Verifica que el backend esté corriendo:

```bash
docker compose ps
docker compose logs backend
```

### El navegador se abre pero no carga la página

- Verifica tu conexión a internet
- Verifica que el payment_link sea válido
- Revisa los screenshots en `screenshots/`

## 🔄 Próximos pasos

Para automatizar completamente el pago (llenar tarjeta y completar), necesitarías:

1. Manejar iframes de Mercado Pago (el formulario de tarjeta está en un iframe)
2. Esperar a que los campos estén listos
3. Llenar los campos de forma segura
4. Manejar el CAPTCHA si aparece

Esto es más complejo y puede requerir configuración adicional.

---

**Última actualización:** 2025-12-04

