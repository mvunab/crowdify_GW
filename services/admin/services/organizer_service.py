"""Servicio para gestión de organizadores"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from uuid import UUID

from shared.database.models import Organizer


class OrganizerService:
    """Servicio para operaciones con organizadores"""

    async def get_organizer_by_user_id(
        self,
        db: AsyncSession,
        user_id: str
    ) -> Optional[Organizer]:
        """
        Obtener organizador por user_id

        Args:
            db: Sesión de base de datos
            user_id: ID del usuario (string UUID)

        Returns:
            Organizer o None si no existe
        """
        try:
            user_id_uuid = UUID(user_id)
        except ValueError:
            return None

        stmt = select(Organizer).where(Organizer.user_id == user_id_uuid)
        result = await db.execute(stmt)
        organizer = result.scalar_one_or_none()

        return organizer
