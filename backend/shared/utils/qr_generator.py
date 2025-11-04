"""Utilidades para generar QR signatures de tickets"""
import hashlib
import hmac
import os
from typing import Optional


def generate_qr_signature(ticket_id: str, secret: Optional[str] = None) -> str:
    """
    Generar QR signature único para un ticket
    
    Usa HMAC-SHA256 para generar una firma segura basada en el ticket_id
    y un secret. Esto asegura que:
    - Cada ticket tenga un QR único
    - No se puedan falsificar fácilmente
    - Se pueda verificar la autenticidad
    
    Args:
        ticket_id: UUID del ticket como string
        secret: Secret key para HMAC (default: env QR_SECRET)
    
    Returns:
        String hexadecimal de 64 caracteres (HMAC-SHA256)
    """
    if secret is None:
        secret = os.getenv("QR_SECRET", "dev-qr-secret-change-in-production")
    
    # Crear HMAC usando el secret y el ticket_id
    message = f"ticket:{ticket_id}"
    signature = hmac.new(
        secret.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    # Combinar ticket_id (sin guiones) con signature para mayor seguridad
    # Formato: {ticket_id_short}{signature}
    ticket_id_clean = ticket_id.replace('-', '')
    
    # Usar primeros 8 caracteres del ticket_id + signature completa
    return f"{ticket_id_clean[:8]}{signature}"


def verify_qr_signature(qr_signature: str, ticket_id: str, secret: Optional[str] = None) -> bool:
    """
    Verificar que un QR signature es válido para un ticket
    
    Args:
        qr_signature: QR signature a verificar
        ticket_id: UUID del ticket como string
        secret: Secret key para HMAC (default: env QR_SECRET)
    
    Returns:
        True si el signature es válido
    """
    expected = generate_qr_signature(ticket_id, secret)
    return hmac.compare_digest(qr_signature, expected)

