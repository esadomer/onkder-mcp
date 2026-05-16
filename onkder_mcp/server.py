from __future__ import annotations

from typing import Literal

from fastmcp import FastMCP

from .answering import answer_with_optional_llm
from .client import DatabaseProvider, OnkderClient
from .models import AnswerResponse, ArchiveResponse, IssueArticlesResponse, PagedMarkdown, SearchResponse
from .parser import detail_to_markdown
from .utils import paginate

mcp = FastMCP(
    name="ONKDER Tibbi MCP",
    instructions=(
        "Turkish Journal of Oncology / onkder.org uzerinde akademik makale arama, "
        "makale metadata/tam metin getirme ve bilimsel referansli yanit uretme araclari."
    ),
)

client = OnkderClient()
database = DatabaseProvider()


@mcp.tool
async def search_onkder_articles(
    query: str,
    limit: int = 10,
    source: Literal["auto", "scrape", "database"] = "auto",
    lang: Literal["en", "tr"] = "en",
) -> SearchResponse:
    """ONKDER makalelerinde baslik/ozet/anahtar kelime odakli akademik arama yapar."""
    limit = max(1, min(limit, 50))
    if source in {"auto", "database"} and database.configured:
        return database.search_articles(query=query, limit=limit)
    return await client.search_articles(query=query, limit=limit, lang=lang)


@mcp.tool
async def advanced_onkder_search(
    title: str | None = None,
    authors: str | None = None,
    summary: str | None = None,
    keyword: str | None = None,
    limit: int = 10,
    lang: Literal["en", "tr"] = "en",
) -> SearchResponse:
    """ONKDER arama formundaki alanlari ayri ayri kullanarak makale arar."""
    limit = max(1, min(limit, 50))
    return await client.search_articles(title=title, authors=authors, summary=summary, keyword=keyword, limit=limit, lang=lang)


@mcp.tool
async def get_onkder_article(article_id: int, lang: Literal["en", "tr"] = "en", include_full_text: bool = True):
    """Belirli bir ONKDER makalesinin metadata, ozet, bolum ve kaynak bilgilerini getirir."""
    return await client.get_article(article_id, lang=lang, include_sections=include_full_text)


@mcp.tool
async def get_onkder_article_markdown(
    article_id: int,
    page_number: int = 1,
    chars_per_page: int = 5000,
    lang: Literal["en", "tr"] = "en",
) -> PagedMarkdown:
    """Makale tam metnini kaynak gostermeye uygun Markdown olarak sayfali dondurur."""
    article = await client.get_article(article_id, lang=lang, include_sections=True)
    markdown = detail_to_markdown(article)
    page, total_pages = paginate(markdown, page_number=page_number, chars_per_page=chars_per_page)
    return PagedMarkdown(
        article_id=article_id,
        page_number=max(1, min(page_number, total_pages)),
        total_pages=total_pages,
        chars_per_page=max(1000, min(chars_per_page, 20000)),
        markdown=page,
    )


@mcp.tool
async def list_onkder_archive(year: int | None = None):
    """ONKDER arsivindeki yil/sayi listesini getirir."""
    issues = await client.list_archive()
    if year is not None:
        issues = [issue for issue in issues if issue.year == year]
    return ArchiveResponse(year=year, returned=len(issues), issues=issues)


@mcp.tool
async def list_onkder_issue_articles(content_id: int, limit: int = 50):
    """Arsivdeki bir sayinin content.php id'si ile makale listesini getirir."""
    limit = max(1, min(limit, 100))
    results = await client.list_issue_articles(content_id, limit=limit)
    return IssueArticlesResponse(content_id=content_id, returned=len(results), results=results)


@mcp.tool
async def answer_onkder_question(
    question: str,
    search_query: str | None = None,
    max_articles: int = 5,
    lang: Literal["en", "tr"] = "en",
) -> AnswerResponse:
    """ONKDER makalelerini tarayip bilimsel referans etiketleriyle yanit uretir."""
    max_articles = max(1, min(max_articles, 10))
    search = await client.search_articles(query=search_query or question, limit=max_articles, lang=lang)
    articles = []
    for result in search.results[:max_articles]:
        try:
            articles.append(await client.get_article(result.id, lang=lang, include_sections=True))
        except Exception:
            continue
    return await answer_with_optional_llm(question, articles)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
