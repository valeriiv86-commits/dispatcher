from typing import Dict, Any
from datetime import datetime
import uuid

# простейшее "хранилище" в памяти
ORDERS: Dict[str, Dict[str, Any]] = {}

def create_order(data: dict) -> dict:
    key = str(uuid.uuid4())
    item = {
        "id": key,
        "created_at": datetime.utcnow().isoformat(),
        **data,
    }
    ORDERS[key] = item
    return item

def list_orders() -> list[dict]:
    return list(ORDERS.values())

def get_order(order_id: str) -> dict | None:
    return ORDERS.get(order_id)

def update_order(order_id: str, data: dict) -> dict | None:
    if order_id not in ORDERS:
        return None
    ORDERS[order_id].update(data)
    return ORDERS[order_id]
