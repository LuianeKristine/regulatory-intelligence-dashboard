import re
from dataclasses import dataclass
from datetime import datetime, date
from typing import List, Optional

import requests
from bs4 import BeautifulSoup

FDA_BASE_URL = "https://www.fda.gov"
FDA_SEARCH_URL = "https://www.fda.gov/regulatory-information/search-fda-guidance-documents"
CENTERS = ["Center for Drug Evaluation and Research", "Center for Biologics Evaluation and Research", "Oncology Center for Excellence"]
STATUS_PATTERNS = {
    "Draft": re.compile(r"draft", re.IGNORECASE),
    "Final": re.compile(r"final", re.IGNORECASE),
}


@dataclass
class GuidanceItem:
    title: str
    url: str
    pdf_url: Optional[str]
    published_date: Optional[date]
    fda_center: str
    status: str
    topic: Optional[str]


class FDAGuidanceScraper:
    def fetch_guidances(self) -> List[GuidanceItem]:
        response = requests.get(FDA_SEARCH_URL, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        items = []
        records = soup.select(".search-result-item, .views-row, article, .result-item")
        if not records:
            records = soup.select("li")

        for record in records:
            title_element = record.select_one("a")
            if title_element is None or not title_element.text.strip():
                continue

            title = title_element.text.strip()
            url = self._normalize_url(title_element.get("href", ""))
            pdf_url = self._extract_pdf_url(record, url)
            metadata = record.get_text(" ", strip=True)
            fda_center = self._extract_center(metadata)
            if fda_center not in CENTERS:
                continue
            status = self._extract_status(metadata)
            published_date = self._extract_published_date(metadata)
            topic = self._extract_topic(metadata)

            items.append(
                GuidanceItem(
                    title=title,
                    url=url,
                    pdf_url=pdf_url,
                    published_date=published_date,
                    fda_center=fda_center,
                    status=status,
                    topic=topic,
                )
            )

        return items

    def _normalize_url(self, url: str) -> str:
        if url.startswith("/"):
            return f"{FDA_BASE_URL}{url}"
        if url.startswith("http"):
            return url
        return f"{FDA_BASE_URL}/{url.lstrip('/')}"

    def _extract_center(self, text: str) -> str:
        for center in CENTERS:
            if center.lower() in text.lower():
                return center
        return "Unknown"

    def _extract_status(self, text: str) -> str:
        for label, pattern in STATUS_PATTERNS.items():
            if pattern.search(text):
                return label
        return "Unknown"

    def _extract_published_date(self, text: str) -> Optional[date]:
        candidates = re.findall(r"(\w+ \d{1,2}, \d{4})", text)
        candidates += re.findall(r"(\d{1,2}/\d{1,2}/\d{4})", text)
        for candidate in candidates:
            try:
                if "/" in candidate:
                    return datetime.strptime(candidate, "%m/%d/%Y").date()
                return datetime.strptime(candidate, "%B %d, %Y").date()
            except ValueError:
                continue
        return None

    def _extract_topic(self, text: str) -> Optional[str]:
        match = re.search(r"Topic[:\s]*([^|\n]+)", text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None

    def _extract_pdf_url(self, record: BeautifulSoup, detail_url: str) -> Optional[str]:
        pdf_link = record.select_one("a[href$='.pdf']")
        if pdf_link is not None:
            return self._normalize_url(pdf_link.get("href", ""))

        try:
            detail_response = requests.get(detail_url, timeout=30)
            detail_response.raise_for_status()
            detail_soup = BeautifulSoup(detail_response.text, "html.parser")
            pdf_link = detail_soup.select_one("a[href$='.pdf'], a[href*='pdf']")
            if pdf_link is not None:
                return self._normalize_url(pdf_link.get("href", ""))
        except requests.RequestException:
            pass

        return None
