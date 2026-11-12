from fastapi import APIRouter, Depends, Query

from .. import db, security as sec

router = APIRouter()


@router.get("/")
def list_audit(limit: int = Query(100, ge=1, le=1000), admin=Depends(sec.admin_user),
               conn=Depends(db.get_db)):
    return [dict(r) for r in conn.execute(
        "SELECT id,ts,username,action,entity,entity_id,details FROM audit_log "
        "ORDER BY id DESC LIMIT ?", (limit,))]
