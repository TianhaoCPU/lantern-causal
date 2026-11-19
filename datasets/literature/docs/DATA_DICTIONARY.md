# 数据字典

本版本来自本地 PubMed 报告、下载清单、全文 OCR 与已有病例登记表；生成脚本不请求网络，不补写缺失的临床或因果标签。更新以显式重建为准，不自动同步。所有 JSON 是 UTF-8，JSONL 的每一行对应一篇论文，`pmid` 为字符串类型的唯一键。

## 每篇 JSON 和 JSONL

| 字段 | 类型 | 含义和来源 |
|---|---|---|
| `schema_version` | string | 当前为 `1.0`。 |
| `pmid` | string | PubMed 唯一编号，只含数字，文件名也使用该编号。 |
| `source_document_id` | string | 原 OCR 文档编号，例如 `005_40918184`，摘要记录亦保留对应序号。 |
| `source_number` | integer | 原检索报告中的顺序，从 1 开始。 |
| `title` | string | PubMed 报告题名，并与下载清单交叉核对。 |
| `publication_year` | integer | 原 PubMed 报告年份。 |
| `journal` | string | 原 PubMed 报告期刊名。 |
| `authors_display` | string/null | 原报告显示的作者字符串，可能只有前三名和 `et al.`，不是完整作者表。 |
| `doi` | string/null | 原报告 DOI；没有时为 `null`。 |
| `pmcid` | string/null | 原下载清单中的 PMC 编号。 |
| `pubmed_url` | string | 由 PMID 构建的 PubMed 文献链接。 |
| `abstract` | string | 原报告的非空摘要，154 篇均有；未改写或总结。 |
| `full_text_available` | boolean | 是否存在通过本次构建校验的全文 OCR。 |
| `content_type` | enum | `ocr_full_text` 或 `abstract_only`。 |
| `text` | string/null | 标准化全文，含页码；与对应全文 TXT 完全相同。缺全文时为 `null`。 |
| `text_sha256` | string/null | `text` 的 UTF-8 编码 SHA-256，缺全文时为 `null`。 |
| `page_count` | integer/null | 全文页数。缺全文时为 `null`。 |
| `pages` | array | 依次排列的逐页索引、质量和位置；无全文时为空数组。 |
| `headings` | array | OCR 标题块索引；无全文时为空数组。尚未统一语义分节。 |
| `tables` | array | OCR 表格块与原 HTML；无全文时为空数组。 |
| `files` | object | 数据集内部的 JSON、全文 TXT 和摘要 TXT 相对路径。 |
| `quality` | object | OCR 状态、复核页、布局标记删除数与图块数量。 |
| `provenance` | object | 原文件位置、哈希、OCR 模型及下载来源。原路径相对于工作区根目录。 |
| `screening` | object/null | 原中文摘要筛选 CSV 的整行，保留原列名；未收录时为 `null`。不是全文审核或因果标签。 |
| `replication_registry` | object | 原中文病例复现登记 CSV 的整行，保留原列名和原有状态。 |
| `annotation_status` | string | 固定为 `not_causal_ground_truth`，表示当前语料不提供真实因果角色标签。 |

## 页码、标题和表格

| 字段 | 类型 | 含义 |
|---|---|---|
| `pages[].page_number` | integer | PDF 页码，从 1 开始。 |
| `pages[].char_start` / `char_end` | integer | Python Unicode 字符偏移，左闭右开。切片返回该页正文，不含 `[Page n]` 或页间分隔符。不是 UTF-8 字节位置。 |
| `pages[].block_count` | integer | 原页的 OCR 块数，含标题、文本、图像等块。 |
| `pages[].status` | string | 源 OCR 页状态，当前完整记录均为 `ok`。 |
| `pages[].warnings` | array[string] | 原 OCR 复核提示。 |
| `pages[].quality_diagnostics` | object | 原页词数、与 PDF 文本层重合诊断及说明；其数值不是人工准确率。 |
| `pages[].generation_finish_reason` | string | OCR 模型结束原因，当前完整页均为 `stop`。 |
| `pages[].rotation_degrees_ccw` | integer | 识别前按原管道校正的逆时针方向角。 |
| `headings[].page_number` / `block_order` | integer | 原页码及页内块序号。 |
| `headings[].level` | integer/null | 原 OCR 标题层级，可能为空。 |
| `headings[].text` | string | OCR 标题文字。 |
| `tables[].page_number` / `block_order` | integer | 原页码及页内块序号。 |
| `tables[].html` | string | 原 OCR 表格块内容，保留 HTML 的行列和合并单元格信息，不重新推断数值。 |
| `tables[].bbox_model` | array[number] | 原模型坐标，未换算成 PDF 点坐标。 |

## 文件、质量和来源

| 字段 | 含义 |
|---|---|
| `files.json` | `json/<PMID>.json`。 |
| `files.txt` | 有全文时为 `txt/<PMID>.txt`，否则为 `null`。 |
| `files.abstract_txt` | `abstracts/<PMID>.txt`，均存在。 |
| `quality.ocr_status` | `complete` 或 `not_available`。 |
| `quality.pages_with_warnings` | 有提示的页码数组，空数组表示当前管道没有发出提示。 |
| `quality.manual_review_recommended` | 是否因这些提示而建议优先复核，不表示无提示的文献已经人工核验。 |
| `quality.ocr_warnings` | 页码与提示代码的紧凑记录。 |
| `quality.removed_standalone_merge_markers` | 从该文页内删除的独立 `<MERGE>` 行数。 |
| `quality.figure_block_count` | 原 OCR 的 `image` 和 `chart` 块数。 |
| `quality.visual_content_fully_transcribed` | 有全文时固定为 `false`，无全文时为 `null`。 |
| `provenance.source_paths_relative_to` | 固定为 `workspace_root`。 |
| `provenance.original_pdf` / `original_ocr_json` / `original_ocr_txt` | 原工作区中的对应路径；无全文时为空值。 |
| `provenance.original_pdf_sha256` / `original_ocr_json_sha256` / `original_ocr_txt_sha256` | 对原文件字节计算的 SHA-256。 |
| `provenance.ocr_model` / `pipeline_signature` | 源 OCR 模型名和配置签名。 |
| `provenance.download_status` / `download_url` | 原下载清单记录的状态与来源地址，未重新请求或核查地址。 |
| `provenance.license_code_from_manifest` | 原清单的许可代码，未知时为 `null`。 |

## 索引和报告

`index.json`、`index.csv` 每篇一行，字段为 `pmid`、`title`、`publication_year`、`doi`、`content_type`、`full_text_available`、`page_count`、`text_characters`、`warning_page_count`、`abstract_screened`、`json`、`txt`、`abstract_txt`。其中 `text_characters` 是全文字符数（含页码），没有全文时为 0；`abstract_screened` 仅表示原筛选表是否收录。CSV 中空值为空单元格，布尔值为 `True/False`；JSON 则使用标准的 `null/true/false`。

`quality_report.json` 包含文献数、全文数、摘要数、页数、表格数、初筛数、提示数、删除的布局标记数、全文哈希重复组、缺全文文献清单和建议复核页清单。`dataset_info.json` 记录数据集版本、时间、标准化方式、构建脚本哈希与来源快照哈希。`reports/validation.json` 记录最近一次已通过的一致性检查，以及是否同时检查了原始工作区。
