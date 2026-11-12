from fastapi import APIRouter
router = APIRouter()

@router.get("/")
def login_stub():
    return {"message": "auth route placeholder"}
