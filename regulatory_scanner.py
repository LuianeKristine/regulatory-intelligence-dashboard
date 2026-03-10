"""
Regulatory Intelligence Scanner
================================
Fetches specific document links (not homepages) from FDA, EMA, ICH.
Extracts text from PDFs when available.
Detects changes via content hashing.
Summarises with Gemini AI.
Saves to Google Sheets: Updates, News, Changes tabs.

Schedule: run daily via GitHub Actions.
"""

import os
import re
import time
import json
import hashlib
import logging
import datetime
import requests
import feedparser
from io import BytesIO
from bs4 import BeautifulSoup

import google.generativeai as genai
import gspread
from google.oauth2.service_account import Credentials

# ── Try PDF extraction (optional) ────────────────────────────
try:
    import pypdf
    HAS_PYPDF = True
except ImportError:
    try:
        import PyPDF2 as pypdf
        HAS_PYPDF = True
    except ImportError:
        HAS_PYPDF = False

# ─────────────────────────────────────────────────────────────
# CONFIG — set via env vars or GitHub Secrets
# ─────────────────────────────────────────────────────────────
GEMINI_API_KEY      = os.environ.get("GEMINI_API_KEY", "")
GCP_CREDS_JSON      = os.environ.get("GCP_SERVICE_ACCOUNT_JSON", "")
SPREADSHEET_NAME    = os.environ.get("SPREADSHEET_NAME", "Raw Intelligence")
MAX_ITEMS_PER_RUN   = int(os.environ.get("MAX_ITEMS_PER_RUN", "30"))
PDF_MAX_CHARS       = 8000   # chars to extract from PDF for summary
REQUEST_TIMEOUT     = 20
REQUEST_DELAY       = 1.2    # seconds between requests (be polite)

FOCUS_TOPICS = [
    "oncology", "cancer", "tumor", "tumour", "carcinoma", "lymphoma", "leukemia",
    "cell therapy", "gene therapy", "CAR-T", "gene editing", "CRISPR", "AAV",
    "autoimmune", "immunology", "rheumatoid", "lupus", "multiple sclerosis", "psoriasis",
    "rare disease", "orphan drug", "rare disorder", "ultra-rare",
]
FOCUS_RE = re.compile("|".join(FOCUS_TOPICS), re.IGNORECASE)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

def safe_get(url, timeout=REQUEST_TIMEOUT, stream=False):
    """GET with retry, respects rate limiting."""
    for attempt in range(3):
        try:
            r = requests.get(url, headers=HEADERS, timeout=timeout, stream=stream)
            r.raise_for_status()
            return r
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                time.sleep(5 * (attempt + 1))
            else:
                log.warning(f"HTTP {e.response.status_code} for {url}")
                return None
        except Exception as e:
            log.warning(f"Request failed ({attempt+1}/3) for {url}: {e}")
            time.sleep(2)
    return None


def content_hash(text: str) -> str:
    """MD5 hash of normalised text — used to detect document changes."""
    normalised = re.sub(r"\s+", " ", text.strip().lower())
    return hashlib.md5(normalised.encode()).hexdigest()[:16]


def extract_pdf_text(url: str) -> str:
    """Download PDF and extract text. Returns empty string on failure."""
    if not HAS_PYPDF:
        return ""
    try:
        r = safe_get(url, timeout=30, stream=True)
        if not r:
            return ""
        raw = BytesIO(r.content)
        reader = pypdf.PdfReader(raw)
        pages = []
        for page in reader.pages[:12]:   # limit to first 12 pages
            try:
                pages.append(page.extract_text() or "")
            except Exception:
                pass
        text = " ".join(pages)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:PDF_MAX_CHARS]
    except Exception as e:
        log.warning(f"PDF extraction failed for {url}: {e}")
        return ""


def find_pdf_link(page_url: str, soup: BeautifulSoup) -> str:
    """Try to find a direct PDF link on the page."""
    # 1. Look for <a> with .pdf in href
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if ".pdf" in href.lower():
            if href.startswith("http"):
                return href
            elif href.startswith("/"):
                from urllib.parse import urlparse
                base = urlparse(page_url)
                return f"{base.scheme}://{base.netloc}{href}"
    return ""


