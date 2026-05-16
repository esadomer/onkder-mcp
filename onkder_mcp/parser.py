from __future__ import annotations

import re

from bs4 import BeautifulSoup, Tag

from .models import (
    ArchiveIssue,
    ArticleDetail,
    ArticleReference,
    ArticleSearchResult,
    ArticleSection,
)
from .utils import (
    BASE_URL,
    article_urls,
    clean_text,
    extract_id_from_href,
    normalize_onkder_url,
    split_authors,
    split_keywords,
)


def parse_search_results(html: str, *, limit: int, source: str = "scrape") -> tuple[int | None, list[ArticleSearchResult]]:
    soup = BeautifulSoup(html, "html.parser")
    page_text = clean_text(soup.get_text(" "))
    total_match = re.search(r"(\d+)\s+Record\s+Found", page_text, re.I)
    total_found = int(total_match.group(1)) if total_match else None
    results: list[ArticleSearchResult] = []

    for title_link in soup.select("a.article_title"):
        article_id = extract_id_from_href(title_link.get("href"))
        if article_id is None:
            continue
        authors_node = _next_element(title_link, "span", "article_authors")
        urls = article_urls(article_id)
        results.append(
            ArticleSearchResult(
                id=article_id,
                title=clean_text(title_link.get_text(" ")),
                authors=split_authors(authors_node.get_text(" ") if authors_node else ""),
                abstract_url=urls["abstract_url"],
                full_text_url=urls["full_text_url"],
                pdf_url=urls["pdf_url"],
                source=source,  # type: ignore[arg-type]
            )
        )
        if len(results) >= limit:
            break

    return total_found, results


def parse_archive(html: str) -> list[ArchiveIssue]:
    soup = BeautifulSoup(html, "html.parser")
    issues: list[ArchiveIssue] = []
    current_year: int | None = None

    for element in soup.select("a"):
        href = element.get("href", "")
        text = clean_text(element.get_text(" "))
        year_match = re.search(r"\b(19|20)\d{2}\b", text)
        if href.startswith("#id_") and year_match:
            current_year = int(year_match.group(0))
            continue
        if "content.php" in href:
            content_id = extract_id_from_href(href)
            if content_id is not None and current_year is not None and text:
                issues.append(
                    ArchiveIssue(
                        content_id=content_id,
                        year=current_year,
                        label=text,
                        url=normalize_onkder_url(href),
                    )
                )
    return issues


def parse_issue_articles(html: str, *, limit: int = 50) -> list[ArticleSearchResult]:
    soup = BeautifulSoup(html, "html.parser")
    issue_meta = _extract_issue_meta(soup)
    results: list[ArticleSearchResult] = []
    seen: set[int] = set()

    for title_link in soup.select("a.article_title"):
        article_id = extract_id_from_href(title_link.get("href"))
        if article_id is None or article_id in seen:
            continue
        seen.add(article_id)
        authors_node = _next_element(title_link, "span", "article_authors")
        urls = article_urls(article_id)
        results.append(
            ArticleSearchResult(
                id=article_id,
                title=clean_text(title_link.get_text(" ")),
                authors=split_authors(authors_node.get_text(" ") if authors_node else ""),
                year=issue_meta.get("year"),
                volume=issue_meta.get("volume"),
                issue=issue_meta.get("issue"),
                abstract_url=urls["abstract_url"],
                full_text_url=urls["full_text_url"],
                pdf_url=urls["pdf_url"],
            )
        )
        if len(results) >= limit:
            break

    return results


def parse_article_detail(html: str, *, article_id: int, include_sections: bool = True) -> ArticleDetail:
    soup = BeautifulSoup(html, "html.parser")
    content = soup.select_one("#icerik-alani") or soup
    urls = article_urls(article_id)
    issue_meta = _extract_issue_meta(soup)

    title = ""
    authors: list[str] = []
    affiliations: list[str] = []
    doi: str | None = None
    keywords: list[str] = []
    summary: str | None = None

    authors_node = content.select_one("#authors_div")
    if authors_node:
        authors = split_authors(authors_node.get_text(" "))

    title_node = authors_node.find_previous("div") if authors_node else _first_article_title(content)
    if title_node:
        title = clean_text(title_node.get_text(" "))

    if authors_node:
        affiliation_node = authors_node.find_next("span")
        if affiliation_node:
            affiliations = [
                clean_text(part)
                for part in affiliation_node.get_text("\n").split("\n")
                if clean_text(part)
            ]

    content_text = clean_text(content.get_text(" "))
    doi_match = re.search(r"\bDOI\s*:\s*([^\s]+)", content_text, re.I)
    if doi_match:
        doi = doi_match.group(1).strip(".,;") or None

    keyword_match = re.search(r"\b(Keywords|Anahtar Kelimeler)\s*:\s*(.+?)(?:\s{2,}|$)", content_text, re.I)
    if keyword_match:
        keywords = split_keywords(keyword_match.group(2))

    sections: list[ArticleSection] = []
    references: list[ArticleReference] = []
    if include_sections:
        sections = _parse_sections(content)
        for section in sections:
            if section.name.lower() in {"summary", "ozet", "özet"}:
                summary = section.text
            if "reference" in section.name.lower() or "kaynak" in section.name.lower():
                references = _parse_references(section.text)

    if summary is None:
        summary_node = content.find("h2", string=re.compile(r"Summary|Özet|Ozet", re.I))
        if summary_node:
            summary = _section_text_from_heading(summary_node)

    return ArticleDetail(
        id=article_id,
        title=title,
        authors=authors,
        affiliations=affiliations,
        year=issue_meta.get("year"),
        volume=issue_meta.get("volume"),
        issue=issue_meta.get("issue"),
        doi=doi,
        keywords=keywords,
        summary=summary,
        sections=sections,
        references=references,
        abstract_url=urls["abstract_url"],
        full_text_url=urls["full_text_url"],
        pdf_url=urls["pdf_url"],
    )


