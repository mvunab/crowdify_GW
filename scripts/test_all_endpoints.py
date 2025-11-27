#!/usr/bin/env python3
"""Script para probar todos los endpoints de la API"""
import sys
import os
import json
import httpx
from typing import Dict, List, Tuple
from datetime import datetime

# Agregar directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_URL = "http://localhost:8000"
TOKEN = None

# Colores para output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
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

def get_token():
    """Obtener token de Supabase"""
    global TOKEN
    if TOKEN:
        return TOKEN
    
    email = os.getenv("TEST_EMAIL", "admin@demo.com")
    password = os.getenv("TEST_PASSWORD", "admin123")
    
    script_path = os.path.join(os.path.dirname(__file__), "get_supabase_token.py")
    import subprocess
    result = subprocess.run(
        ["python3", script_path, "--email", email, "--password", password],
        capture_output=True,
        text=True
    )
    
    for line in result.stdout.split('\n'):
        if line.startswith('eyJ'):  # Token JWT
            TOKEN = line.strip()
            return TOKEN
    
    print_error("No se pudo obtener token")
    return None

def test_endpoint(method: str, path: str, requires_auth: bool = True, 
                 body: Dict = None, params: Dict = None) -> Tuple[bool, str, int]:
    """Probar un endpoint"""
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json"}
    
    if requires_auth:
        token = get_token()
        if not token:
            return False, "No token available", 0
        headers["Authorization"] = f"Bearer {token}"
    
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
            return False, f"Method {method} not supported", 0
        
        status = response.status_code
        is_success = 200 <= status < 300
        
        try:
            response_data = response.json()
            detail = json.dumps(response_data, indent=2)[:200]  # Primeros 200 chars
        except:
            detail = response.text[:200]
        
        return is_success, detail, status
        
    except httpx.ConnectError:
        return False, "Connection error - Is the server running?", 0
    except httpx.TimeoutException:
        return False, "Request timeout", 0
    except Exception as e:
        return False, f"Error: {str(e)}", 0

def extract_endpoints_from_openapi(openapi_path: str) -> List[Dict]:
    """Extraer endpoints del openapi.json"""
    try:
        with open(openapi_path, 'r') as f:
            schema = json.load(f)
    except:
        # Intentar obtener desde la URL
        try:
            response = httpx.get(f"{BASE_URL}/openapi.json", timeout=5.0)
            schema = response.json()
        except:
            print_error("No se pudo obtener openapi.json")
            return []
    
    endpoints = []
    paths = schema.get("paths", {})
    
    for path, methods in paths.items():
        for method, details in methods.items():
            if method.lower() in ["get", "post", "put", "delete", "patch"]:
                security = details.get("security", [])
                requires_auth = len(security) > 0 and any("HTTPBearer" in s for s in security)
                
                endpoints.append({
                    "method": method.upper(),
                    "path": path,
                    "summary": details.get("summary", ""),
                    "requires_auth": requires_auth,
                    "operation_id": details.get("operationId", "")
                })
    
    return endpoints

