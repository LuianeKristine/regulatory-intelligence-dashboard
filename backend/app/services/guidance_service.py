import io
import json
import logging
from typing import Any

import PyPDF2

from app.repositories.summary_repository import GuidanceSummaryRepository
from app.schemas.summary import GuidanceSummaryCreate
from app.utils.openai_client import OpenAIClient, AIClientError

logger = logging.getLogger(__name__)


class GuidanceService:
    def __init__(self, summary_repo: GuidanceSummaryRepository, ai_client: OpenAIClient) -> None:
        self.summary_repo = summary_repo
        self.ai_client = ai_client

    def extract_text_from_pdf(self, pdf_content: bytes) -> str:
        reader = PyPDF2.PdfReader(io.BytesIO(pdf_content))
        pages = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                pages.append(page_text)
        return "\n\n".join(pages).strip()

    def create_summary(self, db: Any, guidance: Any, extracted_text: str) -> dict[str, Any]:
        try:
            response = self.ai_client.summarize_guidance(guidance.title, extracted_text)
            summary_text = response.get("content", "{}")
            summary_data = json.loads(summary_text)
        except (AIClientError, json.JSONDecodeError) as exc:
            logger.warning("Failed to parse AI summary for guidance %s: %s", guidance.title, exc)
            summary_data = {
                "key_points": [],
                "major_changes": [],
                "regulatory_impact": "Unable to parse summary automatically.",
            }

        summary_payload = GuidanceSummaryCreate(
            guidance_id=guidance.id,
            key_points=summary_data.get("key_points", []),
            major_changes=summary_data.get("major_changes", []),
            regulatory_impact=summary_data.get("regulatory_impact", ""),
        )
        return self.summary_repo.create_or_update(db, summary_payload)
