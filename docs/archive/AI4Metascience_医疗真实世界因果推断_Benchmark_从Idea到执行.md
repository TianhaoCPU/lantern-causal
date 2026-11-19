# AI4Metascience：医疗真实世界因果推断边界 Benchmark

> 目标：建立一个可下载、可复现、可审计的 benchmark，检验 AI 是否能把医疗问题、真实世界数据（RWD）和因果推断理论连接成正确的研究方案，并在允许执行代码时给出可信的估计、异质性分析和不确定性说明。
>
> 建议项目名：`AI4MetaCausal-RWE`。本文是从 idea 到执行的工作方案，不等同于监管申报方案，也不替代伦理审查、统计分析计划（SAP）或领域专家审核。

## 1. 先定义要探索的边界

### 1.1 核心研究问题

主问题可以写成：

> 给定临床背景、研究问题、数据字典和可下载数据，AI 能否构造一个可识别、可执行、可复现且与数据生成机制一致的医疗真实世界因果研究，并正确解释结果的因果含义和局限性？

拆成四个可测维度：

1. **因果问题识别**：能否从自然语言背景中区分描述性问题、预测问题、干预问题和反事实问题？
2. **研究设计与识别**：能否写出目标试验、时间零点、治疗策略、结局、混杂假设、可交换性、正值性和一致性？
3. **估计与决策**：能否选择与数据结构匹配的 g-formula、IPTW、边际结构模型、双重稳健估计、TMLE、DML、CATE 或动态治疗策略方法？
4. **科学推理与审计**：能否发现偏倚、量化不确定性、进行敏感性分析、拒绝超出数据支持范围的结论，并产出可复现材料？

### 1.2 不要把三个能力混在一起

Benchmark 必须分别报告：

- **识别能力**：在没有运行模型时，AI 是否知道目标 estimand 和识别假设；
- **估计能力**：运行标准代码后，数值是否接近已知真值或专家参考结果；
- **研究执行能力**：从数据下载、清洗、队列定义、分析到报告是否可重复。

一个模型可以“算对 ATE”但写错时间零点，也可以设计正确但代码有 bug。总分不能掩盖这些差异。

## 2. 理论底座：把“因果状态机”落成可检验对象

“因果状态机”不是目前因果推断中唯一公认的标准术语。项目中建议把它定义为一个**纵向结构因果模型（SCM）+ 状态转移图 + 干预动作 + 结局过程**的操作性表示；不要把自定义名称当作已有理论结论。结构因果模型、潜在结果和目标试验框架分别回答：变量如何生成、干预下会发生什么、以及研究应该模拟哪一个随机试验。

### 2.1 推荐状态机最小形式

```text
S0 目标人群/可入组
 |  A0: 未治疗、治疗 A、治疗 B（或动态策略）
 v
S1 治疗启动后的随访状态
 |  L1: 症状、实验室、依从性、就医等时间变化变量
 |  A1: 继续、换药、停药、加药
 v
S2 中间事件/竞争风险状态
 |  Y: 目标结局；D: 死亡；C: 失访/删失
 v
S3 结局或终止状态
```

每条转移至少记录：时间、触发条件、动作、可观测变量、未观测变量、是否受既往治疗影响、是否可能导致选择偏倚。AI 的任务不是画一张漂亮的图，而是回答：

- 时间零点前的变量能否用于混杂调整？
- 治疗后的变量是否是中介、时间变化混杂，还是碰撞点？
- 是否存在 immortal time、time-varying confounding、informative censoring、competing risk？
- 目标 estimand 是静态策略的 ITT、per-protocol、累积风险差、风险比、RMST，还是 CATE/策略价值？

### 2.2 与目标试验一一对应

所有任务包都应有一份“目标试验协议”金标准，至少包含：

| 要素                 | 必须明确的内容                                      |
| -------------------- | --------------------------------------------------- |
| Eligibility          | 入组标准、排除标准、首次可观察时间、基线窗口        |
| Treatment strategies | 治疗版本、剂量、启动时限、持续/切换规则、对照       |
| Assignment           | 随机分配在理想试验中的含义；RWD 中如何近似          |
| Time zero            | 入组和治疗分配的同一时点，或明确 delayed-entry 设计 |
| Follow-up            | 起止时间、删失、死亡和竞争风险规则                  |
| Outcome              | 定义、代码/表型、测量窗口、复合结局组成             |
| Estimand             | ITT/per-protocol、ATE/ATT/CATE、风险差/比值/RMST 等 |
| Identification       | 一致性、条件可交换性、正值性、无信息删失等假设      |
| Analysis             | g-method、权重、模型、交叉拟合、方差和敏感性分析    |

