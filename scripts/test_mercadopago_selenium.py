#!/usr/bin/env python3
"""
Script de prueba automatizada de Mercado Pago usando Selenium
Este script simula un navegador real y prueba el flujo completo del checkout
"""

import os
import sys
import time
import json
import requests
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
API_BASE = f"{BACKEND_URL}/api/v1"
EVENT_ID = os.getenv("EVENT_ID", "4fb47f6c-83a3-4494-aecc-9947863c031c")
SCREENSHOT_DIR = "screenshots"
WAIT_TIMEOUT = 30

# Tarjeta de prueba de Mercado Pago (Chile - CLP)
TEST_CARD = {
    "number": "4168 8188 4444 7115",
    "cvv": "123",
    "expiry_month": "12",
    "expiry_year": "25",
    "cardholder_name": "APRO",
    "email": "test@test.com"
}

def setup_driver(headless=False, use_brave=False):
    """Configurar el driver de Selenium"""
    chrome_options = Options()
    
    if headless:
        chrome_options.add_argument("--headless")
    
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # Desactivar notificaciones
    prefs = {
        "profile.default_content_setting_values.notifications": 2,
        "profile.default_content_settings.popups": 0
    }
    chrome_options.add_experimental_option("prefs", prefs)
    
    # Configurar para Brave si se solicita
    if use_brave:
        brave_paths = [
            "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",  # macOS estándar
            "/usr/bin/brave-browser",  # Linux
            "C:\\Program Files\\BraveSoftware\\Brave-Browser\\Application\\brave.exe",  # Windows
        ]
        
        brave_path = None
        for path in brave_paths:
            if os.path.exists(path):
                brave_path = path
                break
        
        if brave_path:
            chrome_options.binary_location = brave_path
            print(f"✅ Usando Brave desde: {brave_path}")
        else:
            print("⚠️  Brave no encontrado en ubicaciones estándar")
            print("   Intentando usar ChromeDriver con Brave...")
            print("   Si falla, verifica la ruta de Brave e instala ChromeDriver")
    
    try:
        # Intentar usar ChromeDriver del sistema (funciona con Brave también)
        driver = webdriver.Chrome(options=chrome_options)
        driver.maximize_window()
        return driver
    except Exception as e:
        print(f"❌ Error configurando navegador: {e}")
        print("\n💡 Soluciones:")
        if use_brave:
            print("   1. Verifica que Brave esté instalado")
            print("   2. Instala ChromeDriver (Brave usa Chromium):")
            print("      brew install chromedriver  # macOS")
            print("   3. Verifica que ChromeDriver esté en el PATH:")
            print("      which chromedriver")
            print("      chromedriver --version")
        else:
            print("   1. Instala ChromeDriver:")
            print("      brew install chromedriver  # macOS")
            print("      O descarga desde: https://chromedriver.chromium.org/")
            print("\n   2. Verifica que Chrome esté instalado")
            print("\n   3. Si ChromeDriver está instalado, verifica que esté en el PATH:")
            print("      which chromedriver")
            print("      chromedriver --version")
        sys.exit(1)

