#!/usr/bin/env python3
"""Collect PubMed papers reporting novel risk factors/predictors from public databases.

The default run searches a curated set of non-MIMIC public databases and writes
one Markdown report per database. It returns at most 30 PubMed records per
database; --all retrieves every match up to PubMed's 10,000-record limit. Each
report keeps the complete abstract and adds an abstract-level evidence note.

Examples:
    python pubmed_public_database_risk_factors.py
    python pubmed_public_database_risk_factors.py --all
    python pubmed_public_database_risk_factors.py --limit 10 --databases uk_biobank nhanes
    python pubmed_public_database_risk_factors.py --broad
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import http.client
import os
from pathlib import Path
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any


BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
OUT_DIR = Path("public_database_risk_factor_reports")

FACTOR_QUERY = (
    '("risk factor"[tiab] OR "risk factors"[tiab] OR '
    '"associated factor"[tiab] OR "associated factors"[tiab] OR '
    'predictor[tiab] OR predictors[tiab] OR biomarker[tiab] OR biomarkers[tiab])'
)
NOVELTY_QUERY = (
    '(novel[tiab] OR "new risk factor"[tiab] OR "new risk factors"[tiab] OR '
    '"new predictor"[tiab] OR "new predictors"[tiab] OR '
    '"new biomarker"[tiab] OR "new biomarkers"[tiab] OR '
    'emerging[tiab] OR discovery[tiab] OR discover[tiab] OR "previously unknown"[tiab])'
)

# Exact database phrases reduce false matches from generic uses of "database".
DATABASES: dict[str, dict[str, str]] = {
    "eicu_crd": {
        "name": "eICU Collaborative Research Database",
        "query": '("eICU Collaborative Research Database"[tiab] OR eICU-CRD[tiab] OR "eICU database"[tiab])',
    },
    "uk_biobank": {
        "name": "UK Biobank",
        "query": '("UK Biobank"[tiab] OR "United Kingdom Biobank"[tiab])',
    },
    "nhanes": {
        "name": "NHANES",
        "query": '(NHANES[tiab] OR "National Health and Nutrition Examination Survey"[tiab])',
    },
    "seer": {
        "name": "SEER",
        "query": '(SEER[tiab] OR "Surveillance, Epidemiology, and End Results"[tiab])',
    },
    "all_of_us": {
        "name": "All of Us Research Program",
        "query": '("All of Us Research Program"[tiab] OR "All of Us"[tiab])',
    },
    "amsterdamumcdb": {
        "name": "AmsterdamUMCdb",
        "query": '(AmsterdamUMCdb[tiab] OR "Amsterdam UMC database"[tiab] OR "Amsterdam University Medical Centers database"[tiab])',
    },
    "hirid": {
        "name": "HiRID",
        "query": '(HiRID[tiab] OR "High time-resolution ICU dataset"[tiab] OR "high time resolution ICU"[tiab])',
    },
    "sicdb": {
        "name": "SICdb / Salzburg ICU database",
        "query": '(SICdb[tiab] OR "Salzburg ICU database"[tiab] OR "Salzburg Intensive Care database"[tiab])',
    },
    "biobank_japan": {
        "name": "BioBank Japan",
        "query": '("BioBank Japan"[tiab] OR "Biobank Japan"[tiab])',
    },
    "finn_gen": {
        "name": "FinnGen",
        "query": '(FinnGen[tiab] OR "Finnish genetic study"[tiab])',
    },
    "china_kadoorie": {
        "name": "China Kadoorie Biobank",
        "query": '("China Kadoorie Biobank"[tiab] OR "Kadoorie Biobank"[tiab])',
    },
    "cprd": {
        "name": "Clinical Practice Research Datalink",
        "query": '("Clinical Practice Research Datalink"[tiab] OR CPRD[tiab])',
    },
    "charls": {
        "name": "China Health and Retirement Longitudinal Study",
        "query": '("China Health and Retirement Longitudinal Study"[tiab] OR CHARLS[tiab])',
    },
    "framingham": {
        "name": "Framingham Heart Study",
        "query": '("Framingham Heart Study"[tiab] OR Framingham[tiab])',
    },
    "nis": {
        "name": "US National Inpatient Sample",
        "query": '("National Inpatient Sample"[tiab] OR NIS[tiab])',
    },
}

DATASET_MENTION: dict[str, str] = {
    "eicu_crd": r"eICU(?:-CRD| Collaborative Research Database| database)",
    "uk_biobank": r"UK Biobank|UKBB",
    "nhanes": r"NHANES|National Health and Nutrition Examination Survey",
    "seer": r"SEER|Surveillance, Epidemiology, and End Results",
    "all_of_us": r"All of Us(?: Research Program)?",
    "amsterdamumcdb": r"AmsterdamUMCdb|Amsterdam UMC database|Amsterdam University Medical Centers database",
    "hirid": r"HiRID|high time[- ]resolution ICU",
    "sicdb": r"SICdb|Salzburg ICU database|Salzburg Intensive Care database",
    "biobank_japan": r"BioBank Japan|Biobank Japan",
    "finn_gen": r"FinnGen|Finnish genetic study",
    "china_kadoorie": r"China Kadoorie Biobank|Kadoorie Biobank",
    "cprd": r"Clinical Practice Research Datalink|\bCPRD\b",
    "charls": r"China Health and Retirement Longitudinal Study|\bCHARLS\b",
    "framingham": r"Framingham Heart Study|Framingham",
    "nis": r"National Inpatient Sample|\bNIS\b",
}


def request(params: dict[str, str], email: str | None, api_key: str | None) -> bytes:
    values = dict(params)
    endpoint = values.pop("endpoint", "")
    if email:
        values["email"] = email
    if api_key:
        values["api_key"] = api_key
    url = BASE_URL + endpoint
    full_url = f"{url}?{urllib.parse.urlencode(values)}"
    req = urllib.request.Request(
        full_url,
        headers={"User-Agent": "pubmed-public-risk-factor-search/1.0 (Python urllib)"},
    )
    last_error: Exception | None = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=90) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"NCBI E-utilities HTTP {exc.code}: {body[:500]}") from exc
        except (urllib.error.URLError, http.client.IncompleteRead, ConnectionResetError, TimeoutError) as exc:
            last_error = exc
            if attempt == 3:
                break
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"NCBI E-utilities request failed after retries: {last_error}")


def ncbi_request(endpoint: str, params: dict[str, str], email: str | None, api_key: str | None) -> bytes:
    # NCBI permits about 3 requests/sec without an API key. A small delay also
    # makes a multi-database run polite and reproducible.
    time.sleep(0.38)
    values = dict(params)
    values["endpoint"] = endpoint
    return request(values, email, api_key)


def search_pmids(query: str, limit: int, email: str | None, api_key: str | None) -> tuple[int, list[str]]:
    body = ncbi_request(
        "esearch.fcgi",
        {"db": "pubmed", "term": query, "retmax": str(min(limit, 10000)), "sort": "relevance", "retmode": "xml"},
        email,
        api_key,
    )
    root = ET.fromstring(body)
    count = int(root.findtext("./Count", default="0"))
    pmids = [node.text or "" for node in root.findall("./IdList/Id")]
    return count, pmids


def node_text(node: ET.Element | None) -> str:
    return "".join(node.itertext()).strip() if node is not None else ""


def parse_article(article: ET.Element) -> dict[str, Any]:
    citation = article.find("./MedlineCitation")
    data = citation.find("./Article") if citation is not None else None
    book = article.find("./BookDocument")
    if citation is None or data is None:
        # PubMed can return reports/books as PubmedBookArticle. They can still
        # contain an abstract and a DOI, so keep them in an all-record export.
        if book is None:
            return {}
        pmid = book.findtext("./PMID", default="")
        title = node_text(book.find("./Book/BookTitle"))
        journal = node_text(book.find("./Book/Publisher/PublisherName"))
        date = book.find("./Book/PubDate")
        author_nodes = book.findall("./Book/AuthorList/Author")
    else:
        pmid = citation.findtext("./PMID", default="")
        title = node_text(data.find("./ArticleTitle"))
        journal = node_text(data.find("./Journal/Title"))
        date = data.find("./Journal/JournalIssue/PubDate")
        author_nodes = data.findall("./AuthorList/Author")
    year = date.findtext("./Year", default="") if date is not None else ""
    if not year and date is not None:
        year = (date.findtext("./MedlineDate", default="") or "")[:4]
    authors: list[str] = []
    for author in author_nodes:
        collective = author.findtext("./CollectiveName")
        name = collective or " ".join(x for x in (author.findtext("./LastName"), author.findtext("./Initials")) if x)
        if name:
            authors.append(name)
    parts: list[str] = []
    abstract_parent = data if data is not None else book
    for abstract in abstract_parent.findall("./Abstract/AbstractText") if abstract_parent is not None else []:
        text = node_text(abstract)
        if text:
            label = abstract.attrib.get("Label")
            parts.append(f"{label}: {text}" if label else text)
    doi = ""
    for article_id in article.findall("./PubmedData/ArticleIdList/ArticleId") + article.findall("./BookDocument/ArticleIdList/ArticleId"):
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
        "abstract": " ".join(parts),
        "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else "",
    }


def fetch_articles(pmids: list[str], email: str | None, api_key: str | None, batch_size: int = 100) -> list[dict[str, Any]]:
    if not pmids:
        return []
    # Keep EFetch URLs short when --all retrieves hundreds or thousands of IDs.
    by_pmid: dict[str, dict[str, Any]] = {}
    for start in range(0, len(pmids), batch_size):
        batch = pmids[start : start + batch_size]
        body = ncbi_request(
            "efetch.fcgi",
            {"db": "pubmed", "id": ",".join(batch), "retmode": "xml"},
            email,
            api_key,
        )
        root = ET.fromstring(body)
        articles = root.findall("./PubmedArticle") + root.findall("./PubmedBookArticle")
        for article in articles:
            record = parse_article(article)
            if record.get("pmid"):
                by_pmid[record["pmid"]] = record
    return [by_pmid[pmid] for pmid in pmids if pmid in by_pmid]


def evidence_note(article: dict[str, Any]) -> str:
    text = f"{article['title']} {article['abstract']}"
    if re.search(r"mendelian randomization|instrumental variable|target trial emulation|causal effect", text, re.I):
        return "摘要涉及因果推断设计；仍需核对关键假设、混杂控制及敏感性分析。"
    if re.search(r"machine learning|random forest|xgboost|nomogram|prediction model|predictive model", text, re.I):
        return "包含预测模型或机器学习；模型变量不自动等于新因果危险因素。"
    if re.search(r"external validation|external cohort|multicenter|multi-center|two cohorts|independent cohort", text, re.I):
        return "摘要提到外部/多中心验证；仍属于观察性证据。"
    return "摘要级观察性关联；‘新风险因子’需结合全文和独立验证确认。"


def is_relevant_candidate(database_key: str, article: dict[str, Any]) -> bool:
    title = article["title"]
    abstract = article["abstract"]
    if len(abstract) < 180:
        return False
    # Exclude reviews, conference proceedings, data-resource papers, and protocols.
    if re.search(r"review|editorial|commentary|protocol|symposium|conference|population-based biobanking|data resource|database description|harmonized .* survey", title, re.I):
        return False
    if not re.search(DATASET_MENTION[database_key], abstract, re.I):
        return False
    return bool(re.search(r"risk factor|predictor|biomarker|associated with|association between|risk of", abstract, re.I))


def abstract_finding(article: dict[str, Any]) -> str:
    text = article["abstract"]
    # Prefer an explicit conclusion; otherwise retain a compact abstract tail.
    matches = list(re.finditer(r"(?:CONCLUSIONS?|CONCLUSION|FINDINGS?)\s*:\s*", text, re.I))
    if matches:
        finding = text[matches[-1].end():]
    else:
        finding = text[-800:] if text else "摘要未提供。"
    return re.sub(r"\s+", " ", finding).strip()


def report(database_key: str, spec: dict[str, str], query: str, total: int, fetched_count: int, records: list[dict[str, Any]], limit: int, all_mode: bool) -> str:
    limit_text = "全部（PubMed E-utilities 上限 10,000 条）" if all_mode else str(limit)
    lines = [
        f"# {spec['name']}：公开数据库新风险因子/预测因子文献",
        "",
        f"PubMed 检索完成：命中 **{total}** 条，抓取 **{fetched_count}** 条，写入摘要初筛后 **{len(records)}** 条（每个数据库上限：{limit_text}）。",
        f"检索时间：{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"检索式：`{query}`",
        "",
        "筛选说明：检索聚焦摘要中提到 novel/new/emerging/discovery 以及 risk factor/predictor/biomarker 的文章，并剔除明显的综述、会议摘要、数据资源介绍和摘要未明确提及目标数据库的记录。全量模式会对检索命中的全部记录执行该摘要初筛。以下仍是候选研究，不等同于已证实的全新因果危险因素；预测模型中的变量、已知指标在新队列中的应用和统计关联需要阅读全文及独立验证。",
        "",
    ]
    for index, article in enumerate(records, 1):
        authors = ", ".join(article["authors"][:3])
        if len(article["authors"]) > 3:
            authors += ", et al."
        meta = " · ".join(x for x in (article["year"], article["journal"], f"PMID: {article['pmid']}") if x)
        lines.append(f"## {index}. {article['title']}")
        lines.append("")
        if meta:
            lines.append(f"- **基本信息：** {meta}")
        if authors:
            lines.append(f"- **作者：** {authors}")
        if article["doi"]:
            lines.append(f"- **DOI：** {article['doi']}")
        lines.append(f"- **PubMed：** {article['url']}")
        lines.append(f"- **摘要层面主要发现：** {abstract_finding(article)}")
        lines.append(f"- **证据边界：** {evidence_note(article)}")
        lines.append(f"- **完整摘要：** {article['abstract'] or 'PubMed 未提供摘要。'}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=30, help="records per database (default 30; max 10000; ignored with --all)")
    parser.add_argument("--all", action="store_true", help="write all matches per database, up to PubMed's 10000-record limit")
    parser.add_argument("--databases", nargs="+", choices=sorted(DATABASES), help="database keys to search; default searches all configured databases")
    parser.add_argument("--broad", action="store_true", help="omit novelty terms and search general risk-factor/predictor papers")
    parser.add_argument("--output-dir", default=str(OUT_DIR), help="directory for Markdown reports")
    args = parser.parse_args()
    if not 1 <= args.limit <= 10000:
        parser.error("--limit must be between 1 and 10000")
    selected = args.databases or list(DATABASES)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    email = os.environ.get("NCBI_EMAIL")
    api_key = os.environ.get("NCBI_API_KEY")
    index: list[tuple[str, str, int, int, str]] = []
    failures: list[str] = []
    for key in selected:
        spec = DATABASES[key]
        query = f"{spec['query']} AND {FACTOR_QUERY}" if args.broad else f"{spec['query']} AND {NOVELTY_QUERY} AND {FACTOR_QUERY}"
        try:
            # Fetch a relevance-ranked pool and screen false positives before
            # applying the per-database output cap. --all removes that cap.
            candidate_limit = 10000 if args.all else min(10000, max(args.limit * 4, args.limit))
            total, pmids = search_pmids(query, candidate_limit, email, api_key)
            fetched = fetch_articles(pmids, email, api_key)
            screened = [article for article in fetched if is_relevant_candidate(key, article)]
            records = screened if args.all else screened[:args.limit]
            path = output_dir / f"{key}.md"
            path.write_text(report(key, spec, query, total, len(fetched), records, args.limit, args.all), encoding="utf-8")
            index.append((key, spec["name"], total, len(records), str(path)))
            print(f"{key}: matches={total}, records={len(records)}, file={path}")
        except (RuntimeError, ET.ParseError) as exc:
            failures.append(f"{key}: {exc}")
            print(f"{key}: FAILED: {exc}", file=sys.stderr)

    index_lines = [
        "# 其他公开数据库新风险因子/预测因子文献索引",
        "",
        f"生成时间：{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "默认每个数据库最多保留 30 条经摘要初筛的相关性排序结果；使用 --all 时会抓取并写入所有命中记录中通过摘要初筛的条目。候选研究需结合全文确认是否真正发现新风险因子。",
        "",
        "| 数据库 | PubMed 命中 | 写入条目 | 文件 |",
        "|---|---:|---:|---|",
    ]
    for key, name, total, count, path in index:
        index_lines.append(f"| {name} (`{key}`) | {total} | {count} | [{Path(path).name}]({Path(path).name}) |")
    if failures:
        index_lines.extend(["", "## 失败的数据库", ""])
        index_lines.extend(f"- {failure}" for failure in failures)
    (output_dir / "README.md").write_text("\n".join(index_lines) + "\n", encoding="utf-8")
    return 1 if failures and not index else 0


if __name__ == "__main__":
    raise SystemExit(main())
