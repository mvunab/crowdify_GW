"""Servicio para gestión de usuarios y scanners"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from uuid import UUID
from datetime import datetime
import uuid

from shared.database.models import User


class UserManagementService:
    """Servicio para operaciones con usuarios y scanners"""

    async def get_scanners(
        self,
        db: AsyncSession
    ) -> List[User]:
        """
        Obtener todos los usuarios con rol scanner

        Args:
            db: Sesión de base de datos

        Returns:
            Lista de usuarios con rol scanner
        """
        stmt = select(User).where(
            User.role == "scanner"
        ).order_by(User.created_at.desc())

        result = await db.execute(stmt)
        scanners = result.scalars().all()

        return list(scanners)

    async def get_users_by_role(
        self,
        db: AsyncSession,
        role: str = "user"
    ) -> List[User]:
        """
        Obtener usuarios por rol

        Args:
            db: Sesión de base de datos
            role: Rol a filtrar (default: user)

        Returns:
            Lista de usuarios con el rol especificado
        """
        stmt = select(User).where(
            User.role == role
        ).order_by(User.created_at.desc())

        result = await db.execute(stmt)
        users = result.scalars().all()

        return list(users)

    async def update_user_role(
        self,
        db: AsyncSession,
        user_id: str,
        new_role: str,
        current_user_id: str
    ) -> Optional[User]:
        """
        Actualizar el rol de un usuario

        Args:
            db: Sesión de base de datos
            user_id: ID del usuario a actualizar
            new_role: Nuevo rol
            current_user_id: ID del usuario que hace el cambio

        Returns:
            Usuario actualizado o None

        Raises:
            ValueError: Si hay errores de validación
        """
        # Validar que no se cambie el rol de sí mismo
        if user_id == current_user_id:
            raise ValueError("No puedes cambiar tu propio rol")

        # Validar que el nuevo rol sea válido
        valid_roles = ["user", "scanner", "coordinator", "admin"]
        if new_role not in valid_roles:
            raise ValueError(f"Rol inválido. Debe ser uno de: {', '.join(valid_roles)}")

        # Buscar usuario
        try:
            user_id_uuid = UUID(user_id)
        except ValueError:
            raise ValueError("ID de usuario inválido")

        stmt = select(User).where(User.id == user_id_uuid)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            return None

        # Actualizar rol
        user.role = new_role
        user.updated_at = datetime.utcnow()

        await db.commit()
        await db.refresh(user)

        return user

    async def create_scanner(
        self,
        db: AsyncSession,
        email: str,
        first_name: str,
        last_name: str,
        password: str
    ) -> User:
        """
        Crear un nuevo usuario con rol scanner

        Nota: Esta implementación solo crea el usuario en la tabla public.users.
        Para crear en Supabase Auth, se necesitaría usar el Admin API de Supabase
        o una Edge Function.

        Args:
            db: Sesión de base de datos
            email: Email del scanner
            first_name: Nombre
            last_name: Apellido
            password: Contraseña (se debe hashear en producción)

        Returns:
            Usuario creado

        Raises:
            ValueError: Si el email ya existe
        """
        # Verificar que el email no existe
        stmt = select(User).where(User.email == email)
        result = await db.execute(stmt)
        existing_user = result.scalar_one_or_none()

        if existing_user:
            raise ValueError(f"El email {email} ya está registrado")

        # Validar password (mínimo 8 caracteres)
        if len(password) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres")

        # Crear usuario
        new_user = User(
            id=uuid.uuid4(),
            email=email,
            first_name=first_name,
            last_name=last_name,
            role="scanner",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)

        # TODO: Crear usuario en Supabase Auth usando Admin API
        # Esto requiere configurar SUPABASE_SERVICE_KEY en el entorno
        # y llamar a la API de Supabase Auth

        return new_user

    async def remove_scanner_role(
        self,
        db: AsyncSession,
        scanner_id: str
    ) -> User:
        """
        Remover rol scanner de un usuario (degradar a user)

        Args:
            db: Sesión de base de datos
            scanner_id: ID del scanner

        Returns:
            Usuario actualizado

        Raises:
            ValueError: Si hay errores de validación
        """
        try:
            scanner_id_uuid = UUID(scanner_id)
        except ValueError:
            raise ValueError("ID de scanner inválido")

        # Buscar usuario
        stmt = select(User).where(User.id == scanner_id_uuid)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise ValueError("Scanner no encontrado")

        if user.role != "scanner":
            raise ValueError("El usuario no tiene rol scanner")

        # Cambiar rol a user
        user.role = "user"
        user.updated_at = datetime.utcnow()

        await db.commit()
        await db.refresh(user)

        return user
