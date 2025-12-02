"""Servicio de integración con Mercado Pago"""
import os
from typing import Dict, Optional
import mercadopago
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
        
        self.sdk = mercadopago.SDK(access_token)
        self.webhook_secret = settings.MERCADOPAGO_WEBHOOK_SECRET or os.getenv("MERCADOPAGO_WEBHOOK_SECRET")
        self.environment = settings.MERCADOPAGO_ENVIRONMENT or os.getenv("MERCADOPAGO_ENVIRONMENT", "sandbox")
        self.base_url = settings.APP_BASE_URL or os.getenv("APP_BASE_URL", "http://localhost:5173")
        # URL para webhooks: usar ngrok si está disponible, sino usar localhost
        self.webhook_base_url = settings.NGROK_URL or os.getenv("NGROK_URL") or self.base_url.replace(':5173', ':8000')
    
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
        if not back_urls:
            back_urls = {
                "success": f"{self.base_url}/compra-exitosa",
                "failure": f"{self.base_url}/compra-fallida",
                "pending": f"{self.base_url}/compra-pendiente"
            }
        
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
            "installments": 1,  # Número mínimo de cuotas
            "max_installments": 12  # Número máximo de cuotas
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
        
        # Solo agregar auto_return si las URLs son HTTPS (producción)
        # En desarrollo local (HTTP), no usar auto_return
        if self.base_url.startswith("https://"):
            preference_data["auto_return"] = "approved"
        
        # Crear preferencia
        preference_response = self.sdk.preference().create(preference_data)
        
        if preference_response["status"] != 201:
            error_message = preference_response.get('message', 'Error desconocido')
            error_response = preference_response.get('response', {})
            
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
        
        # En sandbox, usar sandbox_init_point si está disponible, sino init_point
        # En producción, usar init_point
        payment_link = None
        if self.environment == "sandbox":
            payment_link = preference.get("sandbox_init_point") or preference.get("init_point")
        else:
            payment_link = preference.get("init_point")
        
        if not payment_link:
            raise Exception("No se pudo obtener el link de pago de la preferencia")
        
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