目标试验模拟的基本框架来自 Hernán 与 Robins；TARGET guideline 可作为透明报告清单，STROBE/RECORD 用于观察性研究和常规收集健康数据的报告完整性。

## 3. Benchmark 总体架构

### 3.1 三层数据轨道

不要用单一数据集代表“AI 的因果能力”。建议分三层：

| 轨道              | 数据特点                                     | 可评估内容                                                            | 不能声称的内容         |
| ----------------- | -------------------------------------------- | --------------------------------------------------------------------- | ---------------------- |
| A：已知真值合成   | 数据生成机制、潜在结局或真实 DAG 已知        | ATE/CATE 数值误差、识别、代码正确性                                   | 真实临床可迁移性       |
| B：半合成真实结构 | 协变量来自真实医疗数据，治疗/结局或机制可控  | 现实混杂下的估计和设计                                                | 真实世界治疗效果       |
| C：真实 RWD       | 真实 EHR/claims/registry，通常没有真因果效应 | 数据适用性、队列构建、偏倚诊断、可复现性、与已发表研究/负对照的一致性 | “接近金标准”的因果真值 |

主论文的数值排行榜应以 A、B 为主；C 轨道用于检验研究流程是否能在真实数据约束下工作。

### 3.2 首批数据与文章资料

| 资源                         | 获取方式                                          | 真值/限制                                                                   | 建议 benchmark 任务                                                    |
| ---------------------------- | ------------------------------------------------- | --------------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| **Synthea / SyntheticMass**  | MITRE 下载页或本地生成；CSV/FHIR/C-CDA            | 合成患者；可以在模块中植入已知治疗和结局机制                                | 从 FHIR/CSV 构建队列；状态机；动态治疗；已知 ATE/CATE                  |
| **OHDSI Eunomia**            | R 包 `downloadEunomiaData()` 下载；OMOP CDM       | 小型合成 OMOP 数据，适合管道测试，不代表真实效应                            | CDM 词汇映射、队列定义、标准分析、数据质量检查                         |
| **CMS DE-SynPUF 2008–2010**  | CMS 官方下载                                      | 合成 Medicare claims；适合理赔结构和 ETL，不提供真实患者因果真值            | 入组、理赔事件、暴露窗口、删失、claims 研究方案                        |
| **ACIC 2016 challenge**      | `causallib` 数据目录/挑战资料                     | 协变量带有真实背景，治疗和结局为模拟，具有可计算真值                        | 倾向评分、IPTW、matching、标准化、双重稳健；ATE 误差                   |
| **RealCause**                | GitHub / arXiv 论文代码                           | 以真实数据分布拟合生成模型并设定因果结构；提供 ATE/CATE 真值                | 比较估计器；偏差、RMSE、PEHE、policy value；检验预测指标与因果指标差异 |
| **CSuite**                   | Microsoft GitHub 下载                             | 已知结构方程、真实因果图、观测/干预测试集                                   | DAG 识别、干预效应、反事实预测、结构不变性                             |
| **多治疗合成高保真临床数据** | Shi 等论文及其补充数据/代码入口                   | 约 10+ 抗高血压治疗，已知治疗效应，具有纵向诊断、药物、实验室和社会经济变量 | 多值治疗、IPTW/PS matching/DR、CATE、策略比较                          |
| **MIMIC-IV**                 | PhysioNet credentialing、培训和数据使用协议后访问 | 真实去标识 ICU 数据；访问受限；没有天然因果真值                             | EHR 时间轴、治疗启动、结局表型、缺失和时间变化混杂                     |
| **MIMIC-III Demo**           | MIT MIMIC 文档可直接下载                          | 25 个左右表/示例数据；仅适合开发，不可用于最终效应结论                      | SQL、数据字典、时间零点、代码生成和调试                                |

### 3.3 推荐的首个可发表最小集合

第一版不要同时覆盖所有疾病。建议选一个治疗问题，例如“重症患者治疗 A 与治疗 B 对 28 天死亡的影响”，然后用同一研究问题贯穿：

