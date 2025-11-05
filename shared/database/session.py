"""Sesiones de base de datos"""
from shared.database.connection import get_db
from sqlalchemy import text

async def ensure_schema(session):
    """Asegurar que estamos en el schema public"""
    await session.execute(text("SET search_path TO public"))

__all__ = ["get_db", "ensure_schema"]

