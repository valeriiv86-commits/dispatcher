from pydantic import BaseModel
from typing import Optional

class OrderBase(BaseModel):
    client_name: str
    client_phone: str
    from_address: str
    to_address: str
    price: float
    comment: Optional[str] = ""
    performer: Optional[str] = ""
    status: Optional[str] = "new"

class OrderCreate(OrderBase):
    pass

class OrderUpdate(BaseModel):
    status: Optional[str] = None
    performer: Optional[str] = None
    comment: Optional[str] = None
