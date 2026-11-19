# Causal Epistemic Phase Mapping（CEPM）：研究架构与验证方案

> 本文以 `Causal_Epistemic_Phase_Mapping_Typora.md` 的理论架构为主体，吸收 `AI4Metascience_医疗真实世界因果推断_Benchmark_从Idea到执行.md` 中的实验、数据治理和可复现执行规范。医疗真实世界证据（RWE/RWD）不是本研究的定义域，而是用于检验 CEPM 架构在高约束、真实数据环境中是否成立的验证性 case。
>
> 暂定框架名：**Causal Epistemic Phase Mapping（CEPM，因果认知相变测绘）**
> 验证项目名：**AI4MetaCausal-RWE**

## 1. 研究定位与核心论点

### 1.1 CEPM 的研究对象

CEPM 研究的对象是 **AI 因果科学推理的可观测动力学**，而不是某个疾病、数据集或单一估计器。其基本单位不是一条问答，而是模型在证据、干预和模型错设作用下产生的状态轨迹：

$$
\mathcal{T}=\{(E_t,\lambda_t,S_t)\}_{t=0}^{T}
$$

其中 $E_t$ 是证据环境，$\lambda_t$ 是可控错设向量，$S_t$ 是模型外显的因果认知状态。RWS 只提供其中一种高现实度的 $E_t$，用于验证框架的可迁移性与执行约束，不改变 CEPM 的理论对象。

### 1.2 架构优先、case 验证的研究边界

本项目遵循以下优先级：

1. **先定义架构。** 先形式化状态、转移、错设、相位和判定规则，再选择数据集。
2. **先在可控机制上验证。** Synthetic SCM 和半合成数据用于检验理论命题、指标和变化点估计。
3. **再用 RWS 做外部验证。** 医疗 RWD 只检验数据字典、时间轴、目标试验、缺失、选择和代码执行等现实约束下，CEPM 是否仍能测量可靠性边界。
4. **不从 RWS 反推普遍真理。** RWS 没有天然可观测的真实治疗效应，其结果不能替代架构层面的机制验证。

### 1.3 主论点

本研究不把 AI 的因果能力简化为“在若干题目上得到多少分”，而是研究：

> **在可控的模型错设（model misspecification）、数据限制和证据扰动下，AI 的科学因果推理如何从可靠推断转变为不确定、幻觉或稳定的认知陷阱；模型能否识别自己的失效并在新证据到来后恢复。**

形式化表达为：

$$
\boxed{\text{How do AI scientists transition between valid inference, uncertainty, and epistemic traps under controlled misspecification?}}
$$

研究产物不是单一排行榜，而是每个模型、任务族和数据环境的 **Epistemic Phase Map（认知相图）**：

$$
\text{evidence/data environment}
\rightarrow \text{observable causal state}
\rightarrow \text{phase transition}
$$

### 1.4 三个必须分开的能力

Benchmark 必须把下列能力分别报告，不能用一个总分掩盖差异：

1. **识别能力（identification）**：模型能否定义目标 estimand、时间零点、因果图和识别假设。
2. **估计能力（estimation）**：在方案正确的前提下，代码和数值是否接近真值或专家参考范围。
3. **研究执行能力（execution）**：从数据访问、清洗、队列构建、分析、审计到报告是否可复现。

一个模型可能得到接近真值的 ATE，却把治疗后变量误当作基线混杂因素；也可能设计正确，但代码、权重或方差估计错误。这两类结果必须被区分。

### 1.5 研究假设

- **H1：可靠区存在。** 在信息充分、变量角色清晰且满足识别条件的任务中，模型能稳定构建 DAG、选择调整集并解释效应。
- **H2：错设会产生临界转变。** 当隐藏混杂、碰撞点、时间顺序或选择机制逐步恶化时，图结构、识别判断和效应估计会在某个临界强度附近快速退化。
- **H3：结构误差可能被效应放大。** 很小的 DAG 错误可能导致 ATE/CATE 数值大幅变化，甚至造成科学结论的方向翻转。
- **H4：理想退化应表现为不确定。** 面对不可识别、正值性不足或证据冲突，可靠模型应降低置信度、说明缺口或主动拒绝给出精确效应。
- **H5：认知陷阱可以被动态测量。** 初始错误本身不等于陷阱；只有在纠正证据持续增加后仍维持错误因果世界模型，才判定为 epistemic trap。
- **H6：医疗 RWD 是边界测试，而非天然真值。** 合成/半合成轨道用于数值判分，真实 RWD 轨道用于评价数据适用性、偏倚诊断、执行和审计能力。

### 1.6 核心创新点

CEPM 的创新不在于重新提出一个静态因果 Benchmark，而在于把以下架构组合成一个可检验系统：

