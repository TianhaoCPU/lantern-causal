# CEPM 相关研究检索与创新性分析

**检索日期：** 2026-08-30

**对应方案：** `Causal_Epistemic_Phase_Mapping_研究方案.md`

**检索范围：** LLM 因果推理、因果学习 Benchmark、信念更新与校准、受控推理错误、AI 科研 Agent、科学复现、医疗证据综合、模型能力阶段转变。

## 1. 先给结论

### 1.1 这个方向有没有人研究过？

**有，而且相邻研究很多；但按本次检索到的公开资料，没有发现一个已经成熟发表、并与 CEPM 完全同构的统一框架。**

已有研究已经分别覆盖：

- LLM 的因果关系判断、因果发现、反事实推理和因果图推理；
- 因果学习能力的静态 Benchmark、表格数据上的因果发现和因果识别；
- 模型在新证据到来后的信念修正、多轮贝叶斯轨迹和上下文信念管理；
- 受控推理错误注入、CoT 因果忠实性和错误定位；
- AI Agent 的科学文献检索、代码执行、论文复现和完整科研实验；
- 医疗证据综合、真实世界数据分析和科学工作流的可复现性；
- 神经网络中的 grokking、涌现能力等阶段性性能变化。

因此，不能把“用 Benchmark 评估 AI 因果推理”宣称为全新问题。更准确的创新主张是：

> **CEPM 将已有的静态因果能力评测、动态信念更新、受控错误注入和科学工作流审计，统一为一个面向因果错设的行为动力学框架，并把它落到医疗真实世界证据任务中。**

这仍然是一个需要实证验证的研究假设，不应在项目开始时写成“已证明存在认知相变”或“首次发现 AI 因果认知陷阱”。

### 1.2 与已有工作的关系

可以把相关工作分成四层：

| 层次           | 已有研究回答的问题                          | CEPM 的新增问题                                                               |
| -------------- | ------------------------------------------- | ----------------------------------------------------------------------------- |
| 静态因果能力   | 模型当前答对了吗？能否发现结构或判断因果？  | 在错设强度变化时，模型何时从答对变为答错？                                    |
| 信念更新       | 新证据出现后，模型是否更新或保持信念？      | 因果证据、识别条件和反事实证据如何改变 DAG、estimand 与效应结论？             |
| 过程与科研执行 | 推理过程是否忠实？Agent 能否执行/复现研究？ | 错误因果模型是否会沿代码、记忆、报告和后续证据持续传播？                      |
| 可靠性边界     | 是否校准、会不会幻觉、能否拒答？            | 能否绘制 Reliable–Uncertain–Hallucinatory–Epistemic Trap 相图并估计临界边界？ |

## 2. 检索方法与证据等级

### 2.1 检索渠道

本轮使用网页检索，优先选择：

1. arXiv 论文摘要页或论文页；
2. 会议/出版社官方页面；
3. 官方代码仓库和 Benchmark 项目页。

检索词覆盖 `LLM causal reasoning benchmark`、`causal discovery language model`、`belief revision LLM`、`Bayesian belief trajectories`、`scientific agent benchmark`、`paper reproduction agent`、`clinical evidence synthesis LLM`、`phase transition neural network` 等主题。

### 2.2 证据等级

- **A：原始页面已打开并读取摘要/项目说明。** 可用于本报告的主要判断。
- **B：搜索结果返回了明确的论文/项目摘要，但原始页面未能稳定打开。** 只用于线索和保守描述，不作为唯一证据。
- **C：来自用户已有 Markdown 的资料。** 可作为项目背景，但本报告不把它当成本轮独立复核的文献证据。

批量网页打开曾出现超时和会话故障；失败条目没有被当作“未发表”或“没有研究”，而是记录为待复核。特别是 2026 年提交的 arXiv 条目，可能处于预印本早期状态，不能等同于同行评审结论。

## 3. 最直接的 LLM 因果推理研究

### 3.1 Causal Reasoning and Large Language Models（2023/2024）

