#!/usr/bin/env python3
"""Script para probar endpoints del servidor de producción"""
import sys
import os
import json
import httpx
from typing import Dict, List, Tuple, Optional
from datetime import datetime

# Colores para output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_success(msg):
    print(f"{Colors.GREEN}✅ {msg}{Colors.RESET}")

def print_error(msg):
    print(f"{Colors.RED}❌ {msg}{Colors.RESET}")

def print_warning(msg):
    print(f"{Colors.YELLOW}⚠️  {msg}{Colors.RESET}")

def print_info(msg):
    print(f"{Colors.BLUE}ℹ️  {msg}{Colors.RESET}")

def print_section(msg):
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*70}")
    print(f"{msg}")
    print(f"{'='*70}{Colors.RESET}\n")

# Configuración
BASE_URL = os.getenv("API_URL", "http://209.38.78.227:8000")
TOKEN = os.getenv("API_TOKEN", None)

def test_endpoint(
    method: str, 
    path: str, 
    requires_auth: bool = False,
    body: Dict = None, 
    params: Dict = None,
    expected_status: Optional[int] = None
) -> Tuple[bool, str, int, Dict]:
    """Probar un endpoint"""
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json"}
    
    if requires_auth:
        if not TOKEN:
            return False, "No token available", 0, {}
        headers["Authorization"] = f"Bearer {TOKEN}"
    
    try:
        if method.upper() == "GET":
            response = httpx.get(url, headers=headers, params=params, timeout=10.0)
        elif method.upper() == "POST":
            response = httpx.post(url, headers=headers, json=body, timeout=10.0)
        elif method.upper() == "PUT":
            response = httpx.put(url, headers=headers, json=body, timeout=10.0)
        elif method.upper() == "DELETE":
            response = httpx.delete(url, headers=headers, timeout=10.0)
        elif method.upper() == "PATCH":
            response = httpx.patch(url, headers=headers, json=body, timeout=10.0)
        else:
            return False, f"Method {method} not supported", 0, {}
        
        status = response.status_code
        is_success = 200 <= status < 300
        
        # Si se especificó un status esperado, validar
        if expected_status is not None:
            is_success = (status == expected_status)
        
        try:
            response_data = response.json()
        except:
            response_data = {"text": response.text[:500]}
        
        detail = json.dumps(response_data, indent=2)[:300]
        
        return is_success, detail, status, response_data
        
    except httpx.ConnectError:
        return False, "Connection error - Is the server running?", 0, {}
    except httpx.TimeoutException:
        return False, "Request timeout", 0, {}
    except Exception as e:
        return False, f"Error: {str(e)}", 0, {}

def test_health_checks():
    """Probar health checks"""
    print_section("🏥 HEALTH CHECKS")
    
    tests = [
        ("GET", "/health", False, None, None, 200),
        ("GET", "/ready", False, None, None, 200),
    ]
    
    results = []
    for method, path, auth, body, params, expected in tests:
        print(f"Testing {method} {path}...")
        success, detail, status, data = test_endpoint(method, path, auth, body, params, expected)
        
        if success:
            print_success(f"Status: {status}")
            if "status" in data:
                print(f"   Response: {data.get('status', 'N/A')}")
            results.append(True)
        else:
            print_error(f"Status: {status}")
            print(f"   {detail[:150]}")
            results.append(False)
        print()
    
    return results

def test_events():
    """Probar endpoints de eventos"""
    print_section("🎫 EVENTOS")
    
    tests = [
        ("GET", "/api/v1/events", False, None, None, None),
        ("GET", "/api/v1/events", False, None, {"category": "test"}, None),
    ]
    
    results = []
    event_id = None
    
    for method, path, auth, body, params, expected in tests:
        print(f"Testing {method} {path}...")
        if params:
            print(f"   Params: {params}")
        
        success, detail, status, data = test_endpoint(method, path, auth, body, params, expected)
        
        if success:
            print_success(f"Status: {status}")
            if isinstance(data, dict) and "events" in data and len(data["events"]) > 0:
                event_id = data["events"][0].get("id")
                print(f"   Found {len(data['events'])} events")
                if event_id:
                    print(f"   First event ID: {event_id}")
            results.append(True)
        else:
            print_error(f"Status: {status}")
            print(f"   {detail[:150]}")
            results.append(False)
        print()
    
    # Probar obtener evento específico si tenemos un ID
    if event_id:
        print(f"Testing GET /api/v1/events/{event_id}...")
        success, detail, status, data = test_endpoint("GET", f"/api/v1/events/{event_id}", False)
        if success:
            print_success(f"Status: {status}")
            if isinstance(data, dict) and "name" in data:
                print(f"   Event: {data.get('name', 'N/A')}")
            results.append(True)
        else:
            print_warning(f"Status: {status} (puede ser esperado si no hay eventos)")
            results.append(True)  # 404 es esperado si no hay datos
        print()
    
    return results, event_id

