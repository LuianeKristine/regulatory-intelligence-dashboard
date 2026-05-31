import logging
from typing import Any

import openai

from app.core.config import settings

logger = logging.getLogger(__name__)


class AIClientError(Exception):
    pass


class OpenAIClient:
    def __init__(self) -> None:
        if settings.ai_provider != "openai":
            raise AIClientError("Only OpenAI provider is implemented in this release.")

        if not settings.openai_api_key:
            raise AIClientError("OPENAI_API_KEY is required for OpenAI AI provider.")

        openai.api_key = settings.openai_api_key

    def summarize_guidance(self, title: str, extracted_text: str) -> dict[str, Any]:
        prompt = (
            "You are a regulatory intelligence assistant. "
            "Analyze the following FDA guidance text and return a JSON object with key_points, major_changes, "
            "and regulatory_impact. Keep the response valid JSON and do not include additional explanation.\n\n"
            f"Title: {title}\n\n"
            f"Text:\n{extracted_text}\n"
        )

        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You summarize regulatory content into structured JSON."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=800,
        )

        if not response.choices:
            raise AIClientError("OpenAI returned an empty response.")

        content = response.choices[0].message.content.strip()
        logger.info("OpenAI summary response received for guidance %s", title)
        return {"raw_text": content, "content": content}
