"""Rutas de gestión de eventos"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict
from datetime import datetime
from shared.database.session import get_db
from shared.auth.dependencies import get_current_user, get_current_admin, get_optional_user
from services.event_management.models.event import (
    EventResponse,
    EventCreate,
    EventUpdate,
    TicketTypeResponse,
    EventServiceResponse
)
from services.event_management.services.event_service import EventService


router = APIRouter()


@router.get("", response_model=List[EventResponse])
async def get_events(
    category: Optional[str] = Query(None, description="Categoría del evento"),
    search: Optional[str] = Query(None, description="Búsqueda por nombre o ubicación"),
    date_from: Optional[datetime] = Query(None, description="Fecha desde"),
    date_to: Optional[datetime] = Query(None, description="Fecha hasta"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[Dict] = Depends(get_optional_user)
):
    """
    Listar eventos con filtros

    Compatible con: eventsService.getEvents()
    Endpoint público (no requiere autenticación)
    """
    service = EventService()

    events = await service.get_events(
        db=db,
        category=category,
        search=search,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset
    )

    return [
        EventResponse(
            id=str(event.id),
            organizer_id=str(event.organizer_id),
            name=event.name,
            location_text=getattr(event, 'location_text', None),
            point_location=getattr(event, 'point_location', None),
            starts_at=event.starts_at,
            ends_at=getattr(event, 'ends_at', None),
            capacity_total=event.capacity_total,
            capacity_available=event.capacity_available,
            allow_children=getattr(event, 'allow_children', False),
            category=getattr(event, 'category', 'otro'),
            description=getattr(event, 'description', None),
            image_url=getattr(event, 'image_url', None),
            ticket_types=[
                TicketTypeResponse(
                    id=str(tt.id),
                    event_id=str(tt.event_id),
                    name=tt.name,
                    price=float(tt.price),
                    is_child=tt.is_child,
                    created_at=tt.created_at
                )
                for tt in (event.ticket_types if hasattr(event, 'ticket_types') else [])
            ],
            event_services=[
                EventServiceResponse(
                    id=str(es.id),
                    event_id=str(es.event_id),
                    name=es.name,
                    description=es.description,
                    price=float(es.price),
                    service_type=getattr(es, 'service_type', 'general'),
                    stock_total=getattr(es, 'stock', 0),
                    stock_available=getattr(es, 'stock_available', 0),
                    min_age=es.min_age,
                    max_age=es.max_age,
                    created_at=es.created_at
                )
                for es in (event.event_services if hasattr(event, 'event_services') else [])
            ],
            created_at=event.created_at,
            updated_at=getattr(event, 'updated_at', None)
        )
        for event in events
    ]


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[Dict] = Depends(get_optional_user)
):
    """
    Obtener evento por ID

    Compatible con: eventsService.getEventById()
    Endpoint público (no requiere autenticación)
    """
    service = EventService()
    event = await service.get_event_by_id(db, event_id)

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evento no encontrado"
        )

    return EventResponse(
        id=str(event.id),
        organizer_id=str(event.organizer_id),
        name=event.name,
        location_text=getattr(event, 'location_text', None),
        point_location=getattr(event, 'point_location', None),
        starts_at=event.starts_at,
        ends_at=getattr(event, 'ends_at', None),
        capacity_total=event.capacity_total,
        capacity_available=event.capacity_available,
        allow_children=getattr(event, 'allow_children', False),
        category=getattr(event, 'category', 'otro'),
        description=getattr(event, 'description', None),
        image_url=getattr(event, 'image_url', None),
        ticket_types=[
            TicketTypeResponse(
                id=str(tt.id),
                event_id=str(tt.event_id),
                name=tt.name,
                price=float(tt.price),
                is_child=tt.is_child,
                created_at=tt.created_at
            )
            for tt in (event.ticket_types if hasattr(event, 'ticket_types') else [])
        ],
        event_services=[
            EventServiceResponse(
                id=str(es.id),
                event_id=str(es.event_id),
                name=es.name,
                description=es.description,
                price=float(es.price),
                service_type=getattr(es, 'service_type', 'general'),
                stock_total=getattr(es, 'stock', 0),
                stock_available=getattr(es, 'stock_available', 0),
                min_age=es.min_age,
                max_age=es.max_age,
                created_at=es.created_at
            )
            for es in (event.event_services if hasattr(event, 'event_services') else [])
        ],
        created_at=event.created_at,
        updated_at=getattr(event, 'updated_at', None)
    )


@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    event_data: EventCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Dict = Depends(get_current_admin)
):
    """
    Crear nuevo evento

    Requiere: admin role
    Compatible con: adminService.createEvent()
    """
    service = EventService()

    try:
        event = await service.create_event(
            db=db,
            event_data=event_data.dict(),
            user_id=current_user.get("user_id")
        )

        return EventResponse(
            id=str(event.id),
            organizer_id=str(event.organizer_id),
            name=event.name,
            location_text=event.location_text,
            starts_at=event.starts_at,
            ends_at=event.ends_at,
            capacity_total=event.capacity_total,
            capacity_available=event.capacity_available,
            allow_children=event.allow_children,
            created_at=event.created_at
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/{event_id}", response_model=EventResponse)
async def update_event(
    event_id: str,
    event_data: EventUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Dict = Depends(get_current_admin)
):
    """
    Actualizar evento

    Requiere: admin role o ser el organizer del evento
    Compatible con: adminService.updateEvent()
    """
    service = EventService()

    try:
        event = await service.update_event(
            db=db,
            event_id=event_id,
            event_data=event_data.dict(exclude_unset=True),
            user_id=current_user.get("user_id")
        )

        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Evento no encontrado"
            )

        return EventResponse(
            id=str(event.id),
            organizer_id=str(event.organizer_id),
            name=event.name,
            location_text=event.location_text,
            starts_at=event.starts_at,
            ends_at=event.ends_at,
            capacity_total=event.capacity_total,
            capacity_available=event.capacity_available,
            allow_children=event.allow_children,
            created_at=event.created_at
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Dict = Depends(get_current_admin)
):
    """
    Eliminar evento

    Requiere: admin role o ser el organizer del evento
    Compatible con: adminService.deleteEvent()
    """
    service = EventService()

    try:
        success = await service.delete_event(
            db=db,
            event_id=event_id,
            user_id=current_user.get("user_id")
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Evento no encontrado"
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

