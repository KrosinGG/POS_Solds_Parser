from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class EventLocationData(BaseModel):
    City: Optional[str] = None
    CountryCode: Optional[str] = None
    State: Optional[str] = None
    Venue: Optional[str] = None


EventLocation = EventLocationData


class EventItem(BaseModel):
    EventId: int
    EventName: str
    EventLocalDateTime: Optional[str] = None
    EventDateForExport: Optional[str] = None
    EventLocation: Optional[EventLocationData] = None
    AvailableQuantity: int = 0
    SoldQuantity: int = 0
    ExchangeQuantity: int = 0
    Status: int = 1  # 1 = Active
    Performer: Optional[str] = None
    Category: Optional[str] = None


class TicketGroupItem(BaseModel):
    TicketGroupId: Optional[int] = None
    EventId: Optional[int] = None
    AvailableQuantity: int = 0
    SoldQuantity: int = 0
    Quantity: int = 0
    IsShort: bool = False
    Tags: List[str] = Field(default_factory=list)


class ParsedShow(BaseModel):
    """Структурированное представление шоу для выгрузки в Excel и отчет бота."""
    event_id: int
    event_name: str
    venue: str
    city_state: str
    event_datetime_str: str
    event_datetime: Optional[datetime] = None
    sold_count: int
    active_on_hand: int  # Количество листингов с тегами "R", "Drop", "Jump"
    available_count: int = 0
    total_quantity: int = 0
