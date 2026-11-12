import json
import logging
import os
import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger("dispatcher")

REPO_ROOT = Path(__file__).resolve().parents[2]

SCHEMA = """
CREATE TABLE IF NOT EXISTS users(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  role TEXT NOT NULL CHECK(role IN ('admin','dispatcher')),
  active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sessions(
  token_hash TEXT PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  expires_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS performers(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL, phone TEXT NOT NULL, comment TEXT NOT NULL DEFAULT '',
  active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS orders(
  id TEXT PRIMARY KEY, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
  client_name TEXT NOT NULL, client_phone TEXT NOT NULL,
  from_address TEXT NOT NULL, to_address TEXT NOT NULL,
  price REAL NOT NULL, comment TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'new',
  performer_id INTEGER REFERENCES performers(id),
  created_by TEXT);
CREATE TABLE IF NOT EXISTS audit_log(
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, username TEXT,
  action TEXT NOT NULL, entity TEXT, entity_id TEXT, details TEXT);
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def db_path() -> Path:
    p = os.getenv("DB_PATH")
    return Path(p) if p else REPO_ROOT / "data" / "dispatcher.db"


def connect() -> sqlite3.Connection:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    # Одно соединение на запрос; FastAPI может выполнять зависимость и обработчик в разных потоках.
    conn = sqlite3.connect(path, check_same_thread=False, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def get_db():
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()


def audit(conn, username, action, entity=None, entity_id=None, details=None):
    conn.execute(
        "INSERT INTO audit_log(ts,username,action,entity,entity_id,details) VALUES(?,?,?,?,?,?)",
        (now_iso(), username, action, entity,
         None if entity_id is None else str(entity_id),
         json.dumps(details, ensure_ascii=False, default=str) if details is not None else None),
    )


def init_db() -> None:
    from .security import hash_password
    conn = connect()
    try:
        conn.executescript(SCHEMA)
        if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
            name = os.getenv("ADMIN_USERNAME") or "admin"
            password = os.getenv("ADMIN_PASSWORD")
            if not password:
                password = secrets.token_urlsafe(12)[:16]
                f = db_path().parent / "admin_password.txt"
                fd = os.open(f, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
                with os.fdopen(fd, "w") as fh:
                    fh.write(password + "\n")
                os.chmod(f, 0o600)
                log.warning("Initial admin password written to %s", f)
            conn.execute(
                "INSERT INTO users(username,password_hash,role,active,created_at) VALUES(?,?,?,1,?)",
                (name, hash_password(password), "admin", now_iso()))
        conn.commit()
    finally:
        conn.close()
