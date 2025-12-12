from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from io import BytesIO
import qrcode
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib.colors import HexColor
from reportlab.lib import colors
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime

app = FastAPI(title="PDF/QR Service")


class TicketData(BaseModel):
    ticket_id: str
    qr_signature: str
    holder_first_name: str
    holder_last_name: str
    holder_email: Optional[str] = None
    event: Dict[str, Any]
    issued_at: Optional[str] = None


class BulkTicketsRequest(BaseModel):
    """Request para generar PDF con múltiples tickets"""
    tickets: List[TicketData]
    order_id: Optional[str] = None
    buyer_name: Optional[str] = None
    buyer_email: Optional[str] = None


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/qr/{text}")
def qr_png(text: str):
    img = qrcode.make(text)
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")


def generate_ticket_pdf(ticket_data: TicketData) -> BytesIO:
    """
    Genera un PDF profesional del ticket usando ReportLab
    """
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Colores
    primary_color = HexColor("#2563eb")
    secondary_color = HexColor("#1f2937")
    text_color = HexColor("#6b7280")
    bg_color = HexColor("#f8fafc")

    # Header con fondo degradado
    c.setFillColor(bg_color)
    c.rect(0, height - 80*mm, width, 80*mm, fill=1, stroke=0)

    # Logo/Nombre de la app
    c.setFillColor(primary_color)
    c.setFont("Helvetica-Bold", 28)
    c.drawCentredString(width/2, height - 30*mm, "Crowdify")

    # Línea decorativa
    c.setStrokeColor(HexColor("#e5e7eb"))
    c.setLineWidth(2)
    c.line(40*mm, height - 50*mm, width - 40*mm, height - 50*mm)

    # Información del evento
    y_pos = height - 70*mm
    event = ticket_data.event

    # Título del evento
    event_name = event.get('name') or event.get('title') or event.get('nombre') or 'Evento'
    c.setFillColor(secondary_color)
    c.setFont("Helvetica-Bold", 24)

    # Dividir título si es muy largo
    words = event_name.split()
    lines = []
    current_line = words[0] if words else ""
    for word in words[1:]:
        test_line = current_line + " " + word
        if c.stringWidth(test_line, "Helvetica-Bold", 24) < width - 80*mm:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word
    lines.append(current_line)

    for i, line in enumerate(lines):
        c.drawCentredString(width/2, y_pos - i*8*mm, line)

    y_pos -= len(lines) * 8*mm + 10*mm

    # Generar QR Code
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(ticket_data.qr_signature)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")

    # Guardar QR en buffer temporal
    qr_buffer = BytesIO()
    qr_img.save(qr_buffer, format="PNG")
    qr_buffer.seek(0)

    # Dibujar QR code centrado
    qr_size = 60*mm
    qr_x = (width - qr_size) / 2
    qr_y = y_pos - qr_size - 10*mm

    # Borde alrededor del QR
    c.setStrokeColor(HexColor("#e5e7eb"))
    c.setLineWidth(1)
    c.rect(qr_x - 2*mm, qr_y - 2*mm, qr_size + 4*mm, qr_size + 4*mm, fill=0, stroke=1)

    # Dibujar imagen QR
    c.drawImage(ImageReader(qr_buffer), qr_x, qr_y, width=qr_size, height=qr_size)

    y_pos = qr_y - 20*mm

    # Instrucción de escaneo
    c.setFillColor(text_color)
    c.setFont("Helvetica", 12)
    c.drawCentredString(width/2, y_pos, "Escanea este código en la entrada")

    y_pos -= 15*mm

    # Detalles del evento
    c.setFillColor(text_color)
    c.setFont("Helvetica", 11)

    # Fecha
    if event.get('starts_at') or event.get('date'):
        date_str = event.get('starts_at') or event.get('date')
        try:
            if isinstance(date_str, str):
                # Manejar diferentes formatos de fecha
                date_str_clean = date_str.replace('Z', '+00:00')
                if '+' in date_str_clean or date_str_clean.endswith('Z'):
                    date_obj = datetime.fromisoformat(date_str_clean)
                else:
                    date_obj = datetime.fromisoformat(date_str_clean)
                # Formato en español
                meses = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
                        'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
                dias = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
                formatted_date = f"{dias[date_obj.weekday()]}, {date_obj.day} de {meses[date_obj.month - 1]} de {date_obj.year}"
            else:
                formatted_date = str(date_str)
        except Exception as e:
            # Si falla el parsing, usar el string original
            formatted_date = str(date_str)

        c.drawString(40*mm, y_pos, "Fecha:")
        c.setFillColor(secondary_color)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(40*mm, y_pos - 6*mm, formatted_date)
        y_pos -= 12*mm

    # Hora
    if event.get('time'):
        c.setFillColor(text_color)
        c.setFont("Helvetica", 11)
        c.drawString(40*mm, y_pos, "Hora:")
        c.setFillColor(secondary_color)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(40*mm, y_pos - 6*mm, event.get('time'))
        y_pos -= 12*mm

    # Ubicación
    location = event.get('location_text') or event.get('location') or event.get('lugar')
    if location:
        c.setFillColor(text_color)
        c.setFont("Helvetica", 11)
        c.drawString(40*mm, y_pos, "Ubicación:")
        c.setFillColor(secondary_color)
        c.setFont("Helvetica-Bold", 12)
        # Dividir ubicación si es muy larga
        loc_words = location.split()
        loc_lines = []
        loc_current = loc_words[0] if loc_words else ""
        for word in loc_words[1:]:
            test = loc_current + " " + word
            if c.stringWidth(test, "Helvetica-Bold", 12) < width - 80*mm:
                loc_current = test
            else:
                loc_lines.append(loc_current)
                loc_current = word
        loc_lines.append(loc_current)

        for i, line in enumerate(loc_lines):
            c.drawString(40*mm, y_pos - 6*mm - i*5*mm, line)
        y_pos -= (len(loc_lines) * 5*mm + 8*mm)

    # Sección del titular con fondo
    y_pos -= 5*mm
    c.setFillColor(HexColor("#eff6ff"))
    c.rect(40*mm, y_pos - 15*mm, width - 80*mm, 20*mm, fill=1, stroke=0)

    c.setFillColor(primary_color)
    c.setFont("Helvetica", 11)
    c.drawString(40*mm, y_pos - 5*mm, "Titular del Ticket")

    holder_name = f"{ticket_data.holder_first_name} {ticket_data.holder_last_name}"
    c.setFillColor(secondary_color)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40*mm, y_pos - 12*mm, holder_name)

    y_pos -= 30*mm

    # Footer
    c.setFillColor(text_color)
    c.setFont("Helvetica", 9)
    ticket_short_id = ticket_data.ticket_id[-12:] if len(ticket_data.ticket_id) > 12 else ticket_data.ticket_id
    c.drawCentredString(width/2, 20*mm, f"ID: {ticket_short_id}")
    c.setFont("Helvetica", 8)
    c.drawCentredString(width/2, 12*mm, "Crowdify - Sistema de Tickets")

    # Fecha de emisión
    if ticket_data.issued_at:
        try:
            issued_date = datetime.fromisoformat(ticket_data.issued_at.replace('Z', '+00:00'))
            issued_str = issued_date.strftime('Emitido: %d/%m/%Y %H:%M')
        except:
            issued_str = f"Emitido: {ticket_data.issued_at}"
        c.drawCentredString(width/2, 5*mm, issued_str)

    c.save()
    buffer.seek(0)
    return buffer