1. Synthea：验证状态机和已知真值；
2. ACIC/RealCause：验证标准因果估计器；
3. MIMIC-III Demo：验证数据工程与任务包；
4. MIMIC-IV：验证真实 EHR 约束（需获批）；
5. CMS DE-SynPUF：验证 claims 版本的可迁移设计。

这样既有可判分的数字真值，也有真实世界数据的外部效度问题。

## 4. 把每篇文章/每个数据集做成 Task Pack

每个 benchmark case 使用版本化目录，不把答案直接放在模型可见输入里：

```text
cases/HTN-001/
  case.yaml                 # 背景、研究问题、允许的数据和输出要求
  background.pdf            # 文章/指南/临床背景（可下载或项目自有材料）
  data_dictionary.csv       # 字段、单位、时间含义、缺失编码
  data_access.md            # 下载、许可、credentialing、版本
  train/                    # 模型可见数据或抽样
  hidden_truth/             # 评测器专用：DAG、潜在结局、真值、陷阱
  reference_protocol.md     # 专家金标准和可接受变体
  scoring.yaml              # 自动评分规则
  run.sh / notebook.ipynb   # 可复现执行入口
```

`case.yaml` 至少包含：疾病/人群、治疗与对照、时间范围、数据版本、主要结局、要求的 estimand、是否允许工具和代码、资源限制、禁止外部数据、输出格式。

### 4.1 模型输入

- 临床背景和已发表文章（可只提供摘要，也可提供全文）；
- 数据字典、表结构、编码本、下载说明；
- 研究问题和约束（例如只准使用基线变量）；
- 可选：数据样本或本地数据库连接；
- 不提供 hidden truth、参考协议中的陷阱标签和最终结果。

### 4.2 模型输出：同时要求 Markdown 和结构化 JSON

```yaml
study_question: "..."
estimand:
  population: "...
  treatment: "..."
  comparator: "..."
  outcome: "..."
  time_horizon: "..."
  contrast: "risk_difference | risk_ratio | RMST | CATE | ..."
target_trial:
  eligibility: "..."
  time_zero: "..."
  follow_up: "..."
identification_assumptions:
  - consistency
  - conditional_exchangeability
  - positivity
data_mapping:
  exposure: [{table: "...", field: "...", rule: "..."}]
  outcome: [{table: "...", field: "...", rule: "..."}]
  covariates: [{name: "...", role: "baseline_confounder | mediator | collider | ..."}]
analysis:
  primary: "..."
  sensitivity: ["...", "..."]
uncertainty_and_limits: ["..."]
reproducibility: ["data_version", "code", "random_seed", "environment"]
```

结构化字段用于自动评分；Markdown 用于专家评价 AI 的理由、假设和边界意识。

## 5. 评测矩阵：先评方案，再评数字

### 5.1 评分维度

总分建议 100 分，并保留分项分数：

| 维度                   | 分值 | 判定重点                                               |
| ---------------------- | ---: | ------------------------------------------------------ |
| 目标问题和 estimand    |   15 | 是否定义人群、治疗、时间、结局、对比和分析对象         |
| 目标试验与时间轴       |   15 | 入组、time zero、随访、治疗策略、删失、竞争风险        |
| 因果图与识别假设       |   15 | 混杂/中介/碰撞点区分；一致性、交换性、正值性           |
| 数据适用性与映射       |   15 | 字段是否真的测量目标变量；编码、缺失、测量窗口         |
| 方法选择与执行         |   15 | 方法与 estimand/数据结构匹配；权重诊断、交叉拟合、方差 |
| 数值结果               |   15 | ATE bias、RMSE、coverage、CATE PEHE、policy value      |
| 偏倚、敏感性和不确定性 |    5 | 未测混杂、负对照、E-value/偏倚分析、外部效度           |
| 可复现性、伦理和沟通   |    5 | 代码、版本、许可、数据治理和不过度解读                 |

关键错误应设置“闸门”：例如把治疗后变量当基线混杂因素、把预测 AUC 当因果证据、忽略 immortal time、把合成数据结果写成真实患者效应，任一项可使总分封顶（例如不超过 59 分）。

### 5.2 数值指标

对已知真值数据，固定 estimand 后计算：

