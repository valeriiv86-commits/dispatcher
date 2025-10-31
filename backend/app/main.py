from fastapi import FastAPI
from .routers import orders, performers, users, auth, audit

app = FastAPI(title="Dispatcher API")

app.include_router(orders.router, prefix="/orders", tags=["orders"])
app.include_router(performers.router, prefix="/performers", tags=["performers"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(audit.router, prefix="/audit", tags=["audit"])

@app.get("/")
def root():
    return {"ok": True, "service": "dispatcher"}
