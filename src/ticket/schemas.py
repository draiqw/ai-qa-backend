from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class TicketSchema(BaseModel):
    id: str
    chat_id: str
    user_id: str
    connection_type: str
    dialogue: Optional[str]
    status: str
    time_open: Optional[datetime]
    time_close: Optional[datetime]
    category: str