def today_str() -> str:
    return datetime.date.today().isoformat()


def item(source, feed, title, url, pdf_url, summary, raw_text, date_str, tab="Updates"):
    """Standardised item dict."""
    return {
        "tab":      tab,
        "source":   source,
        "feed":     feed,
        "title":    title.strip(),
        "url":      url.strip(),
        "pdf_url":  pdf_url.strip(),
        "summary":  summary.strip(),
        "raw_text": raw_text.strip(),
        "date":     date_str or today_str(),
        "hash":     content_hash(raw_text or summary or title),
    }


# ─────────────────────────────────────────────────────────────
# FDA FETCHERS
# ─────────────────────────────────────────────────────────────

FDA_RSS_FEEDS = [
    ("FDA", "Drug Approvals",       "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/drug-approvals-and-databases/rss.xml"),
    ("FDA", "Press Announcements",  "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/press-announcements/rss.xml"),
    ("FDA", "MedWatch Safety",      "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/medwatch-safety-alerts/rss.xml"),
    ("FDA", "Biologics",            "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/biologics/rss.xml"),
    ("FDA", "Oncology",             "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/hematologyoncology-approvals-safety-notifications/rss.xml"),
    ("FDA", "Gene Therapy",         "https://www.fda.gov/vaccines-blood-biologics/cellular-gene-therapy-products/approved-cellular-and-gene-therapy-products"),
    ("FDA", "Orphan Drug",          "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/rare-diseases-orphan-products/rss.xml"),
]

def fetch_fda() -> list:
    items = []
    seen = set()

    for source, feed_name, url in FDA_RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            entries = feed.entries or []
            log.info(f"FDA [{feed_name}]: {len(entries)} entries")

            for entry in entries[:15]:
                title     = entry.get("title", "").strip()
                link      = entry.get("link",  "").strip()
                raw_sum   = entry.get("summary", entry.get("description", ""))
                pub       = entry.get("published", entry.get("updated", today_str()))

                if not title or link in seen:
                    continue
                if not FOCUS_RE.search(title + " " + raw_sum):
                    continue

                seen.add(link)

                # Fetch the actual page to get specific content + PDF link
                pdf_url  = ""
                raw_text = ""
                page_sum = raw_sum

                time.sleep(REQUEST_DELAY)
                r = safe_get(link)
                if r:
                    soup = BeautifulSoup(r.text, "html.parser")
                    pdf_url = find_pdf_link(link, soup)

                    # Extract article body text
                    for tag in soup.find_all(["article", "main", ".content-body", "#content"]):
                        raw_text = tag.get_text(" ", strip=True)[:PDF_MAX_CHARS]
                        if len(raw_text) > 200:
                            break

                    if not raw_text:
                        body = soup.find("div", class_=re.compile(r"content|article|body", re.I))
                        if body:
                            raw_text = body.get_text(" ", strip=True)[:PDF_MAX_CHARS]

                # If PDF found, try to extract its text
                if pdf_url and not raw_text:
                    raw_text = extract_pdf_text(pdf_url)

                # Try to parse date
                try:
                    import email.utils
                    parsed = email.utils.parsedate_to_datetime(pub)
                    pub_str = parsed.date().isoformat()
                except Exception:
                    pub_str = today_str()

                items.append(item(
                    source=source, feed=feed_name,
                    title=title, url=link, pdf_url=pdf_url,
                    summary=raw_sum[:600], raw_text=raw_text,
                    date_str=pub_str, tab="Updates"
                ))

        except Exception as e:
            log.error(f"FDA [{feed_name}] failed: {e}")

    log.info(f"FDA total: {len(items)} relevant items")
    return items


