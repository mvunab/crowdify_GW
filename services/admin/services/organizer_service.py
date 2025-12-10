"""Servicio para gestión de organizadores"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from uuid import UUID, uuid4

from shared.database.models import Organizer, User


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

    async def create_organizer_for_user(
        self,
        db: AsyncSession,
        user_id: str
    ) -> Optional[Organizer]:
        """
        Crear un organizador automáticamente para un usuario admin
        
        Si el usuario no tiene un organizador asociado, crea uno con valores por defecto
        basados en la información del usuario.

        Args:
            db: Sesión de base de datos
            user_id: ID del usuario (string UUID)

        Returns:
            Organizer creado o None si hay error
        """
        try:
            user_id_uuid = UUID(user_id)
        except ValueError:
            return None

        # Verificar que el usuario existe
        user_stmt = select(User).where(User.id == user_id_uuid)
        user_result = await db.execute(user_stmt)
        user = user_result.scalar_one_or_none()

        if not user:
            return None

        # Verificar que no existe ya un organizador
        existing_organizer = await self.get_organizer_by_user_id(db, user_id)
        if existing_organizer:
            return existing_organizer

        # Crear organizador con valores por defecto
        organizer_name = f"{user.first_name or ''} {user.last_name or ''}".strip() or "Mi Organización"
        contact_email = user.email
        contact_phone = user.phone or None

        new_organizer = Organizer(
            id=uuid4(),
            org_name=organizer_name,
            contact_email=contact_email,
            contact_phone=contact_phone,
            user_id=user_id_uuid
        )

        db.add(new_organizer)
        await db.commit()
        await db.refresh(new_organizer)

        return new_organizer
