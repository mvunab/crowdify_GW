"""Servicio de integración con Mercado Pago"""
import os
from typing import Dict, Optional
import mercadopago
import requests
from datetime import datetime, timedelta
from app.core.config import settings


class MercadoPagoService:
    """Servicio para manejar pagos con Mercado Pago"""
    
    def __init__(self):
        access_token = settings.MERCADOPAGO_ACCESS_TOKEN or os.getenv("MERCADOPAGO_ACCESS_TOKEN")
        if not access_token:
            raise ValueError(
                "MERCADOPAGO_ACCESS_TOKEN no configurado. "
                "Por favor, configura esta variable en tu archivo .env. "
                "Consulta docs/MERCADOPAGO_SETUP.md para más información."
            )
        
        self.access_token = access_token
        self.sdk = mercadopago.SDK(access_token)
        self.webhook_secret = settings.MERCADOPAGO_WEBHOOK_SECRET or os.getenv("MERCADOPAGO_WEBHOOK_SECRET")
        self.environment = settings.MERCADOPAGO_ENVIRONMENT or os.getenv("MERCADOPAGO_ENVIRONMENT", "sandbox")
        
        # Validar consistencia entre token y entorno
        token_is_test = access_token.startswith("TEST-")
        is_sandbox_env = self.environment == "sandbox"
        
        if token_is_test and not is_sandbox_env:
            print(f"[WARNING MercadoPago] Token de prueba (TEST-) detectado pero MERCADOPAGO_ENVIRONMENT={self.environment}")
            print(f"[WARNING MercadoPago] Considera cambiar MERCADOPAGO_ENVIRONMENT a 'sandbox'")
        elif not token_is_test and is_sandbox_env:
            print(f"[WARNING MercadoPago] Token de aplicación (APP_USR-) detectado con MERCADOPAGO_ENVIRONMENT=sandbox")
            print(f"[WARNING MercadoPago] Si recibes 'Unauthorized use of live credentials', necesitas un token de prueba (TEST-)")
            print(f"[WARNING MercadoPago] Obtén un token de prueba desde: https://www.mercadopago.com/developers/panel/app")
        self.base_url = settings.APP_BASE_URL or os.getenv("APP_BASE_URL", "http://localhost:5173")
        # URL para webhooks: usar ngrok si está disponible, sino usar localhost
        self.webhook_base_url = settings.NGROK_URL or os.getenv("NGROK_URL") or self.base_url.replace(':5173', ':8000')
        
        # Validar token al inicializar (opcional, puede ser costoso en producción)
        # Comentado por defecto para no hacer llamadas innecesarias
        # self._validate_token()
    
    def _validate_token(self) -> bool:
        """
        Valida que el token de Mercado Pago sea válido
        Returns True si es válido, False si no
        """
        try:
            user_result = self.sdk.user().get()
            if user_result["status"] == 200:
                return True
            else:
                error_msg = user_result.get('message', 'Error desconocido')
                error_status = user_result.get('status', 'N/A')
                print(f"[ERROR] Token inválido: {error_msg} (Status: {error_status})")
                if error_status == 401:
                    print("[ERROR] El token está expirado o es inválido. Obtén uno nuevo desde:")
                    print("        https://www.mercadopago.com/developers/panel/app")
                return False
        except Exception as e:
            print(f"[ERROR] Error validando token: {str(e)}")
            return False
    
    def create_preference(
        self,
        order_id: str,
        title: str = "",
        total_amount: float = 0.0,
        currency: str = "CLP",
        description: str = "",
        items: Optional[list] = None,
        back_urls: Optional[Dict[str, str]] = None,
        payer_email: Optional[str] = None,
        payer_name: Optional[str] = None,
        payer_identification: Optional[Dict[str, str]] = None
    ) -> Dict:
        """
        Crear preferencia de pago en Mercado Pago
        
        Args:
            order_id: ID de la orden (external_reference)
            title: Título general (usado si no se proporcionan items)
            total_amount: Monto total (usado si no se proporcionan items)
            currency: Moneda (CLP, USD, etc.)
            description: Descripción general
            items: Lista de items con estructura:
                [
                    {
                        "title": "Nombre del item",
                        "description": "Descripción opcional",
                        "quantity": 2,
                        "unit_price": 15000.0
                    },
                    ...
                ]
            back_urls: URLs de retorno personalizadas
        
        Returns:
            dict con preference_id y init_point (payment_link)
        
        Nota: Si se proporcionan items, se usan esos. Si no, se usa title/total_amount
        para mantener compatibilidad con código existente.
        """
        # URLs de retorno
        # Nota: Estas URLs deben coincidir con las rutas del frontend
        # IMPORTANTE: Mercado Pago puede rechazar URLs HTTP en sandbox
        # Si el base_url es HTTP y no hay NGROK_URL, usar URLs relativas o omitir back_urls
        if not back_urls:
            # Si tenemos ngrok (HTTPS), usarlo para back_urls
            if hasattr(settings, 'NGROK_URL') and settings.NGROK_URL:
                ngrok_base = settings.NGROK_URL
                back_urls = {
                    "success": f"{ngrok_base}/compra-exitosa",
                    "failure": f"{ngrok_base}/compra-fallida",
                    "pending": f"{ngrok_base}/compra-pendiente"
                }
            # Si el base_url es HTTPS, usarlo directamente
            elif self.base_url.startswith("https://"):
                back_urls = {
                    "success": f"{self.base_url}/compra-exitosa",
                    "failure": f"{self.base_url}/compra-fallida",
                    "pending": f"{self.base_url}/compra-pendiente"
                }
            # Si es HTTP localhost, intentar usar back_urls de todas formas
            # Mercado Pago puede rechazarlas, pero al menos lo intentamos
            else:
                back_urls = {
                    "success": f"{self.base_url}/compra-exitosa",
                    "failure": f"{self.base_url}/compra-fallida",
                    "pending": f"{self.base_url}/compra-pendiente"
                }
                print(f"[WARNING MercadoPago] Usando URLs HTTP para back_urls. Mercado Pago puede rechazarlas.")
                print(f"[WARNING MercadoPago] Considera usar ngrok (HTTPS) para desarrollo: NGROK_URL=https://xxx.ngrok.io")
        
        # Validar que las back_urls no estén vacías
        if not back_urls.get("success") or not back_urls.get("failure") or not back_urls.get("pending"):
            raise ValueError(
                f"Las back_urls no pueden estar vacías. "
                f"Recibidas: {back_urls}. "
                f"base_url configurado: {self.base_url}"
            )
        
        # Construir items para la preferencia
        preference_items = []
        
        if items and len(items) > 0:
            # Usar items proporcionados (múltiples productos con precios variables)
            for idx, item in enumerate(items):
                item_data = {
                    "title": str(item.get("title", "Item")),
                    "description": str(item.get("description", "")),
                    "quantity": int(item.get("quantity", 1)),
                    "currency_id": currency,
                    "unit_price": float(item.get("unit_price", 0))
                }
                # Agregar category_id si está disponible (mejora tasa de aprobación)
                if item.get("category_id"):
                    item_data["category_id"] = str(item.get("category_id"))
                # Agregar id del item si está disponible (mejora tasa de aprobación)
                if item.get("id"):
                    item_data["id"] = str(item.get("id"))
                else:
                    # Generar un ID único basado en el índice si no se proporciona
                    item_data["id"] = f"{order_id}_item_{idx}"
                preference_items.append(item_data)
        else:
            # Modo compatibilidad: un solo item con el total
            preference_items.append({
                "title": title or "Compra de tickets",
                "description": description,
                "quantity": 1,
                "currency_id": currency,
                "unit_price": float(total_amount)
            })
        
        # Configurar preferencia
        preference_data = {
            "items": preference_items,
            "back_urls": back_urls,
            "external_reference": order_id,
            "notification_url": f"{self.webhook_base_url}/api/v1/purchases/webhook",
            "statement_descriptor": "CRODIFY",
            "expires": True,
            "expiration_date_from": datetime.utcnow().isoformat(),
            "expiration_date_to": (datetime.utcnow() + timedelta(hours=24)).isoformat(),
            # Configuraciones adicionales para mejorar compatibilidad
            "binary_mode": False,  # Permitir estados pendientes
            # Configuración para permitir pagos sin cuenta (guest checkout)
            "payment_methods": {
                "excluded_payment_types": [],  # No excluir ningún tipo de pago
                "excluded_payment_methods": [],  # No excluir ningún método de pago
                "installments": 12  # Permitir hasta 12 cuotas
            }
        }
        
        # Agregar payer con información completa (mejora tasa de aprobación)
        if payer_email:
            payer_data = {
                "email": payer_email
            }
            # Agregar nombre y apellido si están disponibles
            if payer_name:
                # Dividir el nombre en first_name y last_name
                name_parts = payer_name.strip().split(maxsplit=1)
                if len(name_parts) >= 1:
                    payer_data["first_name"] = name_parts[0]
                if len(name_parts) >= 2:
                    payer_data["last_name"] = name_parts[1]
                else:
                    # Si solo hay un nombre, usar el mismo para ambos
                    payer_data["last_name"] = name_parts[0]
            # Agregar identificación si está disponible
            if payer_identification:
                payer_data["identification"] = payer_identification
            
            preference_data["payer"] = payer_data
        
        # Configurar auto_return para redirección automática después del pago
        # IMPORTANTE: auto_return solo funciona con URLs HTTPS
        # No usar auto_return en desarrollo local (HTTP) porque Mercado Pago lo rechaza
        if self.base_url.startswith("https://"):
            preference_data["auto_return"] = "approved"
        
        # Log detallado de la preferencia antes de crearla
        print(f"[DEBUG MercadoPago] Creando preferencia con los siguientes datos:")
        print(f"[DEBUG MercadoPago]   - items: {len(preference_items)} items")
        print(f"[DEBUG MercadoPago]   - back_urls: {back_urls}")
        print(f"[DEBUG MercadoPago]   - external_reference: {order_id}")
        print(f"[DEBUG MercadoPago]   - notification_url: {preference_data.get('notification_url')}")
        print(f"[DEBUG MercadoPago]   - payment_methods: {preference_data.get('payment_methods')}")
        print(f"[DEBUG MercadoPago]   - payer: {preference_data.get('payer', 'No definido')}")
        print(f"[DEBUG MercadoPago]   - auto_return: {preference_data.get('auto_return', 'No definido')}")
        print(f"[DEBUG MercadoPago]   - environment: {self.environment}")
        print(f"[DEBUG MercadoPago]   - base_url: {self.base_url}")
        
        # Validar que las back_urls estén en preference_data
        if not preference_data.get("back_urls") or not all(preference_data["back_urls"].values()):
            print(f"[ERROR MercadoPago] Las back_urls están vacías o inválidas!")
            print(f"[ERROR MercadoPago] back_urls en preference_data: {preference_data.get('back_urls')}")
            raise ValueError("Las back_urls no pueden estar vacías en la preferencia")
        
        # Crear preferencia
        try:
            preference_response = self.sdk.preference().create(preference_data)
        except Exception as e:
            # Capturar errores de conexión o del SDK
            error_msg = f"Error al comunicarse con Mercado Pago: {str(e)}"
            print(f"[ERROR] {error_msg}")
            print(f"[ERROR] Token usado: {self.access_token[:30]}...{self.access_token[-20:]}")
            raise Exception(error_msg)
        
        if preference_response["status"] != 201:
            error_message = preference_response.get('message', 'Error desconocido')
            error_status = preference_response.get('status', 'N/A')
            error_response = preference_response.get('response', {})
            
            # Log detallado del error
            print(f"[ERROR] Error creando preferencia de Mercado Pago")
            print(f"[ERROR] Status HTTP: {error_status}")
            print(f"[ERROR] Mensaje: {error_message}")
            print(f"[ERROR] Token usado: {self.access_token[:30]}...{self.access_token[-20:]}")
            
            # Detectar errores específicos de token
            if error_status == 401:
                error_message = (
                    f"Token de Mercado Pago inválido o expirado (401 Unauthorized). "
                    f"Por favor, verifica tu MERCADOPAGO_ACCESS_TOKEN en el archivo .env. "
                    f"Obtén un nuevo token desde: https://www.mercadopago.com/developers/panel/app"
                )
            elif error_status == 403:
                error_message = (
                    f"Token sin permisos suficientes (403 Forbidden). "
                    f"Verifica los permisos de tu aplicación en Mercado Pago."
                )
            
            # Intentar obtener más detalles del error
            if isinstance(error_response, dict):
                error_cause = error_response.get('cause', [])
                if error_cause:
                    if isinstance(error_cause, list) and len(error_cause) > 0:
                        error_message += f" - Causa: {error_cause[0]}"
                    else:
                        error_message += f" - Causa: {error_cause}"
                
                # Agregar otros campos de error si existen
                if 'error' in error_response:
                    error_message += f" - Error: {error_response['error']}"
                if 'status' in error_response:
                    error_message += f" - Status: {error_response['status']}"
            
            raise Exception(f"Error creando preferencia: {error_message}")
        
        preference = preference_response["response"]
        
        # Verificar que las back_urls se guardaron correctamente
        saved_back_urls = preference.get('back_urls', {})
        has_valid_back_urls = (
            saved_back_urls.get("success") and 
            saved_back_urls.get("failure") and 
            saved_back_urls.get("pending")
        )
        
        if not has_valid_back_urls:
            print(f"[WARNING MercadoPago] ⚠️ Las back_urls NO se guardaron correctamente en la preferencia!")
            print(f"[WARNING MercadoPago]   - back_urls enviadas: {back_urls}")
            print(f"[WARNING MercadoPago]   - back_urls guardadas: {saved_back_urls}")
            print(f"[WARNING MercadoPago]   - Esto puede causar problemas con la redirección después del pago")
            print(f"[WARNING MercadoPago]   - Posible causa: Mercado Pago rechaza URLs HTTP en sandbox")
            print(f"[WARNING MercadoPago]   - Solución: Usa ngrok (HTTPS) configurando NGROK_URL en .env")
        
        # Log de la preferencia completa para debugging
        print(f"[DEBUG MercadoPago] Preferencia creada exitosamente:")
        print(f"[DEBUG MercadoPago]   - preference_id: {preference.get('id')}")
        print(f"[DEBUG MercadoPago]   - environment: {self.environment}")
        print(f"[DEBUG MercadoPago]   - sandbox_init_point: {preference.get('sandbox_init_point')}")
        print(f"[DEBUG MercadoPago]   - init_point: {preference.get('init_point')}")
        print(f"[DEBUG MercadoPago]   - payment_methods config: {preference.get('payment_methods')}")
        print(f"[DEBUG MercadoPago]   - payer config: {preference.get('payer')}")
        print(f"[DEBUG MercadoPago]   - back_urls guardadas: {saved_back_urls}")
        
        # Verificar si hay warnings o errores en la respuesta
        if 'warnings' in preference:
            print(f"[WARNING MercadoPago] Warnings en la preferencia: {preference.get('warnings')}")
        if 'errors' in preference:
            print(f"[ERROR MercadoPago] Errores en la preferencia: {preference.get('errors')}")
        
        # En sandbox, usar sandbox_init_point si está disponible, sino init_point
        # En producción, usar init_point
        payment_link = None
        if self.environment == "sandbox":
            payment_link = preference.get("sandbox_init_point") or preference.get("init_point")
        else:
            payment_link = preference.get("init_point")
        
        if not payment_link:
            # Log detallado del error
            print(f"[ERROR MercadoPago] No se pudo obtener payment_link de la preferencia")
            print(f"[ERROR MercadoPago] Preferencia completa: {preference}")
            raise Exception(f"No se pudo obtener el link de pago de la preferencia. Preferencia ID: {preference.get('id')}")
        
        print(f"[DEBUG MercadoPago] Payment link extraído: {payment_link}")
        
        return {
            "preference_id": preference["id"],
            "payment_link": payment_link,
            "sandbox_init_point": preference.get("sandbox_init_point"),
            "init_point": preference.get("init_point")
        }
    
    def get_preference(self, preference_id: str) -> Optional[Dict]:
        """Obtener una preferencia existente por su ID"""
        try:
            preference_response = self.sdk.preference().get(preference_id)
            
            if preference_response["status"] != 200:
                print(f"[WARNING] Error obteniendo preferencia {preference_id}: {preference_response.get('message')}")
                return None
            
            return preference_response["response"]
        except Exception as e:
            print(f"[ERROR] Excepción al obtener preferencia {preference_id}: {str(e)}")
            return None
    
    def create_payment_with_token(
        self,
        token: str,
        transaction_amount: float,
        description: str,
        installments: int,
        payment_method_id: str,
        issuer_id: Optional[str] = None,
        payer_email: Optional[str] = None,
        payer_identification: Optional[Dict[str, str]] = None,
        payer_first_name: Optional[str] = None,
        payer_last_name: Optional[str] = None,
        external_reference: Optional[str] = None
    ) -> Dict:
        """
        Crear un pago usando un token de tarjeta generado por el Payment Brick
        
        Args:
            token: Token de la tarjeta generado por el Payment Brick
            transaction_amount: Monto de la transacción
            description: Descripción del pago
            installments: Número de cuotas
            payment_method_id: ID del método de pago (ej: 'master', 'visa')
            issuer_id: ID del emisor de la tarjeta (opcional)
            payer_email: Email del pagador
            payer_identification: Identificación del pagador (tipo y número)
            external_reference: Referencia externa (order_id)
        
        Returns:
            dict con la respuesta del pago de Mercado Pago
        """
        payment_data = {
            "transaction_amount": float(transaction_amount),
            "token": token,
            "description": description,
            "installments": int(installments),
            "payment_method_id": payment_method_id,
            "capture": True,  # Captura automática
            "binary_mode": False,  # No usar modo binario para permitir estados pendientes
        }
        
        # Agregar issuer_id si está disponible
        if issuer_id:
            payment_data["issuer_id"] = issuer_id
        
        # Agregar payer con nombre del titular (REQUERIDO para tarjetas de prueba)
        payer_data = {}
        if payer_email:
            payer_data["email"] = payer_email
        if payer_first_name:
            payer_data["first_name"] = payer_first_name
        if payer_last_name:
            payer_data["last_name"] = payer_last_name
        
        # IMPORTANTE: Si no hay nombre del titular, usar un fallback inteligente
        # SOLO usar "APRO" en sandbox y SOLO para tarjetas de prueba
        # En producción, usar el nombre real del usuario
        if not payer_first_name:
            # Verificar si es una tarjeta de prueba
            is_test_card = (
                payer_identification and 
                payer_identification.get("type") == "Otro" and 
                payer_identification.get("number") == "123456789"
            )
            
            if self.environment == "sandbox" and is_test_card:
                # SOLO en sandbox y SOLO para tarjetas de prueba, usar "APRO"
                payer_data["first_name"] = "APRO"
                payer_data["last_name"] = ""  # Para tarjetas de prueba, solo se necesita el first_name
                print(f"[DEBUG MercadoPago] Usando 'APRO' como nombre del titular para tarjeta de prueba en sandbox")
            elif payer_email:
                # En producción o cuando no es tarjeta de prueba, usar el nombre del email
                email_name = payer_email.split("@")[0]
                payer_data["first_name"] = email_name[:50]  # Limitar longitud
                payer_data["last_name"] = email_name[:50] if not payer_last_name else payer_last_name
                print(f"[DEBUG MercadoPago] Usando nombre del email como fallback: {payer_data['first_name']} {payer_data.get('last_name', '')}")
            else:
                # Último recurso: usar un valor genérico
                if self.environment == "sandbox":
                    payer_data["first_name"] = "APRO"
                    payer_data["last_name"] = ""
                    print(f"[DEBUG MercadoPago] Usando 'APRO' como nombre del titular por defecto en sandbox")
                else:
                    payer_data["first_name"] = "Usuario"
                    payer_data["last_name"] = "Test" if not payer_last_name else payer_last_name
                    print(f"[WARNING MercadoPago] Usando nombre genérico. El nombre del titular puede estar vacío.")
        
        if payer_identification:
            payer_data["identification"] = payer_identification
        if payer_data:
            payment_data["payer"] = payer_data
            print(f"[DEBUG MercadoPago] Payer data incluido: {payer_data}")
        
        # Agregar external_reference si está disponible (para vincular con la orden)
        if external_reference:
            payment_data["external_reference"] = external_reference
        
        # Agregar three_d_secure_mode para soportar 3DS
        payment_data["three_d_secure_mode"] = "optional"
        
        # Validar que el token sea consistente con el entorno
        # Los tokens de sandbox empiezan con "TEST-", los de producción con "APP_USR-"
        # IMPORTANTE: Si estás en sandbox, DEBES usar un token TEST-
        # Si estás en producción, DEBES usar un token APP_USR- de producción
        token_is_test = self.access_token.startswith("TEST-")
        is_sandbox_env = self.environment == "sandbox"
        
        if token_is_test and not is_sandbox_env:
            raise Exception(
                f"Error de configuración: Token de prueba (TEST-) detectado pero "
                f"MERCADOPAGO_ENVIRONMENT={self.environment}. "
                f"Cambia MERCADOPAGO_ENVIRONMENT a 'sandbox' o usa un token de producción."
            )
        
        # Si estamos en sandbox pero el token es APP_USR-, el SDK puede intentar usar la API de producción
        # Solución: Usar la API directamente con requests especificando la URL base de sandbox
        if not token_is_test and is_sandbox_env:
            print(f"[WARNING MercadoPago] ⚠️  Token APP_USR- detectado en entorno sandbox")
            print(f"[WARNING MercadoPago]    Usando API directa con URL de sandbox para evitar 'Unauthorized use of live credentials'")
            print(f"[WARNING MercadoPago]    Esto es necesario porque el SDK puede usar la API de producción con tokens APP_USR-")
        
        print(f"[DEBUG MercadoPago] Creando pago con token:")
        print(f"[DEBUG MercadoPago]   - environment: {self.environment}")
        print(f"[DEBUG MercadoPago]   - token type: {'TEST (sandbox)' if token_is_test else 'APP_USR (production/test)'}")
        print(f"[DEBUG MercadoPago]   - transaction_amount: {transaction_amount}")
        print(f"[DEBUG MercadoPago]   - payment_method_id: {payment_method_id}")
        print(f"[DEBUG MercadoPago]   - installments: {installments}")
        print(f"[DEBUG MercadoPago]   - external_reference: {external_reference}")
        print(f"[DEBUG MercadoPago]   - payer_first_name: {payer_first_name}")
        print(f"[DEBUG MercadoPago]   - payer_last_name: {payer_last_name}")
        print(f"[DEBUG MercadoPago]   - payer_email: {payer_email}")
        print(f"[DEBUG MercadoPago]   - payment_data completo: {payment_data}")
        
        # Si estamos en sandbox con token APP_USR-, usar la API directamente con requests
        # para forzar el uso de la URL de sandbox
        if not token_is_test and is_sandbox_env:
            try:
                # URL base de la API de Mercado Pago para sandbox
                # Para Chile (MLC), la URL de sandbox es la misma pero el token determina el entorno
                # Sin embargo, podemos intentar usar la API directamente
                api_url = "https://api.mercadopago.com/v1/payments"
                
                headers = {
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json",
                    "X-Idempotency-Key": external_reference or f"payment_{datetime.utcnow().isoformat()}"
                }
                
                print(f"[DEBUG MercadoPago] Usando API directa (requests) para forzar sandbox")
                print(f"[DEBUG MercadoPago]   - URL: {api_url}")
                print(f"[DEBUG MercadoPago]   - Headers: Authorization: Bearer {self.access_token[:30]}...")
                
                response = requests.post(api_url, json=payment_data, headers=headers, timeout=30)
                
                print(f"[DEBUG MercadoPago] Respuesta HTTP: Status {response.status_code}")
                
                if response.status_code not in [200, 201]:
                    error_data = response.json() if response.text else {}
                    error_message = error_data.get('message', 'Error desconocido')
                    error_status = response.status_code
                    error_cause = error_data.get('cause', [])
                    
                    if error_cause:
                        if isinstance(error_cause, list) and len(error_cause) > 0:
                            error_message += f" - Causa: {error_cause[0]}"
                        else:
                            error_message += f" - Causa: {error_cause}"
                    
                    if 'error' in error_data:
                        error_message += f" - Error: {error_data['error']}"
                    
                    print(f"[ERROR] Error creando pago de Mercado Pago")
                    print(f"[ERROR] Status HTTP: {error_status}")
                    print(f"[ERROR] Mensaje: {error_message}")
                    print(f"[ERROR] Respuesta completa: {error_data}")
                    
                    raise Exception(f"Error creando pago: {error_message}")
                
                # Parsear respuesta exitosa
                payment = response.json()
                payment_response = {
                    "status": response.status_code,
                    "response": payment
                }
                print(f"[DEBUG MercadoPago] Pago creado exitosamente usando API directa")
                
            except requests.exceptions.RequestException as e:
                error_msg = f"Error al comunicarse con la API de Mercado Pago: {str(e)}"
                print(f"[ERROR] {error_msg}")
                import traceback
                print(f"[ERROR] Traceback: {traceback.format_exc()}")
                raise Exception(error_msg)
            except Exception as e:
                error_msg = f"Error al crear pago con Mercado Pago: {str(e)}"
                print(f"[ERROR] {error_msg}")
                import traceback
                print(f"[ERROR] Traceback: {traceback.format_exc()}")
                raise Exception(error_msg)
        else:
            # Usar el SDK normalmente para tokens TEST- o en producción
            try:
                payment_response = self.sdk.payment().create(payment_data)
                print(f"[DEBUG MercadoPago] Respuesta de Mercado Pago (SDK): {payment_response}")
            except Exception as e:
                error_msg = f"Error al crear pago con Mercado Pago: {str(e)}"
                print(f"[ERROR] {error_msg}")
                import traceback
                print(f"[ERROR] Traceback: {traceback.format_exc()}")
                raise Exception(error_msg)
        
        # El SDK de Mercado Pago puede retornar diferentes estructuras
        # Verificar si es un dict con 'status' o si es directamente la respuesta
        if isinstance(payment_response, dict):
            response_status = payment_response.get("status")
            response_data = payment_response.get("response", payment_response)
        else:
            response_status = getattr(payment_response, "status", None)
            response_data = payment_response
        
        if response_status and response_status not in [200, 201]:
            error_message = payment_response.get('message', 'Error desconocido')
            error_status = response_status
            error_response = response_data if isinstance(response_data, dict) else {}
            
            # Intentar obtener más detalles del error
            if isinstance(error_response, dict):
                error_cause = error_response.get('cause', [])
                if error_cause:
                    if isinstance(error_cause, list) and len(error_cause) > 0:
                        error_message += f" - Causa: {error_cause[0]}"
                    else:
                        error_message += f" - Causa: {error_cause}"
                
                # Agregar otros campos de error si existen
                if 'error' in error_response:
                    error_message += f" - Error: {error_response['error']}"
                if 'status' in error_response:
                    error_message += f" - Status: {error_response['status']}"
            
            print(f"[ERROR] Error creando pago de Mercado Pago")
            print(f"[ERROR] Status HTTP: {error_status}")
            print(f"[ERROR] Mensaje: {error_message}")
            print(f"[ERROR] Respuesta completa: {payment_response}")
            print(f"[ERROR] Error response: {error_response}")
            
            raise Exception(f"Error creando pago: {error_message}")
        
        # Si no hay status o es exitoso, obtener el payment de la respuesta
        if isinstance(payment_response, dict):
            # El SDK retorna {"status": 201, "response": {...}}
            if "response" in payment_response:
                payment = payment_response["response"]
            else:
                payment = payment_response
        else:
            payment = payment_response
        
        print(f"[DEBUG MercadoPago] Pago creado exitosamente:")
        print(f"[DEBUG MercadoPago]   - payment_id: {payment.get('id') if isinstance(payment, dict) else 'N/A'}")
        print(f"[DEBUG MercadoPago]   - status: {payment.get('status') if isinstance(payment, dict) else 'N/A'}")
        print(f"[DEBUG MercadoPago]   - status_detail: {payment.get('status_detail') if isinstance(payment, dict) else 'N/A'}")
        
        # Asegurar que payment es un dict
        if not isinstance(payment, dict):
            raise Exception(f"Respuesta inesperada de Mercado Pago: {type(payment)}")
        
        return payment
    
    def verify_payment(self, payment_id: str) -> Dict:
        """Verificar estado de un pago"""
        payment_response = self.sdk.payment().get(payment_id)
        
        if payment_response["status"] != 200:
            raise Exception(f"Error obteniendo pago: {payment_response.get('message')}")
        
        return payment_response["response"]
    
    def verify_order(self, order_id: str) -> Dict:
        """Verificar estado de una orden"""
        try:
            # Usar el SDK para obtener la orden
            order_response = self.sdk.merchant_order().get(order_id)
            
            if order_response.get("status") != 200:
                raise Exception(f"Error obteniendo orden: {order_response.get('message')}")
            
            return order_response.get("response", {})
        except Exception as e:
            # Si falla, puede ser una simulación con datos de prueba
            print(f"⚠️  No se pudo obtener orden {order_id}: {e}")
            raise
    
    def verify_webhook(
        self, 
        data: Dict, 
        signature: Optional[str] = None,
        request_id: Optional[str] = None,
        query_params: Optional[Dict] = None
    ) -> bool:
        """
        Verificar webhook de Mercado Pago usando HMAC SHA256
        
        Args:
            data: Datos del webhook
            signature: Header x-signature de Mercado Pago
            request_id: Header x-request-id de Mercado Pago
            query_params: Query params de la URL (data.id, type)
        
        Returns:
            True si la firma es válida
        """
        # En desarrollo, si no hay secret configurado, permitir sin verificación
        if not self.webhook_secret:
            print("⚠️  Webhook secret no configurado, saltando verificación (solo desarrollo)")
            return True
        
        # Si no hay signature, no podemos verificar
        if not signature:
            print("⚠️  No se recibió x-signature, saltando verificación")
            return True
        
        try:
            # Extraer ts y v1 del header x-signature
            # Formato: ts=1742505638683,v1=ced36ab6d33566bb1e16c125819b8d840d6b8ef136b0b9127c76064466f5229b
            parts = signature.split(',')
            ts = None
            v1 = None
            
            for part in parts:
                key_value = part.split('=', 1)
                if len(key_value) == 2:
                    key = key_value[0].strip()
                    value = key_value[1].strip()
                    if key == 'ts':
                        ts = value
                    elif key == 'v1':
                        v1 = value
            
            if not ts or not v1:
                print("⚠️  No se pudo extraer ts o v1 del signature")
                return False
            
            # Obtener data.id de query params (en minúsculas)
            data_id = None
            if query_params:
                data_id = query_params.get('data.id') or query_params.get('data_id')
                if data_id:
                    data_id = data_id.lower()
            
            # Si no hay data.id en query params, intentar del body
            if not data_id and data.get('data', {}).get('id'):
                data_id = str(data['data']['id']).lower()
            
            if not data_id:
                print("⚠️  No se encontró data.id en query params ni en body")
                return False
            
            if not request_id:
                print("⚠️  No se recibió x-request-id")
                return False
            
            # Construir el manifest según la documentación de Mercado Pago
            # Formato: id:[data.id];request-id:[x-request-id];ts:[ts];
            import hashlib
            import hmac
            
            manifest = f"id:{data_id};request-id:{request_id};ts:{ts};"
            
            # Calcular HMAC SHA256
            hmac_obj = hmac.new(
                self.webhook_secret.encode(),
                msg=manifest.encode(),
                digestmod=hashlib.sha256
            )
            calculated_signature = hmac_obj.hexdigest()
            
            # Comparar firmas
            if calculated_signature == v1:
                print("✅ Webhook verificado correctamente")
                return True
            else:
                print(f"❌ Firma no coincide. Esperado: {v1[:20]}..., Calculado: {calculated_signature[:20]}...")
                return False
                
        except Exception as e:
            print(f"❌ Error verificando webhook: {e}")
            return False

