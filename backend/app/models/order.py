from typing import Literal, Optional

from pydantic import BaseModel, Field

Status = Literal["new", "assigned", "in_progress", "done", "cancelled"]
Role = Literal["admin", "dispatcher"]


class OrderCreate(BaseModel):
    client_name: str
    client_phone: str
    from_address: str
    to_address: str
    price: float = Field(ge=0)
    comment: Optional[str] = ""
    performer_id: Optional[int] = None


class OrderUpdate(BaseModel):
    status: Optional[Status] = None
    performer_id: Optional[int] = None
    comment: Optional[str] = None
    price: Optional[float] = Field(default=None, ge=0)
    client_name: Optional[str] = None
    client_phone: Optional[str] = None
    from_address: Optional[str] = None
    to_address: Optional[str] = None


class PerformerCreate(BaseModel):
    name: str
    phone: str
    comment: Optional[str] = ""


class PerformerUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    comment: Optional[str] = None
    active: Optional[bool] = None


class UserCreate(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=8)
    role: Role = "dispatcher"


class UserUpdate(BaseModel):
    password: Optional[str] = Field(default=None, min_length=8)
    role: Optional[Role] = None
    active: Optional[bool] = None


class PasswordChange(BaseModel):
    old_password: str
    new_password: str = Field(min_length=8)
