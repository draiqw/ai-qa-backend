import uuid
from sqlalchemy import Column, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from src.dao.database import Base
from src.ticket.models import Ticket
class User(Base):
    __tablename__ = "users"
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        nullable=False,
        index=True
    )
    name = Column(String(100), nullable=False)           
    surname = Column(String(100), nullable=False)        
    middlename = Column(String(100), nullable=True)      
    phone = Column(String(100), unique=True, nullable=False)  
    login = Column(String(100), unique=True, nullable=False)  
    email = Column(String(100), unique=True, nullable=False) 
    password = Column(String(100), nullable=False)      
    role = Column(String(100), nullable=False)
    bitrix_id = Column(Integer, nullable=True)           
    tickets = relationship("Ticket", back_populates="user")
