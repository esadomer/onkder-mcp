# ONKDER Tıbbi MCP

ONKDER Tıbbi MCP, [onkder.org](https://onkder.org/) üzerinde yayımlanan **Turkish Journal of Oncology / Türk Onkoloji Dergisi** makaleleri için akademik arama, makale getirme, Markdown dönüştürme ve kanıta dayalı yanıt üretme araçları sağlayan bir FastMCP sunucusudur.

Yargı MCP yaklaşımına benzer biçimde her veri kaynağı işlemi ayrı MCP tool olarak sunulur: arama, doküman getirme, Markdown sayfalama, arşiv/sayı gezme ve referanslı yanıt üretme.

## Özellikler

- `search.php` formu üzerinden başlık, yazar, özet ve anahtar kelime araması.
- `archive.php` ve `content.php?id=...` üzerinden yıl/sayı ve sayı içi makale listesi.
- `abstract.php?id=...`, `text.php?id=...` ve `pdf.php?id=...` bağlantılarından metadata, özet, tam metin, DOI, anahtar kelime ve kaynak çıkarımı.
- Uzun makaleler için sayfalanmış Markdown çıktısı.
- `ONKDER_OPENAI_API_KEY` veya `OPENAI_API_KEY` varsa LLM destekli, kaynak etiketli akademik yanıt üretimi.
- Doğrudan veritabanı erişimi olan kurum içi kurulumlar için opsiyonel, salt okunur SQL arama adaptörü.

## Kurulum

```bash
uv sync
```

veya:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Çalıştırma

```bash
uv run onkder-mcp
```

Claude Desktop benzeri MCP istemcileri için örnek yapılandırma:

```json
{
  "mcpServers": {
    "onkder-mcp": {
      "command": "uv",
      "args": ["run", "onkder-mcp"],
      "cwd": "/Users/esadkay/Documents/tibbimcp"
    }
  }
}
```

## MCP Araçları

- `search_onkder_articles(query, limit, source, lang)`: Genel akademik arama.
- `advanced_onkder_search(title, authors, summary, keyword, limit, lang)`: ONKDER form alanlarıyla ayrıntılı arama.
- `get_onkder_article(article_id, lang, include_full_text)`: Makale metadata ve tam metin bölümleri.
- `get_onkder_article_markdown(article_id, page_number, chars_per_page, lang)`: Sayfalanmış Markdown.
- `list_onkder_archive(year)`: Arşiv yıl/sayı listesi.
- `list_onkder_issue_articles(content_id, limit)`: Belirli sayıdaki makaleler.
- `answer_onkder_question(question, search_query, max_articles, lang)`: ONKDER kaynaklarıyla referanslı yanıt.

## AI Yapılandırması

LLM destekli yanıt için:

```bash
export ONKDER_OPENAI_API_KEY="..."
export ONKDER_AI_MODEL="gpt-4.1-mini"
```

OpenAI uyumlu yerel veya kurumsal bir endpoint kullanılacaksa:

```bash
export OPENAI_BASE_URL="http://localhost:8080/v1"
export ONKDER_AI_MODEL="local-model-name"
```

API anahtarı yoksa `answer_onkder_question` yine çalışır, ancak bulunan makalelerden çıkarımsal kanıt listesi döndürür.

## Doğrudan Veritabanı Adaptörü

ONKDER veritabanına yetkili, salt okunur erişim varsa aşağıdaki değişkenler ayarlanabilir:

```bash
export ONKDER_DATABASE_URL="postgresql+psycopg://readonly:password@host/db"
export ONKDER_DB_SEARCH_SQL='
SELECT id, title, authors, year, volume, issue, doi
FROM articles
WHERE title ILIKE :like_query OR abstract ILIKE :like_query OR keywords ILIKE :like_query
ORDER BY year DESC, id DESC
LIMIT :limit
'
```

`search_onkder_articles(..., source="database")` bu sorguyu kullanır. Güvenlik için yalnızca `SELECT` ile başlayan sorgular kabul edilir.

## Test

```bash
uv run pytest
```

## Notlar

Bu sunucu klinik karar destek sistemi değildir. Üretilen yanıtlar akademik literatür keşfi ve özetleme amacı taşır; tanı veya tedavi önerisi olarak kullanılmamalıdır.
