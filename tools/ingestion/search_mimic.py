#!/usr/bin/env python3
"""Search PubMed for MIMIC-based novel risk-factor and predictor studies.

Examples:
    python pubmed_mimic_risk_factors.py
    python pubmed_mimic_risk_factors.py --limit 20 --format json
    python pubmed_mimic_risk_factors.py --broad

The default query emphasizes records that describe a factor or predictor as
novel/new. Use --broad to retrieve general risk-factor and predictor papers.
Screening is still needed to distinguish discovery from prediction.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any


BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
DATABASE_QUERY = (
    '("Medical Information Mart for Intensive Care"[tiab] OR '
    '"MIMIC-III"[tiab] OR "MIMIC-IV"[tiab] OR '
    '"MIMIC III"[tiab] OR "MIMIC IV"[tiab])'
)
FACTOR_QUERY = (
    '("risk factor"[tiab] OR "risk factors"[tiab] OR '
    '"associated factors"[tiab] OR predictor[tiab] OR predictors[tiab])'
)
DEFAULT_QUERY = (
    f"{DATABASE_QUERY} AND "
    '(novel[tiab] OR "new risk factor"[tiab] OR "new risk factors"[tiab] OR '
    '"new predictor"[tiab] OR "new predictors"[tiab] OR '
    '"new biomarker"[tiab] OR "new biomarkers"[tiab]) AND '
    f"{FACTOR_QUERY}"
)
BROAD_QUERY = f"{DATABASE_QUERY} AND {FACTOR_QUERY}"


def request(url: str, params: dict[str, str], email: str | None, api_key: str | None) -> bytes:
    values = dict(params)
    if email:
        values["email"] = email
    if api_key:
        values["api_key"] = api_key
    full_url = f"{url}?{urllib.parse.urlencode(values)}"
    req = urllib.request.Request(
        full_url,
        headers={"User-Agent": "pubmed-mimic-risk-factor-search/1.0 (Python urllib)"},
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"NCBI E-utilities returned HTTP {exc.code}: {body[:500]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not connect to NCBI E-utilities: {exc.reason}") from exc


def search_pmids(query: str, limit: int, email: str | None, api_key: str | None) -> tuple[int, list[str]]:
    body = request(
        BASE_URL + "esearch.fcgi",
        {"db": "pubmed", "term": query, "retmax": str(min(limit, 10000)), "sort": "relevance", "retmode": "xml"},
        email,
        api_key,
    )
    root = ET.fromstring(body)
    count = int(root.findtext("./Count", default="0"))
    pmids = [item.text or "" for item in root.findall("./IdList/Id")]
    return count, pmids


def node_text(node: ET.Element | None) -> str:
    if node is None:
        return ""
    return "".join(node.itertext()).strip()


def parse_article(article: ET.Element) -> dict[str, Any]:
    citation = article.find("./MedlineCitation")
    article_data = citation.find("./Article") if citation is not None else None
    if citation is None or article_data is None:
        return {}

    pmid = citation.findtext("./PMID", default="")
    title = node_text(article_data.find("./ArticleTitle"))
    journal = node_text(article_data.find("./Journal/Title"))
    pub_date = article_data.find("./Journal/JournalIssue/PubDate")
    year = ""
    if pub_date is not None:
        year = pub_date.findtext("./Year", default="")
        if not year:
            medline_date = pub_date.findtext("./MedlineDate", default="")
            year = medline_date[:4] if medline_date else ""

    authors = []
    for author in article_data.findall("./AuthorList/Author"):
        collective = author.findtext("./CollectiveName")
        last = author.findtext("./LastName")
        initials = author.findtext("./Initials")
        name = collective or " ".join(part for part in (last, initials) if part)
        if name:
            authors.append(name)

    abstract_parts = []
    for part in article_data.findall("./Abstract/AbstractText"):
        label = part.attrib.get("Label")
        text = node_text(part)
        if text:
            abstract_parts.append(f"{label}: {text}" if label else text)

    doi = ""
    for article_id in article.findall("./PubmedData/ArticleIdList/ArticleId"):
        if article_id.attrib.get("IdType") == "doi":
            doi = article_id.text or ""
            break

    return {
        "pmid": pmid,
        "title": title,
        "year": year,
        "journal": journal,
        "authors": authors,
        "doi": doi,
        "abstract": " ".join(abstract_parts),
        "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else "",
    }


def fetch_articles(pmids: list[str], email: str | None, api_key: str | None) -> list[dict[str, Any]]:
    if not pmids:
        return []
    # Stay under the unauthenticated NCBI limit between ESearch and EFetch.
    time.sleep(0.36)
    body = request(
        BASE_URL + "efetch.fcgi",
        {"db": "pubmed", "id": ",".join(pmids), "retmode": "xml"},
        email,
        api_key,
    )
    root = ET.fromstring(body)
    records = [parse_article(article) for article in root.findall("./PubmedArticle")]
    by_pmid = {record["pmid"]: record for record in records if record.get("pmid")}
    return [by_pmid[pmid] for pmid in pmids if pmid in by_pmid]


def markdown_report(query: str, total: int, records: list[dict[str, Any]]) -> str:
    lines = [
        f"PubMed 检索完成：命中 {total} 条，以下列出 {len(records)} 条。",
        f"检索时间：{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"检索式：`{query}`",
        "",
        "注：该检索覆盖风险因素、相关因素及预测因子研究；是否属于真正的‘新风险因子发现’，需结合摘要和全文判断。",
        "",
    ]
    for index, record in enumerate(records, start=1):
        authors = ", ".join(record["authors"][:3])
        if len(record["authors"]) > 3:
            authors += ", et al."
        meta = " · ".join(part for part in (record["year"], record["journal"], f"PMID: {record['pmid']}") if part)
        lines.append(f"{index}. **{record['title']}** ({meta})")
        if authors:
            lines.append(f"   {authors}")
        if record["doi"]:
            lines.append(f"   DOI: {record['doi']}")
        lines.append(f"   {record['url']}")
        abstract = record["abstract"]
        if abstract:
            lines.append(f"   摘要：{abstract}")
        lines.append("")
    return "\n".join(lines).rstrip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=30, help="maximum PubMed records to return (default: 30; E-utilities max: 10000)")
    parser.add_argument("--all", action="store_true", help="retrieve all matches, up to PubMed E-utilities' 10000-record limit")
    parser.add_argument("--query", help="override the PubMed query")
    parser.add_argument("--broad", action="store_true", help="search general risk-factor and predictor studies, without the novelty term")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown", help="output format")
    args = parser.parse_args()
    if not 1 <= args.limit <= 10000:
        parser.error("--limit must be between 1 and 10000")

    email = os.environ.get("NCBI_EMAIL")
    api_key = os.environ.get("NCBI_API_KEY")
    try:
        query = args.query or (BROAD_QUERY if args.broad else DEFAULT_QUERY)
        requested_limit = 10000 if args.all else args.limit
        total, pmids = search_pmids(query, requested_limit, email, api_key)
        records = fetch_articles(pmids, email, api_key)
    except (RuntimeError, ET.ParseError) as exc:
        print(f"PubMed search failed: {exc}", file=sys.stderr)
        return 1

    if args.format == "json":
        print(json.dumps({"query": query, "total_matches": total, "returned": len(records), "articles": records}, ensure_ascii=False, indent=2))
    else:
        print(markdown_report(query, total, records))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