@app.post("/tickets/pdf")
async def generate_ticket_pdf_endpoint(ticket_data: TicketData):
    """
    Genera un PDF profesional del ticket

    Body debe incluir:
    - ticket_id: ID del ticket
    - qr_signature: código QR para escanear
    - holder_first_name, holder_last_name: nombre del titular
    - event: información del evento (name, starts_at, location_text, etc.)
    """
    try:
        pdf_buffer = generate_ticket_pdf(ticket_data)
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=ticket-{ticket_data.ticket_id}.pdf"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando PDF: {str(e)}")


def generate_bulk_tickets_pdf(tickets: List[TicketData], order_id: Optional[str] = None) -> BytesIO:
    """
    Genera un PDF con múltiples tickets (uno por página)
    """
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Colores
    primary_color = HexColor("#2563eb")
    secondary_color = HexColor("#1f2937")
    text_color = HexColor("#6b7280")
    bg_color = HexColor("#f8fafc")

    for idx, ticket_data in enumerate(tickets):
        if idx > 0:
            c.showPage()  # Nueva página para cada ticket después del primero

        # === HEADER ===
        c.setFillColor(bg_color)
        c.rect(0, height - 65*mm, width, 65*mm, fill=1, stroke=0)

        # Logo/Nombre de la app
        c.setFillColor(primary_color)
        c.setFont("Helvetica-Bold", 24)
        c.drawCentredString(width/2, height - 22*mm, "Crowdify")

        # Contador de tickets
        c.setFillColor(text_color)
        c.setFont("Helvetica", 10)
        c.drawCentredString(width/2, height - 32*mm, f"Entrada {idx + 1} de {len(tickets)}")

        # Línea decorativa
        c.setStrokeColor(HexColor("#e5e7eb"))
        c.setLineWidth(1.5)
        c.line(30*mm, height - 42*mm, width - 30*mm, height - 42*mm)

        # === INFORMACIÓN DEL EVENTO ===
        y_pos = height - 55*mm
        event = ticket_data.event

        # Título del evento
        event_name = event.get('name') or event.get('title') or event.get('nombre') or 'Evento'
        c.setFillColor(secondary_color)
        c.setFont("Helvetica-Bold", 20)

        # Dividir título si es muy largo
        words = event_name.split()
        lines = []
        current_line = words[0] if words else ""
        for word in words[1:]:
            test_line = current_line + " " + word
            if c.stringWidth(test_line, "Helvetica-Bold", 20) < width - 60*mm:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word
        lines.append(current_line)

        for i, line in enumerate(lines):
            c.drawCentredString(width/2, y_pos - i*7*mm, line)

        y_pos -= len(lines) * 7*mm + 8*mm

        # === QR CODE ===
        qr = qrcode.QRCode(version=1, box_size=10, border=3)
        qr.add_data(ticket_data.qr_signature)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")

        qr_buffer = BytesIO()
        qr_img.save(qr_buffer, format="PNG")
        qr_buffer.seek(0)

        qr_size = 50*mm
        qr_x = (width - qr_size) / 2
        qr_y = y_pos - qr_size - 5*mm

        # Borde alrededor del QR
        c.setStrokeColor(HexColor("#d1d5db"))
        c.setLineWidth(1)
        c.roundRect(qr_x - 3*mm, qr_y - 3*mm, qr_size + 6*mm, qr_size + 6*mm, 3*mm, fill=0, stroke=1)

        c.drawImage(ImageReader(qr_buffer), qr_x, qr_y, width=qr_size, height=qr_size)

        y_pos = qr_y - 12*mm

        # Instrucción de escaneo
        c.setFillColor(text_color)
        c.setFont("Helvetica", 10)
        c.drawCentredString(width/2, y_pos, "Escanea este código en la entrada")

        y_pos -= 15*mm

        # === DETALLES DEL EVENTO (2 columnas) ===
        left_x = 35*mm
        right_x = width/2 + 10*mm

        # Columna izquierda: Fecha y Hora
        if event.get('starts_at') or event.get('date'):
            date_str = event.get('starts_at') or event.get('date')
            try:
                if isinstance(date_str, str):
                    date_str_clean = date_str.replace('Z', '+00:00')
                    date_obj = datetime.fromisoformat(date_str_clean)
                    meses = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
                            'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
                    dias = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']
                    formatted_date = f"{dias[date_obj.weekday()]}, {date_obj.day} de {meses[date_obj.month - 1]}"
                    formatted_time = date_obj.strftime('%H:%M hrs')
                else:
                    formatted_date = str(date_str)
                    formatted_time = ""
            except:
                formatted_date = str(date_str)
                formatted_time = ""

            c.setFillColor(text_color)
            c.setFont("Helvetica", 9)
            c.drawString(left_x, y_pos, "📅 FECHA")
            c.setFillColor(secondary_color)
            c.setFont("Helvetica-Bold", 11)
            c.drawString(left_x, y_pos - 5*mm, formatted_date)

            if formatted_time:
                c.setFillColor(text_color)
                c.setFont("Helvetica", 9)
                c.drawString(right_x, y_pos, "🕐 HORA")
                c.setFillColor(secondary_color)
                c.setFont("Helvetica-Bold", 11)
                c.drawString(right_x, y_pos - 5*mm, formatted_time)

        y_pos -= 15*mm

        # Ubicación (ancho completo)
        location = event.get('location_text') or event.get('location') or event.get('lugar')
        if location:
            c.setFillColor(text_color)
            c.setFont("Helvetica", 9)
            c.drawString(left_x, y_pos, "📍 UBICACIÓN")
            c.setFillColor(secondary_color)
            c.setFont("Helvetica-Bold", 10)

            # Truncar si es muy largo
            max_width = width - 70*mm
            if c.stringWidth(location, "Helvetica-Bold", 10) > max_width:
                while c.stringWidth(location + "...", "Helvetica-Bold", 10) > max_width and len(location) > 10:
                    location = location[:-1]
                location += "..."
            c.drawString(left_x, y_pos - 5*mm, location)

        y_pos -= 18*mm

        # === TITULAR DEL TICKET ===
        c.setFillColor(HexColor("#eff6ff"))
        c.roundRect(left_x - 5*mm, y_pos - 12*mm, width - 60*mm, 18*mm, 3*mm, fill=1, stroke=0)

        c.setFillColor(primary_color)
        c.setFont("Helvetica", 9)
        c.drawString(left_x, y_pos, "👤 TITULAR")

        holder_name = f"{ticket_data.holder_first_name} {ticket_data.holder_last_name}"
        c.setFillColor(secondary_color)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(left_x, y_pos - 8*mm, holder_name)

        # === FOOTER ===
        c.setFillColor(text_color)
        c.setFont("Helvetica", 8)
        ticket_short_id = ticket_data.ticket_id[-12:] if len(ticket_data.ticket_id) > 12 else ticket_data.ticket_id
        c.drawCentredString(width/2, 18*mm, f"ID: {ticket_short_id}")

        if order_id:
            order_short = order_id[-8:] if len(order_id) > 8 else order_id
            c.drawCentredString(width/2, 12*mm, f"Orden: {order_short}")

        c.setFont("Helvetica", 7)
        c.drawCentredString(width/2, 6*mm, "Crowdify - Sistema de Tickets • www.crowdify.cl")

    c.save()
    buffer.seek(0)
    return buffer


@app.post("/tickets/pdf/bulk")
async def generate_bulk_tickets_pdf_endpoint(request: BulkTicketsRequest):
    """
    Genera un PDF con múltiples tickets (uno por página)

    Body:
    - tickets: Lista de TicketData
    - order_id: ID de la orden (opcional, se muestra en footer)
    - buyer_name: Nombre del comprador (opcional)
    - buyer_email: Email del comprador (opcional)

    Returns: PDF con todos los tickets
    """
    if not request.tickets:
        raise HTTPException(status_code=400, detail="Se requiere al menos un ticket")

    try:
        pdf_buffer = generate_bulk_tickets_pdf(request.tickets, request.order_id)

        filename = f"tickets-{request.order_id[:8] if request.order_id else 'order'}.pdf"

        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando PDF: {str(e)}")
