import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from .. import db, security as sec
from ..models.order import UserCreate, UserUpdate

router = APIRouter(dependencies=[Depends(sec.admin_user)])
COLS = "id,username,role,active,created_at"


def _out(r):
    d = dict(r)
    d["active"] = bool(d["active"])
    return d


@router.get("/")
def list_users(conn=Depends(db.get_db)):
    return [_out(r) for r in conn.execute(f"SELECT {COLS} FROM users ORDER BY id")]


@router.post("/")
def create_user(data: UserCreate, admin=Depends(sec.admin_user), conn=Depends(db.get_db)):
    try:
        cur = conn.execute(
            "INSERT INTO users(username,password_hash,role,active,created_at) VALUES(?,?,?,1,?)",
            (data.username, sec.hash_password(data.password), data.role, db.now_iso()))
    except sqlite3.IntegrityError:
        raise HTTPException(409, "Username already exists")
    db.audit(conn, admin["username"], "user_create", "user", cur.lastrowid,
             {"username": data.username, "role": data.role})
    conn.commit()
    return _out(conn.execute(f"SELECT {COLS} FROM users WHERE id=?", (cur.lastrowid,)).fetchone())


@router.patch("/{user_id}")
def update_user(user_id: int, data: UserUpdate, admin=Depends(sec.admin_user), conn=Depends(db.get_db)):
    if not conn.execute("SELECT 1 FROM users WHERE id=?", (user_id,)).fetchone():
        raise HTTPException(404, "User not found")
    if user_id == admin["id"] and (data.active is False or (data.role and data.role != "admin")):
        raise HTTPException(400, "Cannot deactivate or demote yourself")
    changes = {}
    if data.password is not None:
        conn.execute("UPDATE users SET password_hash=? WHERE id=?",
                     (sec.hash_password(data.password), user_id))
        sec.delete_user_sessions(conn, user_id)
        changes["password"] = "changed"
    if data.role is not None:
        conn.execute("UPDATE users SET role=? WHERE id=?", (data.role, user_id))
        changes["role"] = data.role
    if data.active is not None:
        conn.execute("UPDATE users SET active=? WHERE id=?", (int(data.active), user_id))
        changes["active"] = data.active
    db.audit(conn, admin["username"], "user_update", "user", user_id, changes)
    conn.commit()
    return _out(conn.execute(f"SELECT {COLS} FROM users WHERE id=?", (user_id,)).fetchone())