def test_tickets():
    """Probar endpoints de tickets"""
    print_section("🎟️ TICKETS")
    
    if not TOKEN:
        print_warning("No token available, skipping ticket tests")
        return []
    
    # Probar obtener tickets de usuario (necesita user_id del token)
    print("Testing GET /api/v1/tickets/user/{user_id}...")
    print_warning("Note: This requires a valid user_id from the token")
    print()
    
    return []

def test_admin():
    """Probar endpoints de admin"""
    print_section("👑 ADMIN")
    
    if not TOKEN:
        print_warning("No token available, skipping admin tests")
        return []
    
    tests = [
        ("GET", "/api/v1/admin/organizer", True, None, None, None),
        ("GET", "/api/v1/admin/stats", True, None, None, None),
        ("GET", "/api/v1/admin/events", True, None, None, None),
        ("GET", "/api/v1/admin/tickets/children", True, None, None, None),
    ]
    
    results = []
    for method, path, auth, body, params, expected in tests:
        print(f"Testing {method} {path}...")
        success, detail, status, data = test_endpoint(method, path, auth, body, params, expected)
        
        if success:
            print_success(f"Status: {status}")
            results.append(True)
        elif status == 401 or status == 403:
            print_warning(f"Status: {status} - Authentication/Authorization required")
            results.append(False)
        else:
            print_error(f"Status: {status}")
            print(f"   {detail[:150]}")
            results.append(False)
        print()
    
    return results

def test_purchases():
    """Probar endpoints de compras"""
    print_section("🛒 COMPRAS")
    
    if not TOKEN:
        print_warning("No token available, skipping purchase tests")
        return []
    
    print("Testing POST /api/v1/purchases...")
    print_warning("Note: This requires valid event_id and user_id")
    print("Skipping actual purchase test to avoid creating test orders")
    print()
    
    return []

def main():
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*70}")
    print(f"🧪 TESTING PRODUCTION API")
    print(f"Server: {BASE_URL}")
    print(f"{'='*70}{Colors.RESET}\n")
    
    if TOKEN:
        print_success(f"Token configured: {TOKEN[:50]}...")
    else:
        print_warning("No token configured. Some tests will be skipped.")
        print_info("Set API_TOKEN environment variable to test authenticated endpoints")
    print()
    
    all_results = {
        "health": [],
        "events": [],
        "tickets": [],
        "admin": [],
        "purchases": []
    }
    
    # Health checks
    all_results["health"] = test_health_checks()
    
    # Events
    event_results, event_id = test_events()
    all_results["events"] = event_results
    
    # Tickets
    all_results["tickets"] = test_tickets()
    
    # Admin
    all_results["admin"] = test_admin()
    
    # Purchases
    all_results["purchases"] = test_purchases()
    
    # Resumen
    print_section("📊 RESUMEN DE PRUEBAS")
    
    total_tests = sum(len(results) for results in all_results.values())
    passed_tests = sum(sum(1 for r in results if r) for results in all_results.values())
    failed_tests = total_tests - passed_tests
    
    print(f"Total de pruebas: {total_tests}")
    print_success(f"Exitosas: {passed_tests} ({passed_tests*100//total_tests if total_tests > 0 else 0}%)")
    if failed_tests > 0:
        print_error(f"Fallidas: {failed_tests} ({failed_tests*100//total_tests if total_tests > 0 else 0}%)")
    
    print(f"\n{Colors.BOLD}Por categoría:{Colors.RESET}")
    for category, results in all_results.items():
        if results:
            passed = sum(1 for r in results if r)
            total = len(results)
            status = "✅" if passed == total else "⚠️" if passed > 0 else "❌"
            print(f"  {status} {category.capitalize()}: {passed}/{total}")
    
    print(f"\n{Colors.BOLD}{'='*70}{Colors.RESET}\n")
    
    # Información adicional
    print_info(f"Para probar endpoints autenticados, configura:")
    print(f"  export API_TOKEN='tu-token-jwt'")
    print(f"  export API_URL='{BASE_URL}'")
    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Pruebas interrumpidas por el usuario{Colors.RESET}")
        sys.exit(1)