- `ATE bias = estimated_ATE - true_ATE`；
- `absolute error`、`RMSE`、相对误差；
- 置信区间覆盖率和平均区间宽度；
- CATE 的 PEHE、policy value、policy regret、分层校准；
- 生存结局的风险差、RMST 差、时间依赖校准；
- 权重极端值、有效样本量、positivity overlap；
- 代码运行成功率、数据映射正确率和随机种子可复现率。

不要只按 ATE 排名。一个模型可能在强先验或错误 estimand 下得到“接近”的数字；必须同时检查协议、假设和执行轨迹。

### 5.3 三种评测模式

1. **设计模式**：只给背景和数据字典，评估研究方案，不允许调用分析结果。
2. **工具模式**：允许本地 Python/R、SQL、统计包和文档检索，评估完整执行能力。
3. **端到端模式**：给定真实数据访问环境，要求提交协议、代码、日志、结果和报告。

每个模式都至少运行 3 次，固定模型版本、提示词、工具权限和随机种子。评测者先盲评，再揭示模型身份。

## 6. 从 idea 到执行的工作流

### 阶段 0：预注册项目边界

写 `PROJECT_CHARTER.md`，锁定：主研究问题、主要 estimand、数据轨道、模型条件、主要指标、排除规则、专家组成、停止/修订条件。把“AI 理解因果”拆成可以被证伪的假设，例如：

- H1：AI 能在 90% 的基础案例中正确对齐 time zero 与治疗启动；
- H2：AI 在已知真值数据上选择 DR/DML/Causal Forest 时，误差不劣于固定基线；
- H3：AI 会在未满足正值性或未测混杂时主动降低结论强度；
- H4：AI 的 CATE 结果在亚组外推和策略价值上不稳定，且这种不稳定可被校准或敏感性分析发现。

### 阶段 1：建立资料与数据注册表

`data_registry.csv` 字段建议包括：数据集、版本、下载 URL、许可、是否需培训/协议、患者/事件规模、数据模态、真值状态、主要偏倚、对应文章、校验哈希、最近核验日期。

所有下载文件写入 manifest；不把原始受限数据提交到 Git。对 MIMIC-IV 等数据使用本地或受控云环境，禁止把可识别或受限数据发送给外部模型 API。

### 阶段 2：制作参考答案，而不是单一“标准答案”

由流行病学家、临床医生、统计学家和数据工程师分别审核：

- 目标试验协议；
- DAG/状态机；
- 允许的 estimand 变体；
- 可接受的数据映射；
- 必须发现的陷阱；
- 结果范围和拒绝回答条件。

对真实 RWD，参考答案应写成“可辩护的分析集合”，而不是声称一个因果真值。记录哪些差异属于合理方法选择，哪些是识别错误。

### 阶段 3：先用小数据跑通软件闭环

先用 Eunomia、MIMIC-III Demo、少量 Synthea 数据跑通：数据下载/解压、版本核验、SQL、队列构建、状态机导出、分析、结果表和日志。再扩展到 SyntheticMass、ACIC、RealCause 和受控访问数据。

建议每个 case 有一个命令完成：

```bash
make prepare CASE=HTN-001
make run CASE=HTN-001 MODEL=baseline
make score CASE=HTN-001 RUN=...
make report CASE=HTN-001 RUN=...
```

### 阶段 4：建立固定基线

至少包含：

- 描述性基线：粗效应、分层、标准化；
- 传统因果基线：PS matching、IPTW、outcome regression、AIPW/DR；
- 机器学习基线：DML、causal forest/GRF、meta-learners；
- 纵向基线：g-computation、MSM、IPCW、动态策略；
- 负对照和敏感性基线：负对照结局/暴露、未测混杂偏倚分析。

基线必须先于 AI 跑通，并锁定版本、公式、超参数、交叉验证和随机种子。否则无法判断 AI 是“理解了因果”还是“调用了一个表现好的库”。

### 阶段 5：运行 AI 实验

对每个 case 保存：原始 prompt、系统指令、模型版本、工具调用、SQL/R/Python、错误修复、每次中间输出、最终协议、结果和 token/运行时间。将“主动拒绝不可识别问题”视为一种正确行为，而不是失败。

### 阶段 6：专家复核与错误分类

