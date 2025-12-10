"""Servicio de envío de emails usando Resend"""
import os
import logging
from typing import Optional, List, Union
import base64
import io
import resend
import qrcode
from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Servicio para enviar emails usando Resend (desarrollo y producción)"""
    
    def __init__(self):
        self.resend_api_key = os.getenv("RESEND_API_KEY", "")
        self.from_email = os.getenv("RESEND_FROM_EMAIL", settings.SMTP_FROM)
        
        if not self.resend_api_key:
            logger.warning("RESEND_API_KEY no configurado. Los emails no se enviarán.")
            self.resend_configured = False
        else:
            # Configurar API key de Resend
            resend.api_key = self.resend_api_key
            self.resend_configured = True
            logger.info(f"EmailService (Resend) inicializado con from: {self.from_email}")
    
    def _generate_qr_image_base64(self, qr_data: str) -> str:
        """
        Generar imagen QR como base64 para incluir en email
        
        Args:
            qr_data: Datos para el código QR (qr_signature)
        
        Returns:
            String base64 de la imagen PNG del QR
        """
        try:
            if not qr_data:
                logger.warning("qr_data está vacío, no se puede generar QR")
                return ""
            
            # Crear instancia de QRCode
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(qr_data)
            qr.make(fit=True)
            
            # Crear imagen
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Convertir a bytes
            img_buffer = io.BytesIO()
            img.save(img_buffer, format='PNG')
            img_buffer.seek(0)  # Resetear posición del buffer
            img_bytes = img_buffer.getvalue()
            
            if not img_bytes:
                logger.error("No se generaron bytes de la imagen QR")
                return ""
            
            # Convertir a base64
            img_base64 = base64.b64encode(img_bytes).decode('utf-8')
            
            logger.info(f"QR code generado exitosamente (tamaño: {len(img_bytes)} bytes, base64: {len(img_base64)} caracteres)")
            return img_base64
        except ImportError as e:
            logger.error(f"Error importando qrcode: {e}. ¿Está instalado qrcode[pil]?")
            return ""
        except Exception as e:
            logger.error(f"Error generando QR code: {e}", exc_info=True)
            return ""
    
    async def send_email(
        self,
        to_email: Union[str, List[str]],
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        attachments: Optional[List[dict]] = None
    ) -> bool:
        """
        Enviar email usando Resend
        
        Args:
            to_email: Email destino (string o lista de strings)
            subject: Asunto del email
            html_content: Contenido HTML del email
            text_content: Contenido de texto plano (opcional)
            attachments: Lista de adjuntos (opcional) [{"filename": "file.pdf", "content": bytes, "content_type": "application/pdf"}]
        
        Returns:
            True si se envió correctamente, False en caso contrario
        """
        if not self.resend_configured:
            logger.warning(f"Resend no configurado. Email simulado a {to_email}: {subject}")
            return True
        
        try:
            # Convertir a lista si es string
            if isinstance(to_email, str):
                to_emails = [to_email]
            else:
                to_emails = to_email
            
            # Preparar adjuntos para Resend
            resend_attachments = []
            if attachments:
                for attachment in attachments:
                    # Resend requiere base64 para adjuntos
                    if isinstance(attachment["content"], str):
                        # Si ya es base64, usarlo directamente
                        content_base64 = attachment["content"]
                    else:
                        # Si son bytes, convertir a base64
                        content_base64 = base64.b64encode(attachment["content"]).decode("utf-8")
                    
                    attach_dict = {
                        "filename": attachment["filename"],
                        "content": content_base64,
                    }
                    
                    # Resend no soporta content_id directamente, pero podemos intentar
                    # Si tiene content_id, lo guardamos para referencia pero Resend puede no usarlo
                    # En su lugar, usaremos data URI en el HTML
                    
                    resend_attachments.append(attach_dict)
            
            # Preparar payload para Resend
            params = {
                "from": self.from_email,
                "to": to_emails,
                "subject": subject,
                "html": html_content,
            }
            
            # Agregar texto plano si está disponible
            if text_content:
                params["text"] = text_content
            
            # Agregar adjuntos si hay
            if resend_attachments:
                params["attachments"] = resend_attachments
            
            # Enviar email usando Resend
            # Resend SDK es síncrono, pero podemos ejecutarlo en un thread pool
            import asyncio
            loop = asyncio.get_event_loop()
            
            # Usar la API correcta de Resend
            def send_email_sync():
                try:
                    return resend.Emails.send(params)
                except Exception as e:
                    logger.error(f"Error en Resend SDK: {e}")
                    return {"error": str(e)}
            
            result = await loop.run_in_executor(None, send_email_sync)
            
            if result.get("error"):
                error_msg = result.get("error", "Unknown error")
                logger.error(f"Error enviando email a {to_emails}: {error_msg}")
                return False
            
            logger.info(f"Email enviado exitosamente a {to_emails}: {subject} (ID: {result.get('id', 'N/A')})")
            return True
            
        except Exception as e:
            logger.error(f"Error enviando email a {to_email}: {e}", exc_info=True)
            return False
    
    async def send_ticket_email(
        self,
        to_email: str,
        attendee_name: str,
        event_name: str,
        event_date: str,
        event_location: str,
        ticket_id: str,
        qr_signature: Optional[str] = None,
        qr_code_url: Optional[str] = None,
        pdf_attachment: Optional[bytes] = None
    ) -> bool:
        """
        Enviar email con ticket
        
        Args:
            to_email: Email del asistente
            attendee_name: Nombre del asistente
            event_name: Nombre del evento
            event_date: Fecha del evento
            event_location: Ubicación del evento
            ticket_id: ID del ticket
            qr_signature: QR signature del ticket (para generar imagen QR)
            qr_code_url: URL del código QR (opcional, si no se proporciona qr_signature)
            pdf_attachment: Contenido del PDF del ticket (opcional)
        
        Returns:
            True si se envió correctamente
        """
        # Generar imagen QR si tenemos qr_signature
        qr_image_base64 = ""
        
        if qr_signature:
            logger.info(f"[EMAIL] Generando QR code para ticket {ticket_id} con signature: {qr_signature[:30]}...")
            qr_image_base64 = self._generate_qr_image_base64(qr_signature)
            if qr_image_base64:
                logger.info(f"[EMAIL] ✅ QR code generado exitosamente para ticket {ticket_id} (tamaño base64: {len(qr_image_base64)} caracteres)")
            else:
                logger.error(f"[EMAIL] ❌ No se pudo generar QR code para ticket {ticket_id}")
        else:
            logger.warning(f"[EMAIL] ⚠️ No se proporcionó qr_signature para ticket {ticket_id}")
        
        # Generar HTML del QR usando data URI
        # Nota: Gmail y otros clientes modernos soportan data URIs
        qr_html = ""
        if qr_image_base64:
            # Usar data URI directamente en el HTML
            # Formato optimizado para clientes de email
            qr_html = f'''<div class="qr-code" style="text-align: center; margin: 30px 0; padding: 20px;">
                <div style="display: inline-block; border: 2px solid #e5e7eb; border-radius: 8px; padding: 15px; background: white; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <img src="data:image/png;base64,{qr_image_base64}" 
                         alt="Código QR del Ticket" 
                         width="250" 
                         height="250"
                         style="display: block; margin: 0 auto;" />
                </div>
                <p style="margin-top: 15px; font-size: 12px; color: #6b7280; font-weight: 500;">Escanea este código en la entrada del evento</p>
            </div>'''
            logger.info(f"[EMAIL] ✅ HTML del QR generado para ticket {ticket_id}")
        elif qr_code_url:
            qr_html = f'''<div class="qr-code" style="text-align: center; margin: 30px 0;">
                <img src="{qr_code_url}" 
                     alt="Código QR del Ticket" 
                     style="max-width: 250px; height: auto; display: block; margin: 0 auto;" />
            </div>'''
        else:
            logger.warning(f"[EMAIL] ⚠️ No hay QR code disponible para ticket {ticket_id}")
            # No mostrar nada si no hay QR (mejor que mostrar un placeholder confuso)
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background-color: #4F46E5;
                    color: white;
                    padding: 20px;
                    text-align: center;
                    border-radius: 8px 8px 0 0;
                }}
                .content {{
                    background-color: #f9fafb;
                    padding: 30px;
                    border-radius: 0 0 8px 8px;
                }}
                .ticket-info {{
                    background-color: white;
                    padding: 20px;
                    border-radius: 8px;
                    margin: 20px 0;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                .ticket-info h2 {{
                    margin-top: 0;
                    color: #4F46E5;
                }}
                .info-row {{
                    display: flex;
                    justify-content: space-between;
                    padding: 10px 0;
                    border-bottom: 1px solid #e5e7eb;
                }}
                .info-row:last-child {{
                    border-bottom: none;
                }}
                .info-label {{
                    font-weight: bold;
                    color: #6b7280;
                }}
                .info-value {{
                    color: #111827;
                }}
                .qr-code {{
                    text-align: center;
                    margin: 20px 0;
                }}
                .qr-code img {{
                    max-width: 200px;
                    height: auto;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid #e5e7eb;
                    color: #6b7280;
                    font-size: 14px;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🎫 Tu Ticket está Listo</h1>
            </div>
            <div class="content">
                <p>Hola <strong>{attendee_name}</strong>,</p>
                <p>Tu ticket ha sido generado exitosamente. Aquí están los detalles:</p>
                
                <div class="ticket-info">
                    <h2>Detalles del Evento</h2>
                    <div class="info-row">
                        <span class="info-label">Evento:</span>
                        <span class="info-value">{event_name}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Fecha:</span>
                        <span class="info-value">{event_date}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Ubicación:</span>
                        <span class="info-value">{event_location}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">ID del Ticket:</span>
                        <span class="info-value">{ticket_id}</span>
                    </div>
                </div>
                
                {qr_html}
                
                <p><strong>Importante:</strong> Presenta este ticket (o el código QR) en la entrada del evento.</p>
                
                <div class="footer">
                    <p>Gracias por tu compra. ¡Te esperamos en el evento!</p>
                    <p>Este es un email automático, por favor no respondas.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Hola {attendee_name},
        
        Tu ticket ha sido generado exitosamente.
        
        Detalles del Evento:
        - Evento: {event_name}
        - Fecha: {event_date}
        - Ubicación: {event_location}
        - ID del Ticket: {ticket_id}
        
        Presenta este ticket en la entrada del evento.
        
        Gracias por tu compra. ¡Te esperamos en el evento!
        """
        
        attachments = []
        
        # Agregar PDF si está disponible
        if pdf_attachment:
            attachments.append({
                "filename": f"ticket_{ticket_id}.pdf",
                "content": pdf_attachment,
                "content_type": "application/pdf"
            })
        
        # Nota: El QR se incluye como data URI en el HTML, no como attachment
        # Esto es más compatible y no requiere Content-ID
        
        return await self.send_email(
            to_email=to_email,
            subject=f"Tu ticket para {event_name}",
            html_content=html_content,
            text_content=text_content,
            attachments=attachments if attachments else None
        )
    
    async def send_order_confirmation_email(
        self,
        to_email: str,
        buyer_name: str,
        order_id: str,
        order_total: float,
        currency: str,
        event_name: str,
        tickets_count: int
    ) -> bool:
        """
        Enviar email de confirmación de orden
        
        Args:
            to_email: Email del comprador
            buyer_name: Nombre del comprador
            order_id: ID de la orden
            order_total: Total de la orden
            currency: Moneda (CLP, USD)
            event_name: Nombre del evento
            tickets_count: Cantidad de tickets
        
        Returns:
            True si se envió correctamente
        """
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background-color: #10b981;
                    color: white;
                    padding: 20px;
                    text-align: center;
                    border-radius: 8px 8px 0 0;
                }}
                .content {{
                    background-color: #f9fafb;
                    padding: 30px;
                    border-radius: 0 0 8px 8px;
                }}
                .order-info {{
                    background-color: white;
                    padding: 20px;
                    border-radius: 8px;
                    margin: 20px 0;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>✅ Orden Confirmada</h1>
            </div>
            <div class="content">
                <p>Hola <strong>{buyer_name}</strong>,</p>
                <p>Tu orden ha sido confirmada exitosamente.</p>
                
                <div class="order-info">
                    <h2>Detalles de la Orden</h2>
                    <p><strong>Número de Orden:</strong> {order_id}</p>
                    <p><strong>Evento:</strong> {event_name}</p>
                    <p><strong>Tickets:</strong> {tickets_count}</p>
                    <p><strong>Total:</strong> {currency} {order_total:,.0f}</p>
                </div>
                
                <p>Los tickets serán enviados a este correo electrónico en breve.</p>
                
                <p>Gracias por tu compra.</p>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Hola {buyer_name},
        
        Tu orden ha sido confirmada exitosamente.
        
        Detalles de la Orden:
        - Número de Orden: {order_id}
        - Evento: {event_name}
        - Tickets: {tickets_count}
        - Total: {currency} {order_total:,.0f}
        
        Los tickets serán enviados a este correo electrónico en breve.
        
        Gracias por tu compra.
        """
        
        return await self.send_email(
            to_email=to_email,
            subject=f"Orden confirmada - {event_name}",
            html_content=html_content,
            text_content=text_content
        )
