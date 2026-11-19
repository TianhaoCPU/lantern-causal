# MIMIC 论文文本数据集

本数据集整理工作区已有的论文全文 OCR、PubMed 摘要、初筛记录和病例复现登记表。用 **PMID** 作为唯一标识，供全文检索、论文方法抽取和后续病例任务构建。它包含论文内容和来源记录，未运行患者分析，也未添加隐变量角色或因果图的真值标签。

| 内容 | 数量 |
|---|---:|
| 文献 JSON / JSONL 记录 | 154 |
| 全文 TXT | 138 |
| 摘要 TXT | 154 |
| 缺少全文、仅有摘要及元数据 | 16 |
| 全文页数 / OCR 表格块数 | 1,802 / 665 |
| 进入原摘要筛选表 / 同时有全文 | 83 / 75 |
| 有 OCR 复核提示的论文 / 页 | 22 / 35 |

## 文件布局

~~~text
datasets/literature/
├── txt/<PMID>.txt            # 138 份全文，含页码、公式和制表符分隔的表格
├── abstracts/<PMID>.txt      # 154 份 PubMed 摘要
├── json/<PMID>.json          # 154 份结构化记录，包含正文或明确的缺失标记
├── papers.jsonl             # 同样的 154 份记录，每行一个完整 JSON 对象
├── index.csv                # Excel 可读的文献索引（UTF-8 BOM）
├── index.json               # 轻量索引，不重复放入全文
├── dataset_info.json        # 版本、来源快照、标准化规则
├── quality_report.json      # 缺全文清单、复核页清单及数据质量统计
├── schema/paper.schema.json # 每篇记录的 JSON Schema
├── sources/                 # 构建时的元数据快照，便于脱离工作区读取
├── reports/validation.json  # 已执行的一致性与来源校验
└── docs/                    # 字段字典、处理过程和版本记录
~~~

全文 TXT 直接以 `[Page 1]` 开始，去掉了原 OCR TXT 中重复的题名和管道元数据前言。页内仅移除了 668 个独立的 `<MERGE>` 布局标记；公式、数值、页眉页脚和参考文献仍保留。JSON 的 `text` 与对应 TXT 的 Unicode 内容完全相同，包括末尾换行。JSON 的 `pages` 提供页级字符位置，`headings` 保留 OCR 标题，`tables` 保留原表格 HTML 及其页码。

没有全文的 16 篇使用 `full_text_available=false`、`content_type="abstract_only"`，且 `text`、`page_count`、`files.txt` 为 `null`。其摘要位于 `abstracts/`，不会用摘要冒充全文，也不会生成空的全文 TXT。

## 读取示例

仅需 Python 3.10 及以上版本；构建、校验和下列示例均只使用标准库。以下命令从项目根目录执行；独立复制本数据集后，请将路径改为数据集所在位置。

读取 RDW 首例：

~~~python
import json
from pathlib import Path

dataset = Path("datasets/literature")
paper = json.loads((dataset / "json/40918184.json").read_text(encoding="utf-8"))
print(paper["title"])
print(paper["full_text_available"], paper["page_count"])
text = paper["text"]
print(text[:300])

page = paper["pages"][1]
page_text = text[page["char_start"]:page["char_end"]]
print("第二页：", page_text[:200])
~~~

逐行加载全部全文，不把摘要记录混入全文分析：

~~~python
import json

with open("datasets/literature/papers.jsonl", encoding="utf-8") as stream:
    for line in stream:
        paper = json.loads(line)
        if not paper["full_text_available"]:
            continue
        print(paper["pmid"], len(paper["text"]), len(paper["tables"]))
~~~

筛出需要复核的页：

~~~python
import json
from pathlib import Path

report = json.loads(
    Path("datasets/literature/quality_report.json").read_text(encoding="utf-8")
)
for page in report["pages_recommended_for_review"]:
    print(page["pmid"], page["page_number"], page["warnings"])
~~~

## 重建和校验

仅校验本数据集，不依赖原始工作区：

~~~bash
lantern validate-corpus --dataset datasets/literature
~~~

同时与原始 OCR、PDF、下载清单等核对，并保存校验记录：

~~~bash
lantern validate-corpus --dataset datasets/literature --workspace /path/to/original-assets --report datasets/literature/reports/validation.json
~~~

本地文献资产齐备时重建生成内容。模块代码位于项目根目录的 `src/lantern_causal/datasets/`。重建仅覆盖本数据集生成的文本、记录、索引和来源快照，原文献与 OCR 目录保持原样；文档和脚本保留。出于原文许可和数据使用条款考虑，生成的全文、摘要与逐篇 JSON 默认不纳入 Git；新克隆的仓库需先按项目 README 配置本地文献资产，再运行重建命令。

~~~bash
python -m lantern_causal.datasets.build --workspace /path/to/original-assets --replace-generated
lantern validate-corpus --dataset datasets/literature --workspace /path/to/original-assets --report datasets/literature/reports/validation.json
~~~

## 数据用途与解释

这是供检索和任务制作的**参考语料**。原文结论、题名、PMID、摘要和病例初筛标签可能泄露前述隐变量盲测的答案；生成评测题时须明确哪些内容允许作为模型输入。当前未自动划分训练集和测试集，也没有把初筛的相关风险因子当作真实因果角色。原复现登记表的“未运行”等状态按构建时快照保留。

35 页的提示均为 OCR 文本与原 PDF 文本层的词重合较低，需重点检查。该指标不是人工核定的识别准确率。图表中的全部视觉信息未被文字覆盖，正文含表格不表示图像或曲线已被完整解析。标题是 OCR 识别的标题块，尚未人工整理成统一的 Introduction/Methods/Results 分节。作者信息来自已有摘要索引，部分只列前三名与 `et al.`。原始出版许可不统一，来源清单中缺少许可代码时保留为空值。

字段含义见 [数据字典](docs/DATA_DICTIONARY.md)，整理步骤见 [处理过程](docs/PROCESS.md)，本次变化见 [版本记录](docs/CHANGELOG.md)。
