import uuid
from datetime import datetime
from sqlalchemy import Column, ForeignKey, DateTime, String
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
from src.dao.database import Base

class Ticket(Base):
    __tablename__ = "ticket"
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        nullable=False,
        index=True
    )
    
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("user.id"),
        nullable=True,
    )
    
    chat_id = Column(String(20), nullable=False)
    connection_type = Column(String(50), nullable=False)
    dialogue = Column(JSON, nullable=False)
    status = Column(String(20), nullable=False, default="open")
    time_open = Column(String(30), default=datetime.utcnow)
    time_close = Column(String(30), nullable=True)
    category = Column(String(50), nullable=False)
    
    user = relationship("User", back_populates="tickets", cascade="all, delete-orphan", single_parent=True)
