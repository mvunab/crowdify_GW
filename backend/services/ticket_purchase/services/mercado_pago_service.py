"""Servicio de integración con Mercado Pago"""
import os
from typing import Dict, Optional
import mercadopago
from datetime import datetime, timedelta


class MercadoPagoService:
    """Servicio para manejar pagos con Mercado Pago"""
    
    def __init__(self):
        access_token = os.getenv("MERCADOPAGO_ACCESS_TOKEN")
        if not access_token:
            raise ValueError("MERCADOPAGO_ACCESS_TOKEN no configurado")
        
        self.sdk = mercadopago.SDK(access_token)
        self.webhook_secret = os.getenv("MERCADOPAGO_WEBHOOK_SECRET")
    
    def create_preference(
        self,
        order_id: str,
        title: str,
        total_amount: float,
        currency: str = "CLP",
        description: str = "",
        back_urls: Optional[Dict[str, str]] = None
    ) -> Dict:
        """
        Crear preferencia de pago en Mercado Pago
        
        Returns:
            dict con preference_id y init_point (payment_link)
        """
        # URLs de retorno
        if not back_urls:
            base_url = os.getenv("APP_BASE_URL", "http://localhost:5173")
            back_urls = {
                "success": f"{base_url}/purchase/success",
                "failure": f"{base_url}/purchase/failure",
                "pending": f"{base_url}/purchase/pending"
            }
        
        # Configurar preferencia
        preference_data = {
            "items": [
                {
                    "title": title,
                    "description": description,
                    "quantity": 1,
                    "currency_id": currency,
                    "unit_price": float(total_amount)
                }
            ],
            "back_urls": back_urls,
            "auto_return": "approved",
            "external_reference": order_id,
            "notification_url": f"{os.getenv('APP_BASE_URL', 'http://localhost:8000')}/api/v1/purchases/webhook",
            "statement_descriptor": "CRODIFY",
            "expires": True,
            "expiration_date_from": datetime.utcnow().isoformat(),
            "expiration_date_to": (datetime.utcnow() + timedelta(hours=24)).isoformat()
        }
        
        # Crear preferencia
        preference_response = self.sdk.preference().create(preference_data)
        
        if preference_response["status"] != 201:
            raise Exception(f"Error creando preferencia: {preference_response.get('message')}")
        
        preference = preference_response["response"]
        
        return {
            "preference_id": preference["id"],
            "payment_link": preference["init_point"],
            "sandbox_init_point": preference.get("sandbox_init_point")
        }
    
    def verify_payment(self, payment_id: str) -> Dict:
        """Verificar estado de un pago"""
        payment_response = self.sdk.payment().get(payment_id)
        
        if payment_response["status"] != 200:
            raise Exception(f"Error obteniendo pago: {payment_response.get('message')}")
        
        return payment_response["response"]
    
    def verify_webhook(self, data: Dict, signature: Optional[str] = None) -> bool:
        """
        Verificar webhook de Mercado Pago
        
        Nota: En producción, deberías validar la firma del webhook
        """
        # TODO: Implementar verificación de firma si es necesario
        return True