至少两名盲法评审者按 rubric 独立评分，报告 Cohen's kappa 或 Krippendorff's alpha。第三名评审者解决分歧。错误分类建议：

1. **语义错误**：问题/治疗/结局理解错；
2. **时间错误**：time zero、窗口、随访或 immortal time 错；
3. **图错误**：混杂、中介、碰撞点或选择机制错；
4. **估计错误**：estimand 与估计器不匹配；
5. **数据错误**：字段、编码、缺失、单位或数据版本错；
6. **数值/代码错误**：程序、权重、方差或单位错；
7. **沟通错误**：把关联写成因果、隐藏限制或夸大外推。

### 阶段 7：报告与开放材料

论文和仓库至少公开：任务包索引、背景资料来源、可公开数据下载脚本、数据字典、参考协议、评分器、基线代码、环境文件、模型调用元数据、错误分类、伦理说明和限制。受限数据只公开获取说明、查询代码和合成测试数据。

报告时对照 TARGET、STROBE 和 RECORD；监管语境下参考 FDA RWE Framework，说明数据相关性、可靠性、适用性和研究设计边界。

## 7. 近代数学理论的探索轨道

数学扩展值得做，但必须转成可评分的命题，不能只增加术语。

### 7.1 集合论/测度论：支持、可识别性和缺失

- 把人群、治疗策略和结局写成可测空间中的随机变量；
- 用支持集表示正值性：某个基线区域中是否同时观察到各治疗？
- 明确观测 sigma-algebra 与潜在结果之间的关系；
- 将 MAR/MNAR、删失和截断写成观测机制，测试 AI 是否知道哪些量不可由数据识别。

可评分例子：给出两个治疗在某亚组完全没有重叠，要求 AI 报告“该亚组 CATE 不可由当前数据识别”，而不是输出一个精确数字。

### 7.2 群论/不变性：重标记、站点迁移和公平性

把性别、医院、编码系统或时间段的重标记视为群作用，要求方法在应保持不变的变换下保持 estimand/决策不变；对真实分布变化则要求明确 transportability 假设。测试包括：

- 表名/代码同构变换后，队列逻辑是否改变；
- 医院域标签变化后，模型是否错误地把站点当治疗机制；
- 亚组重编码后，CATE 是否出现不合理的非不变性；
- fairness 与效应异质性是否被混为一谈。

### 7.3 后续可选方向

在主 benchmark 稳定后再加入：结构因果表示学习、信息论的互信息/泄漏检测、最优传输的跨站点迁移、动态规划和强化学习中的动态治疗策略、类别论/图范畴的机制组合。每个方向都要提供形式化定义、可运行数据生成器和反例；否则放入“理论讨论”而不是排行榜。

## 8. 数据治理、伦理和安全

- 受限 EHR/claims 只在批准的本地或受控云环境运行；不上传原始记录、自由文本或可重识别组合。
- 记录 IRB/伦理豁免、数据使用协议、培训、许可和下载版本。
- 合成数据也要声明它不是临床验证；Synthea/DE-SynPUF 的结果不能被写成真实患者疗效。
- 对模型输出做隐私泄漏、成员推断、敏感属性推断和不当医疗建议检查。
- 任何真实世界结论都由临床和流行病学专家复核；AI 不能作为独立的临床或监管决策者。

## 9. 建议的仓库结构与里程碑

```text
AI4MetaCausal-RWE/
  README.md
  PROJECT_CHARTER.md
  data_registry.csv
  cases/
  generators/              # SCM、状态机、潜在结局、反例
  pipelines/               # 下载、ETL、队列、分析
  baselines/               # 传统、DR、DML、CATE、纵向
  evaluator/               # schema、指标、rubric、专家标注
  reports/
  environments/            # conda/renv/Docker 锁定文件
  tests/
```

里程碑：

| 时间         | 交付物                                                     |
| ------------ | ---------------------------------------------------------- |
| 第 1–2 周    | 项目章程、数据注册表、任务 schema、伦理/访问清单           |
| 第 3–6 周    | Synthea/Eunomia/ACIC 三个可公开运行 case；固定基线和评分器 |
| 第 7–10 周   | MIMIC-III Demo、CMS DE-SynPUF case；状态机和 CATE 轨道     |
| 第 11–16 周  | 专家盲评、错误 taxonomy、模型条件对照、预注册分析          |
| 第 17 周以后 | MIMIC-IV 受控访问 case、跨站点/数学扩展、论文和数据卡      |

