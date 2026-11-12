import os

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm

from .. import db, security as sec
from ..models.order import PasswordChange

router = APIRouter()


@router.post("/login")
def login(request: Request, form: OAuth2PasswordRequestForm = Depends(), conn=Depends(db.get_db)):
    key = (form.username, request.client.host if request.client else "?")
    if sec.is_locked(key):
        raise HTTPException(429, "Too many failed attempts, try later")
    u = conn.execute("SELECT * FROM users WHERE username=?", (form.username,)).fetchone()
    ok = sec.verify_password(form.password, u["password_hash"] if u else sec.DUMMY_HASH)
    if not (u and ok and u["active"]):
        sec.register_fail(key)
        db.audit(conn, form.username, "login_failed", "user", u["id"] if u else None)
        conn.commit()
        raise HTTPException(401, "Incorrect username or password")
    sec.clear_fails(key)
    sec.purge_expired_sessions(conn)
    token = sec.create_session(conn, u["id"])
    db.audit(conn, u["username"], "login", "user", u["id"])
    conn.commit()
    return {"access_token": token, "token_type": "bearer",
            "user": {"id": u["id"], "username": u["username"], "role": u["role"]}}


@router.post("/logout")
def logout(token: str = Depends(sec.oauth2), user=Depends(sec.current_user), conn=Depends(db.get_db)):
    sec.delete_session(conn, token)
    conn.commit()
    return {"ok": True}


@router.get("/me")
def me(user=Depends(sec.current_user)):
    return user


@router.post("/password")
def change_password(data: PasswordChange, token: str = Depends(sec.oauth2),
                    user=Depends(sec.current_user), conn=Depends(db.get_db)):
    row = conn.execute("SELECT password_hash FROM users WHERE id=?", (user["id"],)).fetchone()
    if not sec.verify_password(data.old_password, row["password_hash"]):
        raise HTTPException(400, "Wrong old password")
    conn.execute("UPDATE users SET password_hash=? WHERE id=?",
                 (sec.hash_password(data.new_password), user["id"]))
    sec.delete_user_sessions(conn, user["id"], keep_token=token)
    db.audit(conn, user["username"], "password_change", "user", user["id"])
    conn.commit()
    first = conn.execute("SELECT MIN(id) FROM users").fetchone()[0]
    if user["id"] == first:
        f = db.db_path().parent / "admin_password.txt"
        if f.exists():
            os.remove(f)
    return {"ok": True}