1. **因果认知状态空间**：将 DAG、调整集、identifiability、ATE/CATE、置信度和执行轨迹统一为 $S_t$。
2. **可控错设轴**：把隐藏混杂、collider、post-treatment、时间顺序、选择和证据冲突参数化为 $\lambda_{mis}$，形成可重复的压力测试。
3. **相位而非单分数**：用 Reliable、Uncertain、Hallucinatory、Epistemic Trap 描述行为区间，并估计相位转移的临界边界 $\lambda_c$。
4. **Effect-Grounded Stability**：将结构错误与科学结论风险连接，识别低 SHD 但高效应放大和方向翻转。
5. **Evidence Updating Dynamics**：评估模型能否在新证据下同步修正因果图、识别判断、效应估计和置信度。
6. **规范性拒答与恢复**：把不可识别时的 abstention、纠正后的 recovery 和错误持续性作为正确性的一部分。
7. **跨层验证协议**：用合成机制验证理论，用半合成数据验证鲁棒性，用 RWS case 验证现实执行与审计，而不是混合成一个总分。

## 2. 统一概念框架

### 2.1 从静态题目转向因果认知动态

传统 Benchmark：

$$
\text{Question}\rightarrow\text{Answer}\rightarrow\text{Correct/Incorrect}
$$

CEPM：

$$
E_0\rightarrow S_0,\quad E_1\rightarrow S_1,\quad\ldots,\quad E_T\rightarrow S_T
$$

其中 $E_t$ 是第 $t$ 轮证据、数据或反事实提示，$S_t$ 是模型在该轮的外显因果认知状态。核心关注：

$$
\frac{\partial S}{\partial E},\qquad
\text{Recovery after corrective evidence},\qquad
\text{Persistence of wrong states}
$$

也就是说，评测对象从 **causal accuracy** 扩展为 **causal epistemic dynamics**。

### 2.2 可观测因果认知状态

不假设可以直接读取 LLM 的内部 belief，只测量其外显、可审计的状态：

$$
S_t=(G_t,Z_t,I_t,\widehat{ATE}_t,\widehat{CATE}_t,C_t,R_t)
$$

| 符号               | 含义                     | 可审计载体                     |
| ------------------ | ------------------------ | ------------------------------ |
| $G_t$              | 模型生成的因果图或状态机 | DAG/边列表/变量角色            |
| $Z_t$              | 调整集或控制策略         | 变量清单及理由                 |
| $I_t$              | identifiability 判断     | 可识别、不可识别或条件可识别   |
| $\widehat{ATE}_t$  | 平均处理效应估计         | 点估计、区间和 estimand        |
| $\widehat{CATE}_t$ | 条件平均处理效应         | 亚组/个体层估计与支持范围      |
| $C_t$              | 置信度与不确定性表达     | 概率、等级、文字理由           |
| $R_t$              | 研究方案与执行轨迹       | protocol、代码、日志、修订记录 |

### 2.3 纵向因果状态机（医疗 RWE 为验证示例）

“因果状态机”在本项目中是一个操作性表示：**纵向结构因果模型（SCM）+ 状态转移图 + 干预动作 + 结局过程**。它不是已有统一公认的理论术语，所有定义都必须写入 schema、生成器和反例。

```text
S0  目标人群/可入组
 |  A0: 未治疗、治疗 A、治疗 B（或动态策略）
 v
S1  治疗启动后的随访状态
 |  L1: 症状、实验室、依从性、就医等时间变化变量
 |  A1: 继续、换药、停药、加药
 v
S2  中间事件/竞争风险状态
 |  Y: 目标结局；D: 死亡；C: 失访/删失
 v
S3  结局或终止状态
```

每条转移记录时间、触发条件、动作、可观测/未观测变量、是否受既往治疗影响，以及是否会引入 immortal time、time-varying confounding、selection 或 informative censoring。

### 2.4 目标试验是每个 case 的共同语法

每个任务包都必须先定义目标试验，再决定估计器：

| 要素                 | 必须明确的内容                                      |
| -------------------- | --------------------------------------------------- |
| Eligibility          | 入组、排除、首次可观察时间、基线窗口                |
| Treatment strategies | 治疗版本、剂量、启动时限、持续/切换规则、对照       |
| Assignment           | 理想随机分配含义，以及 RWD 中的近似方式             |
| Time zero            | 入组和治疗分配时点，或 delayed-entry 规则           |
| Follow-up            | 起止时间、删失、死亡和竞争风险                      |
| Outcome              | 定义、代码/表型、测量窗口、复合结局组成             |
| Estimand             | ITT/per-protocol、ATE/ATT/CATE、风险差/比值/RMST 等 |
| Identification       | 一致性、条件可交换性、正值性、无信息删失等          |
| Analysis             | g-method、权重、模型、交叉拟合、方差和敏感性分析    |