def fetch_fda_api() -> list:
    """openFDA API — drug labels and approvals with specific document links."""
    items = []
    seen = set()

    queries = [
        ("oncology",    "indications_and_usage:oncology+cancer+tumor"),
        ("gene therapy","indications_and_usage:gene+therapy"),
        ("cell therapy","indications_and_usage:cell+therapy"),
        ("rare disease","indications_and_usage:rare+disease+orphan"),
        ("autoimmune",  "indications_and_usage:autoimmune+rheumatoid+lupus"),
    ]

    for label, q in queries:
        url = (
            f"https://api.fda.gov/drug/label.json"
            f"?search={q}&sort=effective_time:desc&limit=5"
        )
        try:
            r = safe_get(url)
            if not r:
                continue
            data = r.json()
            results = data.get("results", [])
            log.info(f"openFDA [{label}]: {len(results)} results")

            for res in results:
                brand  = res.get("openfda", {}).get("brand_name", [""])[0]
                generic= res.get("openfda", {}).get("generic_name", [""])[0]
                title  = f"{brand} ({generic})" if generic else brand or "Unknown Drug"
                app_no = res.get("openfda", {}).get("application_number", [""])[0]
                # Build a specific FDA drugs@FDA URL
                link   = f"https://www.accessdata.fda.gov/scripts/cder/daf/index.cfm?event=overview.process&ApplNo={app_no.replace('NDA','').replace('BLA','').strip()}" if app_no else "https://www.fda.gov/drugs/drug-approvals-and-databases"
                indications = " ".join(res.get("indications_and_usage", [""]))[:600]
                eff_time    = res.get("effective_time", "")
                try:
                    pub_str = datetime.datetime.strptime(eff_time, "%Y%m%d").date().isoformat()
                except Exception:
                    pub_str = today_str()

                key = title + pub_str
                if key in seen:
                    continue
                seen.add(key)

                items.append(item(
                    source="FDA", feed=f"openFDA API ({label})",
                    title=title, url=link, pdf_url="",
                    summary=indications[:600], raw_text=indications,
                    date_str=pub_str, tab="Updates"
                ))
            time.sleep(REQUEST_DELAY)
        except Exception as e:
            log.error(f"openFDA [{label}] failed: {e}")

    log.info(f"openFDA total: {len(items)} items")
    return items


# ─────────────────────────────────────────────────────────────
# EMA FETCHERS
# ─────────────────────────────────────────────────────────────

EMA_SOURCES = [
    ("EMA", "Press Releases",  "https://www.ema.europa.eu/en/news/press-releases-news"),
    ("EMA", "New Medicines",   "https://www.ema.europa.eu/en/medicines/search-medicine?search_api_views_fulltext=&field_ema_medicine_status=authorised&field_ema_medicine_type=human"),
    ("EMA", "Oncology",        "https://www.ema.europa.eu/en/medicines/search-medicine?search_api_views_fulltext=oncology&field_ema_medicine_status=authorised"),
    ("EMA", "Gene Therapy",    "https://www.ema.europa.eu/en/medicines/search-medicine?search_api_views_fulltext=gene+therapy&field_ema_medicine_status=authorised"),
    ("EMA", "Rare Medicines",  "https://www.ema.europa.eu/en/medicines/search-medicine?search_api_views_fulltext=orphan&field_ema_medicine_status=authorised"),
]

EMA_RSS_FEEDS = [
    ("EMA", "News RSS",        "https://www.ema.europa.eu/en/news/rss.xml"),
    ("EMA", "Human Medicines", "https://www.ema.europa.eu/en/medicines/rss.xml"),
]

def _parse_ema_date(text: str) -> str:
    """Try several date formats common in EMA pages."""
    for fmt in ("%d/%m/%Y", "%d %B %Y", "%B %d, %Y", "%Y-%m-%d"):
        try:
            return datetime.datetime.strptime(text.strip(), fmt).date().isoformat()
        except Exception:
            pass
    return today_str()