def detail_to_markdown(article: ArticleDetail) -> str:
    lines = [f"# {article.title or f'Article {article.id}'}", ""]
    if article.authors:
        lines += ["**Authors:** " + ", ".join(article.authors)]
    citation_bits = [
        "Turkish Journal of Oncology",
        str(article.year) if article.year else None,
        f"Vol {article.volume}" if article.volume else None,
        f"No {article.issue}" if article.issue else None,
    ]
    lines += ["**Citation:** " + ", ".join(bit for bit in citation_bits if bit)]
    if article.doi:
        lines += [f"**DOI:** {article.doi}"]
    lines += [f"**URL:** {article.abstract_url}", ""]
    if article.keywords:
        lines += ["**Keywords:** " + ", ".join(article.keywords), ""]
    for section in article.sections:
        lines += [f"## {section.name}", "", section.text, ""]
    if not article.sections and article.summary:
        lines += ["## Summary", "", article.summary, ""]
    return "\n".join(lines).strip()


def _next_element(start: Tag, tag_name: str, class_name: str) -> Tag | None:
    for sibling in start.next_elements:
        if isinstance(sibling, Tag) and sibling.name == tag_name and class_name in sibling.get("class", []):
            return sibling
    return None


def _extract_issue_meta(soup: BeautifulSoup | Tag) -> dict[str, int | str | None]:
    text = clean_text(soup.get_text(" "))
    meta: dict[str, int | str | None] = {"year": None, "volume": None, "issue": None}
    match = re.search(r"\b(19|20)\d{2}\s*,\s*Vol\s*([0-9A-Za-z]+)\s*,\s*Num\s*([0-9A-Za-z]+)", text, re.I)
    if match:
        meta["year"] = int(match.group(0)[:4])
        meta["volume"] = match.group(2)
        meta["issue"] = match.group(3)
        return meta
    match = re.search(r"Vol\s+([0-9A-Za-z]+),\s*Number\s+([0-9A-Za-z]+)", text, re.I)
    if match:
        meta["volume"] = match.group(1)
        meta["issue"] = match.group(2)
    year_match = re.search(r"\b(19|20)\d{2}\b", text)
    if year_match:
        meta["year"] = int(year_match.group(0))
    return meta


def _first_article_title(content: Tag) -> Tag | None:
    candidates = [
        node
        for node in content.find_all("div")
        if "font-weight:bold" in (node.get("style") or "") and len(clean_text(node.get_text(" "))) > 8
    ]
    return candidates[0] if candidates else None


def _parse_sections(content: Tag) -> list[ArticleSection]:
    sections: list[ArticleSection] = []
    for heading in content.find_all("h2"):
        name = clean_text(heading.get_text(" "))
        if not name:
            continue
        text = _section_text_from_heading(heading)
        if text:
            sections.append(ArticleSection(name=name, text=text))
    return sections


def _section_text_from_heading(heading: Tag) -> str:
    parent = heading.parent
    if not parent:
        return ""
    clone = BeautifulSoup(str(parent), "html.parser")
    for node in clone.select("h2, a.menu, a.selected_menu, script, style"):
        node.decompose()
    for node in clone.select("a[name]"):
        if not clean_text(node.get_text(" ")):
            node.decompose()
    return clean_text(clone.get_text("\n"))


def _parse_references(text: str) -> list[ArticleReference]:
    references: list[ArticleReference] = []
    chunks = re.split(r"\n(?=\d+[\.\)])", text)
    for chunk in chunks:
        chunk = clean_text(chunk)
        if not chunk:
            continue
        match = re.match(r"^(\d+)[\.\)]\s*(.+)", chunk, re.S)
        if match:
            references.append(ArticleReference(index=int(match.group(1)), text=clean_text(match.group(2))))
        else:
            references.append(ArticleReference(text=chunk))
    return references
