"""Servicio de integración con Payku - Async con httpx"""
import os
from typing import Dict, Optional
import httpx
from datetime import datetime
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class PaykuService:
    """Servicio para manejar pagos con Payku"""

    def __init__(self):
        self.token_publico = settings.PAYKU_TOKEN_PUBLICO or os.getenv("PAYKU_TOKEN_PUBLICO")
        self.token_privado = settings.PAYKU_TOKEN_PRIVADO or os.getenv("PAYKU_TOKEN_PRIVADO")
        self.environment = settings.PAYKU_ENVIRONMENT or os.getenv("PAYKU_ENVIRONMENT", "sandbox")

        if not self.token_publico:
            raise ValueError(
                "PAYKU_TOKEN_PUBLICO no configurado. "
                "Por favor, configura esta variable en tu archivo .env."
            )

        if not self.token_privado:
            raise ValueError(
                "PAYKU_TOKEN_PRIVADO no configurado. "
                "Por favor, configura esta variable en tu archivo .env."
            )

        # Configurar URL base según el ambiente
        if self.environment == "sandbox":
            self.base_api_url = "https://des.payku.cl/api"
            print(f"[INFO Payku] ⚠️  Usando ambiente SANDBOX (pruebas)")
            print(f"[INFO Payku] ⚠️  IMPORTANTE: Asegúrate de tener tokens de SANDBOX obtenidos desde https://des.payku.cl")
        else:
            self.base_api_url = "https://app.payku.cl/api"
            print(f"[INFO Payku] ✅ Usando ambiente PRODUCCIÓN")
            print(f"[INFO Payku] ⚠️  IMPORTANTE: Asegúrate de tener tokens de PRODUCCIÓN obtenidos desde https://app.payku.cl")

        self.api_url = f"{self.base_api_url}/transaction"
        self.base_url = settings.APP_BASE_URL or os.getenv("APP_BASE_URL", "http://localhost:3000")
        # Para redirects, usar APP_BASE_URL directamente (localhost:3000 en desarrollo)
        # No usar ngrok para redirects porque puede estar offline
        # ngrok solo se usa para webhooks (que requieren URL pública)
        self.frontend_url = self.base_url
        # URL para webhooks: usar ngrok si está disponible, sino usar localhost
        self.webhook_base_url = settings.NGROK_URL or os.getenv("NGROK_URL") or self.base_url.replace(':5173', ':8000')

        print(f"[DEBUG Payku] Configuración:")
        print(f"[DEBUG Payku]   - Environment: {self.environment}")
        print(f"[DEBUG Payku]   - Base API URL: {self.base_api_url}")
        print(f"[DEBUG Payku]   - API URL: {self.api_url}")
        print(f"[DEBUG Payku]   - Frontend URL (redirects): {self.frontend_url}")
        print(f"[DEBUG Payku]   - Webhook Base URL: {self.webhook_base_url}")
        print(f"[DEBUG Payku]   - Webhook URL completa: {self.webhook_base_url}/api/v1/purchases/payku-webhook")
        print(f"[DEBUG Payku]   - Token Público (primeros 20 chars): {self.token_publico[:20] if self.token_publico else 'NO CONFIGURADO'}...")
        print(f"[DEBUG Payku]   - Token Privado (primeros 20 chars): {self.token_privado[:20] if self.token_privado else 'NO CONFIGURADO'}...")

        # Advertencia si el ambiente es sandbox pero el token parece ser de producción
        if self.environment == "sandbox" and self.token_publico:
            # Los tokens de sandbox generalmente tienen un formato diferente
            # Esta es solo una advertencia, no un bloqueo
            logger.warning("Si recibes error 401, verifica que los tokens sean de SANDBOX (des.payku.cl)")

    async def create_transaction(
        self,
        order_id: str,
        email: str,
        amount: float,
        subject: str = "",
        currency: str = "CLP",
        payment: int = 99,
        urlreturn: Optional[str] = None,
        urlnotify: Optional[str] = None
    ) -> Dict:
        """
        Crear transacción de pago en Payku (ASYNC)

        Args:
            order_id: ID de la orden (usado como order en Payku)
            email: Email del cliente
            amount: Monto de la transacción
            subject: Descripción del pago
            currency: Moneda de la transacción (ej. "CLP")
            payment: Código del método de pago (99 = Todos los métodos)
            urlreturn: URL de retorno después del pago
            urlnotify: URL para recibir notificaciones de webhook

        Returns:
            dict con transaction_id y url para redirección
        """
        # URLs de retorno
        if not urlreturn:
            urlreturn = f"{self.base_url.rstrip('/')}/compra-exitosa?order_id={order_id}&payment_provider=payku"
            logger.debug(f"URL de retorno configurada: {urlreturn}")

        # Validar que urlreturn sea HTTPS en producción o tenga un formato válido
        if urlreturn and not urlreturn.startswith(('http://', 'https://')):
            raise ValueError(f"URL de retorno inválida: {urlreturn}. Debe comenzar con http:// o https://")

        if not urlnotify:
            urlnotify = f"{self.webhook_base_url}/api/v1/purchases/payku-webhook"

        # Validar que el monto sea un entero (Payku requiere montos en centavos/pesos enteros)
        amount_int = int(round(amount))

        # Preparar datos de la transacción
        transaction_data = {
            "email": email,
            "order": order_id,
            "subject": subject or f"Compra de tickets - Orden {order_id}",
            "amount": amount_int,
            "currency": currency,
            "payment": payment,  # 99 = Todos los métodos de pago
            "urlreturn": urlreturn,
            "urlnotify": urlnotify
        }

        # Headers para autenticación
        headers = {
            "Authorization": f"Bearer {self.token_publico}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        logger.info(f"Creando transacción Payku para orden {order_id}, monto: {amount_int}")

        try:
            # Usar httpx async para no bloquear el event loop
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.api_url,
                    json=transaction_data,
                    headers=headers
                )

            logger.debug(f"Payku respuesta HTTP: Status {response.status_code}")

            if response.status_code != 200:
                error_data = {}
                error_text = response.text
                try:
                    error_data = response.json() if error_text else {}
                except:
                    error_data = {"raw_response": error_text}

                error_message = error_data.get('message') or error_data.get('error') or error_data.get('detail') or 'Error desconocido'
                error_status = response.status_code

                logger.error(f"Error creando transacción Payku - Status: {error_status}, Mensaje: {error_message}")

                if error_status == 401:
                    if self.environment == "sandbox":
                        error_message = (
                            f"Token de Payku inválido para SANDBOX (401). "
                            f"Verifica tokens en https://des.payku.cl"
                        )
                    else:
                        error_message = (
                            f"Token de Payku inválido para PRODUCCIÓN (401). "
                            f"Verifica tokens en https://app.payku.cl"
                        )

                raise Exception(f"Error creando transacción: {error_message}")

            # Parsear respuesta exitosa
            transaction_response = response.json()

            payment_url = transaction_response.get('url')
            transaction_id = transaction_response.get('id') or transaction_response.get('transaction_id')
            status = transaction_response.get('status', 'pending')

            if not payment_url:
                logger.error(f"No se pudo obtener URL de pago. Respuesta: {transaction_response}")
                raise Exception(f"No se pudo obtener el link de pago de Payku")

            logger.info(f"Transacción Payku creada: {transaction_id}, URL: {payment_url[:50]}...")

            return {
                "transaction_id": transaction_id,
                "payment_link": payment_url,
                "url": payment_url,
                "status": status
            }

        except httpx.TimeoutException as e:
            error_msg = f"Timeout al comunicarse con Payku: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
        except httpx.RequestError as e:
            error_msg = f"Error de conexión con Payku: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"Error al crear transacción con Payku: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)

    async def verify_transaction(self, transaction_id: str) -> Dict:
        """
        Verificar estado de una transacción (ASYNC)

        Args:
            transaction_id: ID de la transacción en Payku

        Returns:
            dict con el estado de la transacción
        """
        try:
            verify_url = f"{self.api_url}/{transaction_id}"

            headers = {
                "Authorization": f"Bearer {self.token_publico}",
                "Content-Type": "application/json"
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(verify_url, headers=headers)

            if response.status_code != 200:
                error_data = response.json() if response.text else {}
                error_message = error_data.get('message', 'Error desconocido')
                raise Exception(f"Error obteniendo transacción: {error_message}")

            return response.json()

        except httpx.TimeoutException as e:
            error_msg = f"Timeout verificando transacción Payku: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
        except httpx.RequestError as e:
            error_msg = f"Error de conexión verificando Payku: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"Error verificando transacción: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)

    def process_webhook(self, webhook_data: Dict) -> Dict:
        """
        Procesar webhook de Payku

        Args:
            webhook_data: Datos del webhook recibido

        Returns:
            dict con información procesada del webhook
        """
        # Extraer datos del webhook según la documentación oficial
        transaction_id = webhook_data.get('transaction_id') or webhook_data.get('id')
        payment_key = webhook_data.get('payment_key')
        transaction_key = webhook_data.get('transaction_key')
        verification_key = webhook_data.get('verification_key')
        order_id = webhook_data.get('order') or webhook_data.get('ordencompra')
        status = webhook_data.get('status')
        amount = webhook_data.get('monto') or webhook_data.get('amount')
        fecha = webhook_data.get('fecha')

        logger.info(f"Procesando webhook Payku - order_id: {order_id}, status: {status}")

        # Mapear estados de Payku a estados internos
        status_mapping = {
            'success': 'approved',
            'failed': 'rejected',
            'pending': 'pending',
            'completado': 'approved',
            'completed': 'approved',
            'pendiente': 'pending',
            'cancelado': 'cancelled',
            'cancelled': 'cancelled',
            'rechazado': 'rejected',
            'rejected': 'rejected'
        }

        mapped_status = status_mapping.get(status.lower() if status else '', status)

        return {
            "transaction_id": transaction_id,
            "payment_key": payment_key,
            "transaction_key": transaction_key,
            "verification_key": verification_key,
            "order_id": order_id,
            "status": mapped_status,
            "original_status": status,
            "amount": amount,
            "fecha": fecha,
            "webhook_data": webhook_data
        }

