from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from .. import db, security as sec
from ..models.order import PerformerCreate, PerformerUpdate

router = APIRouter()


def _out(r):
    d = dict(r)
    d["active"] = bool(d["active"])
    return d


@router.get("/")
def list_performers(active: Optional[bool] = None, user=Depends(sec.current_user), conn=Depends(db.get_db)):
    q, args = "SELECT * FROM performers", ()
    if active is not None:
        q, args = q + " WHERE active=?", (int(active),)
    return [_out(r) for r in conn.execute(q + " ORDER BY id", args)]


@router.post("/")
def create(data: PerformerCreate, user=Depends(sec.current_user), conn=Depends(db.get_db)):
    cur = conn.execute(
        "INSERT INTO performers(name,phone,comment,active,created_at) VALUES(?,?,?,1,?)",
        (data.name, data.phone, data.comment or "", db.now_iso()))
    db.audit(conn, user["username"], "performer_create", "performer", cur.lastrowid,
             data.model_dump())
    conn.commit()
    return _out(conn.execute("SELECT * FROM performers WHERE id=?", (cur.lastrowid,)).fetchone())


@router.patch("/{pid}")
def update(pid: int, data: PerformerUpdate, user=Depends(sec.current_user), conn=Depends(db.get_db)):
    if not conn.execute("SELECT 1 FROM performers WHERE id=?", (pid,)).fetchone():
        raise HTTPException(404, "Performer not found")
    ch = data.model_dump(exclude_none=True)
    if "active" in ch:
        ch["active"] = int(ch["active"])
    if ch:
        conn.execute(f"UPDATE performers SET {','.join(k + '=?' for k in ch)} WHERE id=?",
                     (*ch.values(), pid))
    db.audit(conn, user["username"], "performer_update", "performer", pid, ch)
    conn.commit()
    return _out(conn.execute("SELECT * FROM performers WHERE id=?", (pid,)).fetchone())
