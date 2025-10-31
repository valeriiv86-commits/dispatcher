from fastapi import APIRouter, HTTPException
from ..models.order import OrderCreate, OrderUpdate
from .. import db

router = APIRouter()

@router.get("/")
def list_all():
    return db.list_orders()

@router.post("/")
def create(order: OrderCreate):
    return db.create_order(order.dict())

@router.get("/{order_id}")
def get_one(order_id: str):
    item = db.get_order(order_id)
    if not item:
        raise HTTPException(404, "Order not found")
    return item

@router.patch("/{order_id}")
def update(order_id: str, data: OrderUpdate):
    updated = db.update_order(order_id, {k: v for k, v in data.dict().items() if v is not None})
    if not updated:
        raise HTTPException(404, "Order not found")
    return updated