## 10. 预期论文/成果包

建议拆成三类成果，而不是把所有内容塞进一篇文章：

1. **Benchmark 论文**：任务定义、数据轨道、评分协议、基线和 AI 结果；
2. **方法论文**：因果状态机/纵向表示，以及对 time-varying confounding、动态策略或 CATE 的改进；
3. **Meta-science 论文**：分析 AI 错误如何暴露因果概念、数据生成机制、可识别性和研究报告规范的边界。

论文结论应按证据层级写：合成真值上的数值能力、半合成数据上的现实混杂鲁棒性、真实 RWD 上的流程和审计能力，三者不能互相替代。

## 11. 资料与访问链接（已检索，核验日期：2026-08-29）

### 因果理论与估计

- [Hernán & Robins, Causal Inference: What If?（作者/Harvard 资料页）](https://hsph.harvard.edu/profile/miguel-hernan/)
- [Using Big Data to Emulate a Target Trial When a Randomized Trial Is Not Available（PMC，直接打开受验证码限制）](https://pmc.ncbi.nlm.nih.gov/articles/4832051/)
- [Athey, Tibshirani & Wager, Generalized Random Forests](https://arxiv.org/abs/1610.01271)
- [Chernozhukov et al., Double/Debiased Machine Learning](https://academic.oup.com/ectj/article/21/1/C1/5056401)
- [Pearl, Structural Causal Models（UCLA PDF）](https://ftp.cs.ucla.edu/pub/stat_ser/r351.pdf)

### 数据与 benchmark

- [Synthea 下载页](https://synthea.mitre.org/downloads)；[Synthea 方法学论文](https://pmc.ncbi.nlm.nih.gov/articles/PMC7651916/)
- [OHDSI Eunomia 下载文档](https://ohdsi.github.io/Eunomia/reference/downloadEunomiaData.html)
- [CMS DE-SynPUF 官方页面](https://www.cms.gov/data-research/statistics-trends-and-reports/medicare-claims-synthetic-public-use-files/cms-2008-2010-data-entrepreneurs-synthetic-public-use-file-de-synpuf)
- [MIMIC-IV v2.2（PhysioNet）](https://physionet.org/content/mimiciv/2.2/)
- [MIMIC 数据访问说明](https://mimic.mit.edu/docs/faq/how-to-get-access.html)
- [MIMIC-III Demo 文档](https://mimic.mit.edu/docs/iii/demo.html)
- [ACIC 2016 数据目录（causallib）](https://github.com/BiomedSciAI/causallib/blob/master/causallib/datasets/data/acic_challenge_2016/README.md)
- [RealCause 代码仓库](https://github.com/bradyneal/realcause)；[RealCause 论文](https://arxiv.org/abs/2011.15007)
- [Microsoft CSuite](https://github.com/microsoft/csuite)
- [高保真多治疗合成临床数据论文](https://www.frontiersin.org/journals/artificial-intelligence/articles/10.3389/frai.2022.918813/full)

### 标准、报告和监管

- [TARGET Guideline 官方网站](https://target-guideline.org/)
- [STROBE 官方网站](https://www.strobe-statement.org/)
- [FDA Framework for FDA’s Real-World Evidence Program（PDF）](https://www.fda.gov/media/120060/download)
- [OHDSI Data Standardization / OMOP CDM](https://www.ohdsi.org/data-standardization/)

## 12. 限制与待核验事项

- MIMIC-IV、部分论文补充数据和某些 claims 资源的访问条款可能变化；每次发布前应重新核验版本、许可和下载 URL。
- 真实 RWD 没有可观测的“真实治疗效应”；与已发表研究一致不等于被证实。C 轨道的评分必须聚焦设计、数据适用性、敏感性和复现。
- Synthea、DE-SynPUF、ACIC、RealCause 的真值依赖生成机制或假设；排行榜只对相应 DGP 有效。
- “因果状态机”和集合论/群论扩展是本项目的研究定义，必须通过形式化规范、反例和消融实验验证，不能直接宣称为临床有效方法。
- 目标试验报告规范、FDA/OHDSI 页面和软件接口会更新；应在每次 benchmark release 中保存网页快照或 DOI/版本号。