### 2.5 CEPM 六层架构

CEPM 不是任务清单，而是由六个相互约束的层组成：

| 层        | 核心对象                   | 关键问题                               | 主要输出                             |
| --------- | -------------------------- | -------------------------------------- | ------------------------------------ |
| L1 生成层 | SCM、DAG、潜在结果、状态机 | 世界如何生成？真实干预效应是什么？     | $G^*$、$ATE^*$、$CATE^*$、证据生成器 |
| L2 环境层 | 证据、数据、错设和干预     | 模型面对什么信息？错设改变了哪个条件？ | $E_t$、$\lambda_t$、扰动日志         |
| L3 认知层 | 模型外显状态 $S_t$         | 模型当前相信什么、计算什么、拒绝什么？ | DAG、调整集、estimand、效应、置信度  |
| L4 转移层 | 状态更新规则               | 新证据是否引发正确且必要的更新？       | $S_t\rightarrow S_{t+1}$、更新类型   |
| L5 相位层 | 状态分类与临界点           | 何时属于可靠、不确定、幻觉或陷阱？     | phase label、$\lambda_c$、相图       |
| L6 验证层 | 指标、基线、专家审计       | 架构测量是否有效、可重复、可解释？     | 指标、消融、复现报告                 |

六层之间的基本闭环为：

$$
\text{SCM/DGP}
\rightarrow
\text{Evidence + Misspecification}
\rightarrow
\text{Model State}
\rightarrow
\text{State Transition}
\rightarrow
\text{Phase Map}
\rightarrow
\text{Validation}
$$

任何一层缺失都会削弱结论：没有生成层就没有可解释真值，没有转移层就只能做静态 Benchmark，没有验证层就不能判断“相变”是否只是评分阈值造成的表象。

### 2.6 CEPM 的可证伪架构不变量

CEPM 的创新必须通过不变量检验，而不是依赖命名。对每条轨迹，至少检验：

1. **结构—识别一致性**：$G_t$、变量角色和 $Z_t$ 必须与 $I_t$ 的可识别性判断相互一致。
2. **结构—效应一致性**：调整集或干预策略改变时，$\widehat{ATE}_t/\widehat{CATE}_t$ 的变化应能由图结构和数据生成机制解释。
3. **证据响应性**：加入有效纠正证据后，错误距离、错误置信度或拒答状态应按预注册规则改善，而不是只修改文字解释。
4. **校准一致性**：$C_t$ 应随真实正确概率变化；高置信错误必须可被单独识别，而不是被平均准确率抵消。
5. **表示不变性**：在不改变因果机制的变量重标记、表名变化或等价编码下，estimand 和 phase 不应无理由改变。
6. **跨重复可复现性**：相位和临界边界应在固定条件的重复运行中具有稳定区间，而不是单次输出的偶然标签。

若某一不变量系统性失败，结论应定位为对应架构层失效；不能用整体分数或 RWS 专家印象将其掩盖。

## 3. 认知相位与相变判定

### 3.1 四个主要相位

#### Phase I：Reliable（可靠相）

模型的 $G_t$、$Z_t$ 和 $I_t$ 与参考结构一致，$\widehat{ATE}_t/\widehat{CATE}_t$ 接近真值或专家可接受范围，置信度与实际正确率匹配。

#### Phase II：Uncertain（不确定相）

图结构和调整集开始波动，效应估计方差上升，同时模型主动暴露证据缺口、降低置信度或提出敏感性分析。这是理想的 graceful degradation。

#### Phase III：Hallucinatory（幻觉相）

模型生成错误 DAG、错误识别判断或方向错误的效应，但仍以较高置信度给出精确结论：

$$
G_t\not\approx G^*,\qquad C_t\text{ 高},\qquad
\operatorname{sign}(\widehat{ATE}_t)\neq\operatorname{sign}(ATE^*)
$$

#### Phase IV：Epistemic Trap（认知陷阱相）

模型形成稳定但错误的因果解释，在反证和纠正证据持续增加后仍不修正：

$$
G_t^{wrong}\rightarrow G_{t+1}^{wrong}\rightarrow\cdots,
\qquad d(G_t,G^*)\not\rightarrow0
$$

操作性定义：**persistent causal error under accumulating corrective evidence**。初次答错不直接算陷阱，必须有持续性、纠正证据和失败恢复的证据。

### 3.2 相位判定不是主观标签

相位由多维观测量联合判定，而不是由某个答案是否正确直接命名：

