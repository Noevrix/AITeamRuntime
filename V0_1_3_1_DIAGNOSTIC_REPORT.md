# V0.1.3.1 DSH ProviderError 离线诊断

## 结论

**直接根因已确认：审核轮次耗尽 4096 输出 token 预算，以 max-tokens 结束，只有 reasoning，没有最终文本。** DSH Adapter 正确拒绝非 completed 结果，但将具体结束原因合并为通用 ProviderError；上层又只保存异常类名，导致上次报告无法区分原因。

本轮只读取既有证据、调用 SDK 的纯解析函数、执行 Fake/Mock 离线测试。真实 DSH/Codex/WorkBuddy 调用均为 0，完整 E2E 0，未重跑审核，未修改安装目录、提交或推送。原有未提交修改和失败运行证据全部保留。

## 具体证据

项目：909429deed4245999d473a928370c348。

- 规划任务：fc7dafe937ad4b8299c541cc9eebff85，COMPLETED。
- 审核任务：663544a72f994b48a13fd48983f2a883，FAILED。
- Blackboard 的 sessions 将两阶段绑定到同一个 DSH 会话：99d5331c0bc54fb8b6f4a4165963bdb8。
- 在用户 `.dsh/sessions` 下找到该运行工作目录对应的上述会话专属 `session.v4.jsonl.zstd`。只对本次运行做结果/结束状态摘要，没有打开凭证文件、导出原始日志、提取/打印/复制 Cookie、Token 或 Key。未检查其他用户会话。

| 证据 | 规划 | 审核 |
| --- | --- | --- |
| assistant/message seq | 15 | 24 |
| 内容块类型 | reasoning、text | reasoning，无 text |
| 最终文本字符数 | 7484 | 0 |
| 最终文本 JSON | 合法 PROPOSE | 无文本可解析 |
| usage.outputTokens | 3212 | 4096 |
| turn/end seq | 17 | 26 |
| reason.kind | completed | max-tokens |
| description 字符/UTF-8 字节 | 307 / 307 | 26947 / 26947 |
| Adapter 完整 prompt 字符/UTF-8 字节 | 585 / 585 | 27318 / 27318 |
| 数据库 RUNNING 到结束约耗时 | 17.65 秒 | 24.22 秒 |

审核 turn/end 时间为 2026-10-19 12:48:10.501 UTC；数据库任务 FAILED 为 12:48:10.505806 UTC，紧接其后。时间、会话、阶段及结束原因一致。

使用本地安装 SDK 0.2.1rc2 的纯函数 `finish_reason(events)` 和 `final_response(events)` 对各轮已保存事件离线解析，分别得到 completed / 7484 字符及 max-tokens / 0 字符。没有创建 SDK 客户端或启动 Host。这与 Adapter 分支完全吻合。

## 参数、会话与错误链

两阶段复用同一个 Adapter、SDK 运行时和 architect 会话，均为 `deepseek-account` / `deepseek-flash`，`profile=sdk`，同一用户 home。SDK max_tokens=4096、request_timeout_seconds=120，Adapter 调用等待 120 秒，Kernel turn_timeout=180 秒；初始化 20 秒、shutdown 1 秒。审核输入更长且会话包含之前规划，但没有证据可以将“输入更长”单独认定为失败原因或 context 超限。

确认的路径：

1. SDK 收集到审核的 assistant/message 和 turn/end；最终文本提取函数只拼接 text 块，不将 reasoning 当作结果。
2. SDK 返回 finish_reason=max-tokens；Adapter 检查非 completed 后立即抛 ProviderError。
3. 该检查发生在 json.loads / Result.model_validate 之前，因此本次不是 JSON 解析抛错，也没有可用于 APPROVE 的最终回答。
4. 本次 ProviderError 是 Adapter 主动创建，没有证据表明存在 HTTP 异常或下层 SDK 异常链。已有项目记录没有 HTTP 状态码和 Python traceback；会话事件没有 error 类型事件。不能反推底层 HTTP 状态，也不能声称完全没有内部重试。

为什么 reasoning 用满预算，是否调整提示或增加预算就必然成功，现有证据无法证明。确认的是这次终止机制，而不是模型内部推理过程的原因。

## 出错位置与诊断丢失

