import asyncio
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers.guidances import router as guidance_router
from app.api.routers.health import router as health_router
from app.api.routers.scrape import router as scrape_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.db.base import Base
from app.db.session import engine, get_db
from app.services.scraper_service import ScraperService

logger = logging.getLogger(__name__)
app = FastAPI(title="RegAI Regulatory Intelligence", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(guidance_router)
app.include_router(health_router)
app.include_router(scrape_router)

scraper_service = ScraperService()


@app.on_event("startup")\ndef on_startup() -> None:
    configure_logging()
    logger.info("Starting RegAI backend")
    Base.metadata.create_all(bind=engine)
    asyncio.create_task(run_daily_scrape())


async def run_daily_scrape() -> None:
    while True:
        try:
            logger.info("Executing daily guidance scrape")
            await asyncio.to_thread(run_scrape_once)
        except Exception as exc:
            logger.exception("Daily scrape failed: %s", exc)
        await asyncio.sleep(settings.daily_scrape_seconds)


def run_scrape_once() -> None:
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        scraper_service.sync_guidance(db)
    finally:
        db.close()
