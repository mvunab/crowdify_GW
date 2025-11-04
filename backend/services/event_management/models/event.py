"""Modelos Pydantic para eventos"""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from uuid import UUID


class EventResponse(BaseModel):
    id: str
    organizer_id: str
    name: str
    location_text: Optional[str] = None
    point_location: Optional[str] = None
    starts_at: datetime
    ends_at: Optional[datetime] = None
    capacity_total: int
    capacity_available: int
    allow_children: bool
    category: Optional[str] = "otro"
    description: Optional[str] = None
    image_url: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class EventCreate(BaseModel):
    organizer_id: str
    name: str
    location_text: Optional[str] = None
    starts_at: datetime
    ends_at: Optional[datetime] = None
    capacity_total: int
    allow_children: bool = False


class EventUpdate(BaseModel):
    name: Optional[str] = None
    location_text: Optional[str] = None
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    capacity_total: Optional[int] = None
    capacity_available: Optional[int] = None
    allow_children: Optional[bool] = None