- `src/ai_team/providers/dsh/adapter.py` 当前 139–141 行：非 completed 检查；原先将 session 不匹配、max-tokens、其他结束原因合并，未保存 finish_reason、usage、响应长度。
- 同文件 143 行：JSON 解析位置，本次没有走到这里。
- 同文件 `_call`：原先 SDK 异常包装只保留类名并 from None，丢弃安全的结构化错误码；这不是此次 max-tokens 的触发路径，但属于需要修复的诊断缺口。
- `src/ai_team/kernel/team_kernel.py` PROVIDER_FAILURE：原先只记录 type(exc).__name__。
- `scripts/dual_real_validation.py`：原先 summary 和失败事件也只保存异常类名。
- `src/ai_team/orchestration/dual_real.py`：原先失败后阶段记录停留 STARTED。
- SDK 的 stderr 队列只在内存中保存，项目没有持久化原始堆栈/诊断。不能从历史 summary 恢复已丢失的信息，也不应该为诊断输出原始 stderr 或异常正文。

## 最小修改

1. 新增 `src/ai_team/providers/diagnostics.py`：白名单错误分类、数字型 RPC code / HTTP status（仅在异常对象明确提供时）、有限类型名称链；不保存异常文本、data、请求头、响应体或任意字段。数值也有类型和范围检查，未知字符串及畸形字段被丢弃。
2. DSH Adapter：新增 MODEL_MAX_TOKENS、MODEL_TURN_FAILED、SESSION_MISMATCH、INVALID_MODEL_JSON、INVALID_MODEL_CONTENT、INVALID_MODEL_DECISION；保存安全长度和 output_tokens。SDK 连接/协议/RPC 异常分开，TimeoutError 保持类型但去掉原始正文；清理失败不掩盖原始分类。仍拒绝 max-tokens，即使它附带可解析的 APPROVE 也不放行。
3. Kernel：PROVIDER_FAILURE 增加脱敏 diagnostic。
4. DualRealWorkflow：异常时阶段标记 FAILED，记录同样的安全分类并立即重新抛出，没有重试。
5. 双 AI 启动器：summary 与失败事件保存安全分类。
6. 新增 `tests/unit/test_provider_diagnostics.py`，全部使用合成值和 Fake SDK。

没有改动 4096 token 配置、模型路由、SDK 包、工作流调用上限或真实验证入口的排他运行目录。没有把历史失败记录改写成新诊断结果，也未修改 WorkBuddy。

## 离线测试

- 初次相关测试 37 passed；补充恶意/畸形字段过滤及超时正文脱敏后，最终相关测试 **38 passed**。
- 最终必要回归：`tests/unit tests/integration`，**74 passed**，2.16 秒。
- 新增 15 个测试用例。此前 62 项包含 3 项 E2E；本轮保留其余 59 项并增加 15 项，未执行那 3 项 E2E，因此不宣称完整 77 项通过。
- 覆盖错误分类、数字错误码/安全异常链、凭证样式内容过滤、超时/连接关闭、max-tokens、无效 JSON、空响应、Mock 响应、错误阶段决定均不产生 APPROVE；Kernel 任务 FAILED 且持久化分类，应用层只有一次调用。
- 对实际历史事件的 SDK 纯解析复核不计作真实调用或新的验收通过。

## 下一次真实验证前的条件

诊断记录与离线防回归条件已具备；**目前还不应直接运行旧的双 AI 启动器**，它有一次性运行目录保护，且会重新执行规划/实现。

建议下一步先离线准备“只审核现有产物一次”的专用入口：核对已有源码/测试日志哈希和原始需求，保存输入引用，限制一个 DSH 任务，禁用应用层重试，不启动 Codex 或 WorkBuddy，不删除旧运行目录。

然后将审核输出限制为短 JSON（APPROVE 或 REQUEST_CHANGES，有限条具体意见），通过官方 SDK 支持的 max_tokens 参数提供显式且有上限的审核预算，例如将 4096 提升至 8192 作为待验证候选值。不是保证成功的修复，也不应无限增加额度；无需修改 DSH 安装或申请新 Key。应先增加预算参数/边界测试，再确认用户接受该预算并明确授权一次真实审核。

启动前确保没有共享 home 的桌面 Host 或其他 SDK 并发写入，不登出账户、不提取凭证。继续让官方运行时处理账户授权。真实调用仍必须 completed、非 Mock、合法结构和合法审核决定；再次失败立即停止。

## Git 与验收状态

HEAD 保持 479e433。当前已有未提交文件全部保留；本轮在现有改动上追加上述最小诊断变更和本报告。git diff --check 通过，运行目录和 .env 继续被忽略；没有真实凭证、私人配置或原始会话日志加入版本控制。未提交、未推送。

V0.1.3 端到端验收仍为 FAILED。V0.1.3.1 离线诊断与脱敏记录修复通过；不据此将 DSH 审核能力标记 PASS。
