# 合成流程任务的模型调用与离线评分

`lantern blind-infer` 把固定的 9 条人工流程任务接到 OpenAI Chat Completions 协议，再将响应导出给 `blind-eval`。接口使用 Python 标准库；只有显式运行这个命令且不带 `--dry-run` 时才会请求供应商。其他实验和评分命令继续在本地执行。

当前已核验请求预览、模拟服务调用、异常输出和断点恢复，尚未运行真实供应商或留出模型评测。模型接口的实现不代表模型在这些题目上的表现，也不完成 MIMIC 队列实验。

## 1. 检查将要发送的请求

从项目根目录执行；不需要密钥，也不会发出网络请求：

~~~bash
lantern blind-infer \
  --provider-config configs/providers/openai_compatible.example.json \
  --dry-run \
  --output outputs/llm_preview.json
~~~

预览保存 9 个完整请求体、逐请求 SHA-256、任务包指纹和运行配置指纹。系统消息使用任务包内的固定提示；每条用户消息只含字段定义、目标表达式、任务 ID 和该题的抽取流程。不接收任意任务文件、患者记录、遮蔽表或评分报告作为输入。

任务来自 `blind-tasks` 的同一导出接口。完整人工队列、真实图标签、掩蔽种子、参考风险差和评分结果不进入请求。每题独立调用一次，不共享对话，也不把统计评分反馈给模型。现有 9 条题目仍然是公开的开发样例，不能当作留出题库。

## 2. 配置并运行

复制示例配置，手动把 `model` 改成选定的模型 ID；若供应商提供固定版本，填写固定版本。将 `base_url` 设为供应商的 API 前缀，例如 `https://api.openai.com/v1`，程序会追加 `/chat/completions`。

~~~bash
cp configs/providers/openai_compatible.example.json configs/providers/experiment.local.json
~~~

配置字段如下；不接受未列出的参数，也不接受配置文件中的 API 密钥。

| 字段 | 含义 |
|---|---|
| `schema_version` | 固定为整数 `1`。 |
| `base_url` | 不带凭据、查询或片段的 HTTPS API 前缀；本机回环模拟服务可使用 HTTP。 |
| `model` | 明确指定的模型 ID；示例占位值只用于预览。 |
| `api_key_env` | 保存令牌的环境变量名，默认 `OPENAI_API_KEY`。 |
| `timeout_seconds` | 每次请求的超时参数，默认 60 秒，允许范围 `(0, 300]`。 |
| `max_completion_tokens` | 单次输出 token 上限，默认 2048；推理模型可能需要更大的上限。 |
| `json_mode` | 默认 `true`，发送 `response_format={"type":"json_object"}`；不支持时可设为 `false`，仍要求完整 JSON。 |
| `temperature` | 默认 `null`，省略该请求参数；仅对支持它的模型填写数值。 |

在运行环境设置 `api_key_env` 指定的令牌后执行以下命令。程序不自动加载 `.env` 文件。这个步骤会调用所配置的供应商，至多启动 9 次请求，可能产生费用：

~~~bash
lantern blind-infer \
  --provider-config configs/providers/experiment.local.json \
  --output outputs/llm_run.json \
  --responses outputs/llm_responses.json
~~~

运行报告保存请求、请求指纹、原始响应文本、供应商返回的模型名、请求 ID、完成原因、可用的 token 用量和逐题状态。HTTP 错误只记录错误类别与状态码；令牌不进入请求体或日志，响应文本中意外回显的令牌会被替换。传输层拒绝自动重定向，并限制响应体大小。请求为非流式且带 `store=false`；兼容端点仍须支持使用的参数。

兼容性以实际供应商为准。当前实现使用 [Chat Completions 接口](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create)，没有实现 Responses、工具调用、批处理或供应商专属参数。[JSON mode](https://developers.openai.com/api/docs/guides/structured-outputs) 不保证候选图结构正确，因此本地继续执行图结构与逐字引用校验。

## 3. 评分与错误分母

模型响应包与现有外部 JSON 响应格式相同，可以直接评分：

~~~bash
lantern blind-eval \
  --config configs/experiments/missingness_pilot.json \
  --responses outputs/llm_responses.json \
  --output outputs/llm_evaluation.json
~~~

| 调用状态 | 写入评分响应包的内容 |
|---|---|
| `valid_proposal` | 原始 JSON 提案；通过语法和引用校验不等于图结论正确。 |
| `invalid_proposal` | 保留解析后的无效提案，供评分器计入无效输出。 |
| `invalid_json` | `null`；包括代码围栏、重复键、非有限数字和非完整 JSON。 |
| `non_stop_completion` | `null`；包括长度截断，即使可见部分恰好能解析也不采用。 |
| `refusal` | `null`。 |
| `invalid_provider_response` / `provider_error` | `null`；同时在运行报告记录错误类别。 |
| `in_flight` | `null`；表示该请求已经准备发送，但未保存到最终结果，送达情况可能未知。 |
| 尚未开始的任务 | 响应包暂不包含该题，评分器按漏答计数。 |

所有已开始但失败的任务仍保留题目 ID，完整运行时评分分母为 9 题。程序不移除失败题，不解析围栏来修补答案，不在观察评分后重试，也不替模型补图。`blind-eval` 本身不调用供应商；其 `provider_called=false` 描述评分步骤，不能作为外部响应来源的认证。运行报告与指纹提供本地复现记录，不验证供应商身份或模型来源。

## 4. 中断后恢复

每题开始前和结束后分别保存检查点。报告是恢复依据，评分响应包可由它重建。使用原配置和相同输出路径继续：

~~~bash
lantern blind-infer \
  --provider-config configs/providers/experiment.local.json \
  --output outputs/llm_run.json \
  --responses outputs/llm_responses.json \
  --resume
~~~

恢复要求任务包、模型配置和完整请求一致，只执行尚未开始的任务。已失败、已完成和 `in_flight` 的任务均不自动重发，避免中断时重复提交送达情况未知的请求。若确需重跑，创建另一组输出文件并保留原报告；新运行与原运行分开报告。已有输出文件不会被新的非恢复运行覆盖，预览文件也不能作为正式运行检查点。

## 5. 本地核验

~~~bash
python -m unittest discover -s tests -v
~~~

测试使用本机 HTTP 模拟服务和人工响应，核对请求内容、鉴权头、CLI 到评分的链路、用量记录、网络错误、重定向、响应大小、拒答、截断、无效 JSON、凭据回显以及中断恢复。模拟服务按规则生成答案，其测试结果不能记作 LLM 得分。MIMIC 数据提取、正式 E3 题库、模型运行与预登记评分仍需按 [预实验方案](mimic_pilot.md) 单独完成。
