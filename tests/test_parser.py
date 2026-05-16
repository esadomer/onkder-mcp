from onkder_mcp.parser import parse_archive, parse_article_detail, parse_issue_articles, parse_search_results


def test_parse_search_results() -> None:
    html = """
    <div>2 Record Found</div>
    <a href="abstract.php?lang=en&id=4" class="article_title">Prognostic factors in cancer</a>
    <span class="article_authors">Canfeza SEZGIN, Osman ZEKIOGLU</span>
    <a href="abstract.php?lang=en&id=6" class="article_title">Children with cancer</a>
    <span class="article_authors">Rejin KEBUDI</span>
    """
    total, results = parse_search_results(html, limit=10)

    assert total == 2
    assert [item.id for item in results] == [4, 6]
    assert results[0].title == "Prognostic factors in cancer"
    assert results[0].authors == ["Canfeza SEZGIN", "Osman ZEKIOGLU"]


def test_parse_archive() -> None:
    html = """
    <a data-toggle="collapse" href="#id_2026"><div>2026</div></a>
    <div class="collapse" id="id_2026">
      <a href="content.php?id=159">Number 2</a><br/>
      <a href="content.php?id=158">Number 1</a><br/>
    </div>
    """
    issues = parse_archive(html)

    assert len(issues) == 2
    assert issues[0].year == 2026
    assert issues[0].content_id == 159


def test_parse_issue_articles() -> None:
    html = """
    <span class="issue_data">Vol 41, Number 1</span>
    <a href="abstract.php?id=1539" class="article_title">ARID1A and colorectal cancer</a>
    <span class="article_authors">Jasiya QADIR,Sabhiya MAJID</span>
    """
    results = parse_issue_articles(html)

    assert results[0].id == 1539
    assert results[0].volume == "41"
    assert results[0].issue == "1"


def test_parse_article_detail_sections() -> None:
    html = """
    <div id="icerik-alani">
      <div>2018 , Vol 33 , Num 2</div>
      <div style="font-weight:bold">Prognostic Importance of Ki-67</div>
      <div id="authors_div">Gul KANYILMAZ<sup>1</sup>,Hatice ONDER<sup>2</sup></div>
      <span><sup>1</sup>Department A<br><sup>2</sup>Department B</span>
      <span><span style="font-weight:bold;">DOI :</span>10.5505/tjo.2018.1752</span>
      <span><span style="font-weight:bold;">Keywords :</span>glioma; Ki-67</span>
      <div><div><h2>Summary</h2><b>OBJECTIVE</b><br>Predictive role.</div></div>
      <div><div><h2>References</h2>1. First reference\n2. Second reference</div></div>
    </div>
    """
    article = parse_article_detail(html, article_id=1021)

    assert article.title == "Prognostic Importance of Ki-67"
    assert article.year == 2018
    assert article.volume == "33"
    assert article.issue == "2"
    assert article.doi == "10.5505/tjo.2018.1752"
    assert "Ki-67" in article.keywords
    assert article.summary == "OBJECTIVE\nPredictive role."
    assert len(article.references) == 2
