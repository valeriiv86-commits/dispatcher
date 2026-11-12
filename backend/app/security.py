import base64
import hashlib
import hmac
import secrets
import time
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

from .db import get_db, now_iso

oauth2 = OAuth2PasswordBearer(tokenUrl="/auth/login")
SESSION_DAYS = 30
_N, _R, _P = 2**14, 8, 1


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    h = hashlib.scrypt(password.encode(), salt=salt, n=_N, r=_R, p=_P)
    return "scrypt$" + base64.b64encode(salt).decode() + "$" + base64.b64encode(h).decode()


def verify_password(password: str, stored: str) -> bool:
    try:
        _, s, h = stored.split("$")
        salt, want = base64.b64decode(s), base64.b64decode(h)
        got = hashlib.scrypt(password.encode(), salt=salt, n=_N, r=_R, p=_P)
    except Exception:
        return False
    return hmac.compare_digest(got, want)


# Для несуществующих логинов сверяем с фиктивным хешем, чтобы время ответа не выдавало, есть ли такой пользователь.
DUMMY_HASH = hash_password(secrets.token_urlsafe(16))


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_session(conn, user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    exp = (datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)).isoformat()
    conn.execute("INSERT INTO sessions(token_hash,user_id,expires_at) VALUES(?,?,?)",
                 (_hash_token(token), user_id, exp))
    return token


def delete_session(conn, token: str) -> None:
    conn.execute("DELETE FROM sessions WHERE token_hash=?", (_hash_token(token),))


def delete_user_sessions(conn, user_id: int, keep_token: str | None = None) -> None:
    """Смена пароля завершает все остальные входы пользователя."""
    keep = _hash_token(keep_token) if keep_token else ""
    conn.execute("DELETE FROM sessions WHERE user_id=? AND token_hash<>?", (user_id, keep))


def purge_expired_sessions(conn) -> None:
    conn.execute("DELETE FROM sessions WHERE expires_at<?", (now_iso(),))


def current_user(token: str = Depends(oauth2), conn=Depends(get_db)):
    row = conn.execute(
        "SELECT u.id,u.username,u.role,u.active,s.expires_at FROM sessions s "
        "JOIN users u ON u.id=s.user_id WHERE s.token_hash=?", (_hash_token(token),)).fetchone()
    if not row or not row["active"] or row["expires_at"] < now_iso():
        raise HTTPException(401, "Invalid or expired token",
                            headers={"WWW-Authenticate": "Bearer"})
    return {"id": row["id"], "username": row["username"], "role": row["role"]}


def admin_user(user=Depends(current_user)):
    if user["role"] != "admin":
        raise HTTPException(403, "Admin only")
    return user


# --- failed-login limiter (in-memory) ---
MAX_FAILS, WINDOW = 5, 300
_fails: dict[tuple, list[float]] = {}


MAX_KEYS = 10000


def _recent(key):
    t = time.monotonic()
    lst = [x for x in _fails.get(key, []) if t - x < WINDOW]
    if lst:
        _fails[key] = lst
    else:
        _fails.pop(key, None)
    return lst


def is_locked(key) -> bool:
    return len(_recent(key)) >= MAX_FAILS


def register_fail(key) -> None:
    if len(_fails) >= MAX_KEYS:
        # Не даём словарю расти без предела: сначала убираем устаревшие записи.
        for k in list(_fails):
            _recent(k)
        if len(_fails) >= MAX_KEYS:
            _fails.clear()
    _fails[key] = _recent(key) + [time.monotonic()]


def clear_fails(key) -> None:
    _fails.pop(key, None)


def reset_limiter() -> None:
    _fails.clear()