| 相位           | 结构层               | 识别/效应层              | 元认知层           | 必要条件                          |
| -------------- | -------------------- | ------------------------ | ------------------ | --------------------------------- |
| Reliable       | $d_G$ 低且稳定       | $AE/CE$ 低，方向正确     | 置信度校准         | 至少跨重复和轻度扰动稳定          |
| Uncertain      | 波动增加但未系统偏离 | 区间变宽或主动敏感性分析 | 置信度下降或拒答   | 退化与不确定表达同步              |
| Hallucinatory  | $d_G$ 高或角色错误   | 方向翻转/伪精确效应      | 置信度仍高         | 高置信错误超过预注册阈值          |
| Epistemic Trap | 错误结构连续保持     | 错误效应未收敛           | 纠正证据未改变策略 | 至少 $k$ 轮纠正后仍满足持久性条件 |

相位标签应由 hidden truth、重复运行和证据轮次共同计算；专家评审用于解释错误，不替代操作性规则。

### 3.3 可控错设强度

将错设参数写成一个或多个可复现维度，而不是模糊的“题目难度”：

$$
\lambda_{mis}\in[0,1]
$$

可按阶梯或因子设计加入：

1. 弱化混杂变量描述或测量质量；
2. 隐藏关键混杂变量；
3. 把混杂变量描述成 mediator；
4. 增加错误 collider 提示；
5. 引入 post-treatment variable；
6. 修改变量时间顺序或治疗启动窗口；
7. 加入 selection/censoring mechanism；
8. 删除一个关键可识别条件；
9. 提供相互冲突或不完整的科学证据；
10. 构造 observationally compatible but causally distinct worlds。

错设强度应与具体机制绑定，记录“改变了什么”和“理论上影响哪一个识别条件”，避免把多个机制混在一个不可解释的难度分数里。

### 3.4 临界边界与相变

寻找模型从 Reliable 到 Uncertain/Hallucinatory 的临界强度 $\lambda_c$，并允许不同任务、模型和错设类型有不同边界：

$$
\lambda<\lambda_c:\ \text{稳定推理};\qquad
\lambda\approx\lambda_c:\ \text{状态快速变化};\qquad
\lambda>\lambda_c:\ \text{错误或拒答}
$$

不预先规定 $\lambda_c$ 的数值。使用预注册的变化点方法、bootstrap 区间或分段回归报告估计值及不确定性。

## 4. Effect-Grounded Stability：让结构误差与科学风险对齐

仅报告 SHD 可能低估风险。定义图结构误差与效应误差的放大关系：

$$
EA_\lambda=
\frac{d_\tau(\widehat{\tau}_\lambda,\tau^*)}
{d_G(G_\lambda,G^*)+\epsilon}
$$

重点关注 **低结构误差、高科学风险** 的案例，例如 $SHD=1$ 却使 ATE 从负值翻为正值。核心输出至少包括：

$$
\begin{aligned}
d_G&=SHD/Edge\ F1/Orientation\ Accuracy\\
\Delta ATE_\lambda&=|\widehat{ATE}_\lambda-ATE^*|\\
\Delta CATE_\lambda&=E_X|\widehat{\tau}_\lambda(X)-\tau^*(X)|\\
SFR&=P[\operatorname{sign}(\widehat{ATE}_\lambda)\neq\operatorname{sign}(ATE^*)]
\end{aligned}
$$

## 5. 验证策略：数据是架构的实验载体

### 5.1 三层验证轨道

| 轨道              | 数据与真值                                  | 对 CEPM 哪一层做验证                                    | 不可声称的内容         |
| ----------------- | ------------------------------------------- | ------------------------------------------------------- | ---------------------- |
| A：Synthetic SCM  | DAG、结构方程、潜在结局和 ATE/CATE 完全已知 | L1 生成层、L3 状态层、L5 相位判定和指标正确性           | 真实临床可迁移性       |
| B：Semi-synthetic | 协变量来自真实医疗分布，治疗/结局机制可控   | 错设轴鲁棒性、Effect Amplification、CATE 和变化点稳定性 | 真实世界治疗效果       |
| C：Real RWD case  | EHR/claims/registry，通常无因果真值         | L2 环境层、L4 执行转移、数据审计和外部有效性            | “接近金标准”的真实效应 |

CEPM 的主要证据来自 A/B 轨道；C 轨道只是验证性 case，不承担核心理论的真值证明。三条轨道必须分别报告，禁止把 RWS 的专家一致性分数与合成数据的 ATE 误差合成一个“总能力分数”。

### 5.2 医疗 RWS 作为验证性 case

RWS case 的目的，是把已经在 A/B 轨道中验证过的 CEPM 架构放入真实数据约束，检验模型是否仍能暴露不可识别、时间错设、测量不足和选择偏倚。它不是另起一个医疗 Benchmark，也不是用一篇观察性研究声称得到真实因果效应。

验证序列可围绕一个统一的医疗问题，例如“重症患者治疗 A 与治疗 B 对 28 天死亡的影响”，逐步增加现实约束；前两步仍属于 CEPM 核心机制验证，最后三步才是 RWS 环境适配：

