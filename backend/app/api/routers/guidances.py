from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.guidance_repository import GuidanceRepository
from app.schemas.guidance import GuidanceRead

router = APIRouter(prefix="/guidances", tags=["guidances"])

guidance_repo = GuidanceRepository()


@router.get("/", response_model=List[GuidanceRead])
def list_guidances(
    center: Optional[str] = Query(None, description="Filter by FDA center"),
    status: Optional[str] = Query(None, description="Draft or Final"),
    published_from: Optional[date] = Query(None, description="Start of published date range"),
    published_to: Optional[date] = Query(None, description="End of published date range"),
    search: Optional[str] = Query(None, description="Text search across guidance metadata"),
    db: Session = Depends(get_db),
) -> List[GuidanceRead]:
    return guidance_repo.list(
        db,
        center=center,
        status=status,
        published_from=published_from,
        published_to=published_to,
        search=search,
    )


@router.get("/{guidance_id}", response_model=GuidanceRead)
def get_guidance(guidance_id: int, db: Session = Depends(get_db)) -> GuidanceRead:
    guidance = guidance_repo.get_by_id(db, guidance_id)
    if guidance is None:
        raise HTTPException(status_code=404, detail="Guidance not found")
    return guidance
