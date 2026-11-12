from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from . import db
from .routers import orders, performers, users, auth, audit


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    yield


app = FastAPI(title="Dispatcher API", lifespan=lifespan)

app.include_router(orders.router, prefix="/orders", tags=["orders"])
app.include_router(performers.router, prefix="/performers", tags=["performers"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(audit.router, prefix="/audit", tags=["audit"])


@app.get("/")
def root():
    return {"ok": True, "service": "dispatcher"}


_static = Path(__file__).parent / "static"
if _static.is_dir():
    app.mount("/ui", StaticFiles(directory=_static, html=True), name="ui")
