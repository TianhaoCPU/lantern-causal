# Causal Epistemic Phase Mapping

## 1. 核心研究问题

本研究关注的不是传统意义上的“AI在因果推理任务上能得多少分”，而是：

> **在受控的模型错设（model misspecification）与证据扰动下，AI的科学因果推理会如何从可靠推断逐步转变为不确定、错误甚至陷入稳定错误？**

核心问题可表述为：


$$
\boxed{
\text{How do AI scientists transition between valid inference, uncertainty, and epistemic traps under controlled model misspecification?}
}

$$

研究目标是绘制 AI 因果科学推理的 **Epistemic Phase Map（认知相图）**，识别其可靠推理区、临界区、幻觉区与认知陷阱区。

---

## 2. 基本思想

传统 Benchmark 通常采用：


$$
\text{Task} \rightarrow \text{Model} \rightarrow \text{Score}

$$

例如 Accuracy、F1、DAG SHD、ATE Error 等。

本研究改为：


$$
\text{Controlled Misspecification}
\rightarrow
\text{Observable Causal Reasoning State}
\rightarrow
\text{Phase Transition}

$$

通过连续调节一个或多个错设参数：


$$
\lambda_{\mathrm{mis}}

$$

观察模型的因果推理状态如何变化。

因此，研究对象不再只是“答案是否正确”，而是：


$$
\boxed{
\text{AI的因果认知状态如何随问题环境变化}
}

$$

---

## 3. 可观测的因果认知状态

不假设能够直接读取 LLM 内部真实 belief，而只定义其外显、可测量的科学推理状态：


$$
S_t =
(
G_t,
Z_t,
\widehat{ATE}_t,
\widehat{CATE}_t,
I_t,
C_t
)

$$

其中：

- $G_t$：模型生成的因果图 / DAG
- $Z_t$：模型选择的 adjustment set
- $\widehat{ATE}_t$：模型设计对应的平均处理效应估计
- $\widehat{CATE}_t$：条件平均处理效应
- $I_t$：对 identifiability 的判断
- $C_t$：模型置信度或不确定性表达

随后研究：


$$
S_0 \rightarrow S_1 \rightarrow \cdots \rightarrow S_T

$$

即模型在持续加入证据、扰动和错设条件后的认知动态。

---

## 4. “滑动变阻器”式实验变量

构造连续的模型错设强度：


$$
\lambda_{\mathrm{mis}} \in [0,1]

$$

其中：

### $\lambda_{\mathrm{mis}}=0$

信息充分、因果结构清晰、变量定义正确。

### 随着 $\lambda_{\mathrm{mis}}$ 增加

逐步加入：

1. Confounder 信息弱化
2. 隐藏关键混杂变量
3. 将 Confounder 描述成 Mediator
4. 加入错误 Collider 提示
5. 引入 Post-treatment variable
6. 修改变量时间顺序
7. 加入 Selection / Censoring mechanism
8. 加入互相冲突的科学证据
9. 删除关键可识别条件
10. 构造 observationally compatible but causally distinct worlds

最终可以进入：


$$
P(Y\mid do(X))

$$

在当前信息条件下不可识别的区域。

---

## 5. 核心输出链

对每一个 $\lambda_{\mathrm{mis}}$，记录：


$$
\lambda_{\mathrm{mis}}
\rightarrow
G_{\lambda}
\rightarrow
Z_{\lambda}
\rightarrow
\widehat{ATE}_{\lambda}
/
\widehat{CATE}_{\lambda}
\rightarrow
Confidence_{\lambda}

$$

从而同时观察：

### 5.1 图结构稳定性


$$
d_G(G_{\lambda}, G^*)

$$

可使用：

- Structural Hamming Distance
- Edge F1
- Orientation Accuracy
- Adjustment Set Jaccard Similarity

### 5.2 ATE 稳定性


$$
\Delta ATE_{\lambda}
=
|
\widehat{ATE}_{\lambda}
-
ATE^*
|

$$

### 5.3 CATE 稳定性


$$
\Delta CATE_{\lambda}
=
E_X
\left[
|
\widehat{\tau}_{\lambda}(X)
-
\tau^*(X)
|
\right]

$$

### 5.4 因果结论翻转


$$
SignFlipRate
=
P
\left[
\operatorname{sign}
(
\widehat{ATE}_{\lambda}
)
\neq
\operatorname{sign}
(
ATE^*
)
\right]

$$

### 5.5 Calibration

比较：


$$
Confidence_{\lambda}

$$

与真实正确概率之间的关系。

特别关注：


$$
\boxed{
\text{Confidently Wrong}
}

$$

---

## 6. 因果认知相位

可以将模型状态划分为四个主要 phase。

### Phase I：Reliable Phase

满足：