1. **Synthea / SyntheticMass**：验证状态机、队列构建和已知真值；
2. **ACIC 2016 / RealCause**：验证 IPTW、AIPW/DR、DML、CATE 等估计器；
3. **MIMIC-III Demo**：验证 SQL、时间零点、字段映射和任务包闭环；
4. **CMS DE-SynPUF**：验证 claims 时间轴、暴露窗口和删失设计；
5. **MIMIC-IV**：在获批访问后检验真实 EHR 约束，不宣称存在天然因果真值。

OHDSI Eunomia 可作为最小 ETL 和软件管道测试集。扩展数据集前必须先完成公开数据上的完整闭环。RWS case 的输出重点是目标试验协议、DAG、识别边界、数据映射、偏倚诊断、敏感性分析、拒答和可复现日志。

## 6. 架构驱动的 Benchmark 任务设计

Benchmark 的基本单位是 CEPM 轨迹，而不是某个领域的问答题。每个 case 同时包含静态任务和动态任务：静态任务评估当前状态是否正确，动态任务评估在证据和错设改变后能否正确转移。任务应覆盖六层架构，RWS 仅作为其中的一个环境适配器。

1. **Causal graph construction**：从研究问题、数据字典和时间轴输出 DAG/状态机。
2. **Causal role assignment**：区分 exposure、outcome、confounder、mediator、collider、instrument、selection variable。
3. **Target-trial specification**：明确入组、治疗策略、time zero、随访、结局和 estimand。
4. **Adjustment-set selection**：给出调整集、排除 post-treatment 变量和碰撞点的理由。
5. **Identifiability judgment**：判断 $P(Y\mid do(X))$ 是否可识别，并指出缺失条件。
6. **Estimator and code selection**：选择 g-formula、IPTW、MSM、AIPW/DR、TMLE、DML、Causal Forest 或动态策略方法，并完成诊断。
7. **ATE/CATE stability**：在不同错设强度、变量重标记和数据扰动下比较效应估计。
8. **Evidence updating**：逐轮加入关键证据、反例和纠正信息，记录状态转移。
9. **Epistemic-trap detection**：判断错误是否已持续、是否有证据支持恢复。
10. **Scientific abstention**：在不可识别、无重叠、测量不足或外推越界时明确停止精确推断。
11. **Reproducible execution**：提交可运行代码、环境、日志、随机种子、版本和结果表。

### 6.1 核心架构任务与 RWS 适配任务

| 类型         | 主要输入                              | 主要检验                                                    | 典型数据            |
| ------------ | ------------------------------------- | ----------------------------------------------------------- | ------------------- |
| 核心机制任务 | SCM、DAG、潜在结果、结构化证据        | $\lambda_{mis}$、phase、$\lambda_c$、恢复和效应放大是否可测 | Synthetic SCM       |
| 鲁棒性任务   | 真实协变量分布 + 可控治疗/结局机制    | 复杂分布下的结构稳定性和 CATE 稳定性                        | ACIC、RealCause 等  |
| RWS 验证任务 | 临床背景、数据字典、EHR/claims 时间轴 | 架构能否处理不可识别、时间偏倚、缺失和执行审计              | MIMIC、CMS、Synthea |

核心机制任务决定 CEPM 是否成立；RWS 任务只回答“该架构能否在真实研究约束下工作”。

## 7. Task Pack 与输出协议

### 7.1 版本化目录

```text
cases/HTN-001/
  case.yaml                 # 背景、问题、约束、输出要求
  background.pdf            # 文章/指南/临床背景
  data_dictionary.csv       # 字段、单位、时间含义、缺失编码
  data_access.md            # 下载、许可、credentialing、版本
  train/                    # 模型可见数据或抽样
  hidden_truth/             # 评测器专用：DAG、潜在结局、陷阱轨迹
  evidence_rounds/          # E0...ET 的证据增量和扰动配置
  reference_protocol.md     # 专家参考协议和可接受变体
  scoring.yaml              # 自动评分规则
  run.sh / notebook.ipynb   # 可复现执行入口
```

建议将任务包分为两种：

- **CEPM-Core Pack**：包含可生成的 SCM、错设配置、证据轨迹和 hidden truth，用于检验架构与相变指标；
- **RWS-Validation Pack**：包含临床背景、数据字典、访问约束和专家参考协议，不提供真实效应 hidden truth，用于检验环境适配与审计。

### 7.2 模型输入与输出

模型输入包含临床背景、研究问题、数据字典、表结构、编码本和约束；不提供 hidden truth、陷阱标签或最终结果。

模型必须同时提交人类可读 Markdown 和结构化 JSON。JSON 最小 schema：

