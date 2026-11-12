import uuid
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query

from .. import db, security as sec
from ..models.order import OrderCreate, OrderUpdate, Status
from ..notify import notify

router = APIRouter()

SELECT = ("SELECT o.*, p.name AS performer_name FROM orders o "
          "LEFT JOIN performers p ON p.id=o.performer_id")


def _get(conn, oid):
    r = conn.execute(SELECT + " WHERE o.id=?", (oid,)).fetchone()
    if not r:
        raise HTTPException(404, "Order not found")
    return dict(r)


def _check_performer(conn, pid):
    if pid is not None and not conn.execute("SELECT 1 FROM performers WHERE id=?", (pid,)).fetchone():
        raise HTTPException(400, "Unknown performer_id")


@router.get("/")
def list_all(status: Optional[Status] = None, limit: int = Query(200, ge=1, le=1000),
             user=Depends(sec.current_user), conn=Depends(db.get_db)):
    q, args = SELECT, []
    if status:
        q += " WHERE o.status=?"
        args.append(status)
    q += " ORDER BY o.created_at DESC, o.rowid DESC LIMIT ?"
    return [dict(r) for r in conn.execute(q, (*args, limit))]


@router.post("/")
def create(order: OrderCreate, bg: BackgroundTasks, user=Depends(sec.current_user),
           conn=Depends(db.get_db)):
    _check_performer(conn, order.performer_id)
    oid, ts = str(uuid.uuid4()), db.now_iso()
    status = "assigned" if order.performer_id is not None else "new"
    conn.execute(
        "INSERT INTO orders(id,created_at,updated_at,client_name,client_phone,from_address,"
        "to_address,price,comment,status,performer_id,created_by) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
        (oid, ts, ts, order.client_name, order.client_phone, order.from_address, order.to_address,
         order.price, order.comment or "", status, order.performer_id, user["username"]))
    db.audit(conn, user["username"], "order_create", "order", oid,
             {"price": order.price, "performer_id": order.performer_id})
    conn.commit()
    notify(bg, f"Новый заказ: {order.from_address} → {order.to_address}, "
               f"{order.price:g} ₽, клиент {order.client_name}")
    return _get(conn, oid)


@router.get("/{order_id}")
def get_one(order_id: str, user=Depends(sec.current_user), conn=Depends(db.get_db)):
    return _get(conn, order_id)


@router.patch("/{order_id}")
def update(order_id: str, data: OrderUpdate, bg: BackgroundTasks,
           user=Depends(sec.current_user), conn=Depends(db.get_db)):
    old = _get(conn, order_id)
    ch = data.model_dump(exclude_unset=True)
    ch = {k: v for k, v in ch.items() if v is not None or k == "performer_id"}
    if ch.get("performer_id") is not None:
        _check_performer(conn, ch["performer_id"])
        if old["status"] == "new" and "status" not in ch:
            ch["status"] = "assigned"
    if ch:
        ch["updated_at"] = db.now_iso()
        conn.execute(f"UPDATE orders SET {','.join(k + '=?' for k in ch)} WHERE id=?",
                     (*ch.values(), order_id))
    ch.pop("updated_at", None)
    db.audit(conn, user["username"], "order_update", "order", order_id, ch)
    conn.commit()
    new = _get(conn, order_id)
    if new["status"] != old["status"]:
        notify(bg, f"Заказ {order_id[:8]}: статус {old['status']} → {new['status']}")
    return new