def fetch_ema() -> list:
    items = []
    seen = set()

    # 1. Try RSS first (most reliable, specific URLs)
    for source, feed_name, rss_url in EMA_RSS_FEEDS:
        try:
            feed = feedparser.parse(rss_url)
            entries = feed.entries or []
            log.info(f"EMA RSS [{feed_name}]: {len(entries)} entries")
            for entry in entries[:20]:
                title = entry.get("title", "").strip()
                link  = entry.get("link",  "").strip()
                raw   = entry.get("summary", "")
                pub   = entry.get("published", entry.get("updated", ""))

                if not title or link in seen:
                    continue
                if not FOCUS_RE.search(title + " " + raw):
                    continue
                seen.add(link)

                pdf_url  = ""
                raw_text = ""
                time.sleep(REQUEST_DELAY)
                r = safe_get(link)
                if r:
                    soup = BeautifulSoup(r.text, "html.parser")
                    pdf_url = find_pdf_link(link, soup)
                    # EMA uses .content-body or article
                    for sel in ["article", ".content-body", ".field-items", "#content"]:
                        el = soup.select_one(sel)
                        if el:
                            raw_text = el.get_text(" ", strip=True)[:PDF_MAX_CHARS]
                            break

                if pdf_url and not raw_text:
                    raw_text = extract_pdf_text(pdf_url)

                try:
                    import email.utils
                    pub_str = email.utils.parsedate_to_datetime(pub).date().isoformat()
                except Exception:
                    pub_str = today_str()

                items.append(item(
                    source=source, feed=feed_name,
                    title=title, url=link, pdf_url=pdf_url,
                    summary=raw[:600], raw_text=raw_text,
                    date_str=pub_str, tab="Updates"
                ))
        except Exception as e:
            log.error(f"EMA RSS [{feed_name}] failed: {e}")

    # 2. Scrape search pages for specific medicine URLs
    for source, feed_name, page_url in EMA_SOURCES:
        try:
            time.sleep(REQUEST_DELAY)
            r = safe_get(page_url)
            if not r:
                continue
            soup = BeautifulSoup(r.text, "html.parser")

            # EMA search results: each result is in a <article> or <li class="ecl-list-item">
            result_links = []

            # Method 1: article blocks
            for article in soup.find_all("article", limit=10):
                a = article.find("a", href=True)
                if a:
                    href = a["href"]
                    if not href.startswith("http"):
                        href = "https://www.ema.europa.eu" + href
                    result_links.append((a.get_text(strip=True), href))

            # Method 2: search result list items
            if not result_links:
                for li in soup.find_all("li", class_=re.compile(r"ecl-list|search-result|result", re.I), limit=10):
                    a = li.find("a", href=True)
                    if a:
                        href = a["href"]
                        if not href.startswith("http"):
                            href = "https://www.ema.europa.eu" + href
                        result_links.append((a.get_text(strip=True), href))

            log.info(f"EMA [{feed_name}]: {len(result_links)} result links found")

            for title, link in result_links:
                if link in seen:
                    continue
                if not FOCUS_RE.search(title):
                    continue
                seen.add(link)

                pdf_url  = ""
                raw_text = ""
                time.sleep(REQUEST_DELAY)
                detail = safe_get(link)
                if detail:
                    dsoup = BeautifulSoup(detail.text, "html.parser")
                    pdf_url = find_pdf_link(link, dsoup)
                    for sel in ["article", ".content-body", ".field-items", "#content", "main"]:
                        el = dsoup.select_one(sel)
                        if el:
                            raw_text = el.get_text(" ", strip=True)[:PDF_MAX_CHARS]
                            break

                    # Try to find date on page
                    dt_el = dsoup.find(class_=re.compile(r"date|published", re.I))
                    pub_str = _parse_ema_date(dt_el.get_text(strip=True)) if dt_el else today_str()
                else:
                    pub_str = today_str()

                if pdf_url and not raw_text:
                    raw_text = extract_pdf_text(pdf_url)

                items.append(item(
                    source=source, feed=feed_name,
                    title=title, url=link, pdf_url=pdf_url,
                    summary="", raw_text=raw_text,
                    date_str=pub_str, tab="Updates"
                ))

        except Exception as e:
            log.error(f"EMA [{feed_name}] scrape failed: {e}")

    log.info(f"EMA total: {len(items)} relevant items")
    return items


# ─────────────────────────────────────────────────────────────
# ICH FETCHERS
# ─────────────────────────────────────────────────────────────

