from __future__ import annotations

import math
import re
from html import unescape
from urllib.parse import parse_qs, urljoin, urlparse

from bs4 import BeautifulSoup

BASE_URL = "https://onkder.org/"


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    value = unescape(value)
    value = value.replace("\xa0", " ")
    value = re.sub(r"[ \t\r\f\v]+", " ", value)
    value = re.sub(r"\n\s*\n+", "\n\n", value)
    return value.strip()


def normalize_onkder_url(href: str | None) -> str:
    if not href:
        return BASE_URL
    href = href.replace("https:///onkder.org", BASE_URL.rstrip("/"))
    href = href.replace("http:///onkder.org", BASE_URL.rstrip("/"))
    return urljoin(BASE_URL, href)


def extract_id_from_href(href: str | None) -> int | None:
    if not href:
        return None
    parsed = urlparse(normalize_onkder_url(href))
    values = parse_qs(parsed.query).get("id")
    if values and values[0].isdigit():
        return int(values[0])
    match = re.search(r"\bid=(\d+)", href)
    return int(match.group(1)) if match else None


def split_authors(text: str) -> list[str]:
    text = clean_text(re.sub(r"\s*\d+\s*", "", text))
    return [clean_text(part) for part in text.split(",") if clean_text(part)]


def split_keywords(text: str) -> list[str]:
    text = re.sub(r"^(Keywords|Anahtar Kelimeler)\s*:\s*", "", clean_text(text), flags=re.I)
    parts = re.split(r"[,;]\s*|\s{2,}", text)
    return [clean_text(part) for part in parts if clean_text(part)]


def soup_text(markup: str) -> str:
    soup = BeautifulSoup(markup, "html.parser")
    return clean_text(soup.get_text("\n"))


def paginate(text: str, page_number: int = 1, chars_per_page: int = 5000) -> tuple[str, int]:
    text = text or ""
    chars_per_page = max(1000, min(chars_per_page, 20000))
    total_pages = max(1, math.ceil(len(text) / chars_per_page))
    page_number = max(1, min(page_number, total_pages))
    start = (page_number - 1) * chars_per_page
    return text[start : start + chars_per_page], total_pages


def article_urls(article_id: int) -> dict[str, str]:
    return {
        "abstract_url": f"{BASE_URL}abstract.php?id={article_id}",
        "full_text_url": f"{BASE_URL}text.php?id={article_id}",
        "pdf_url": f"{BASE_URL}pdf.php?id={article_id}",
    }


def to_markdown_heading(text: str, level: int = 2) -> str:
    return f"{'#' * level} {clean_text(text)}"
