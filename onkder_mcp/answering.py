from __future__ import annotations

import os

from openai import AsyncOpenAI

from .models import AnswerResponse, ArticleDetail, EvidenceItem
from .parser import detail_to_markdown
from .utils import clean_text


def build_evidence(articles: list[ArticleDetail], *, excerpt_chars: int = 700) -> list[EvidenceItem]:
    evidence: list[EvidenceItem] = []
    for index, article in enumerate(articles, start=1):
        excerpt_source = article.summary or "\n".join(section.text for section in article.sections[:2])
        evidence.append(
            EvidenceItem(
                article_id=article.id,
                title=article.title,
                citation_label=f"[{index}]",
                url=article.abstract_url,
                doi=article.doi,
                excerpt=clean_text(excerpt_source)[:excerpt_chars] or None,
            )
        )
    return evidence


async def answer_with_optional_llm(question: str, articles: list[ArticleDetail]) -> AnswerResponse:
    evidence = build_evidence(articles)
    if not evidence:
        return AnswerResponse(
            question=question,
            answer="ONKDER aramasinda bu soru icin kullanilabilir makale bulunamadi; yanit uretmek icin once daha dar veya farkli bir arama sorgusu deneyin.",
            evidence=[],
            mode="extractive_no_llm",
        )
    api_key = os.getenv("ONKDER_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        answer = _extractive_answer(question, evidence)
        return AnswerResponse(question=question, answer=answer, evidence=evidence, mode="extractive_no_llm")

    client = AsyncOpenAI(api_key=api_key, base_url=os.getenv("OPENAI_BASE_URL") or None)
    model = os.getenv("ONKDER_AI_MODEL", "gpt-4.1-mini")
    context = "\n\n".join(_compact_article_context(article, idx) for idx, article in enumerate(articles, start=1))
    system = (
        "Turkish Journal of Oncology kaynaklarina dayanan tibbi-akademik bir asistansin. "
        "Yalnizca verilen kanitlardan yanit ver, klinik karar veya kesin tedavi onerisi verme, "
        "belirsizlikleri belirt ve her onemli iddiayi [1], [2] gibi kaynak etiketleriyle destekle."
    )
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": f"Soru: {question}\n\nKaynaklar:\n{context}"},
        ],
        temperature=0.2,
    )
    answer = response.choices[0].message.content or ""
    return AnswerResponse(question=question, answer=answer.strip(), evidence=evidence, mode="llm")


def _compact_article_context(article: ArticleDetail, index: int) -> str:
    markdown = detail_to_markdown(article)
    return f"[{index}] Article ID {article.id}\n{markdown[:8000]}"


def _extractive_answer(question: str, evidence: list[EvidenceItem]) -> str:
    lines = [
        "LLM anahtari yapilandirilmadigi icin yanit, bulunan makalelerden alintisiz-ozetleyici kanit listesi olarak hazirlandi.",
        f"Soru: {question}",
        "",
        "Ilgili ONKDER kaynaklari:",
    ]
    for item in evidence:
        doi = f" DOI: {item.doi}." if item.doi else ""
        excerpt = f" Ozet bulgular: {item.excerpt}" if item.excerpt else ""
        lines.append(f"{item.citation_label} {item.title}.{doi} {item.url}.{excerpt}")
    return "\n".join(lines)
