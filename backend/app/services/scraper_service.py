import logging
from typing import Any

import requests
from sqlalchemy.orm import Session

from app.repositories.guidance_repository import GuidanceRepository
from app.repositories.summary_repository import GuidanceSummaryRepository
from app.schemas.guidance import GuidanceCreate, GuidanceUpdate
from app.schemas.summary import GuidanceSummaryCreate
from app.services.guidance_service import GuidanceService
from app.utils.hash_utils import compute_hash
from app.utils.openai_client import OpenAIClient
from scraper.fda_guidances import FDAGuidanceScraper

logger = logging.getLogger(__name__)


class ScraperService:
    def __init__(self) -> None:
        self.guidance_repo = GuidanceRepository()
        self.summary_repo = GuidanceSummaryRepository()
        self.ai_client = OpenAIClient()
        self.guidance_service = GuidanceService(self.summary_repo, self.ai_client)
        self.scraper = FDAGuidanceScraper()

    def download_pdf(self, url: str) -> bytes:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.content

    def sync_guidance(self, db: Session) -> dict[str, int]:
        scraped_items = self.scraper.fetch_guidances()
        current_urls = {item.url for item in scraped_items}
        results = {"created": 0, "updated": 0, "removed": 0}

        for item in scraped_items:
            content_hash = compute_hash(
                item.title,
                item.url,
                item.published_date.isoformat() if item.published_date else "",
                item.fda_center,
                item.status,
            )
            existing = self.guidance_repo.get_by_url(db, item.url)
            if existing is None:
                guidance = self.guidance_repo.create(
                    db,
                    GuidanceCreate(
                        title=item.title,
                        url=item.url,
                        pdf_url=item.pdf_url,
                        fda_center=item.fda_center,
                        topic=item.topic,
                        status=item.status,
                        published_date=item.published_date,
                        content_hash=content_hash,
                    ),
                )
                results["created"] += 1
                self._generate_summary(db, guidance, item)
            elif existing.content_hash != content_hash:
                guidance = self.guidance_repo.update(
                    db,
                    existing,
                    GuidanceUpdate(
                        title=item.title,
                        pdf_url=item.pdf_url,
                        fda_center=item.fda_center,
                        topic=item.topic,
                        status=item.status,
                        published_date=item.published_date,
                        content_hash=content_hash,
                    ),
                )
                results["updated"] += 1
                self._generate_summary(db, guidance, item)

        for existing_url in list(self.guidance_repo.get_all_urls(db)):
            if existing_url not in current_urls:
                self.guidance_repo.delete_by_url(db, existing_url)
                results["removed"] += 1

        logger.info("Scrape sync completed: %s", results)
        return results

    def _generate_summary(self, db: Session, guidance: Any, item: Any) -> None:
        if not item.pdf_url:
            logger.warning("Skipping summary generation because PDF URL is missing for %s", item.url)
            return

        try:
            pdf_content = self.download_pdf(item.pdf_url)
            extracted_text = self.guidance_service.extract_text_from_pdf(pdf_content)
            self.guidance_service.create_summary(db, guidance, extracted_text)
        except Exception as exc:
            logger.exception("Failed to generate summary for guidance %s: %s", guidance.url, exc)