$$
G_{\lambda}\approx G^*

$$

且：


$$
\widehat{ATE}_{\lambda}
\approx
ATE^*

$$

同时：

- adjustment set 合理
- identifiability 判断正确
- confidence 与真实正确性一致

---

### Phase II：Uncertain Phase

表现为：


$$
G_{\lambda}
\text{ 开始不稳定}

$$

并伴随：

- adjustment set 波动
- ATE/CATE 方差增加
- confidence 下降
- 模型开始主动表达不确定性

这是理想的 graceful degradation。

---

### Phase III：Hallucinatory Phase

表现为：


$$
G_{\lambda}
\neq
G^*

$$

且：


$$
Confidence_{\lambda}
\text{ 仍然较高}

$$

可能进一步出现：


$$
\operatorname{sign}
(
\widehat{ATE}_{\lambda}
)
\neq
\operatorname{sign}
(
ATE^*
)

$$

即科学结论发生反转。

---

### Phase IV：Epistemic Trap

模型已经形成一个稳定但错误的因果解释，并且后续加入反证仍无法有效修正：


$$
G_t^{wrong}
\rightarrow
G_{t+1}^{wrong}
\rightarrow
G_{t+2}^{wrong}

$$

即使：


$$
Evidence_t \uparrow

$$

仍然有：


$$
d(G_t,G^*)
\not\rightarrow 0

$$

以及：


$$
|
\widehat{ATE}_t
-
ATE^*
|
\not\rightarrow 0

$$

可将 Epistemic Trap 定义为：


$$
\boxed{
\text{persistent causal error under accumulating corrective evidence}
}

$$

---

## 7. 关键创新：从静态 Benchmark 转向 Epistemic Dynamics

传统方法：


$$
Question
\rightarrow
Answer
\rightarrow
Correct/Incorrect

$$

本研究：


$$
Evidence_0
\rightarrow
S_0

$$

$$
Evidence_1
\rightarrow
S_1

$$

$$
\cdots

$$

$$
Evidence_T
\rightarrow
S_T

$$

研究：


$$
\frac{\partial S}{\partial Evidence}

$$

即：

> 模型是否能够随着新证据到来持续修正自己的因果世界模型？

因此评测的对象从：


$$
\text{Causal Accuracy}

$$

升级为：


$$
\boxed{
\text{Causal Epistemic Dynamics}
}

$$

---

## 8. Phase Transition / 临界边界

研究重点不是某一个固定 Score，而是寻找临界错设强度：


$$
\lambda_c

$$

使模型从：


$$
Reliable
\rightarrow
Uncertain
\rightarrow
Hallucinatory

$$

发生相变。

例如：


$$
\lambda < 0.40

$$

模型保持稳定。

当：


$$
\lambda \approx 0.45

$$

由于一个关键 Confounder 被错误分类：


$$
Confounder
\rightarrow
Mediator

$$

导致：


$$
Adjustment Set
\rightarrow
改变

$$

进一步导致：


$$
ATE=-0.12
\rightarrow
ATE=+0.08

$$

此时可以定义：


$$
\lambda_c \approx 0.45

$$

作为该模型在该任务族上的因果认知临界点。

---

## 9. Effect-Grounded Stability

本研究不应只评价：


$$
SHD(G,G^*)

$$

因为一个 DAG 中很小的结构错误可能产生巨大的科学结论变化。

可以进一步定义：


$$
\boxed{
Effect Amplification
}

$$

$$
EA_{\lambda}
=
\frac{
d_{\tau}
(
\widehat{\tau}_{\lambda},
\tau^*
)
}{
d_G
(
G_{\lambda},
G^*
)
+
\epsilon
}

$$

用于衡量：

> 一个很小的图结构变化，是否被放大成巨大的 ATE/CATE 变化。

特别关注：


$$
SHD = 1

$$

但：


$$
ATE<0
\rightarrow
ATE>0

$$

这种“低结构误差、高科学结论风险”的情况。

---

## 10. Evidence Updating Test

可以专门设计纠错实验。

初始阶段故意提供不完整或误导性信息：


$$
E_0

$$

模型产生：


$$
G_0^{wrong}

$$

随后逐轮增加纠正证据：


$$
E_1,E_2,\ldots,E_T

$$

理想模型应满足：


$$
d(G_t,G^*)
\rightarrow 0

$$

以及：


$$
|
\widehat{ATE}_t
-
ATE^*
|
\rightarrow 0

$$

如果证据不断增强，但模型仍坚持原错误结论，则判定为 epistemic trap。

---

## 11. 建议数据层级

### Dataset 1：Synthetic SCM

目的：

- 完全知道真实 DAG
- 完全知道 ATE/CATE ground truth
- 可人为控制 confounding、collider、mediator、selection 等机制

