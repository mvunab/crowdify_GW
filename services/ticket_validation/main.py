"""Service entry point para ticket validation"""
from fastapi import FastAPI
from services.ticket_validation.routes.validation import router

app = FastAPI(title="Ticket Validation Service")
app.include_router(router, prefix="/api/v1/tickets", tags=["tickets"])