def main():
    print(f"\n{Colors.BOLD}{'='*70}")
    print(f"🧪 TESTING ALL API ENDPOINTS")
    print(f"{'='*70}{Colors.RESET}\n")
    
    # Obtener token primero
    print_info("Obteniendo token de autenticación...")
    token = get_token()
    if not token:
        print_error("No se pudo obtener token. Abortando.")
        return
    print_success(f"Token obtenido: {token[:50]}...\n")
    
    # Obtener endpoints
    print_info("Obteniendo lista de endpoints desde OpenAPI...")
    openapi_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs", "openapi.json")
    endpoints = extract_endpoints_from_openapi(openapi_path)
    
    if not endpoints:
        print_error("No se encontraron endpoints")
        return
    
    print_success(f"Encontrados {len(endpoints)} endpoints\n")
    
    # Probar cada endpoint
    results = {
        "success": [],
        "failed": [],
        "skipped": []
    }
    
    print(f"{Colors.BOLD}Probando endpoints...{Colors.RESET}\n")
    
    for i, endpoint in enumerate(endpoints, 1):
        method = endpoint["method"]
        path = endpoint["path"]
        summary = endpoint["summary"]
        requires_auth = endpoint["requires_auth"]
        
        print(f"[{i}/{len(endpoints)}] {method} {path}")
        if summary:
            print(f"      {summary}")
        
        # Preparar body según el endpoint
        body = None
        params = None
        
        # Endpoints que necesitan datos específicos
        if "validate" in path.lower():
            body = {"qr_signature": "test-signature-123", "event_id": None}
        elif "purchases" in path and method == "POST":
            body = {
                "event_id": "00000000-0000-0000-0000-000000000001",
                "user_id": "00000000-0000-0000-0000-000000000002",
                "attendees": [{"name": "Test User", "email": "test@test.com", "is_child": False}]
            }
        elif "events" in path and method == "POST":
            body = {
                "name": "Test Event",
                "location_text": "Test Location",
                "starts_at": "2024-12-31T20:00:00Z",
                "ends_at": "2025-01-01T02:00:00Z",
                "capacity_total": 100
            }
        elif "tickets/user" in path:
            # Extraer user_id del path
            if "/user/" in path:
                parts = path.split("/user/")
                if len(parts) > 1:
                    user_id = parts[1].split("/")[0]
                    path = path.replace(user_id, "00000000-0000-0000-0000-000000000002")
        
        # Reemplazar IDs de ejemplo en paths
        if "{ticket_id}" in path:
            path = path.replace("{ticket_id}", "00000000-0000-0000-0000-000000000001")
        if "{event_id}" in path:
            path = path.replace("{event_id}", "00000000-0000-0000-0000-000000000001")
        if "{order_id}" in path:
            path = path.replace("{order_id}", "00000000-0000-0000-0000-000000000001")
        if "{user_id}" in path:
            path = path.replace("{user_id}", "00000000-0000-0000-0000-000000000002")
        if "{id}" in path and "admin" in path:
            path = path.replace("{id}", "00000000-0000-0000-0000-000000000001")
        
        # Probar endpoint
        success, detail, status = test_endpoint(method, path, requires_auth, body, params)
        
        if success:
            print_success(f"Status: {status}")
            results["success"].append(endpoint)
        elif status == 404:
            print_warning(f"Status: {status} - Endpoint existe pero recurso no encontrado (OK)")
            results["success"].append(endpoint)  # 404 es esperado si no hay datos
        elif status == 401 or status == 403:
            print_warning(f"Status: {status} - {detail[:100]}")
            results["failed"].append({**endpoint, "error": f"Auth error: {status}"})
        else:
            print_error(f"Status: {status}")
            if detail:
                print(f"      {detail[:150]}")
            results["failed"].append({**endpoint, "error": detail[:200], "status": status})
        
        print()
    
    # Resumen
    print(f"\n{Colors.BOLD}{'='*70}")
    print(f"📊 RESUMEN DE PRUEBAS")
    print(f"{'='*70}{Colors.RESET}\n")
    
    total = len(endpoints)
    success_count = len(results["success"])
    failed_count = len(results["failed"])
    
    print(f"Total endpoints: {total}")
    print_success(f"Exitosos: {success_count} ({success_count*100//total if total > 0 else 0}%)")
    if failed_count > 0:
        print_error(f"Fallidos: {failed_count} ({failed_count*100//total if total > 0 else 0}%)")
    
    if results["failed"]:
        print(f"\n{Colors.BOLD}Endpoints con problemas:{Colors.RESET}\n")
        for endpoint in results["failed"]:
            print(f"  {Colors.RED}❌{Colors.RESET} {endpoint['method']} {endpoint['path']}")
            if "error" in endpoint:
                print(f"      Error: {endpoint['error'][:100]}")
    
    print(f"\n{Colors.BOLD}{'='*70}{Colors.RESET}\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Pruebas interrumpidas por el usuario{Colors.RESET}")
        sys.exit(1)

