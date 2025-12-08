"""Servicio de integración con Payku"""
import os
from typing import Dict, Optional
import requests
from datetime import datetime
from app.core.config import settings


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
            print(f"[WARNING Payku] Si recibes error 401, verifica que los tokens sean de SANDBOX (des.payku.cl)")
            print(f"[WARNING Payku] Obtén tokens de sandbox desde: https://des.payku.cl → Integración → Tokens")
    
    def create_transaction(
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
        Crear transacción de pago en Payku
        
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
        # Payku redirige a esta URL después del pago con parámetros GET: ?order_id=xxx&payment_provider=payku
        # IMPORTANTE: Payku necesita una URL pública para redirigir. En desarrollo local:
        # - Opción 1: Usar ngrok para el frontend (FRONTEND_URL)
        # - Opción 2: Si usas localhost:3000, solo funcionará si pruebas desde tu navegador local
        if not urlreturn:
            # Usar APP_BASE_URL (puede ser localhost:3000 o ngrok)
            urlreturn = f"{self.base_url.rstrip('/')}/compra-exitosa?order_id={order_id}&payment_provider=payku"
            print(f"[DEBUG Payku] ✅ URL de retorno configurada: {urlreturn}")
            print(f"[DEBUG Payku]   - Base URL: {self.base_url}")
            print(f"[DEBUG Payku]   - Order ID: {order_id}")
            print(f"[DEBUG Payku]   - ⚠️  NOTA: Payku necesita URL pública. Si usas localhost, solo funciona desde tu navegador local")
        
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
        # Según la documentación de Payku, se usa el TOKEN PÚBLICO en el header Authorization
        headers = {
            "Authorization": f"Bearer {self.token_publico}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        print(f"[DEBUG Payku] Creando transacción con los siguientes datos:")
        print(f"[DEBUG Payku]   - URL: {self.api_url}")
        print(f"[DEBUG Payku]   - Environment: {self.environment}")
        print(f"[DEBUG Payku]   - Token usado (primeros 20): {self.token_publico[:20] if self.token_publico else 'NO TOKEN'}...")
        print(f"[DEBUG Payku]   - order: {order_id}")
        print(f"[DEBUG Payku]   - email: {email}")
        print(f"[DEBUG Payku]   - amount: {amount_int}")
        print(f"[DEBUG Payku]   - subject: {transaction_data['subject']}")
        print(f"[DEBUG Payku]   - currency: {currency}")
        print(f"[DEBUG Payku]   - payment: {payment}")
        print(f"[DEBUG Payku]   - urlreturn: {urlreturn}")
        print(f"[DEBUG Payku]   - urlnotify: {urlnotify}")
        print(f"[DEBUG Payku]   - Headers: Authorization: Bearer {self.token_publico[:20]}...")
        
        try:
            response = requests.post(
                self.api_url,
                json=transaction_data,
                headers=headers,
                timeout=30
            )
            
            print(f"[DEBUG Payku] Respuesta HTTP: Status {response.status_code}")
            
            if response.status_code != 200:
                error_data = {}
                error_text = response.text
                try:
                    error_data = response.json() if error_text else {}
                except:
                    error_data = {"raw_response": error_text}
                
                error_message = error_data.get('message') or error_data.get('error') or error_data.get('detail') or 'Error desconocido'
                error_status = response.status_code
                
                print(f"[ERROR Payku] Error creando transacción")
                print(f"[ERROR Payku] Status HTTP: {error_status}")
                print(f"[ERROR Payku] URL: {self.api_url}")
                print(f"[ERROR Payku] Environment: {self.environment}")
                print(f"[ERROR Payku] Token usado (primeros 20): {self.token_publico[:20] if self.token_publico else 'NO TOKEN'}...")
                print(f"[ERROR Payku] Mensaje: {error_message}")
                print(f"[ERROR Payku] Respuesta completa: {error_data}")
                print(f"[ERROR Payku] Response text: {error_text}")
                
                if error_status == 401:
                    if self.environment == "sandbox":
                        error_message = (
                            f"❌ Token de Payku inválido para SANDBOX (401 Unauthorized).\n\n"
                            f"🔧 SOLUCIÓN:\n"
                            f"1. Ve a https://des.payku.cl y regístrate/inicia sesión\n"
                            f"2. Accede a: Integración → Tokens Integración y API\n"
                            f"3. Copia el Token Público y Token Privado de SANDBOX\n"
                            f"4. Actualiza tu .env con los nuevos tokens:\n"
                            f"   PAYKU_TOKEN_PUBLICO=tu_token_publico_sandbox\n"
                            f"   PAYKU_TOKEN_PRIVADO=tu_token_privado_sandbox\n"
                            f"   PAYKU_ENVIRONMENT=sandbox\n\n"
                            f"⚠️  Los tokens de producción (app.payku.cl) NO funcionan en sandbox (des.payku.cl)\n"
                            f"📝 Token actual usado: {self.token_publico[:30] if self.token_publico else 'NO CONFIGURADO'}..."
                        )
                    else:
                        error_message = (
                            f"❌ Token de Payku inválido para PRODUCCIÓN (401 Unauthorized).\n\n"
                            f"🔧 SOLUCIÓN:\n"
                            f"1. Ve a https://app.payku.cl y verifica tus tokens\n"
                            f"2. Asegúrate de usar tokens de PRODUCCIÓN, no de sandbox\n"
                            f"3. Verifica que el token no haya expirado\n"
                            f"📝 Token actual usado: {self.token_publico[:30] if self.token_publico else 'NO CONFIGURADO'}..."
                        )
                elif error_status == 403:
                    error_message = (
                        f"Token sin permisos suficientes (403 Forbidden). "
                        f"Verifica los permisos de tu cuenta en Payku."
                    )
                elif error_status == 400:
                    error_message = (
                        f"Error en la solicitud (400 Bad Request). "
                        f"Verifica los datos enviados: {error_data}"
                    )
                
                raise Exception(f"Error creando transacción: {error_message}")
            
            # Parsear respuesta exitosa
            transaction_response = response.json()
            
            print(f"[DEBUG Payku] Transacción creada exitosamente:")
            print(f"[DEBUG Payku]   - Respuesta completa: {transaction_response}")
            
            # Según la documentación de Payku, la respuesta tiene:
            # - status: "pending"
            # - id: "trx3b4d77b43acd9a720" (ID de la transacción)
            # - url: "https://BASE_URL/url_de_pago" (URL para redirigir al pagador)
            payment_url = transaction_response.get('url')
            transaction_id = transaction_response.get('id') or transaction_response.get('transaction_id')
            status = transaction_response.get('status', 'pending')
            
            if not payment_url:
                print(f"[ERROR Payku] No se pudo obtener URL de pago de la respuesta")
                print(f"[ERROR Payku] Respuesta completa: {transaction_response}")
                raise Exception(f"No se pudo obtener el link de pago de Payku. Respuesta: {transaction_response}")
            
            if not transaction_id:
                print(f"[WARNING Payku] No se pudo obtener transaction_id de la respuesta")
                print(f"[WARNING Payku] Respuesta completa: {transaction_response}")
            
            print(f"[DEBUG Payku] Payment URL extraída: {payment_url}")
            print(f"[DEBUG Payku] Transaction ID: {transaction_id}")
            print(f"[DEBUG Payku] Status: {status}")
            
            return {
                "transaction_id": transaction_id,
                "payment_link": payment_url,
                "url": payment_url,  # Alias para compatibilidad
                "status": status
            }
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Error al comunicarse con la API de Payku: {str(e)}"
            print(f"[ERROR Payku] {error_msg}")
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"Error al crear transacción con Payku: {str(e)}"
            print(f"[ERROR Payku] {error_msg}")
            raise Exception(error_msg)
    
    def verify_transaction(self, transaction_id: str) -> Dict:
        """
        Verificar estado de una transacción
        
        Args:
            transaction_id: ID de la transacción en Payku
        
        Returns:
            dict con el estado de la transacción
        """
        try:
            # Payku permite consultar el estado de una transacción
            # URL: https://app.payku.cl/api/transaction/{transaction_id}
            verify_url = f"{self.api_url}/{transaction_id}"
            
            headers = {
                "Authorization": f"Bearer {self.token_publico}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(verify_url, headers=headers, timeout=30)
            
            if response.status_code != 200:
                error_data = response.json() if response.text else {}
                error_message = error_data.get('message', 'Error desconocido')
                raise Exception(f"Error obteniendo transacción: {error_message}")
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Error al comunicarse con la API de Payku: {str(e)}"
            print(f"[ERROR Payku] {error_msg}")
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"Error verificando transacción: {str(e)}"
            print(f"[ERROR Payku] {error_msg}")
            raise Exception(error_msg)
    
    def process_webhook(self, webhook_data: Dict) -> Dict:
        """
        Procesar webhook de Payku
        
        Args:
            webhook_data: Datos del webhook recibido
        
        Returns:
            dict con información procesada del webhook
        
        Según la documentación de Payku, el webhook envía:
        - transaction_id: ID de la transacción
        - payment_key: Clave de pago
        - transaction_key: Clave de transacción
        - verification_key: Clave de verificación
        - order: ID de la orden del comercio
        - status: "success" (aprobado) o "failed" (rechazado)
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
        
        print(f"[DEBUG Payku] Procesando webhook:")
        print(f"[DEBUG Payku]   - transaction_id: {transaction_id}")
        print(f"[DEBUG Payku]   - payment_key: {payment_key}")
        print(f"[DEBUG Payku]   - transaction_key: {transaction_key}")
        print(f"[DEBUG Payku]   - verification_key: {verification_key}")
        print(f"[DEBUG Payku]   - order_id: {order_id}")
        print(f"[DEBUG Payku]   - status: {status}")
        print(f"[DEBUG Payku]   - amount: {amount}")
        print(f"[DEBUG Payku]   - fecha: {fecha}")
        
        # Mapear estados de Payku a estados internos
        # Según la documentación: "success" = aprobado, "failed" = rechazado
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

