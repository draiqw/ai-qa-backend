from pydantic import BaseModel, EmailStr
from typing import Optional
import uuid

class UserCreateSchema(BaseModel):
    email: EmailStr
    phone: str
    login: str
    password: str
    name: Optional[str] = None
    surname: Optional[str] = None
    middlename: Optional[str] = None
    role: Optional[str] = None

class UserResponseSchema(BaseModel):
    id: uuid.UUID
    email: EmailStr
    phone: str
    login: str
    name: Optional[str] = None
    surname: Optional[str] = None
    middlename: Optional[str] = None
    role: Optional[str] = None

    class Config:
        orm_mode = True

class AuthSchema(BaseModel):
    email: EmailStr
    password: str