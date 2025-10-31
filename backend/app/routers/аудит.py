from fastapi import APIRouter
router = APIRouter()

@router.get("/")
def audit_stub():
    return {"message": "audit log"}
