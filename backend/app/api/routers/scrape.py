from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.scraper_service import ScraperService

router = APIRouter(prefix="/scrape", tags=["scrape"])

scraper_service = ScraperService()


@router.post("/guidances")
def run_guidance_scrape(db: Session = Depends(get_db)) -> dict[str, int]:
    return scraper_service.sync_guidance(db)
