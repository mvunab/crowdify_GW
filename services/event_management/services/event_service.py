"""Servicio de gestión de eventos"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_, text
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import datetime
from uuid import UUID
from shared.database.models import Event, Organizer, TicketType
from shared.cache.redis_client import cache_get, cache_set, cache_delete


class EventService:
    """Servicio para gestionar eventos"""

    @staticmethod
    async def get_events(
        db: AsyncSession,
        category: Optional[str] = None,
        search: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Event]:
        """
        Obtener lista de eventos con filtros

        Compatible con: eventsService.getEvents()
        """
        # Cache deshabilitado temporalmente para evitar inconsistencias
        # TODO: Implementar cache más robusto con invalidación automática

        # Asegurar que estamos en el schema public (Session Pooler puede resetearlo)
        try:
            await db.execute(text("SET search_path TO public"))
        except:
            pass  # Si ya está configurado, continuar

        # Eager load de relaciones para evitar N+1 queries
        stmt = select(Event).options(
            selectinload(Event.organizer),
            selectinload(Event.ticket_types),
            selectinload(Event.event_services)
        )

        # Filtros
        conditions = []

        if search:
            conditions.append(
                or_(
                    Event.name.ilike(f"%{search}%"),
                    Event.location_text.ilike(f"%{search}%")
                )
            )

        if date_from:
            conditions.append(Event.starts_at >= date_from)

        if date_to:
            conditions.append(Event.starts_at <= date_to)

        if conditions:
            stmt = stmt.where(and_(*conditions))

        # Ordenar por fecha de inicio
        stmt = stmt.order_by(Event.starts_at.asc())

        # Paginación
        stmt = stmt.limit(limit).offset(offset)

        result = await db.execute(stmt)
        events = result.scalars().all()

        return events

    @staticmethod
    async def get_event_by_id(
        db: AsyncSession,
        event_id: str
    ) -> Optional[Event]:
        """
        Obtener evento por ID

        Compatible con: eventsService.getEventById()
        """
        await db.execute(text("SET search_path TO public"))
        stmt = select(Event).options(
            selectinload(Event.organizer),
            selectinload(Event.ticket_types),
            selectinload(Event.event_services)
        ).where(Event.id == event_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def create_event(
        db: AsyncSession,
        event_data: dict,
        user_id: str
    ) -> Event:
        """
        Crear nuevo evento

        Requiere: admin role
        Compatible con: adminService.createEvent()
        """
        # Verificar que el organizer existe y pertenece al usuario
        stmt = select(Organizer).where(
            Organizer.id == event_data["organizer_id"],
            Organizer.user_id == user_id
        )
        result = await db.execute(stmt)
        organizer = result.scalar_one_or_none()

        if not organizer:
            raise ValueError("Organizer no encontrado o no pertenece al usuario")

        # Crear evento
        event = Event(
            id=UUID(event_data.get("id")) if event_data.get("id") else None,
            organizer_id=event_data["organizer_id"],
            created_by_user_id=UUID(user_id) if user_id else None,  # Admin que crea el evento
            name=event_data["name"],
            location_text=event_data.get("location_text"),
            starts_at=event_data["starts_at"],
            ends_at=event_data.get("ends_at"),
            capacity_total=event_data["capacity_total"],
            capacity_available=event_data["capacity_total"],
            allow_children=event_data.get("allow_children", False),
            category=event_data.get("category", "otro"),  # ✅ Nuevo campo
            description=event_data.get("description"),  # ✅ Nuevo campo
            image_url=event_data.get("image_url"),  # ✅ Nuevo campo
            created_at=datetime.utcnow()
        )

        db.add(event)
        await db.commit()
        await db.refresh(event)

        # ✅ Crear ticket_type "General" si se proporciona precio
        if "price" in event_data and event_data["price"] is not None and event_data["price"] > 0:
            ticket_type = TicketType(
                event_id=event.id,
                name="General",
                price=event_data["price"],
                is_child=False
            )
            db.add(ticket_type)
            await db.commit()

        # ✅ Crear event_services si se proporcionan
        if "services" in event_data and event_data["services"]:
            from shared.database.models import EventService as EventServiceModel

            for service_data in event_data["services"]:
                stock = service_data.get("stock", service_data.get("stock_total", 0))
                event_service = EventServiceModel(
                    event_id=event.id,
                    name=service_data.get("name"),
                    description=service_data.get("description"),
                    price=service_data.get("price", 0),
                    service_type=service_data.get("service_type", "general"),
                    stock=stock,
                    stock_available=service_data.get("stock_available", stock),
                    min_age=service_data.get("min_age"),
                    max_age=service_data.get("max_age")
                )
                db.add(event_service)

            await db.commit()


        return event

    @staticmethod
    async def _invalidate_events_cache():
        """Invalidar cache de listado de eventos"""
        # Invalidar todos los posibles límites en cache
        for limit in [10, 20, 50, 100]:
            await cache_delete(f"events:list:{limit}")

    @staticmethod
    async def update_event(
        db: AsyncSession,
        event_id: str,
        event_data: dict,
        user_id: str
    ) -> Optional[Event]:
        """
        Actualizar evento

        Requiere: admin role o ser el organizer del evento
        Compatible con: adminService.updateEvent()
        """
        stmt = select(Event).where(Event.id == event_id)
        result = await db.execute(stmt)
        event = result.scalar_one_or_none()

        if not event:
            return None

        # Verificar permisos: admin o organizer del evento
        stmt_org = select(Organizer).where(
            Organizer.id == event.organizer_id,
            Organizer.user_id == user_id
        )
        result_org = await db.execute(stmt_org)
        organizer = result_org.scalar_one_or_none()

        if not organizer:
            # TODO: Verificar si el usuario es admin
            raise ValueError("No tienes permisos para editar este evento")

        # Actualizar campos
        if "name" in event_data:
            event.name = event_data["name"]
        if "location_text" in event_data:
            event.location_text = event_data["location_text"]
        if "starts_at" in event_data:
            event.starts_at = event_data["starts_at"]
        if "ends_at" in event_data:
            event.ends_at = event_data["ends_at"]
        if "capacity_total" in event_data:
            # Ajustar capacity_available si cambia capacity_total
            new_total = event_data["capacity_total"]
            if new_total < event.capacity_total:
                # Reducir capacidad disponible proporcionalmente
                event.capacity_available = min(
                    event.capacity_available,
                    new_total - (event.capacity_total - event.capacity_available)
                )
            else:
                # Aumentar capacidad disponible
                event.capacity_available += (new_total - event.capacity_total)
            event.capacity_total = new_total
        if "capacity_available" in event_data:
            event.capacity_available = event_data["capacity_available"]
        if "allow_children" in event_data:
            event.allow_children = event_data["allow_children"]
        if "category" in event_data:
            event.category = event_data["category"]
        if "description" in event_data:
            event.description = event_data["description"]
        if "image_url" in event_data:
            event.image_url = event_data["image_url"]

        # Manejar actualización de precio del ticket General
        if "price" in event_data and event_data["price"] is not None:
            # Buscar ticket_type General existente
            stmt_tt = select(TicketType).where(
                TicketType.event_id == event_id,
                TicketType.name == "General",
                TicketType.is_child == False
            )
            result_tt = await db.execute(stmt_tt)
            ticket_type = result_tt.scalar_one_or_none()

            if ticket_type:
                # Actualizar precio existente
                ticket_type.price = event_data["price"]
            else:
                # Crear nuevo ticket_type General
                new_ticket_type = TicketType(
                    event_id=event_id,
                    name="General",
                    price=event_data["price"],
                    is_child=False
                )
                db.add(new_ticket_type)

        # ✅ Manejar actualización de servicios del evento
        if "services" in event_data:
            from shared.database.models import EventService as EventServiceModel            # Eliminar servicios existentes
            from sqlalchemy import delete as sql_delete
            delete_stmt = sql_delete(EventServiceModel).where(EventServiceModel.event_id == event_id)
            await db.execute(delete_stmt)
            await db.flush()  # ✅ Aplicar eliminaciones inmediatamente

            # Crear nuevos servicios
            if event_data["services"]:
                for service_data in event_data["services"]:
                    stock = service_data.get("stock", service_data.get("stock_total", 0))
                    event_service = EventServiceModel(
                        event_id=event_id,
                        name=service_data.get("name"),
                        description=service_data.get("description"),
                        price=service_data.get("price", 0),
                        service_type=service_data.get("service_type", "general"),
                        stock=stock,
                        stock_available=service_data.get("stock_available", stock),
                        min_age=service_data.get("min_age"),
                        max_age=service_data.get("max_age")
                    )
                    db.add(event_service)

        await db.commit()
        await db.refresh(event)

        # Invalidar cache
        await EventService._invalidate_events_cache()

        return event

    @staticmethod
    async def delete_event(
        db: AsyncSession,
        event_id: str,
        user_id: str
    ) -> bool:
        """
        Eliminar evento

        Requiere: admin role o ser el organizer del evento
        Compatible con: adminService.deleteEvent()
        """
        stmt = select(Event).where(Event.id == event_id)
        result = await db.execute(stmt)
        event = result.scalar_one_or_none()

        if not event:
            return False

        # Verificar permisos
        stmt_org = select(Organizer).where(
            Organizer.id == event.organizer_id,
            Organizer.user_id == user_id
        )
        result_org = await db.execute(stmt_org)
        organizer = result_org.scalar_one_or_none()

        if not organizer:
            # TODO: Verificar si el usuario es admin
            raise ValueError("No tienes permisos para eliminar este evento")

        # Verificar que no haya tickets vendidos
        if event.capacity_available < event.capacity_total:
            raise ValueError("No se puede eliminar un evento con tickets vendidos")

        await db.delete(event)
        await db.commit()

        # Invalidar cache
        await EventService._invalidate_events_cache()

        return True


