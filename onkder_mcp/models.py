from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


SourceKind = Literal["scrape", "database"]
Language = Literal["en", "tr"]


class ArticleSearchResult(BaseModel):
    id: int
    title: str
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    volume: str | None = None
    issue: str | None = None
    doi: str | None = None
    abstract_url: str
    full_text_url: str
    pdf_url: str
    source: SourceKind = "scrape"


class SearchResponse(BaseModel):
    query: str | None = None
    total_found: int | None = None
    returned: int
    source: SourceKind
    results: list[ArticleSearchResult]


class ArchiveIssue(BaseModel):
    content_id: int
    year: int
    label: str
    url: str


class ArticleSection(BaseModel):
    name: str
    text: str


class ArticleReference(BaseModel):
    index: int | None = None
    text: str


class ArticleDetail(BaseModel):
    id: int
    title: str
    authors: list[str] = Field(default_factory=list)
    affiliations: list[str] = Field(default_factory=list)
    journal: str = "Turkish Journal of Oncology"
    year: int | None = None
    volume: str | None = None
    issue: str | None = None
    doi: str | None = None
    keywords: list[str] = Field(default_factory=list)
    summary: str | None = None
    sections: list[ArticleSection] = Field(default_factory=list)
    references: list[ArticleReference] = Field(default_factory=list)
    abstract_url: str
    full_text_url: str
    pdf_url: str
    source: SourceKind = "scrape"


class PagedMarkdown(BaseModel):
    article_id: int
    page_number: int
    total_pages: int
    chars_per_page: int
    markdown: str


class EvidenceItem(BaseModel):
    article_id: int
    title: str
    citation_label: str
    url: str
    doi: str | None = None
    excerpt: str | None = None


class AnswerResponse(BaseModel):
    question: str
    answer: str
    evidence: list[EvidenceItem]
    mode: Literal["llm", "extractive_no_llm"]