ICH_PAGES = {
    "Efficacy":           "https://www.ich.org/page/efficacy-guidelines",
    "Quality":            "https://www.ich.org/page/quality-guidelines",
    "Safety":             "https://www.ich.org/page/safety-guidelines",
    "Multidisciplinary":  "https://www.ich.org/page/multidisciplinary-guidelines",
}

# ICH guideline codes to always capture regardless of topic
ICH_CODE_RE = re.compile(r"\b(E\d+|Q\d+|S\d+|M\d+)\b", re.IGNORECASE)

ICH_KEYWORDS_RE = re.compile(
    r"oncol|cancer|tumor|gene\s+therapy|cell\s+therapy|rare|orphan|autoimmun|"
    r"immunol|stability|impurit|bioequiv|pharmacovig|eCTD|pharmacokineti|"
    r"clinical\s+trial|safety|efficacy|quality|guideline|revision|addendum|"
    r"Step\s+[1-5]|finalised|adopted",
    re.IGNORECASE
)

def fetch_ich() -> list:
    items = []
    seen = set()

    for category, url in ICH_PAGES.items():
        try:
            time.sleep(REQUEST_DELAY)
            r = safe_get(url)
            if not r:
                continue
            soup = BeautifulSoup(r.text, "html.parser")

            # ICH pages list guidelines in tables or <ul> lists
            # Each row has: code, title, step/status, date, PDF link
            rows_found = 0

            # Method 1: table rows
            for tr in soup.find_all("tr"):
                cells = tr.find_all(["td", "th"])
                if len(cells) < 2:
                    continue
                row_text = " ".join(c.get_text(strip=True) for c in cells)
                if not ICH_KEYWORDS_RE.search(row_text) and not ICH_CODE_RE.search(row_text):
                    continue

                # Find the main link in the row
                a = tr.find("a", href=True)
                if not a:
                    continue
                href = a["href"]
                if not href.startswith("http"):
                    href = "https://www.ich.org" + href

                title = a.get_text(strip=True) or row_text[:100]
                if href in seen or len(title) < 5:
                    continue
                seen.add(href)
                rows_found += 1

                # Check if there's a direct PDF link in the row
                pdf_url = ""
                for link_el in tr.find_all("a", href=True):
                    if ".pdf" in link_el["href"].lower():
                        pdf_url = link_el["href"]
                        if not pdf_url.startswith("http"):
                            pdf_url = "https://www.ich.org" + pdf_url
                        break

                # Scrape the specific guideline page
                raw_text = ""
                time.sleep(REQUEST_DELAY)
                detail = safe_get(href)
                if detail:
                    dsoup = BeautifulSoup(detail.text, "html.parser")
                    if not pdf_url:
                        pdf_url = find_pdf_link(href, dsoup)
                    for sel in ["article", ".content-body", "main", "#content", ".field-items"]:
                        el = dsoup.select_one(sel)
                        if el:
                            raw_text = el.get_text(" ", strip=True)[:PDF_MAX_CHARS]
                            break

                if pdf_url and not raw_text:
                    raw_text = extract_pdf_text(pdf_url)

                # Try to get a date from the row
                date_cell = ""
                for c in cells:
                    text = c.get_text(strip=True)
                    if re.search(r"\d{4}", text) and len(text) < 20:
                        date_cell = text
                        break

                items.append(item(
                    source="ICH", feed=f"ICH {category} Guidelines",
                    title=title, url=href, pdf_url=pdf_url,
                    summary=row_text[:400], raw_text=raw_text,
                    date_str=_parse_ema_date(date_cell) if date_cell else today_str(),
                    tab="Updates"
                ))

            # Method 2: list items / cards (fallback if no table)
            if rows_found == 0:
                for a in soup.find_all("a", href=True):
                    href = a["href"]
                    title = a.get_text(strip=True)
                    if len(title) < 8:
                        continue
                    if not ICH_CODE_RE.search(title) and not ICH_KEYWORDS_RE.search(title):
                        continue
                    if not href.startswith("http"):
                        href = "https://www.ich.org" + href
                    if href in seen:
                        continue
                    seen.add(href)

                    pdf_url  = ""
                    raw_text = ""
                    time.sleep(REQUEST_DELAY)
                    detail = safe_get(href)
                    if detail:
                        dsoup = BeautifulSoup(detail.text, "html.parser")
                        pdf_url = find_pdf_link(href, dsoup)
                        for sel in ["article", ".content-body", "main"]:
                            el = dsoup.select_one(sel)
                            if el:
                                raw_text = el.get_text(" ", strip=True)[:PDF_MAX_CHARS]
                                break

                    if pdf_url and not raw_text:
                        raw_text = extract_pdf_text(pdf_url)

                    items.append(item(
                        source="ICH", feed=f"ICH {category} Guidelines",
                        title=title, url=href, pdf_url=pdf_url,
                        summary="", raw_text=raw_text,
                        date_str=today_str(), tab="Updates"
                    ))

            log.info(f"ICH [{category}]: {rows_found} guideline rows found")

        except Exception as e:
            log.error(f"ICH [{category}] failed: {e}")

    log.info(f"ICH total: {len(items)} items")
    return items