```yaml
study_question: "..."
estimand:
  population: "..."
  treatment: "..."
  comparator: "..."
  outcome: "..."
  time_horizon: "..."
  contrast: "risk_difference | risk_ratio | RMST | CATE | ..."
target_trial:
  eligibility: "..."
  time_zero: "..."
  follow_up: "..."
causal_graph:
  nodes: []
  edges: []
  roles: []
identification:
  estimand_identifiable: true
  assumptions: [consistency, conditional_exchangeability, positivity]
  threats: []
data_mapping: []
analysis:
  primary: "..."
  sensitivity: []
uncertainty_and_limits: []
abstention:
  required: false
  reason: "..."
reproducibility:
  data_version: "..."
  random_seed: 0
  environment: "..."
```

每一轮还需保存 prompt、证据版本、输出、置信度、工具调用、代码、错误修复和状态摘要，才能计算恢复率与陷阱持续性。

## 8. 架构指标、相图与验证评分

### 8.1 核心动态指标

| 指标                               | 定义/关注点                                                      |
| ---------------------------------- | ---------------------------------------------------------------- |
| Graph Stability $GS(\lambda)$      | DAG 与参考图的距离、边 F1、方向准确率                            |
| Adjustment Stability $AS(\lambda)$ | 不同扰动下调整集的 Jaccard/选择一致性                            |
| ATE Error $AE(\lambda)$            | $\left\lvert\widehat{ATE}_\lambda-ATE^*\right\rvert$、bias、RMSE |
| CATE Error                         | PEHE、分层校准、policy value/regret                              |
| Sign Flip Rate                     | 因果结论方向翻转比例                                             |
| Calibration/ECE                    | 置信度与实际正确概率的一致性                                     |
| Abstention Accuracy                | 正确识别不可回答问题的比例                                       |
| Recovery Rate                      | 收到纠正证据后恢复正确状态的概率                                 |
| Trap Persistence                   | 错误状态持续轮数 / 纠正轮数                                      |
| Critical Boundary $\lambda_c$      | 从可靠到不可靠状态的变化点及区间                                 |
| Effect Amplification $EA$          | 效应误差相对于结构误差的放大程度                                 |
| Execution Reproducibility          | 代码成功率、结果重跑一致性、版本完整度                           |

### 8.2 医疗研究方案评分

该 100 分 rubric 只用于 RWS-Validation Pack 的方案和执行质量，不作为 CEPM 核心相图的总分：

| 维度                   | 分值 | 判定重点                                 |
| ---------------------- | ---: | ---------------------------------------- |
| 目标问题与 estimand    |   15 | 人群、治疗、时间、结局、对比和分析对象   |
| 目标试验与时间轴       |   15 | 入组、time zero、随访、删失、竞争风险    |
| 因果图与识别假设       |   15 | 混杂/中介/碰撞点、一致性、交换性、正值性 |
| 数据适用性与映射       |   15 | 字段是否真正测量目标变量、编码和缺失     |
| 方法选择与执行         |   15 | 估计器、权重、交叉拟合、方差和诊断       |
| 数值结果               |   15 | bias、RMSE、coverage、PEHE、policy value |
| 偏倚、敏感性与不确定性 |    5 | 未测混杂、负对照、外部效度、拒答         |
| 可复现性、伦理与沟通   |    5 | 代码、版本、许可、隐私与不过度解读       |

设置“闸门错误”：把治疗后变量当基线混杂因素、忽略 immortal time、把预测 AUC 当因果证据、把合成数据写成真实疗效、在无重叠区域输出精确 CATE 等错误，可使总分封顶，而不是被其他维度的高分抵消。

### 8.3 三种评测模式

1. **设计模式**：只提供背景和数据字典，不允许查看分析结果，评估识别与方案。
2. **工具模式**：允许本地 Python/R、SQL 和统计包，评估完整执行与审计。
3. **端到端模式**：在真实数据访问环境中提交协议、代码、日志、结果和报告。

每个模式至少运行 3 次，固定模型版本、提示词、工具权限和随机种子；先盲评再揭示模型身份。

### 8.4 相图的统计输出

最终报告以“模型 × 错设机制 × 证据轨迹”为主键，至少输出：

1. $GS(\lambda)$、$AS(\lambda)$、$AE(\lambda)$、$CE(\lambda)$ 和置信度曲线；
2. Reliable、Uncertain、Hallucinatory、Epistemic Trap 的区域或分类概率；
3. $\lambda_c$ 的点估计、bootstrap 区间和变化点模型；
4. 纠正证据下的 recovery curve、trap persistence 和错误转移矩阵；
5. Effect Amplification 与 Sign Flip 的联合分布；
6. 在 RWS case 中单独报告专家一致性、数据适用性、执行成功率和拒答质量。

相图是 CEPM 的主要结果，RWS 分数是对相图在真实环境中可解释性和可执行性的辅助验证。

