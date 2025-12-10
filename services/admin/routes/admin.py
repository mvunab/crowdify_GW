"""Rutas de administración"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload
from typing import Dict, Optional, List
from datetime import datetime
import json

from shared.database.session import get_db
from shared.auth.dependencies import get_current_admin, get_current_admin_or_coordinator
from services.admin.models.admin import (
    OrganizerResponse,
    ScannerResponse,
    ScannersListResponse,
    UserResponse,
    UsersListResponse,
    UpdateUserRoleRequest,
    CreateScannerRequest,
    DeleteScannerResponse,
    DashboardStatsResponse,
    AdminEventsListResponse,
    AdminEventResponse,
    AdminTicketsListResponse,
    AdminTicketResponse,
    ChildrenExportResponse,
    ChildExportData,
    ChildMedication,
    ChildComprador,
    TicketTypeInfo,
    EventServiceInfo,
    OrganizerInfo,
    EventStats,
    ServiceStats,
    OrderUserInfo,
    OrderInfo,
    OrderItemInfo,
    ChildDetails,
    TicketsSummary,
    EventInfo,
    ChildTicketInfo,
    GlobalChildTicketsResponse,
    OrdersListResponse,
    OrderResponse,
    TicketDetailResponse,
    CreateManualTicketsRequest,
    CreateManualTicketsResponse
)
from services.admin.services.organizer_service import OrganizerService
from services.admin.services.user_management_service import UserManagementService
from services.admin.services.stats_service import StatsService
from services.admin.services.admin_events_service import AdminEventsService
from services.admin.services.tickets_admin_service import TicketsAdminService
from services.admin.services.admin_orders_service import AdminOrdersService
from services.admin.services.manual_tickets_service import ManualTicketsService
from shared.database.models import (
    Ticket as TicketModel,
    TicketChildDetail as TicketChildDetailsModel,
    TicketChildMedication as TicketChildMedicationModel,
    Event as EventModel,
    Organizer as OrganizerModel
)


router = APIRouter()


# ==================== ORGANIZER ====================

@router.get("/organizer", response_model=OrganizerResponse)
async def get_organizer_info(
    db: AsyncSession = Depends(get_db),
    current_user: Dict = Depends(get_current_admin)
):
    """
    Obtener información del organizador asociado al usuario actual
    
    Si el usuario no tiene un organizador asociado, se crea automáticamente
    uno con valores por defecto basados en la información del usuario.

    Requiere autenticación de admin
    """
    service = OrganizerService()

    # Intentar obtener el organizador existente
    organizer = await service.get_organizer_by_user_id(
        db=db,
        user_id=current_user.get("user_id")
    )

    # Si no existe, crear uno automáticamente
    if not organizer:
        organizer = await service.create_organizer_for_user(
            db=db,
            user_id=current_user.get("user_id")
        )

    if not organizer:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener o crear organizador"
        )

    return OrganizerResponse(
        id=str(organizer.id),
        org_name=organizer.org_name,
        contact_email=organizer.contact_email,
        contact_phone=organizer.contact_phone,
        user_id=str(organizer.user_id),
        created_at=organizer.created_at,
        updated_at=organizer.updated_at
    )


# ==================== SCANNERS & USERS ====================

@router.get("/scanners", response_model=ScannersListResponse)
async def get_scanners(
    db: AsyncSession = Depends(get_db),
    current_user: Dict = Depends(get_current_admin)
):
    """
    Listar todos los usuarios con rol scanner

    Requiere autenticación de admin
    """
    service = UserManagementService()

    scanners = await service.get_scanners(db=db)

    return ScannersListResponse(
        scanners=[
            ScannerResponse(
                id=str(scanner.id),
                email=scanner.email,
                first_name=scanner.first_name,
                last_name=scanner.last_name,
                role=scanner.role,
                created_at=scanner.created_at
            )
            for scanner in scanners
        ]
    )


@router.get("/users", response_model=UsersListResponse)
async def get_users(
    role: str = Query("user", description="Rol a filtrar"),
    db: AsyncSession = Depends(get_db),
    current_user: Dict = Depends(get_current_admin)
):
    """
    Listar usuarios por rol

    Requiere autenticación de admin
    """
    service = UserManagementService()

    users = await service.get_users_by_role(db=db, role=role)

    return UsersListResponse(
        users=[
            UserResponse(
                id=str(user.id),
                email=user.email,
                first_name=user.first_name,
                last_name=user.last_name,
                role=user.role,
                created_at=user.created_at
            )
            for user in users
        ]
    )


@router.put("/users/{user_id}/role", response_model=UserResponse)
async def update_user_role(
    user_id: str,
    request: UpdateUserRoleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Dict = Depends(get_current_admin)
):
    """
    Cambiar el rol de un usuario

    Requiere autenticación de admin
    No permite cambiar el propio rol
    """
    service = UserManagementService()

    try:
        user = await service.update_user_role(
            db=db,
            user_id=user_id,
            new_role=request.role,
            current_user_id=current_user.get("user_id")
        )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )

        return UserResponse(
            id=str(user.id),
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            role=user.role,
            created_at=user.created_at
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/scanners", response_model=ScannerResponse, status_code=status.HTTP_201_CREATED)
async def create_scanner(
    request: CreateScannerRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Dict = Depends(get_current_admin)
):
    """
    Crear un nuevo usuario con rol scanner

    Requiere autenticación de admin
    Nota: Solo crea en DB, no en Supabase Auth (requiere configuración adicional)
    """
    service = UserManagementService()

    try:
        scanner = await service.create_scanner(
            db=db,
            email=request.email,
            first_name=request.first_name,
            last_name=request.last_name,
            password=request.password
        )

        return ScannerResponse(
            id=str(scanner.id),
            email=scanner.email,
            first_name=scanner.first_name,
            last_name=scanner.last_name,
            role=scanner.role,
            created_at=scanner.created_at
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/scanners/{scanner_id}", response_model=DeleteScannerResponse)
async def delete_scanner(
    scanner_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Dict = Depends(get_current_admin)
):
    """
    Remover rol scanner de un usuario (degradar a user)

    Requiere autenticación de admin
    No elimina el usuario, solo cambia su rol
    """
    service = UserManagementService()

    try:
        user = await service.remove_scanner_role(
            db=db,
            scanner_id=scanner_id
        )

        return DeleteScannerResponse(
            message="Scanner role removed successfully",
            user_id=str(user.id)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ==================== STATS ====================

@router.get("/stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    date_from: Optional[datetime] = Query(None, description="Fecha desde"),
    date_to: Optional[datetime] = Query(None, description="Fecha hasta"),
    db: AsyncSession = Depends(get_db),
    current_user: Dict = Depends(get_current_admin)
):
    """
    Obtener estadísticas del dashboard

    Requiere autenticación de admin
    """
    # Obtener organizer_id del usuario (crear automáticamente si no existe)
    organizer_service = OrganizerService()
    organizer = await organizer_service.get_organizer_by_user_id(
        db=db,
        user_id=current_user.get("user_id")
    )

    # Si no existe, crear uno automáticamente
    if not organizer:
        organizer = await organizer_service.create_organizer_for_user(
            db=db,
            user_id=current_user.get("user_id")
        )

    if not organizer:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener o crear organizador"
        )

    # Calcular estadísticas
    stats_service = StatsService()
    stats = await stats_service.get_dashboard_stats(
        db=db,
        organizer_id=str(organizer.id),
        date_from=date_from,
        date_to=date_to
    )

    return DashboardStatsResponse(**stats)


# ==================== EVENTS ====================

@router.get("/events", response_model=AdminEventsListResponse)
async def get_admin_events(
    event_status: str = Query("all", description="Filtro de estado: upcoming, ongoing, past, all"),
    sort: str = Query("starts_at_desc", description="Ordenamiento: starts_at_asc, starts_at_desc, revenue_desc"),
    my_events: bool = Query(False, description="Si es True, solo devuelve eventos del organizador del usuario actual"),
    db: AsyncSession = Depends(get_db),
    current_user: Dict = Depends(get_current_admin_or_coordinator)
):
    """
    Listar eventos con estadísticas

    - Si `my_events=true`: Solo devuelve eventos del organizador del usuario actual
    - Si `my_events=false` (default): Devuelve todos los eventos (solo para coordinators o super admins)
    
    Requiere autenticación de admin o coordinator
    """
    role = current_user.get("role")
    
    # Determinar organizer_id según el parámetro my_events
    organizer_id = None
    if my_events:
        # Obtener el organizador del usuario actual
        organizer_service = OrganizerService()
        organizer = await organizer_service.get_organizer_by_user_id(
            db=db,
            user_id=current_user.get("user_id")
        )
        
        # Si no existe, crear uno automáticamente
        if not organizer:
            organizer = await organizer_service.create_organizer_for_user(
                db=db,
                user_id=current_user.get("user_id")
            )
        
        if organizer:
            organizer_id = str(organizer.id)
        else:
            # Si no se puede obtener/crear organizador, devolver lista vacía
            return AdminEventsListResponse(events=[])

    events_service = AdminEventsService()
    events_with_stats = await events_service.get_events_with_stats(
        db=db,
        organizer_id=organizer_id,  # None = todos los eventos, str = filtrar por organizador
        status=event_status,
        sort=sort
    )

    # Formatear respuesta
    admin_events = []
    for item in events_with_stats:
        event = item["event"]
        stats = item["stats"]

        admin_events.append(
            AdminEventResponse(
                id=str(event.id),
                name=event.name,
                description=event.description,  # ✅ Agregado
                location_text=event.location_text,
                point_location=event.point_location,
                starts_at=event.starts_at,
                ends_at=event.ends_at,
                capacity_total=event.capacity_total,
                capacity_available=event.capacity_available,
                category=event.category,
                image_url=event.image_url,
                organizer=OrganizerInfo(
                    id=str(event.organizer.id),
                    org_name=event.organizer.org_name
                ),
                ticket_types=[
                    TicketTypeInfo(
                        id=str(tt.id),
                        name=tt.name,
                        price=float(tt.price),
                        is_child=tt.is_child
                    )
                    for tt in event.ticket_types
                ],
                event_services=[  # ✅ Agregado - Servicios completos
                    EventServiceInfo(
                        id=str(es.id),
                        name=es.name,
                        description=es.description,
                        price=float(es.price),
                        service_type=es.service_type,
                        stock_total=es.stock,
                        stock_available=es.stock_available,
                        min_age=es.min_age,
                        max_age=es.max_age
                    )
                    for es in event.event_services
                ],
                stats=EventStats(
                    tickets_sold=stats["tickets_sold"],
                    tickets_remaining=stats["tickets_remaining"],
                    revenue=stats["revenue"],
                    sales_percentage=stats["sales_percentage"],
                    services_stats=[
                        ServiceStats(**service_stat)
                        for service_stat in stats["services_stats"]
                    ]
                )
            )
        )

    return AdminEventsListResponse(events=admin_events)


# ==================== TICKETS ====================

@router.get("/events/{event_id}/tickets", response_model=AdminTicketsListResponse)
async def get_event_tickets(
    event_id: str,
    ticket_status: Optional[str] = Query(None, description="Filtrar por estado"),
    is_child: Optional[bool] = Query(None, description="Filtrar por tipo"),
    include_child_details: bool = Query(True, description="Incluir detalles de niños"),
    search: Optional[str] = Query(None, description="Buscar por nombre o documento"),
    db: AsyncSession = Depends(get_db),
    current_user: Dict = Depends(get_current_admin_or_coordinator)
):
    """
    Listar todos los tickets de un evento con detalles completos

    Requiere autenticación de admin o coordinator
    """

    tickets_service = TicketsAdminService()

    try:
        result = await tickets_service.get_event_tickets(
            db=db,
            event_id=event_id,
            status=ticket_status,
            is_child=is_child,
            include_child_details=include_child_details,
            search=search
        )

        event = result["event"]
        tickets = result["tickets"]
        summary = result["summary"]

        # Formatear tickets
        formatted_tickets = []
        for ticket in tickets:
            # Order item info
            order_item_info = None
            if ticket.order_item and ticket.order_item.order:
                order = ticket.order_item.order
                order_user = order.user

                order_item_info = OrderItemInfo(
                    order_id=str(ticket.order_item.order_id),
                    order=OrderInfo(
                        user=OrderUserInfo(
                            email=order_user.email if order_user else "",
                            first_name=order_user.first_name if order_user else None,
                            last_name=order_user.last_name if order_user else None
                        )
                    )
                )

            # Child details
            child_details_data = None
            if ticket.is_child and ticket.child_details:
                cd = ticket.child_details
                medications = [
                    ChildMedication(
                        nombre_medicamento=med.nombre_medicamento,
                        frecuencia=med.frecuencia,
                        observaciones=med.observaciones
                    )
                    for med in cd.medications
                ] if cd.medications else []

                child_details_data = ChildDetails(
                    nombre=cd.nombre,
                    rut=cd.rut,
                    tipo_documento=cd.tipo_documento,
                    fecha_nacimiento=cd.fecha_nacimiento.isoformat() if cd.fecha_nacimiento else "",
                    edad=cd.edad,
                    correo=cd.correo,
                    toma_medicamento=cd.toma_medicamento,
                    es_alergico=cd.es_alergico,
                    detalle_alergias=cd.detalle_alergias,
                    nombre_contacto_emergencia=cd.nombre_contacto_emergencia,
                    parentesco_contacto_emergencia=cd.parentesco_contacto_emergencia,
                    numero_emergencia=cd.numero_emergencia,
                    pais_telefono=cd.pais_telefono,
                    iglesia=cd.iglesia,
                    tiene_necesidad_especial=cd.tiene_necesidad_especial,
                    detalle_necesidad_especial=cd.detalle_necesidad_especial,
                    medicamentos=medications
                )

            if order_item_info:
                formatted_tickets.append(
                    AdminTicketResponse(
                        id=str(ticket.id),
                        holder_first_name=ticket.holder_first_name,
                        holder_last_name=ticket.holder_last_name,
                        holder_document_type=ticket.holder_document_type,
                        holder_document_number=ticket.holder_document_number,
                        is_child=ticket.is_child,
                        status=ticket.status,
                        qr_signature=ticket.qr_signature,
                        issued_at=ticket.issued_at,
                        validated_at=ticket.validated_at,
                        used_at=ticket.used_at,
                        order_item=order_item_info,
                        child_details=child_details_data
                    )
                )

        return AdminTicketsListResponse(
            event=EventInfo(
                id=str(event.id),
                name=event.name
            ),
            tickets=formatted_tickets,
            summary=TicketsSummary(**summary)
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/events/{event_id}/tickets/children/export", response_model=ChildrenExportResponse)
async def export_children_tickets(
    event_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Dict = Depends(get_current_admin_or_coordinator)
):
    """
    Exportar datos de niños en formato JSON para generar Excel en frontend

    Requiere autenticación de admin o coordinator
    """

    tickets_service = TicketsAdminService()

    try:
        result = await tickets_service.export_children_tickets(
            db=db,
            event_id=event_id
        )

        event = result["event"]
        tickets = result["tickets"]

        # Formatear children
        children = []
        for ticket in tickets:
            if not ticket.child_details:
                continue

            cd = ticket.child_details

            # Medicamentos
            medications = [
                ChildMedication(
                    nombre_medicamento=med.nombre_medicamento,
                    frecuencia=med.frecuencia,
                    observaciones=med.observaciones
                )
                for med in cd.medications
            ] if cd.medications else []

            # Comprador
            comprador_nombre = ""
            comprador_email = ""
            if ticket.order_item and ticket.order_item.order and ticket.order_item.order.user:
                user = ticket.order_item.order.user
                comprador_nombre = f"{user.first_name or ''} {user.last_name or ''}".strip()
                comprador_email = user.email

            children.append(
                ChildExportData(
                    ticket_id=str(ticket.id),
                    nombre=cd.nombre,
                    rut=cd.rut,
                    tipo_documento=cd.tipo_documento,
                    fecha_nacimiento=cd.fecha_nacimiento.isoformat() if cd.fecha_nacimiento else "",
                    edad=cd.edad,
                    correo=cd.correo,
                    toma_medicamento=cd.toma_medicamento,
                    es_alergico=cd.es_alergico,
                    detalle_alergias=cd.detalle_alergias,
                    nombre_contacto_emergencia=cd.nombre_contacto_emergencia,
                    parentesco_contacto_emergencia=cd.parentesco_contacto_emergencia,
                    numero_emergencia=cd.numero_emergencia,
                    pais_telefono=cd.pais_telefono,
                    iglesia=cd.iglesia,
                    tiene_necesidad_especial=cd.tiene_necesidad_especial,
                    detalle_necesidad_especial=cd.detalle_necesidad_especial,
                    medicamentos=medications,
                    ticket_status=ticket.status,
                    comprador=ChildComprador(
                        nombre=comprador_nombre,
                        email=comprador_email
                    )
                )
            )

        return ChildrenExportResponse(
            event=EventInfo(
                id=str(event.id),
                name=event.name
            ),
            children=children
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/tickets/children", response_model=GlobalChildTicketsResponse)
async def get_all_children_tickets(
    search: Optional[str] = Query(None, description="Buscar por nombre, RUT o iglesia"),
    db: AsyncSession = Depends(get_db),
    current_user: Dict = Depends(get_current_admin_or_coordinator)
):
    """
    Obtener todos los tickets infantiles de todos los eventos
    Requiere autenticación de admin o coordinator
    """
    try:
        # Admin y coordinator ven TODOS los tickets infantiles (sin filtro de organizer_id)

        # Query: Join tickets -> ticket_child_details -> events
        # Solo filtrar por is_child=true
        # Eager load medications relationship
        query = (
            select(TicketModel, TicketChildDetailsModel, EventModel)
            .join(TicketChildDetailsModel, TicketModel.id == TicketChildDetailsModel.ticket_id)
            .join(EventModel, TicketModel.event_id == EventModel.id)
            .options(selectinload(TicketChildDetailsModel.medications))
            .where(TicketModel.is_child == True)  # ✅ Solo filtrar por is_child
            .order_by(TicketModel.issued_at.desc())
        )

        # Apply search filter if provided
        if search:
            search_filter = or_(
                TicketChildDetailsModel.nombre.ilike(f"%{search}%"),
                TicketChildDetailsModel.rut.ilike(f"%{search}%"),
                TicketChildDetailsModel.iglesia.ilike(f"%{search}%")
            )
            query = query.where(search_filter)

        result = await db.execute(query)
        rows = result.all()

        # Build response
        child_tickets = []
        for ticket, child_details, event in rows:
            # Get medications from relationship (TicketChildMedication objects)
            medicamentos = []
            if child_details.medications:
                medicamentos = [
                    {
                        "nombre_medicamento": med.nombre_medicamento,
                        "frecuencia": med.frecuencia,
                        "observaciones": med.observaciones
                    }
                    for med in child_details.medications
                ]

            child_info = ChildTicketInfo(
                ticket_id=str(ticket.id),
                event_id=str(event.id),
                event_name=event.name,
                event_date=event.starts_at.isoformat() if event.starts_at else "",
                nombre=child_details.nombre,
                rut=child_details.rut,
                edad=child_details.edad,
                es_alergico=child_details.es_alergico,
                detalle_alergias=child_details.detalle_alergias,
                toma_medicamento=child_details.toma_medicamento,
                medicamentos=medicamentos,
                tiene_necesidad_especial=child_details.tiene_necesidad_especial,
                detalle_necesidad_especial=child_details.detalle_necesidad_especial,
                iglesia=child_details.iglesia,
                nombre_contacto_emergencia=child_details.nombre_contacto_emergencia,
                parentesco_contacto_emergencia=child_details.parentesco_contacto_emergencia,
                numero_emergencia=child_details.numero_emergencia,
                issued_at=ticket.issued_at.isoformat() if ticket.issued_at else ""
            )
            child_tickets.append(child_info)

        return GlobalChildTicketsResponse(
            tickets=child_tickets,
            total_count=len(child_tickets)
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener tickets infantiles: {str(e)}"
        )


# ==================== PENDING ORDERS ====================

@router.get("/orders/pending", response_model=OrdersListResponse)
async def get_pending_orders(
    db: AsyncSession = Depends(get_db),
    current_user: Dict = Depends(get_current_admin)
):
    """
    Obtener todas las órdenes pendientes con método de pago bank_transfer

    Requiere autenticación de admin
    """
    service = AdminOrdersService()

    try:
        orders_data = await service.get_pending_orders(db=db)

        # Convertir a modelos Pydantic
        orders = [
            OrderResponse(
                id=order["id"],
                user_id=order["user_id"],
                user_email=order["user_email"],
                user_name=order["user_name"],
                subtotal=order["subtotal"],
                discount_total=order["discount_total"],
                total=order["total"],
                commission_total=order["commission_total"],
                currency=order["currency"],
                status=order["status"],
                payment_provider=order["payment_provider"],
                payment_reference=order["payment_reference"],
                receipt_url=order["receipt_url"],
                created_at=order["created_at"],
                updated_at=order["updated_at"],
                paid_at=order["paid_at"],
                tickets_count=order["tickets_count"],
                tickets=None  # No incluimos tickets en la lista
            )
            for order in orders_data
        ]

        return OrdersListResponse(orders=orders)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener órdenes pendientes: {str(e)}"
        )


@router.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order_detail(
    order_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Dict = Depends(get_current_admin)
):
    """
    Obtener detalle completo de una orden específica, incluyendo todos los tickets asociados

    Requiere autenticación de admin
    """
    service = AdminOrdersService()

    try:
        order_data = await service.get_order_detail(db=db, order_id=order_id)

        if not order_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Orden no encontrada"
            )

        # Convertir tickets a modelos Pydantic
        tickets = None
        if order_data.get("tickets"):
            tickets = [
                TicketDetailResponse(**ticket)
                for ticket in order_data["tickets"]
            ]

        return OrderResponse(
            id=order_data["id"],
            user_id=order_data["user_id"],
            user_email=order_data["user_email"],
            user_name=order_data["user_name"],
            subtotal=order_data["subtotal"],
            discount_total=order_data["discount_total"],
            total=order_data["total"],
            commission_total=order_data["commission_total"],
            currency=order_data["currency"],
            status=order_data["status"],
            payment_provider=order_data["payment_provider"],
            payment_reference=order_data["payment_reference"],
            receipt_url=order_data["receipt_url"],
            created_at=order_data["created_at"],
            updated_at=order_data["updated_at"],
            paid_at=order_data["paid_at"],
            tickets_count=order_data["tickets_count"],
            tickets=tickets
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener detalle de orden: {str(e)}"
        )


@router.post("/orders/{order_id}/confirm", response_model=OrderResponse)
async def confirm_order(
    order_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Dict = Depends(get_current_admin)
):
    """
    Confirma una orden pendiente.
    
    Acciones:
    1. Cambia el estado de la orden de 'pending' → 'completed'
    2. Cambia el estado de todos los tickets asociados de 'pending' → 'issued'
    3. Establece paid_at en la orden
    
    ⚠️ IMPORTANTE: Usa stored procedure para garantizar transacciones atómicas
    
    Requiere autenticación de admin
    """
    service = AdminOrdersService()

    try:
        # Confirmar orden (usando stored procedure)
        order_data = await service.confirm_order(db=db, order_id=order_id)

        if not order_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Orden no encontrada o no está en estado pendiente"
            )

        # Convertir tickets a modelos Pydantic
        tickets = None
        if order_data.get("tickets"):
            try:
                tickets = [
                    TicketDetailResponse(**ticket)
                    for ticket in order_data["tickets"]
                ]
            except Exception as ticket_error:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error creating ticket responses: {ticket_error}, tickets data: {order_data.get('tickets')}")
                tickets = []

        try:
            response = OrderResponse(
                id=order_data["id"],
                user_id=order_data["user_id"],
                user_email=order_data["user_email"],
                user_name=order_data["user_name"],
                subtotal=order_data["subtotal"],
                discount_total=order_data["discount_total"],
                total=order_data["total"],
                commission_total=order_data["commission_total"],
                currency=order_data["currency"],
                status=order_data["status"],
                payment_provider=order_data["payment_provider"],
                payment_reference=order_data["payment_reference"],
                receipt_url=order_data["receipt_url"],
                created_at=order_data["created_at"],
                updated_at=order_data["updated_at"],
                paid_at=order_data["paid_at"],
                tickets_count=order_data["tickets_count"],
                tickets=tickets
            )
            return response
        except Exception as response_error:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error creating OrderResponse: {response_error}, order_data keys: {list(order_data.keys())}, order_data: {order_data}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al construir respuesta: {str(response_error)}"
            )

    except ValueError as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"ValueError confirming order {order_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al confirmar orden: {str(e)}"
            )


# ==================== MANUAL TICKETS ====================

@router.post("/manual-tickets", response_model=CreateManualTicketsResponse, status_code=status.HTTP_201_CREATED)
async def create_manual_tickets(
    request: CreateManualTicketsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Dict = Depends(get_current_admin)
):
    """
    Crear tickets manualmente desde el admin
    
    Útil para pagos realizados fuera del sistema
    
    Requiere autenticación de admin
    """
    service = ManualTicketsService()

    try:
        result = await service.create_manual_tickets(
            db=db,
            event_id=request.event_id,
            buyer={
                "first_name": request.buyer.first_name,
                "last_name": request.buyer.last_name,
                "email": request.buyer.email,
                "document_type": request.buyer.document_type,
                "document_number": request.buyer.document_number,
            },
            quantity=request.quantity,
            services=[
                {
                    "service_id": s.service_id,
                    "quantity": s.quantity
                }
                for s in (request.services or [])
            ] if request.services else None,
            notes=request.notes
        )

        return CreateManualTicketsResponse(
            order_id=result["order_id"],
            tickets_created=result["tickets_created"],
            message=f"Se crearon {result['tickets_created']} ticket(s) exitosamente"
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear tickets manualmente: {str(e)}"
        )
