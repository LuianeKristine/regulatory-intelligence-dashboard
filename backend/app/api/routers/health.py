from fastapi import APIRouter

from app.db.session import engine
from app.db.base import Base

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "database": "available"}