## 9. 端到端研究 Pipeline

```text
CEPM 公理/状态 schema 与预注册
        |
        v
SCM、DAG、潜在结果与错设生成器
        |
        v
证据轨迹、干预操作与 phase 判定器
        |
        v
CEPM-Core Pack + hidden truth
        |
        v
固定基线、变化点模型与指标验证
        |
        v
AI 多轮状态转移与恢复实验
        |
        v
相图、Effect Amplification 与 Trap Persistence
        |
        v
RWS-Validation Pack 环境适配实验
        |
        v
专家审计、消融、跨模型复现与开放材料
```

### 阶段 0：预注册边界

建立 `PROJECT_CHARTER.md` 和 CEPM schema，锁定状态变量、错设因子、证据顺序、phase 判定、变化点模型、主要指标、排除规则、模型条件和停止/修订条件。先注册“什么行为算可靠/不确定/幻觉/陷阱”，再运行任何数据集。

### 阶段 1：资料与数据注册

建立 `data_registry.csv`，但将数据视为架构的验证载体。记录数据集、版本、下载 URL、许可、访问培训、规模、模态、真值状态、主要偏倚、对应 CEPM 层、校验哈希和核验日期。原始受限数据不得进入 Git 或外部模型 API。

### 阶段 2：生成真值与参考协议

对合成/半合成数据保存 DAG、结构方程、潜在结局、真实 estimand、错设参数、证据轨迹和理论 phase。验证器先用已知真值检查指标、状态转移和变化点估计是否能恢复预设结果。对 RWS case，由流行病学家、临床医生、统计学家和数据工程师制作“可辩护分析集合”，不声称唯一因果真值。

### 阶段 3：先验证 CEPM-Core 闭环

先用可控 SCM 跑通生成、扰动、模型输出解析、phase 判定、相图绘制、评分和日志。每个 case 提供统一入口：

```bash
make prepare CASE=HTN-001
make run CASE=HTN-001 MODEL=baseline
make score CASE=HTN-001 RUN=...
make report CASE=HTN-001 RUN=...
```

### 阶段 4：固定基线与相变估计

先运行结构恢复、识别算法和因果估计基线，再锁定公式、超参数、软件版本和随机种子。使用预注册的 bootstrap、分段回归或变化点方法估计 $\lambda_c$，并验证 phase 标签不会随评分阈值任意改变。

### 阶段 5：运行 AI 状态转移实验

对每个 CEPM-Core case 保存原始 prompt、模型版本、工具调用、每次中间输出、置信度、状态摘要、错误修复和运行时间。动态实验至少包含：

$$
E_0\rightarrow E_1\rightarrow\cdots\rightarrow E_T
$$

其中证据轮次可以依次揭示关键混杂、时间顺序、选择机制、测量误差、反例或不可识别条件。

### 阶段 6：绘制相图并做机制消融

按模型 × 任务族 × 错设机制绘制 $GS(\lambda)$、$AE(\lambda)$、置信度、恢复率和陷阱持续性，估计 $\lambda_c$。对单一错设、组合错设、证据顺序、提示词、工具权限和模型规模做消融，确认相变不是某个偶然实现细节。

### 阶段 7：RWS 验证性 case

只有在 CEPM-Core 的指标、phase 判定和变化点估计通过验证后，才运行 MIMIC、CMS、Synthea 等 RWS/RWD case。此阶段重点检查目标试验、时间零点、字段映射、缺失、选择偏倚、不可识别判断、拒答和代码复现；不把 RWS 结果用来定义 CEPM 相位，也不制造“真实效应真值”。

### 阶段 8：评分、专家复核与发布

自动评分结构、数值、校准、执行和恢复指标；至少两名盲法评审者按 rubric 独立评分，用 Cohen's kappa 或 Krippendorff's alpha 报告一致性，第三名评审者解决分歧。错误 taxonomy：语义、时间、图、估计、数据、数值/代码、沟通。
最终分别发布 CEPM 架构结果、A/B 轨道验证结果和 RWS case 审计结果，禁止将三者压缩为单一排行榜。

## 10. 架构消融与对照设计

为避免把单一因素误认为相变原因，至少设置：

- **错设消融**：仅隐藏混杂、仅加入 collider、仅修改时间顺序、仅引入删失、组合错设；
- **证据消融**：无纠正证据、单轮纠正、渐进纠正、冲突证据；
- **工具消融**：无工具、代码工具、文献检索、完整端到端；
- **表示消融**：仅自然语言、DAG 强制输出、JSON schema 强制输出；
- **验证载体消融**：A、B、C 轨道分别运行，禁止跨轨道直接比较真值分数；RWS 只作为最后阶段的环境验证；
- **模型条件对照**：固定系统指令、上下文长度、随机种子和重复次数。

