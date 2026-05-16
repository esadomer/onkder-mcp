from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any, Literal

import httpx
from sqlalchemy import create_engine, text

from .models import ArticleSearchResult, SearchResponse
from .parser import parse_archive, parse_article_detail, parse_issue_articles, parse_search_results
from .utils import BASE_URL, article_urls


class OnkderClient:
    def __init__(self, base_url: str = BASE_URL, timeout: float = 20.0) -> None:
        self.base_url = base_url.rstrip("/") + "/"
        self.timeout = timeout
        self.user_agent = os.getenv(
            "ONKDER_USER_AGENT",
            "onkder-mcp/0.1 academic-search (+https://onkder.org)",
        )

    async def search_articles(
        self,
        *,
        query: str | None = None,
        title: str | None = None,
        authors: str | None = None,
        summary: str | None = None,
        keyword: str | None = None,
        limit: int = 10,
        lang: Literal["en", "tr"] = "en",
    ) -> SearchResponse:
        if query and not any([title, authors, summary, keyword]):
            total_found, results = await self._general_query_search(query=query, limit=limit)
        else:
            total_found, results = await self._search_form(
                title=title,
                authors=authors,
                summary=summary,
                keyword=keyword,
                limit=limit,
            )
        if lang == "tr":
            for result in results:
                result.abstract_url = f"{self.base_url}abstract.php?lang=tr&id={result.id}"
        return SearchResponse(query=query or title or keyword or summary or authors, total_found=total_found, returned=len(results), source="scrape", results=results)

    async def get_article(self, article_id: int, *, lang: Literal["en", "tr"] = "en", include_sections: bool = True):
        path = f"text.php?id={article_id}" if include_sections else f"abstract.php?lang={lang}&id={article_id}"
        html = await self._request_text("GET", path)
        return parse_article_detail(html, article_id=article_id, include_sections=include_sections)

    async def list_archive(self):
        html = await self._request_text("GET", "archive.php")
        return parse_archive(html)

    async def list_issue_articles(self, content_id: int, *, limit: int = 50):
        html = await self._request_text("GET", f"content.php?id={content_id}")
        return parse_issue_articles(html, limit=limit)

    async def _request_text(self, method: str, path: str, **kwargs: Any) -> str:
        headers = {"User-Agent": self.user_agent, "Accept": "text/html,application/xhtml+xml"}
        async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout, follow_redirects=True, headers=headers) as client:
            response = await client.request(method, path, **kwargs)
            response.raise_for_status()
            response.encoding = response.encoding or "utf-8"
            return response.text

    async def _search_form(
        self,
        *,
        title: str | None = None,
        authors: str | None = None,
        summary: str | None = None,
        keyword: str | None = None,
        limit: int = 10,
    ) -> tuple[int | None, list[ArticleSearchResult]]:
        data = {
            "authors": authors or "",
            "title": title or "",
            "summary": summary or "",
            "keyword": keyword or "",
            "sbmt_search": "Search",
        }
        html = await self._request_text("POST", "search.php", data=data)
        return parse_search_results(html, limit=limit)

    async def _general_query_search(self, *, query: str, limit: int) -> tuple[int | None, list[ArticleSearchResult]]:
        seen: dict[int, ArticleSearchResult] = {}
        total_found = 0
        terms = [query]
        tokens = [token for token in query.replace("/", " ").split() if len(token) >= 3]
        if len(tokens) > 1:
            terms.extend(tokens[:4])

        for term in terms:
            for field in ("title", "keyword", "summary"):
                search_kwargs = {field: term}
                total, results = await self._search_form(limit=limit, **search_kwargs)
                if total:
                    total_found += total
                for result in results:
                    seen.setdefault(result.id, result)
                    if len(seen) >= limit:
                        return total_found or None, list(seen.values())

        return total_found or None, list(seen.values())


class DatabaseProvider:
    """Optional read-only database adapter for deployments with direct ONKDER DB access."""

    def __init__(self, database_url: str | None = None, search_sql: str | None = None) -> None:
        self.database_url = database_url or os.getenv("ONKDER_DATABASE_URL")
        self.search_sql = search_sql or os.getenv("ONKDER_DB_SEARCH_SQL")

    @property
    def configured(self) -> bool:
        return bool(self.database_url and self.search_sql)

    def search_articles(self, *, query: str, limit: int = 10) -> SearchResponse:
        if not self.configured:
            raise RuntimeError("ONKDER_DATABASE_URL ve ONKDER_DB_SEARCH_SQL ayarlanmamis.")
        assert self.database_url is not None
        assert self.search_sql is not None
        if not self.search_sql.lstrip().lower().startswith("select"):
            raise ValueError("ONKDER_DB_SEARCH_SQL guvenlik icin yalnizca SELECT ile baslamalidir.")

        engine = create_engine(self.database_url)
        params = {"query": query, "like_query": f"%{query}%", "limit": limit}
        with engine.connect() as connection:
            rows = connection.execute(text(self.search_sql), params).mappings().fetchmany(limit)

        results = [self._row_to_article(row) for row in rows]
        return SearchResponse(query=query, total_found=None, returned=len(results), source="database", results=results)

    @staticmethod
    def _row_to_article(row: Mapping[str, Any]) -> ArticleSearchResult:
        article_id = int(row["id"])
        urls = article_urls(article_id)
        authors_raw = row.get("authors") or ""
        authors = authors_raw if isinstance(authors_raw, list) else [part.strip() for part in str(authors_raw).split(",") if part.strip()]
        return ArticleSearchResult(
            id=article_id,
            title=str(row.get("title") or ""),
            authors=authors,
            year=int(row["year"]) if row.get("year") else None,
            volume=str(row.get("volume")) if row.get("volume") else None,
            issue=str(row.get("issue")) if row.get("issue") else None,
            doi=str(row.get("doi")) if row.get("doi") else None,
            abstract_url=str(row.get("abstract_url") or urls["abstract_url"]),
            full_text_url=str(row.get("full_text_url") or urls["full_text_url"]),
            pdf_url=str(row.get("pdf_url") or urls["pdf_url"]),
            source="database",
        )