# ─────────────────────────────────────────────────────────────
# CHANGE DETECTION
# ─────────────────────────────────────────────────────────────

def detect_changes(new_items: list, existing_rows: list) -> list:
    """
    Compare new items against existing sheet rows by URL.
    Returns list of 'change' items where content hash differs.
    """
    # Build map: url -> hash from existing sheet
    existing_map = {}
    for row in existing_rows:
        url  = str(row.get("URL", "")).strip()
        h    = str(row.get("Content Hash", "")).strip()
        if url and h:
            existing_map[url] = h

    changes = []
    for it in new_items:
        url      = it["url"]
        new_hash = it["hash"]
        if url in existing_map and existing_map[url] != new_hash:
            change_item = it.copy()
            change_item["tab"]          = "Changes"
            change_item["change_date"]  = today_str()
            change_item["old_hash"]     = existing_map[url]
            changes.append(change_item)
            log.info(f"CHANGE DETECTED: {it['title'][:80]}")

    log.info(f"Change detection: {len(changes)} changed documents")
    return changes


# ─────────────────────────────────────────────────────────────
# GEMINI ANALYSIS
# ─────────────────────────────────────────────────────────────

def analyse_with_gemini(items: list) -> list:
    """
    Enriches each item with AI-generated fields.
    Returns items with added keys: ai_summary, raw_excerpt,
    implications, action_items, priority, therapeutic_area, health_authority
    """
    if not GEMINI_API_KEY:
        log.warning("GEMINI_API_KEY not set — skipping AI analysis")
        for it in items:
            it.update({
                "ai_summary": it.get("summary", ""),
                "raw_excerpt": it.get("raw_text", "")[:300],
                "implications": "",
                "action_items": "",
                "priority": "Medium",
                "therapeutic_area": "-",
                "health_authority": it.get("source", "-"),
            })
        return items

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash")

    SYSTEM = """You are a senior regulatory affairs specialist in pharma.
Analyse the provided regulatory document and return ONLY valid JSON (no markdown, no preamble).

{
  "ai_summary":        "2-3 sentence plain-English summary of what this document is about",
  "implications":      "Key regulatory implications for pharma/biotech companies (2-3 sentences)",
  "action_items":      "Specific actions companies should take in response (bullet list as single string, use \\n)",
  "priority":          "High | Medium | Low",
  "therapeutic_area":  "Primary therapeutic area (Oncology / Gene Therapy / Cell Therapy / Rare Disease / Autoimmune / Other)",
  "health_authority":  "FDA | EMA | ICH | Other"
}

Priority guide:
- High:   New approval, major label change, safety recall, critical guideline update
- Medium: Draft guidance, consultation, minor update, review status change
- Low:    Administrative update, meeting minutes, general information
"""

    analysed = []
    for i, it in enumerate(items):
        log.info(f"Gemini [{i+1}/{len(items)}] {it['title'][:60]}")
        content = it.get("raw_text") or it.get("summary") or it.get("title")
        prompt  = f"Title: {it['title']}\nSource: {it['source']}\nDate: {it['date']}\n\nContent:\n{content[:5000]}"

        result = {}
        for attempt in range(3):
            try:
                resp = model.generate_content(SYSTEM + "\n\n" + prompt)
                raw  = resp.text.strip()
                raw  = re.sub(r"^```json\s*|```$", "", raw, flags=re.MULTILINE).strip()
                result = json.loads(raw)
                break
            except json.JSONDecodeError:
                log.warning(f"JSON parse failed attempt {attempt+1}")
                time.sleep(2)
            except Exception as e:
                log.error(f"Gemini error: {e}")
                time.sleep(5)

        it.update({
            "ai_summary":       result.get("ai_summary",       it.get("summary", "")[:300]),
            "raw_excerpt":      (it.get("raw_text") or "")[:400],
            "implications":     result.get("implications",     ""),
            "action_items":     result.get("action_items",     ""),
            "priority":         result.get("priority",         "Medium"),
            "therapeutic_area": result.get("therapeutic_area", "-"),
            "health_authority": result.get("health_authority", it.get("source", "-")),
        })
        analysed.append(it)
        time.sleep(1.5)   # Gemini rate limit

    return analysed