[Kıcıman et al., Causal Reasoning and Large Language Models: Opening a New Frontier for Causality](https://arxiv.org/abs/2305.00050)

该工作是 LLM 因果推理研究的早期系统性工作之一，覆盖因果论证生成、成对因果发现、反事实推理和事件因果判断。论文显示 LLM 能利用文本上下文形成形式上合理的因果论证，同时存在不可预测的失败模式；作者还强调，模型主要处理文本元数据，而不是直接从真实数值观测数据执行统计因果识别。

**对 CEPM 的启示：**

- 支持把 LLM 因果推理作为独立实证对象；
- 支持同时评估因果准确性和失败模式；
- 说明“语言上的因果合理性”与“数据驱动的识别有效性”必须分开。

**CEPM 尚未被该工作覆盖的部分：**

- 连续错设强度与临界边界；
- 置信度—正确率校准；
- 纠正证据下的恢复率和陷阱持续性；
- 医疗 RWD 的目标试验、代码执行和审计。

### 3.2 Corr2Cause：从相关性判断因果性

[Jin et al., Can Large Language Models Infer Causation from Correlation?](https://arxiv.org/abs/2306.05836)（ICLR 2024）

Corr2Cause 直接测试模型能否从相关性陈述区分因果关系，数据规模超过 20 万样本，并评估多个语言模型。检索到的论文摘要指出，既有模型在变量名和表述变化后泛化困难，说明模型可能依赖表面语义而非稳定的因果规则。

**与 CEPM 的对应：** 可作为分布外稳健性、变量重标记和因果方向任务的静态基线。CEPM 进一步把表述变化、结构扰动和隐藏机制组织成连续实验轨迹，而不是只比较最终准确率。

### 3.3 CausalBench：因果学习能力综合 Benchmark

[Zhou et al., CausalBench: A Comprehensive Benchmark for Causal Learning Capability of LLMs](https://arxiv.org/abs/2404.06349)

CausalBench 将任务分为相关性判断、因果骨架发现和因果识别，并与传统因果学习算法比较。检索到的原始摘要显示，LLM 在简单关系上有一定能力，但在大图、碰撞点结构和直接利用数值分布方面明显较弱，模型容易依赖实体语义关联。

**与 CEPM 的对应：**

- 可复用其图结构、骨架和碰撞点诊断；
- 支持把结构发现、识别和解释分成不同分项；
- 为固定统计基线与 LLM 对照提供先例。

**关键差异：** CausalBench 是静态能力矩阵，没有把不可识别判断、置信度、证据更新、恢复和持久性错误组织为状态动力学。

### 3.4 CaLM：大规模多维因果评估

[Chen et al., Causal Evaluation of Language Models](https://arxiv.org/abs/2405.00622)

CaLM 被描述为综合性因果评估框架，包含因果目标、适配方法、指标和错误类型四个模块；数据集包含大量样本，覆盖多类因果目标、适配方法和评估指标，并在多个语言模型上进行系统比较。

**与 CEPM 的对应：** CaLM 是 CEPM 最重要的静态 Benchmark 前序之一。CEPM 需要明确说明：自身不是重新发明“因果任务分类和错误 taxonomy”，而是在 CaLM 式横截面评估之上增加时间轴、错设轴、证据轴和相位判定。

### 3.5 CARL-GT：因果图与表格数据

[Tu et al., CARL-GT: Evaluating Causal Reasoning Capabilities of Large Language Models](https://arxiv.org/abs/2412.17970)

CARL-GT 使用因果图和表格数据评估因果图推理、知识发现和决策。摘要指出，模型从表格数据发现新因果关系的能力较弱，不同任务类别的表现差异明显。

**与 CEPM 的对应：** 它证明图、表格和决策可以放入同一 Benchmark；CEPM 可在此基础上加入医疗数据字典、目标试验、估计器执行和多轮证据更新。

### 3.6 EconCausal：上下文变化、误导证据与因果符号翻转

[Lee et al., EconCausal: A Context-Aware Economic Reasoning Benchmark for Large Language Models](https://arxiv.org/abs/2510.07231)

EconCausal 从大量实证经济与金融研究中构建带上下文的因果关系基准，检索到的原始页面显示，它专门测试上下文变化时模型是否修正因果方向，并加入误导性证据。模型在需要根据上下文重新判断因果符号时准确率明显下降。

**这是 CEPM 最接近的因果相邻工作之一。** 它已经触及：

- 上下文依赖的因果效应；
- 因果符号在环境改变下翻转；
- 误导证据鲁棒性；
- 结构化科学证据 Benchmark。

**但仍有明显差异：** 检索到的工作重点是经济领域的上下文因果判断，不是 `DAG → identification → ATE/CATE → evidence recovery` 的纵向链条，也没有将 Reliable、Uncertain、Hallucinatory、Epistemic Trap 定义为统一相位并估计临界边界。

## 4. 信念更新、校准与认知状态研究

### 4.1 Belief-R：模型是否会修正既有信念

[Wilie et al., Belief Revision: The Adaptability of Large Language Models Reasoning](https://arxiv.org/abs/2406.19764)

Belief-R 和 delta reasoning（$\Delta R$）测试模型在新证据到来后是否应当压制先前推断。论文在多个模型上发现，模型通常难以适当地修正既有信念；更容易更新的模型又可能在不需要更新时过度改变，形成“更新敏感性—稳定性”的权衡。

**对 CEPM 的直接意义：**

- 证明“证据更新轨迹”比单轮最终答案更有信息量；
- 提供 Failed Update 和 Failed Stay 的一般性前驱；
- 可作为 CEPM 的非因果信念更新基线。

**CEPM 的增量：** 把“新证据”具体化为混杂、碰撞点、时间顺序、可识别性和效应反例，并要求更新的不只是文本结论，而是 DAG、调整集、estimand、ATE/CATE 和置信度。

### 4.2 BayesBench：多轮证据下的完整信念轨迹

[Samanta et al., BayesBench: Evaluating LLM Belief Trajectories Under Multi-Turn Evidence Accumulation](https://arxiv.org/abs/2606.30850)

该预印本提出多轮证据累积 Benchmark，用完整信念轨迹而不是最终答案与贝叶斯理性更新轨迹比较，覆盖参数估计、贝叶斯预测和带潜变量/角色框架的预测。原始页面摘要指出，模型规模提升了潜状态推断和证据累积，但不一定转化为理性的下游预测。

**与 CEPM 的关系非常近：** CEPM 应将 BayesBench 视为“轨迹级认识论评估”的直接相邻工作，而不是声称自己首次提出轨迹评估。

**关键差异：** BayesBench 主要是贝叶斯信念更新；CEPM 的对象是因果模型错设、识别边界、效应估计、拒答和医疗研究执行。

> **状态说明：** 这是 2026 年预印本，引用时应标注 arXiv 版本和检索日期，不应写成已经完成同行评审的定论。

### 4.3 BeliefTrack：保持、更新与噪声隔离

[Xu et al., When Should Models Change Their Minds? Contextual Belief Management in Large Language Models](https://arxiv.org/abs/2605.30219)

BeliefTrack 将长程交互中的上下文信念管理分解为：

- **Failed Stay**：本应保持信念却错误改变；
- **Failed Update**：有效新证据出现却没有更新；
- **Failed Isolation**：没有隔离任务无关信息或噪声。

原始页面还描述了有限信念空间和符号验证器，并报告信念状态奖励和表征 steering 对失败率的改善。

**对 CEPM 的价值：**

- 为 CEPM 的微观状态转移错误提供成熟术语；
- 支持记录“该轮为什么改变/不改变”；
- 支持把恢复时间、滞后和噪声隔离纳入动态评测。

**关键差异：** BeliefTrack 是闭世界的有限信念任务；CEPM 需要在开放世界的医疗因果环境中处理部分可识别、测量误差、未测混杂和估计器不确定性。

> **状态说明：** 同样属于 2026 年预印本，应在文献综述中标注状态。

### 4.4 MQUAKE 与知识编辑后的多跳一致性

[MQUAKE: Assessing Knowledge Editing in Language Models via Multi-Hop Questions](https://arxiv.org/abs/2305.14795)

MQUAKE 研究知识编辑后，模型是否能将被修改的事实传播到多跳结论。其核心启示是：模型可能记住局部新事实，却没有修正下游推理。

**与 CEPM 的关系：** 这为“局部证据更新成功但全局因果模型未更新”的陷阱定义提供了方法类比。CEPM 可把局部更新扩展成 DAG、调整集和效应结论的一致性检查。

## 5. 受控错误、推理忠实性与幻觉

### 5.1 Unveiling and Causalizing CoT

[Fu et al., Unveiling and Causalizing CoT: A Causal Perspective](https://arxiv.org/abs/2502.18239)

该工作把 Chain-of-Thought 描述为结构因果模型，并提出 CoT Average Causal Effect（CACE）来衡量推理步骤之间的因果贡献，尝试发现和修正无效或不可理解的推理步骤。

**与 CEPM 的互补关系：** CACE 类指标可用于 CEPM 的微观过程层，定位一条推理链从哪一步开始偏离；CEPM 则关注偏离之后是否形成跨轮、跨代码和跨证据的宏观状态转移。

### 5.2 C2-Faith：受控错误注入与过程级评估

[Mittal and Arike, C2-Faith: Benchmarking LLM Judges for Causal and Coverage Faithfulness in Chain-of-Thought Reasoning](https://arxiv.org/abs/2603.05167)

C2-Faith 将推理忠实性拆成因果性和覆盖度，通过单步骤替换、步骤删除等受控干预，评估错误检测、定位和推理完整性判断。检索到的摘要指出，模型通常能发现“有错误”，但难以定位错误步骤，并会高估缺失步骤后的覆盖度。

**与 CEPM 的直接连接：**

- 受控错误注入可成为 CEPM 的实验构造方法；
- “发现错误但不能定位”可以成为独立状态；
- “缺失证据却高置信判断完整”可以成为高置信陷阱指标。

**差异：** C2-Faith 主要评估 judge 对 CoT 的过程忠实性，CEPM 评估任务模型本身是否在因果世界模型层面更新和恢复。

## 6. AI 科研 Agent、科学复现与医疗证据综合

### 6.1 PlanBench 与 ActionReasoningBench

[PlanBench](https://arxiv.org/abs/2206.10498) 将规划和状态变化推理转成可机械验证的行动序列；[ActionReasoningBench](https://arxiv.org/abs/2406.04046) 进一步测试动作可执行性、动作效果、状态追踪、幻觉检测和复合问题。

它们不是因果推断 Benchmark，但为 CEPM 提供两点方法先例：

1. 用显式状态、动作、转移规则和目标状态替代模糊的自由文本评分；
2. 评估完整轨迹和状态变化，而不是只评估最后一句答案。

CEPM 的区别在于，状态是因果认知状态，动作包括干预/证据注入，转移规则受识别条件和数据生成机制约束。

### 6.2 ScienceAgentBench

[ScienceAgentBench: Toward Rigorous Assessment of Language Agents for Data-Driven Scientific Discovery](https://arxiv.org/abs/2410.05080)

该 Benchmark 从真实同行评审论文中抽取数据驱动科学任务，要求 Agent 输出可独立执行的 Python 程序，并同时评估代码、执行结果和成本。它强调先评估科学工作流中的独立环节，再讨论端到端自动化发现。

**对 CEPM 的启示：**

- 支持把研究设计、代码、执行结果和成本分开评分；
- 支持由领域专家验证任务；
- 说明端到端完成率不能替代识别层面的正确性。

### 6.3 CORE-Bench

[CORE-Bench: Fostering the Credibility of Published Research Through a Computational Reproducibility Agent Benchmark](https://arxiv.org/abs/2409.11363)

CORE-Bench 将科研可信度与计算可复现性联系起来，评估 Agent 能否重新执行已发表研究。它为 CEPM 的 `Execution Reproducibility` 指标、环境锁定、日志保存和结果重跑提供直接先例。

### 6.4 PaperBench

[Starace et al., PaperBench: Evaluating AI’s Ability to Replicate AI Research](https://arxiv.org/abs/2504.01848)；[ICML 2025 页面](https://proceedings.mlr.press/v267/starace25a.html)；[OpenAI 项目页](https://openai.com/index/paperbench/)

PaperBench 评估 Agent 从论文理解、代码开发到实验执行和结果复现的能力，使用层级化子任务和与原论文作者共同制定的 rubric。

**与 CEPM 的关系：** PaperBench 证明科学 Agent 评测可以细化到大量可审计子任务；CEPM 应采用同样的过程证据思路，但把关键错误定义为因果识别错误、时间错误、错设传播和过度因果解释。

### 6.5 EXP-Bench

[EXP-Bench: Can AI Conduct AI Research Experiments?](https://arxiv.org/abs/2505.24785)

EXP-Bench 评估 Agent 提出假设、设计实验、实现代码、运行实验和分析结果的完整链条。检索到的项目摘要显示，局部环节得分可以高于端到端成功率，说明“会做某一步”不能推出“能完成可信科研”。

**对 CEPM 的启示：** CEPM 需要报告识别、估计、执行和沟通的分项分数，并设置闸门错误，防止一个偶然接近真值的数字掩盖方案层面的致命错误。

### 6.6 TrialMind / TrialReviewBench

[Accelerating Clinical Evidence Synthesis with Large Language Models](https://arxiv.org/abs/2406.17755)

该工作面向临床证据综合，提出 LLM 辅助的检索、筛选、抽取、综合和专家监督流程，并构建临床研究证据综合 Benchmark。

**对 CEPM 的关系：** 它是医疗证据工作流的相邻前例，但重点是证据综合流程准确性，不是因果模型在错设、不可识别和纠正证据下的动态变化。CEPM 应把它视为医疗证据输入层，而不是直接竞争的因果相图工作。

## 7. “阶段转变”在机器学习中的先例

### 7.1 Grokking

[Power et al., Grokking: Generalization Beyond Overfitting on Small Algorithmic Datasets](https://arxiv.org/abs/2201.02177)

Grokking 研究显示，模型可能先过拟合，再在持续训练后突然获得泛化能力。这是“性能可能发生阶段性跃迁”的重要先例。

**但不能直接类比 CEPM：** grokking 研究的是训练过程中的泛化跃迁，不是因果认知、证据更新、置信度或稳定错误陷阱。CEPM 必须通过错设强度变化和行为轨迹证明相变，而不能仅借用“phase”一词。

### 7.2 Emergent Abilities

[Wei et al., Emergent Abilities of Large Language Models](https://arxiv.org/abs/2206.07682)

该工作讨论规模增加后某些下游能力似乎突然出现。后续研究对涌现是否是指标尺度效应存在争论，因此 CEPM 不应把任何性能曲线的陡升直接解释为内部认知相变。

**CEPM 应采取更保守的操作定义：** “phase”表示基于可观测输出和预注册阈值划分的行为状态，不代表已经读取到模型内部的真实 belief 或神经机制。

## 8. 综合相似度矩阵

| 工作                      | 静态因果 | 因果图/识别 | 多轮更新 |  受控错设 | 校准/拒答 | 科研执行 | 医疗 RWD | 相位/陷阱 |
| ------------------------- | -------: | ----------: | -------: | --------: | --------: | -------: | -------: | --------: |
| Causal Reasoning and LLMs |        ✓ |        部分 |          |           |      部分 |          |          |           |
| Corr2Cause                |        ✓ |        部分 |          |           |           |          |          |           |
| CausalBench               |        ✓ |           ✓ |          |           |           |          |          |           |
| CaLM                      |        ✓ |           ✓ |          |      部分 |      部分 |          |          |           |
| CARL-GT                   |        ✓ |           ✓ |          |           |           |     部分 |          |           |
| EconCausal                |        ✓ |        部分 |     部分 |  误导证据 |      部分 |          |          |           |
| Belief-R                  |          |             |        ✓ |  证据扰动 |           |          |          |           |
| BayesBench                |          |             |       ✓✓ |           |           |          |          |      轨迹 |
| BeliefTrack               |          |             |       ✓✓ | 噪声/冲突 |           |          |          |  状态失败 |
| C2-Faith                  |          |        过程 |          |        ✓✓ |  自评偏差 |          |          |           |
| ScienceAgentBench         |          |             |          |           |           |       ✓✓ |     部分 |           |
| CORE-Bench                |          |             |          |           |           |       ✓✓ |     部分 |           |
| PaperBench                |          |             |          |           |           |       ✓✓ |          |           |
| EXP-Bench                 |          |             |          |           |           |       ✓✓ |          |           |
| TrialReviewBench          |          |             |     部分 |           |      部分 |        ✓ |        ✓ |           |
| **CEPM 目标**             |        ✓ |          ✓✓ |       ✓✓ |        ✓✓ |        ✓✓ |        ✓ |       ✓✓ |        ✓✓ |

矩阵表示的是本报告对研究范围的归纳，不是各论文作者对 CEPM 概念的承诺。空白表示本次检索未找到明确覆盖，不等于该方向绝对没有任何相关工作。

## 9. CEPM 可以主张什么创新

### 9.1 最稳妥的创新表述

建议在论文摘要和项目章程中使用以下表述：

> We propose a causal epistemic dynamics benchmark that evaluates how AI systems revise causal graphs, identification judgments, treatment-effect estimates, uncertainty, and research plans under controlled misspecification and sequential evidence updates. The benchmark maps observable behavior into reliability phases and quantifies transition thresholds, recovery, confident error, and persistent causal traps in healthcare RWE tasks.

中文可写为：

> 本研究提出一个因果认知动力学 Benchmark，在可控模型错设和序列证据更新下，联合评估 AI 的因果图、识别判断、ATE/CATE、置信度和研究执行计划，并在医疗真实世界证据任务中量化可靠性相位、临界边界、纠正恢复、高置信错误和持续性因果陷阱。

### 9.2 不建议的表述

- “首次研究 LLM 因果推理”：已有 Causal Reasoning、Corr2Cause、CausalBench、CaLM、CARL-GT 等工作。
- “首次研究模型信念更新”：已有 Belief-R、BayesBench、BeliefTrack 等工作。
- “首次使用受控错误评估推理”：已有 C2-Faith 等过程级干预工作。
- “证明 AI 存在认知相变”：在没有变化点统计、重复实验和替代解释排除前，只能说“检验是否存在行为相变”。
- “真实 RWD 上得到 AI 因果能力金标准”：真实 RWD 通常没有可观测真因果效应，只能评价设计、适用性、偏倚诊断和可复现性。

### 9.3 需要真正做出差异的最小实验

如果只做静态 DAG 问答，CEPM 与 CausalBench/CaLM/CARL-GT 的区分度不足。至少应完成以下最小闭环：

1. 在 Synthetic SCM 中固定真实 DAG、潜在结局和 ATE/CATE；
2. 单独控制隐藏混杂、collider、post-treatment、时间顺序和删失等错设因素；
3. 以多个 $\lambda_{mis}$ 水平重复运行，并估计 $GS(\lambda)$、$AE(\lambda)$、置信度和拒答；
4. 在同一 case 中逐轮加入纠正证据，记录 DAG、调整集、identifiability 和效应结论是否共同更新；
5. 定义 Recovery Rate、Trap Persistence、Sign Flip Rate 和 $\lambda_c$ 的预注册判定规则；
6. 在真实 RWD case 中取消“真效应排行榜”，改用专家参考协议、数据适用性和可复现性评分；
7. 证明效果不是由提示词格式、上下文长度、代码工具或单一模型造成，并报告消融结果。

## 10. 可能的理论贡献与边界

### 10.1 可能的贡献

- **统一状态表示：** 将 DAG、调整集、identifiability、效应估计、置信度和执行轨迹放入同一可观测状态 $S_t$；
- **错设—响应曲线：** 将隐藏混杂、碰撞点、时间错误和选择机制从离散题目变成可控实验轴；
- **效应落地的结构稳定性：** 通过 Effect Amplification 识别低 SHD 但高科学风险的错误；
- **规范性更新评估：** 用可识别的目标状态和纠正证据定义恢复，而不是把“模型说我错了”当作自我修正；
- **医疗 RWE 审计层：** 把目标试验、时间零点、数据映射、代码和伦理治理纳入因果能力评价。

### 10.2 必须避免的理论过度解释

- 外显置信度不是模型内部 belief；
- 行为相位不是神经机制相位；
- 变化点可能来自评分阈值、提示词、上下文窗口或数据分布，而不是真正的内部机制跃迁；
- 合成真值上的恢复不能直接推出临床安全性；
- 与一篇已发表 RWE 研究结果一致，不代表因果结论被验证。

## 11. 建议新增的相关工作章节结构

论文可按以下顺序写 Related Work：

1. **LLM causal reasoning benchmarks**：Causal Reasoning、Corr2Cause、CausalBench、CaLM、CARL-GT；
2. **Belief revision and epistemic state tracking**：Belief-R、BayesBench、BeliefTrack；
3. **Process faithfulness and controlled reasoning perturbations**：Causalized CoT、C2-Faith；
4. **Scientific-agent and reproducibility benchmarks**：PlanBench、ScienceAgentBench、CORE-Bench、PaperBench、EXP-Bench；
5. **Clinical evidence synthesis and RWE execution**：TrialReviewBench 及目标试验/RWD 相关方法；
6. **Phase transitions and emergent behavior**：Grokking、Emergent Abilities；
7. **Gap statement**：现有工作分别研究静态能力、信念更新、过程忠实性或科研执行，CEPM 研究它们在因果错设和医疗 RWD 环境中的联合动力学。

## 12. 检索到的关键来源清单

以下链接均为本轮实际检索并成功读取页面或明确摘要的来源；预印本状态以检索日期为准。

### 因果推理与 Benchmark

- [Causal Reasoning and Large Language Models](https://arxiv.org/abs/2305.00050)
- [Can Large Language Models Infer Causation from Correlation? / Corr2Cause](https://arxiv.org/abs/2306.05836)
- [CausalBench](https://arxiv.org/abs/2404.06349)
- [Causal Evaluation of Language Models / CaLM](https://arxiv.org/abs/2405.00622)
- [CARL-GT](https://arxiv.org/abs/2412.17970)
- [EconCausal](https://arxiv.org/abs/2510.07231)

### 信念更新与过程忠实性

- [Belief Revision / Belief-R](https://arxiv.org/abs/2406.19764)
- [BayesBench](https://arxiv.org/abs/2606.30850)
- [BeliefTrack / Contextual Belief Management](https://arxiv.org/abs/2605.30219)
- [MQUAKE](https://arxiv.org/abs/2305.14795)
- [Unveiling and Causalizing CoT](https://arxiv.org/abs/2502.18239)
- [C2-Faith](https://arxiv.org/abs/2603.05167)

### 科研 Agent 与复现

- [PlanBench](https://arxiv.org/abs/2206.10498)
- [ActionReasoningBench](https://arxiv.org/abs/2406.04046)
- [ScienceAgentBench](https://arxiv.org/abs/2410.05080)
- [CORE-Bench](https://arxiv.org/abs/2409.11363)
- [PaperBench](https://arxiv.org/abs/2504.01848)
- [PaperBench: ICML 2025 proceedings](https://proceedings.mlr.press/v267/starace25a.html)
- [EXP-Bench](https://arxiv.org/abs/2505.24785)
- [TrialMind / TrialReviewBench](https://arxiv.org/abs/2406.17755)

### 阶段性能力变化

- [Grokking](https://arxiv.org/abs/2201.02177)
- [Emergent Abilities of Large Language Models](https://arxiv.org/abs/2206.07682)

## 13. 仍需补检与复核的方向

本轮检索已经覆盖 CEPM 的直接相邻工作，但要用于正式投稿，还应补充系统综述级别的检索：

- causal discovery under distribution shift、invariant causal prediction、transportability；
- hidden-confounding sensitivity analysis、partial identification、causal uncertainty；
- selective prediction、abstention、LLM calibration 和 hallucination benchmarks；
- clinical LLM causal reasoning、target-trial emulation agents、MIMIC/EHR 因果分析；
- metacognition、self-correction、memory contamination 和 adversarial evidence；
- 2025–2026 年新发表的 causal agent、RWE agent 和 process-level evaluation 工作。

这些方向与 CEPM 高度相关，但本次网页工具在部分批量检索中发生超时，因此不把未成功读取的结果写成已核验结论。正式投稿前应通过 Semantic Scholar/OpenAlex、Google Scholar、DBLP、PubMed 和会议 proceedings 做去重、引用追踪和截止日期冻结。

## 14. 最终判断

**判断：该方向不是“无人研究”，而是“已有多个成熟邻域，尚缺一个经过实证验证的跨层统一框架”。**

最有说服力的论文贡献不是提出一个新名词，而是证明以下事实至少有一部分成立：

1. 因果错设强度可以被独立操控，并可重复诱发结构、识别和效应层面的状态变化；
2. 模型的置信度、拒答和实际正确性之间存在可测的错配；
3. 小结构错误确实可能被放大为高风险效应错误；
4. 纠正证据下存在可区分的恢复、失败更新和持续性陷阱轨迹；
5. 这些轨迹在不同模型、任务族和医疗数据轨道上具有可重复的差异；
6. 真实 RWD 上的结论可以通过目标试验、数据适用性、专家审计和可复现性被约束，而不是依赖伪造的因果真值。

如果上述证据无法得到，CEPM 仍可退回为一个有价值的因果压力测试 Benchmark，但不应继续使用“认知相变”这一强理论表述。
