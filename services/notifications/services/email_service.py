"""Servicio de envío de emails"""
import os
from typing import Dict, Optional
import sendgrid
from sendgrid.helpers.mail import Mail, Email, To, Content


class EmailService:
    """Servicio para enviar emails usando SendGrid"""
    
    def __init__(self):
        api_key = os.getenv("EMAIL_API_KEY")
        self.from_email = os.getenv("EMAIL_FROM", "noreply@crodify.com")
        
        if api_key:
            self.sg = sendgrid.SendGridAPIClient(api_key=api_key)
        else:
            self.sg = None
            print("WARNING: EMAIL_API_KEY no configurado, emails no se enviarán")
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """
        Enviar email
        
        Returns:
            True si se envió correctamente
        """
        if not self.sg:
            print(f"Email simulado a {to_email}: {subject}")
            return True
        
        try:
            message = Mail(
                from_email=Email(self.from_email),
                to_emails=To(to_email),
                subject=subject,
                html_content=Content("text/html", html_content)
            )
            
            if text_content:
                message.add_content(Content("text/plain", text_content))
            
            response = self.sg.send(message)
            
            if response.status_code in [200, 202]:
                return True
            else:
                print(f"Error enviando email: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"Excepción enviando email: {e}")
            return False
    
    async def send_ticket_email(
        self,
        to_email: str,
        attendee_name: str,
        event_name: str,
        ticket_id: str,
        qr_code_url: Optional[str] = None
    ) -> bool:
        """Enviar email con ticket"""
        html_content = f"""
        <html>
            <body>
                <h1>Tu ticket para {event_name}</h1>
                <p>Hola {attendee_name},</p>
                <p>Tu ticket ha sido generado exitosamente.</p>
                <p>ID del ticket: {ticket_id}</p>
                {"<img src='" + qr_code_url + "' alt='QR Code' />" if qr_code_url else ""}
                <p>Presenta este ticket en la entrada del evento.</p>
            </body>
        </html>
        """
        
        return await self.send_email(
            to_email=to_email,
            subject=f"Tu ticket para {event_name}",
            html_content=html_content
        )