# ─────────────────────────────────────────────────────────────
# GOOGLE SHEETS
# ─────────────────────────────────────────────────────────────

SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

SHEET_COLUMNS = {
    "Updates": [
        "Title", "URL", "PDF URL", "Source", "Feed", "Published Date",
        "AI Summary", "Raw Text Excerpt", "Implications", "Action Items",
        "Priority", "Therapeutic Area", "Health Authority", "Content Hash",
    ],
    "Changes": [
        "Title", "URL", "PDF URL", "Source", "Feed", "Original Date",
        "Change Detected Date", "AI Summary", "Raw Text Excerpt",
        "Implications", "Action Items", "Priority", "Therapeutic Area",
        "Health Authority", "New Hash", "Old Hash",
    ],
    "News": [
        "Title", "URL", "PDF URL", "Source", "Feed", "Published Date",
        "AI Summary", "Raw Text Excerpt", "Implications", "Action Items",
        "Priority", "Therapeutic Area", "Health Authority", "Content Hash",
    ],
}

def get_gspread_client():
    if GCP_CREDS_JSON:
        creds_dict = json.loads(GCP_CREDS_JSON)
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    else:
        creds = Credentials.from_service_account_file("service_account.json", scopes=SCOPES)
    return gspread.authorize(creds)


def ensure_worksheet(spreadsheet, tab_name: str):
    """Create worksheet with headers if it doesn't exist."""
    try:
        ws = spreadsheet.worksheet(tab_name)
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=tab_name, rows=2000, cols=20)
        ws.append_row(SHEET_COLUMNS.get(tab_name, ["Title", "URL", "Date"]))
        log.info(f"Created new worksheet: {tab_name}")
    return ws


def load_existing(ws) -> list:
    """Load all rows as list of dicts."""
    try:
        return ws.get_all_records()
    except Exception:
        return []


def save_to_sheets(items: list):
    """Save items to the appropriate Google Sheets tabs."""
    gc  = get_gspread_client()
    spr = gc.open(SPREADSHEET_NAME)

    # Group by tab
    by_tab = {}
    for it in items:
        tab = it.get("tab", "Updates")
        by_tab.setdefault(tab, []).append(it)

    for tab_name, tab_items in by_tab.items():
        ws = ensure_worksheet(spr, tab_name)
        existing = load_existing(ws)
        existing_urls = {str(r.get("URL", "")).strip() for r in existing}

        rows_added = 0
        for it in tab_items:
            if it["url"] in existing_urls:
                log.info(f"Skip (exists): {it['title'][:60]}")
                continue

            if tab_name == "Changes":
                row = [
                    it.get("title"),         it.get("url"),           it.get("pdf_url"),
                    it.get("source"),        it.get("feed"),          it.get("date"),
                    it.get("change_date"),   it.get("ai_summary"),    it.get("raw_excerpt"),
                    it.get("implications"),  it.get("action_items"),  it.get("priority"),
                    it.get("therapeutic_area"), it.get("health_authority"),
                    it.get("hash"),          it.get("old_hash"),
                ]
            else:
                row = [
                    it.get("title"),         it.get("url"),           it.get("pdf_url"),
                    it.get("source"),        it.get("feed"),          it.get("date"),
                    it.get("ai_summary"),    it.get("raw_excerpt"),   it.get("implications"),
                    it.get("action_items"),  it.get("priority"),      it.get("therapeutic_area"),
                    it.get("health_authority"), it.get("hash"),
                ]

            try:
                ws.append_row(row, value_input_option="USER_ENTERED")
                rows_added += 1
                time.sleep(0.5)   # Sheets API rate limit
            except Exception as e:
                log.error(f"Failed to append row: {e}")

        log.info(f"Saved {rows_added} new rows to '{tab_name}'")

    return f"https://docs.google.com/spreadsheets/d/{spr.id}"


