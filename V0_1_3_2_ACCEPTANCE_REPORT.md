# V0.1.3.2 独立 DSH 审核入口准备报告

## 结论

**离线准备 PASS，真实审核未执行。** 已新增只审核既有 TODO CLI 的独立入口。默认执行只做离线证据检查，只有显式 `--execute` 才允许启动官方 DSH SDK。没有调用 DSH、Codex 或 WorkBuddy，没有运行完整 E2E，没有重跑旧工作流。

V0.1.3 的整体验收仍为 FAILED；本轮不能证明账户模型真实接受参数或实际审核通过。

## 根因及参数依据

原失败已由 V0.1.3.1 定位：输出预算 4096 被 reasoning 耗尽，结束原因 max-tokens，没有最终文本。该值原先在 DSHAdapter.connect 中硬编码。

本轮只读核对安装版本 0.2.1-rc.2 的 app.asar 官方包文档以及本地 Python SDK 0.2.1rc2 源码：

- `deepseek_harness/api.py` 的 DeepSeekHarnessConfig 实际具有 `max_tokens` 和 `reasoning_effort`；start 将两者传给 initialize。
- `deepseek_harness/client.py` 将它们转换为初始化载荷的 `maxTokens`、`reasoningEffort`。离线接口契约测试调用此真实序列化代码，但替换 request，不启动进程或发网络请求。
- 安装内 `@deepseek-ai/dsh-llm-deepseek-account/README.md` 明确该账户模型路由提供 off、low、high、max。
- 安装内 `@deepseek-ai/dsh-llm-deepseek/README.md` 明确 off 转换为 `thinking.type: disabled`；low/high/max 开启 thinking 并设置 output_config.effort。不支持的 effort 会失败，而不是猜测替代参数。

因此新审核默认采用 **max_tokens=4096、reasoning_effort="off"**，优先关闭会消耗本轮预算的 reasoning，不先盲目加倍额度。入口允许预算 2048、4096、8192，允许 effort off 或 low；Adapter 总边界为整数 1024–8192，原默认行为仍为 4096、effort 未指定。不会修改桌面 profile 或系统环境变量，不会在失败后切换预算/模式重试。

这是依据当前安装接口支持做出的最小配置修复，不是模型效果保证。若未来服务端不接受或未按预期执行 off，必须依据新诊断停止分析，不能宣称已关闭 reasoning。

## 审核输入和输出

输入来源为 `runs/v013-dual-real`：

- `blackboard.sqlite`：原始需求、DSH 规划 decision 和 PROPOSE 消息、成功测试事件、原任务及产物哈希。
- `workspace/todo.py`
- `workspace/test_todo.py`
- `workspace/test_runtime_contract.py`
- `workspace/USAGE.md`
- `workspace/tests-1.txt`：历史实际 14 项测试通过日志。

读取 SQLite 使用只读、immutable 模式，并要求历史 WAL 不存在；不修改历史数据库。逐个验证 5 个文件的 SHA-256，拒绝改变的产物、缺失记录、符号链接文件、越界/过大文件和不匹配的测试记录。历史测试不会重新执行。测试结果仅证明原有产物在原环境中的历史验证。

原规划引用：decision `ab7de08a632e467f8717584638927b7a`，任务 `fc7dafe937ad4b8299c541cc9eebff85`，项目 `909429deed4245999d473a928370c348`。

只摘录原规划的第 2 节 CLI contract 与第 11 节 Acceptance checklist，逐字保留，不让模型生成摘要。完整规划通过 decision ID 和 SHA-256 可追溯。去掉重复的 Blackboard 全量任务/历史消息，保留真实完整源码、测试源码、说明和测试日志。

离线预检得到证据 JSON **16886 UTF-8 字节**，与原审核任务正文 26947 字节相比减少约 37%；另有固定的短审核指令。证据大小上限 24000 字节，不静默截断。新运行时使用新会话，不恢复失败会话的历史上下文。

要求返回 JSON：

```json
{"type":"APPROVE","content":"简短审核摘要","findings":[]}
```

type 只允许 APPROVE 或 REQUEST_CHANGES；content 最多 300 字符，findings 最多 3 条、每条最多 240 字符。REQUEST_CHANGES 至少包含一条发现。Adapter 严格验证后将摘要和发现写入 Result.content，供现有任务/Blackboard 机制持久化。超限、Mock 标记、非法类型和格式都不会写成有效审核结论。

## 独立入口与状态

入口：`scripts/dsh_review_probe.py`。

内部使用现有 DSHAdapter + TeamKernel + Blackboard，账户路由 deepseek-account / deepseek-flash、官方 dsh.cmd、用户 `.dsh` home、独立 sdk profile。没有导入或启动 Codex/WorkBuddy 工作流。