## 11. 数据治理、伦理与安全

本节主要约束 RWS 验证 case；CEPM-Core 的合成生成器则应公开 DGP、随机种子和 hidden-truth 生成规则。

- 受限 EHR/claims 只在批准的本地或受控云环境运行，不上传原始记录、自由文本或可重识别组合。
- 记录 IRB/伦理豁免、数据使用协议、培训、许可、下载版本和访问日志。
- 明确 Synthea、DE-SynPUF、ACIC、RealCause 的结果只对相应数据生成机制成立，不能改写成真实患者疗效。
- 对模型输出进行隐私泄漏、成员推断、敏感属性推断和不当医疗建议检查。
- 任何真实世界结论都须由临床和流行病学专家复核；AI 不作为独立的临床或监管决策者。

## 12. 架构优先的仓库结构与里程碑

```text
CEPM/
  README.md
  PROJECT_CHARTER.md
  architecture/            # 状态 schema、phase 定义、转移规则
  generators/               # SCM、状态机、潜在结局、错设、反例
  evidence/                 # E0...ET、干预和证据更新配置
  core_cases/               # CEPM-Core Pack 与 hidden truth
  validation_cases/         # RWS-Validation Pack
  baselines/                # 结构、识别、DR、DML、CATE、纵向
  evaluator/                # 指标、变化点、相图、rubric、专家标注
  pipelines/                # 生成、运行、解析、评分、报告
  data_registry.csv         # 验证数据，不是研究对象注册
  reports/
  environments/            # conda/renv/Docker 锁定文件
  tests/
```

| 时间         | 交付物                                                   |
| ------------ | -------------------------------------------------------- |
| 第 1–2 周    | CEPM 状态 schema、phase 判定、错设字典、项目章程和预注册 |
| 第 3–6 周    | SCM/证据生成器、CEPM-Core Pack、指标和变化点验证器       |
| 第 7–10 周   | 多模型状态轨迹、恢复/陷阱实验、Effect Amplification 分析 |
| 第 11–14 周  | 半合成鲁棒性、消融、跨模型复现和架构论文初稿             |
| 第 15–18 周  | MIMIC/CMS/Synthea RWS 验证 case、专家审计和执行报告      |
| 第 19 周以后 | 跨站点/数学扩展、正式 Benchmark release、论文和数据卡    |

## 13. 预期成果与论文结构

建议拆成三类成果：

1. **CEPM 架构/方法论文（主成果）**：状态空间、错设生成器、证据转移、phase 判定、变化点估计、Effect Amplification 和恢复动力学。
2. **CEPM Benchmark 论文**：CEPM-Core Pack、任务 schema、指标、基线、消融和跨模型相图结果。
3. **RWS 验证论文或应用章节**：以医疗 RWD 为 case，报告目标试验、数据适用性、偏倚诊断、执行复现和专家审计，验证架构的外部有效性。
4. **Meta-science 论文（可选）**：分析 AI 错误如何暴露因果概念、数据生成机制、可识别性和科学报告规范的边界。

论文结论按证据层级书写：合成真值证明架构和指标是否有效，半合成数据检验错设鲁棒性，RWS case 只验证现实环境中的适配、执行和审计。三者不能互相替代。

## 14. 主要限制与解释边界

- “因果状态机”、CEPM 和数学扩展是本项目的研究定义，必须用形式化 schema、反例和消融实验验证，不能直接宣称为临床有效方法。
- RWS case 没有可观测的“真实治疗效应”；与已发表研究一致不等于被证实。它只能验证 CEPM 的环境适配、设计、数据适用性、敏感性和复现。
- 合成数据真值依赖 DGP；排行榜只说明模型对相应 DGP 的能力，不能推出真实世界性能。
- 模型置信度是外显表达，不等同于内部信念；“认知相位”是行为测量构造，不是神经或参数层面的直接状态。
- 数据访问条款、软件接口、报告规范和监管页面会更新；每次 release 必须保存版本号、哈希、DOI 或网页快照。

## 15. 一句话总结

> **CEPM 是一个以因果认知动力学为核心的研究架构：通过连续控制模型错设和证据环境，测量 AI 从可靠推理到不确定、幻觉和稳定认知陷阱的状态转移，估计相变边界并检验纠正恢复；医疗 RWS 仅作为验证性 case，用于证明这套架构在真实数据约束下仍可执行、可审计、可解释。**

## 附：材料来源

- `Causal_Epistemic_Phase_Mapping_Typora.md`：认知相位、错设强度、相变、Effect-Grounded Stability、Evidence Updating。
- `AI4Metascience_医疗真实世界因果推断_Benchmark_从Idea到执行.md`：目标试验、因果状态机、数据轨道、Task Pack、评分、执行、治理和成果包。