def create_purchase():
    """Crear una compra y obtener el payment_link"""
    print("📦 Creando compra...")
    
    payload = {
        "event_id": EVENT_ID,
        "attendees": [
            {
                "name": "Test User",
                "email": TEST_CARD["email"],
                "document_type": "RUT",
                "is_child": False
            }
        ],
        "selected_services": {},
        "payment_method": "mercadopago"
    }
    
    try:
        response = requests.post(
            f"{API_BASE}/purchases",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        response.raise_for_status()
        
        data = response.json()
        order_id = data.get("order_id")
        payment_link = data.get("payment_link")
        
        if not payment_link or payment_link == "null":
            print(f"❌ Error: payment_link es null")
            print(f"   Respuesta: {data}")
            return None, None
        
        print(f"✅ Compra creada")
        print(f"   Order ID: {order_id}")
        print(f"   Payment Link: {payment_link}")
        return order_id, payment_link
        
    except Exception as e:
        print(f"❌ Error creando compra: {e}")
        return None, None

def take_screenshot(driver, name):
    """Tomar screenshot"""
    if not os.path.exists(SCREENSHOT_DIR):
        os.makedirs(SCREENSHOT_DIR)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{SCREENSHOT_DIR}/{name}_{timestamp}.png"
    driver.save_screenshot(filename)
    print(f"   📸 Screenshot guardado: {filename}")
    return filename

def get_console_errors(driver):
    """Obtener errores de la consola del navegador"""
    logs = driver.get_log('browser')
    errors = [log for log in logs if log['level'] == 'SEVERE']
    return errors

def test_payment_link(payment_link, headless=False, use_brave=False):
    """Probar el payment_link con Selenium"""
    browser_name = "Brave" if use_brave else "Chrome"
    print(f"\n🌐 Abriendo payment_link en {browser_name}...")
    print(f"   {payment_link}")
    
    driver = None
    try:
        driver = setup_driver(headless=headless, use_brave=use_brave)
        driver.get(payment_link)
        
        # Esperar a que la página cargue
        print("⏳ Esperando a que cargue el checkout...")
        time.sleep(5)
        
        # Tomar screenshot inicial
        take_screenshot(driver, "01_checkout_loaded")
        
        # Obtener errores de consola
        console_errors = get_console_errors(driver)
        if console_errors:
            print(f"⚠️  Errores en consola del navegador:")
            for error in console_errors[:5]:  # Mostrar solo los primeros 5
                print(f"   - {error.get('message', 'N/A')}")
        else:
            print("✅ No hay errores en la consola")
        
        # Verificar que estamos en la página de Mercado Pago
        current_url = driver.current_url
        print(f"📍 URL actual: {current_url}")
        
        if "mercadopago" not in current_url.lower():
            print(f"⚠️  Advertencia: No estamos en la página de Mercado Pago")
        
        # Intentar encontrar el formulario de pago
        print("\n🔍 Buscando formulario de pago...")
        
        # Mercado Pago puede usar diferentes selectores
        # Intentar varios selectores comunes
        form_found = False
        selectors_to_try = [
            ("iframe", "id", "cardNumber"),
            ("iframe", "name", "cardNumber"),
            ("input", "id", "cardNumber"),
            ("input", "name", "cardNumber"),
            ("input", "placeholder", "Número de tarjeta"),
            ("div", "class", "card-form"),
            ("form", "id", "cardForm"),
        ]
        
        for selector_type, attr, value in selectors_to_try:
            try:
                if selector_type == "iframe":
                    iframe = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, f"iframe[{attr}='{value}']"))
                    )
                    print(f"✅ Encontrado iframe: {attr}='{value}'")
                    form_found = True
                    break
                else:
                    element = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, f"{selector_type}[{attr}='{value}']"))
                    )
                    print(f"✅ Encontrado elemento: {selector_type}[{attr}='{value}']")
                    form_found = True
                    break
            except TimeoutException:
                continue
        
        if not form_found:
            print("⚠️  No se pudo encontrar el formulario de pago automáticamente")
            print("   Esto puede ser normal si Mercado Pago usa un iframe dinámico")
            take_screenshot(driver, "02_form_not_found")
        
        # Esperar un poco más para que cargue completamente
        time.sleep(3)
        take_screenshot(driver, "03_page_loaded")
        
        # Obtener el título de la página
        page_title = driver.title
        print(f"📄 Título de la página: {page_title}")
        
        # Obtener el HTML de la página (limitado)
        page_source_length = len(driver.page_source)
        print(f"📊 Tamaño del HTML: {page_source_length} caracteres")
        
        # Verificar si hay mensajes de error visibles
        error_selectors = [
            "div.error",
            "div.alert-danger",
            "span.error",
            "[class*='error']",
            "[id*='error']"
        ]
        
        errors_found = []
        for selector in error_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    text = element.text.strip()
                    if text and text not in errors_found:
                        errors_found.append(text)
            except:
                continue
        
        if errors_found:
            print(f"⚠️  Errores visibles en la página:")
            for error in errors_found:
                print(f"   - {error}")
        else:
            print("✅ No hay errores visibles en la página")
        
        print("\n✅ Prueba completada")
        print("\n📝 Resumen:")
        print(f"   - URL: {current_url}")
        print(f"   - Título: {page_title}")
        print(f"   - Errores de consola: {len(console_errors)}")
        print(f"   - Errores visibles: {len(errors_found)}")
        print(f"   - Formulario encontrado: {form_found}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error durante la prueba: {e}")
        import traceback
        traceback.print_exc()
        
        if driver:
            take_screenshot(driver, "error")
        
        return False
        
    finally:
        if driver:
            print("\n🔄 Cerrando navegador...")
            driver.quit()

def main():
    """Función principal"""
    print("=" * 60)
    print("🧪 Prueba Automatizada de Mercado Pago con Selenium")
    print("=" * 60)
    print()
    
    # Parsear argumentos
    payment_link = None
    headless = False
    use_brave = False
    
    for arg in sys.argv[1:]:
        if arg in ["--brave", "-b"]:
            use_brave = True
        elif arg in ["--headless", "-h"]:
            headless = True
        elif arg.startswith("http"):
            payment_link = arg
        elif not arg.startswith("-"):
            # Si no es una opción, podría ser un payment_link
            payment_link = arg
    
    # Si no se proporcionó payment_link, crear uno nuevo
    if not payment_link:
        print("📋 Creando nueva compra...")
        order_id, payment_link = create_purchase()
        if not payment_link:
            print("❌ No se pudo obtener payment_link")
            sys.exit(1)
    else:
        print(f"📋 Usando payment_link proporcionado: {payment_link}")
    
    if use_brave:
        print("🦁 Usando Brave Browser")
    else:
        print("🌐 Usando Chrome")
    
    if headless:
        print("👻 Ejecutando en modo headless")
    else:
        print("👀 Ejecutando con navegador visible")
    
    print()
    
    # Ejecutar la prueba
    success = test_payment_link(payment_link, headless=headless, use_brave=use_brave)
    
    if success:
        print("\n✅ Prueba completada exitosamente")
        print(f"📸 Screenshots guardados en: {SCREENSHOT_DIR}/")
        sys.exit(0)
    else:
        print("\n❌ La prueba falló")
        print(f"📸 Revisa los screenshots en: {SCREENSHOT_DIR}/")
        sys.exit(1)

if __name__ == "__main__":
    main()