用于核心理论验证。

---

### Dataset 2：Semi-synthetic Causal Benchmark

候选：

- IHDP
- Twins
- ACIC

目的：

- 存在更真实的数据分布
- 保留 ATE/CATE ground truth
- 验证方法是否在复杂数据下稳定

---

### Dataset 3：Real-world Scientific Study

例如真实世界医疗数据 / RWS protocol。

目的：

验证：

- 模型是否识别数据不可观测问题
- 是否正确判断 identifiability
- 是否能够发现 immortal time bias
- 是否能够识别 selection / censoring
- 是否能够知道“这个问题当前数据无法回答”

这里评价重点从 ground-truth effect 转向：

- expert consensus
- design validity
- causal assumptions
- protocol repair ability

---

## 12. Benchmark 任务

可以设计以下任务：

### Task 1：Causal Graph Construction

输入研究问题与数据描述，输出 DAG。

### Task 2：Causal Role Assignment

识别：

- Exposure
- Outcome
- Confounder
- Mediator
- Collider
- Instrument
- Selection variable

### Task 3：Adjustment Set Selection

判断应该调整哪些变量。

### Task 4：Identifiability Judgment

回答：


$$
P(Y\mid do(X))

$$

是否可识别。

### Task 5：ATE/CATE Estimation Stability

比较不同 perturbation 下的效应估计稳定性。

### Task 6：Evidence Updating

逐轮加入新证据，观察模型是否纠正。

### Task 7：Epistemic Trap Detection

判断模型是否陷入稳定错误。

### Task 8：Scientific Abstention

当问题不可识别时，模型是否能够明确停止推断。

---

## 13. 建议主要指标

### Graph Stability


$$
GS(\lambda)

$$

### Adjustment Stability


$$
AS(\lambda)

$$

### ATE Error


$$
AE(\lambda)
=
|
\widehat{ATE}_{\lambda}-ATE^*
|

$$

### CATE Error


$$
CE(\lambda)

$$

### Sign Flip Rate


$$
SFR

$$

### Calibration Error


$$
ECE

$$

### Abstention Accuracy

正确识别不可回答问题的比例。

### Recovery Rate

模型在收到纠正证据后恢复正确因果结构的概率。

### Trap Persistence


$$
TP
=
\frac{
\text{错误状态持续轮数}
}{
\text{总纠正轮数}
}

$$

### Critical Boundary


$$
\lambda_c

$$

用于表征模型从可靠推理向不可靠推理转变的临界点。

---

## 14. 与已有工作的区别

### ToolLoad-Bench 类工作

主要研究：


$$
\text{任务复杂度}
\rightarrow
\text{Agent执行能力崩溃}

$$

即：

> How complex can an agent execute?

---

### Epistemic Traps

主要研究：


$$
\text{Model misspecification}
+
\text{reward structure}
\rightarrow
\text{stable behavioral misalignment}

$$

即：

> Why can a rational agent become trapped in a stable wrong behavior?

---

### 本研究

重点研究：


$$
\text{Controlled causal misspecification}
\rightarrow
\text{DAG}
\rightarrow
\text{Identification}
\rightarrow
ATE/CATE
\rightarrow
\text{Evidence updating}

$$

即：


$$
\boxed{
\text{When does AI scientific causal reasoning stop being reliable, and does it know or recover from that failure?}
}

$$

---

## 15. 更高层研究意义

该方向不只是一个新的因果 Benchmark。

它研究的是：


$$
\boxed{
\text{AI Scientific Epistemology}
}

$$

即：

> AI 如何形成、维持、修正和放弃一个科学解释？

核心科学问题包括：

1. AI 是否存在稳定的因果表示？
2. AI 的因果推理是否存在临界相变？
3. 小幅模型错设是否会导致巨大的科学结论漂移？
4. AI 是否能够知道一个因果问题不可识别？
5. AI 是否能够在新证据出现后修正自己的科学模型？
6. AI 是否存在长期稳定的 causal epistemic trap？
7. 不同模型的 epistemic phase boundary 是否具有可重复的结构差异？

---

## 16. 推荐暂定名称

### 方法 / 框架名称

**Causal Epistemic Phase Mapping (CEPM)**

中文：

**因果认知相变测绘框架**

### Benchmark 名称候选

- CausalBoundary
- CausalPhaseBench
- EpistemicCausalBench
- SciBoundary
- CausalStressBench

---

## 17. 一句话总结

> **Causal Epistemic Phase Mapping 不再只测 AI 是否能回答因果问题，而是通过连续控制模型错设与证据环境，测量 AI 从可靠科学推理到不确定、幻觉和稳定认知陷阱的相变边界，并通过 DAG、identifiability、ATE/CATE 与证据更新动态共同刻画其科学推理可靠性。**