def update_hashes(items: list):
    """Update Content Hash column for changed documents."""
    if not items:
        return
    gc  = get_gspread_client()
    spr = gc.open(SPREADSHEET_NAME)
    for tab_name in ["Updates", "News"]:
        try:
            ws   = spr.worksheet(tab_name)
            rows = ws.get_all_values()
            if not rows:
                continue
            headers = rows[0]
            url_col  = headers.index("URL")          if "URL"          in headers else None
            hash_col = headers.index("Content Hash") if "Content Hash" in headers else None
            if url_col is None or hash_col is None:
                continue
            url_to_new_hash = {it["url"]: it["hash"] for it in items if it.get("url")}
            for row_i, row in enumerate(rows[1:], start=2):
                url = row[url_col] if len(row) > url_col else ""
                if url in url_to_new_hash:
                    ws.update_cell(row_i, hash_col + 1, url_to_new_hash[url])
        except Exception as e:
            log.error(f"Hash update failed for {tab_name}: {e}")


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────

def run():
    log.info("=" * 60)
    log.info(f"Regulatory Scanner — {today_str()}")
    log.info("=" * 60)

    # 1. Fetch all sources
    all_items = []
    all_items.extend(fetch_fda())
    all_items.extend(fetch_fda_api())
    all_items.extend(fetch_ema())
    all_items.extend(fetch_ich())

    log.info(f"Total items fetched: {len(all_items)}")

    # 2. Deduplicate by URL
    seen, unique = set(), []
    for it in all_items:
        key = it.get("url") or it.get("title", "")
        if key and key not in seen:
            seen.add(key)
            unique.append(it)

    log.info(f"After deduplication: {len(unique)} unique items")

    if not unique:
        log.warning("No items found. Check network access and RSS feeds.")
        return

    # 3. Load existing data for change detection
    try:
        gc  = get_gspread_client()
        spr = gc.open(SPREADSHEET_NAME)
        existing_updates = load_existing(ensure_worksheet(spr, "Updates"))
        existing_news    = load_existing(ensure_worksheet(spr, "News"))
        existing_all     = existing_updates + existing_news
    except Exception as e:
        log.error(f"Could not load existing data: {e}")
        existing_all = []

    # 4. Detect changes in already-known documents
    changes = detect_changes(unique, existing_all)

    # 5. Combine new items + changed items for analysis
    to_analyse = unique[:MAX_ITEMS_PER_RUN] + changes

    # 6. Gemini analysis
    log.info(f"Analysing {len(to_analyse)} items with Gemini…")
    analysed = analyse_with_gemini(to_analyse)

    # 7. Save to Sheets
    sheet_url = save_to_sheets(analysed)

    # 8. Update hashes for changed documents
    if changes:
        update_hashes(changes)

    # 9. Summary
    log.info("=" * 60)
    log.info(f"DONE — {len(analysed)} items processed")
    log.info(f"Changes detected: {len(changes)}")
    log.info(f"Sheet: {sheet_url}")
    log.info("=" * 60)

    return {
        "items_processed": len(analysed),
        "changes_detected": len(changes),
        "sheet_url": sheet_url,
    }


if __name__ == "__main__":
    run()