新结果写入 `runs/v0132-dsh-review/`，与历史运行隔离。该目录必须不存在；首次执行排他创建，再执行会返回 ALREADY_ATTEMPTED，不覆盖结果、不重试。不要删除目录来绕过一次性保护。

新 Blackboard 保存任务、消息、审核 decision、源项目/规划/产物引用、输入快照 SHA-256、模型结束原因和安全诊断。成功后重新打开数据库核对审核 decision、任务状态及真实消息。终端摘要不包含模型正文、源文件正文、私人路径或原始异常；仅输出状态、ID、预算、调用次数、诊断字段及持久化验证布尔值。

| status | 含义 | 退出码 |
| --- | --- | --- |
| READY_OFFLINE | 证据离线检查通过，未启动模型 | 0 |
| APPROVE | completed、合法真实审核通过且持久化验证成功 | 0 |
| REQUEST_CHANGES | 合法真实审核返回修改要求，产物未获通过 | 2 |
| MAX_TOKENS | 输出预算耗尽，即使带部分 APPROVE 也拒绝 | 1 |
| INVALID_RESPONSE | 无最终文本、无效 JSON、结构/决定不合法等 | 1 |
| PROVIDER_ERROR | SDK/连接/超时/其他执行失败，详见安全 diagnostic | 1 |
| LOCAL_SETUP_ERROR / ALREADY_ATTEMPTED | 本地检查或一次性保护阻止执行 | 1 |

结束原因 max-tokens 优先分类为 MODEL_MAX_TOKENS；completed 但没有最终文本为 MISSING_FINAL_TEXT；非空文本无法解析为结果为 INVALID_MODEL_JSON。上述情况不会以缺省 APPROVE 或 Mock 替代。

## 准确命令

只做离线检查（本轮已执行，输出 READY_OFFLINE、model_called=false）：

```powershell
Set-Location '<project-root>'
python .\scripts\dsh_review_probe.py
```

**下一轮用户明确准备好后**，先保存并彻底退出 DeepSeek Harness 桌面客户端及后台 Host，停止其他使用同一 home 的 DSH CLI/SDK。无需登出账户，无需退出 Codex 应用，无需输入或申请 API Key。然后只执行一次：

```powershell
Set-Location '<project-root>'
python .\scripts\dsh_review_probe.py --execute --max-tokens 4096 --reasoning-effort off
```

此命令会真实消耗账户额度。本轮未执行。使用的 home 默认为当前用户 `.dsh`，如桌面配置已改变须先核对，不复制凭证文件。官方运行时自行读取已有账户授权，项目不提取凭证。

应用层最多一个 FINAL_REVIEW 任务，失败立即停止；不调用 Codex、不返工、不重新规划。SDK/服务端仍可能有内部请求或重试，不能把一次应用层任务等同于一次底层 HTTP/推理请求。

## 测试与修改

最终相关轻量测试：**44 passed**，2.04 秒。

随后单元与集成回归仅运行一次：**90 passed**，3.29 秒；保留原有 74 项并新增 16 项。未执行 3 个 E2E，不宣称完整 93 项通过。

新增测试覆盖正常两种审核决定、max-tokens 无文本、completed 无文本、无效 JSON、Mock/过多发现拒绝、ProviderError、超时、连接失败；验证失败没有 APPROVE、只有一次调用、再次运行被阻止、异常不泄露合成凭证、历史数据库不变、预算边界及实际 SDK 参数序列化。

首次新增测试发现事件引用与 project_id 参数同名，模型调用前失败；已改为嵌套 source_references，并通过上述最终测试。没有借此触发任何真实调用。

本轮修改文件：

- `src/ai_team/providers/dsh/adapter.py`：受限预算/effort、专用短审核格式验证、安全结果元数据、缺少最终文本分类。
- `src/ai_team/providers/diagnostics.py`：新增 MISSING_FINAL_TEXT。
- `src/ai_team/providers/dsh/review_probe.py`：证据校验和一次审核执行。
- `scripts/dsh_review_probe.py`：默认离线、显式执行 CLI。
- `tests/unit/test_dsh_review_probe.py`：16 项离线测试。
- 本报告。

git diff --check 通过。所有已有未提交修改保留，历史产物未覆盖，安装目录和桌面设置未修改；.env 和 runs/ 仍被忽略，无密钥或私人配置加入版本控制。未提交、未推送。

**具备进行一次受控真实审核的准备条件**：本机证据可读且哈希匹配、接口参数有版本依据、离线测试通过。账户有效性、服务端实际行为和真实审核结果仍未验证；本轮到此停止。
