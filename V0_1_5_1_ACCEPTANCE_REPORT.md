# V0.1.5.1 — WorkBuddy 接入前审计与协议确认准备

日期：2026-10-20。HEAD：479e433。本轮无真实 API、OAuth、模型或 E2E 调用。

## 结论

WorkBuddy Adapter 仍为 **PARTIAL**，OAuth 为 **REQUIRED**，Smoke Test / Three-Agent E2E 均 **NOT_RUN**。底层存在真实 HTTPS 请求代码，但尚未证明对真实账户有效；正式 Provider 审核因缺少官方关联/终态协议而有意阻断。DSH/Codex 保持此前 REAL 验收，未在本轮复验。

## 实现审计矩阵

IMPLEMENTED 仅表示对应代码真实存在且有离线证据，不等于真实 API 验收。以下文件路径相对项目根；行号为本轮结果。

| 能力 | 状态 | 代码位置及证据/边界 |
| --- | --- | --- |
| OAuth 完整部署 | PARTIAL | src/ai_team/providers/workbuddy/auth.py:33，scripts/workbuddy_auth.py；已实现授权 URL、换取与刷新，未实现回调服务器及跨主机安全交付，没有获准应用 |
| state 校验 | IMPLEMENTED | src/ai_team/providers/workbuddy/auth.py:60；校验回调来源、state、时间窗口；新增拒绝重复空参数和非 ASCII 不匹配的 Mock 用例 |
| Access Token 使用 | IMPLEMENTED | src/ai_team/providers/workbuddy/client.py:103；Bearer 请求、401 失效，不重放；Fake transport 验证 |
| Refresh Token 更新 | PARTIAL | src/ai_team/providers/workbuddy/auth.py:104、120；可信组件刷新/旋转保存及失败锁定已测；默认桌面 configured_client 未接入刷新服务 |
| Token 安全存储 | IMPLEMENTED | src/ai_team/providers/workbuddy/store.py:10、56、73；当前用户 DPAPI、先加密后写盘；本轮 Mock 加密/损坏检测测试通过，未重测真实 DPAPI |
| 部署安全性 | UNVERIFIED | secret/refresh 必须留在获准可信组件；普通桌面分发架构和平台资格未确认；有加密不等于平台许可 |
| 配置缺失 | IMPLEMENTED | src/ai_team/providers/workbuddy/config.py:9、49；存在性检测不解密，NOT_CONFIGURED/AUTH_REQUIRED 明确 |
| 本地助手 online | IMPLEMENTED | src/ai_team/providers/workbuddy/client.py:117；布尔响应检查，connect/health_check 已有代码；真实 online UNVERIFIED |
| 发消息 | PARTIAL | client.py:123、adapter.py:90；底层 POST 与观察入口可用；正式 send_message/send_task 在 adapter.py:66/72 阻断 |
| 增量读取 | IMPLEMENTED | client.py:132、adapter.py:90；有界读取、去重、过滤；合成无关消息/重复消息测试通过，真实流 UNVERIFIED |
| 最终回复 | MISSING | 无被官方证实的本地终态解析器；COMPLETION_UNCONFIRMED，不能把文本回显当最终结果 |
| 任务与消息关联 | PARTIAL | adapter.py:90；nonce 严格回显和本地 handle/ID 哈希引用已实现；不是官方 reply-to 或任务隔离保证 |
| 完成/失败/超时 | PARTIAL | adapter.py:90、probe.py:14；本地失败/超时/升级等待持久化已测；无远端完成、失败语义 |
| 取消 | PARTIAL | adapter.py:78、82；远端取消不支持，本地等待取消已实现，本轮修复 handle 隔离 |
| Blackboard | IMPLEMENTED | src/ai_team/providers/workbuddy/probe.py:14、src/ai_team/memory/blackboard.py:8；Mock 观察和失败记录、独立重开数据库验证；真实输出持久化 UNVERIFIED |
| 错误分类/脱敏 | IMPLEMENTED | client.py:21、request_json；不输出原始错误正文、限定错误分类；tests/unit/test_workbuddy_api.py 验证敏感合成错误不出现在摘要 |
| 无限重试防护 | IMPLEMENTED | adapter.py:90、auth.py:120；单次提交、有限轮询/总超时、刷新失败锁定，Mock 测试确认无再次 POST |

脚本交换前消耗 pending 的机制是单进程操作者流程，不是跨进程事务锁；目前不适合未经设计的多用户 OAuth 服务。网络取消不能杀死已启动的 HTTP 工作线程，不等于远端取消。未知消息和审批消息不会自动作答；当前可能最终超时，并非已实现审批状态机。

## 官方协议核对

本轮依据：

- [A：Open API](https://open.workbuddy.cn/docs/openapi)：可直接读取，“准备工作”“认证授权 API”“本地助理 API”“返回码规范”。
- [B：第三方应用](https://open.workbuddy.cn/docs/third-party-app)：直接打开两次返回读取错误；通过官方域名搜索结果获取该页正文，能核对注册/审核/服务端授权/Token 生命周期段落。不是登录后的平台验证，资料获取方式存在此限制。
- [C：联系渠道](https://open.workbuddy.cn/docs/contact)：仅用于核实公开咨询渠道，不作为 API 协议依据。

| 待核对事项 | 分类 | 结论及依据 |
| --- | --- | --- |
| 应用注册及审核流程 | OFFICIALLY_CONFIRMED | A/B 要求开发者应用、配置及用户授权；B 说明审核启用。具体个人主体资格仍见下一行 |
| 个人开发者 Windows 本地应用资格 | REQUIRES_OFFICIAL_CONFIRMATION | A/B 没有明确覆盖本项目；分享能力的企业条件不能套到 Local Assistant |
| 开源应用每人各自 OAuth | REQUIRES_OFFICIAL_CONFIRMATION | B 有用户授权概念，但未明确开源公共客户端/自带应用凭据的分发方案 |
| 公网服务器、固定域名是否必须 | REQUIRES_OFFICIAL_CONFIRMATION | B 要求服务端换取/保存凭据；不能据此推定一定要独立公网服务器或固定域名 |
| 回调注册及精确匹配 | OFFICIALLY_CONFIRMED | A 要求已登记 redirect_uri，换取时与授权请求字节一致 |
| localhost/loopback/PKCE 原生客户端 | NOT_DOCUMENTED | A/B 未给该接入方向的明确支持规则。本项目 HTTPS-only 是保守实现限制，不是官方全面禁止其他回调的结论 |
| online 查询 | OFFICIALLY_CONFIRMED | A：GET /openapi/v2/localassistant，readable 权限，data.online 为 bool |
| 发消息请求与结果 | OFFICIALLY_CONFIRMED | A：POST /openapi/v2/localassistant/message，JSON content 字符串、msg_type=text；code=0/data.message_id |
| 增量读取 | OFFICIALLY_CONFIRMED | A：同路径 GET，message_id 指定“之后的消息”，data.messages 为数组、每条 content 为数组 |
| 回复与原请求严格一一关联 | NOT_DOCUMENTED | 游标不是已确认的 reply-to；不能把其后的任意 assistant 消息关联到本任务 |
| 标识 | OFFICIALLY_CONFIRMED | A 本地消息有 message_id，HTTP 包装有 request_id |
| 本地 task_id/session_id 与隔离语义 | NOT_DOCUMENTED | 不将云端任务/ACP/产物的标识套用到本地助手 |
| 本地完成/失败/取消契约 | NOT_DOCUMENTED | 没有明确的本地任务终态/取消确认字段；文本 APPROVE 不是协议终态 |
| 过期/刷新 | OFFICIALLY_CONFIRMED | A 提供 expires_in 和 refresh grant；B 有有效期说明 |
| 生命周期差异/旋转/撤销 | REQUIRES_OFFICIAL_CONFIRMATION | A 示例 3600 秒与 B 的 24 小时/60 天说明应由平台澄清；本项目读取实际 expires_in。撤销入口/通知/重用规则未确认 |
| 权限、限流错误 | OFFICIALLY_CONFIRMED | A/B 有 readable、invokable 和 401/403/429 等规则 |
| 精确 QPS/并发/日配额/费用 | NOT_DOCUMENTED | 在所核对页面未找到本项目可直接采用的数值，需要平台确认 |

状态码表虽提及 device_auth 场景，但没有本项目所需完整授权参数/流程，不据此实现设备授权。以上“未说明”仅限核对的文档，不是断言官方后台绝无此能力。

## 实际安全发现及最小修复

1. **OAuth 参数歧义**：原 parse_qs 默认丢弃空值，`有效state&state=` 或 `code=c&code=` 会被当作单值；`error=` 也可能被忽略。现在保留空值、限制参数数量，拒绝重复 code/state 和任何 error。非 ASCII state 比较改用字节，避免 TypeError 替代明确错误。畸形 pending/URL 也被安全拒绝。
2. **取消目标不匹配**：原 cancel_wait 验证 handle 存在后就取消全局 active task，第二个合法 handle 能误取消第一个等待。新增 active_handle，取消前必须匹配；退出等待时清空。
3. **隐藏输入回退**：getpass 不支持隐藏输入时可能警告后回退到可见 stdin。脚本新增 hidden_input，将该警告转为错误，在回退读取之前停止；授权码回调和 secret 均适用，不输出输入值。

新增 7 项 Mock 用例均通过。没有放宽完成判断，没有增加真实接口或调用次数，没有修改 Token 文件、客户端设置、Kernel、DSH/Codex 代码。

本次不是全面渗透测试或生产安全认证：保留单进程可信操作者假设；服务端密钥托管、跨用户隔离、授权撤销持久化及代理部署仍是后续设计项。

## 测试

轻量：

```powershell
python -m pytest tests/unit/test_workbuddy_api.py tests/unit/test_workbuddy_preparation.py tests/unit/test_core.py -k 'not test_dpapi_synthetic_memory_roundtrip' -q -p no:cacheprovider --basetemp '<workspace>\pytest-v0151-light'
```

**59 passed，1 deselected，1.44 秒。**

离线回归：

```powershell
python -m pytest tests/unit tests/integration -k 'not test_dpapi_synthetic_memory_roundtrip' -q -p no:cacheprovider --basetemp '<workspace>\pytest-v0151-regression'
```

**138 passed，1 deselected，3.94 秒。** 原 132 项 + 新增 7 项 = 139 项；按本轮全部使用 Mock 的限制，排除原生 DPAPI 合成加解密那 1 项，未删除测试，未把排除项算作通过。存储逻辑仍通过 Mock 加密/损坏检测用例验证。

既有测试已覆盖缺配置、授权失败、过期刷新、401/403/429、超时/连接失败、无效 JSON、不相关回复、增量/最终样式文本不当作完成、失败不 APPROVE、无再次 POST、Blackboard 持久化，不重复新增同义用例。

仅执行无网络配置检查，当前 client_id_present=false、redirect_uri_present=false、encrypted_token_present=false、deployment_approved_by_operator=false，返回 NOT_CONFIGURED。没有解密/读取任何凭证值。真实调用数为 0。

## 官方咨询与用户步骤

已创建 [可直接复制的咨询文案](docs/workbuddy-open-platform-questions.md)，含官方公开邮箱、社群入口及用户自行提交步骤。未发送、未注册、未申请权限。

用户需先确认应用类型、个人资格、公共客户端/服务端方案和正式终态；获准后亲自注册/提交审核、登记回调及两个最小 scopes，再亲自同意 OAuth。当前具体缺少获批应用 ID、回调配置、已确认部署和合法 token；不是缺客户端安装路径。

**当前不具备直接进行真实 OAuth 配置和验收级 Smoke Test 的完整条件。** 可以先发送咨询、讨论批准的授权部署；不能因为加密存储或配置开关存在就跳过平台准入。即使以后观察到 nonce 回显，仍不能在终态缺口未解决时宣称 Smoke PASS。

## V0.1.6 方案

1. 用户提供官方非敏感答复，更新资格、回调、关联、终态、撤销及配额契约；无明确答复时保持 PARTIAL/MOCK。
2. 按获准方案实现回调服务或公共客户端流程，以及凭据的服务端边界；不要猜 localhost/PKCE 参数，不把 refresh/secret 分发给普通桌面用户。
3. 取得正式关联/终态样例后，先离线覆盖成功、失败、取消、审批等待、多请求混杂和限流；再决定是否解除 review gate。
4. 经用户授权，先只读 online，再一次无副作用消息；提交结果不确定不重试，核对真实关联、终态和 Blackboard。
5. 只有上述验收成功才讨论一次受控三 Agent 联调；不会自动执行。

## 本轮文件与 Git

修改：src/ai_team/providers/workbuddy/auth.py、src/ai_team/providers/workbuddy/adapter.py、scripts/workbuddy_auth.py、tests/unit/test_workbuddy_api.py。

新增：docs/workbuddy-open-platform-questions.md、V0_1_5_1_ACCEPTANCE_REPORT.md。

HEAD 仍为 479e433，dirty，无暂存、提交或推送。以本轮开始时所有既有文件哈希为基准复核，仅以上四个已有文件改变；其他历史未提交工作与报告保留。最终 diff --check 及敏感模式检查结果见完成核验；不修改安装目录、不清理工作区。

完整未提交文件清单附于下节。

## 最终工作区清单

```text
 M .env.example
 M V0_1_2_ACCEPTANCE_REPORT.md
 M docs/dsh-auth-setup.md
 M docs/workbuddy-integration.md
 M scripts/dsh_plan_probe.py
 M src/ai_team/cli.py
 M src/ai_team/kernel/team_kernel.py
 M src/ai_team/orchestration/workflow.py
 M src/ai_team/providers/dsh/adapter.py
 M src/ai_team/providers/dsh/probe.py
 M src/ai_team/providers/dsh/runtime.py
 M src/ai_team/providers/workbuddy/adapter.py
 M tests/unit/test_dsh_auth.py
 M tests/unit/test_dsh_probe.py
?? V0_1_3_1_DIAGNOSTIC_REPORT.md
?? V0_1_3_2_ACCEPTANCE_REPORT.md
?? V0_1_3_ACCEPTANCE_REPORT.md
?? V0_1_3_FINAL_ACCEPTANCE_REPORT.md
?? V0_1_4_ACCEPTANCE_REPORT.md
?? V0_1_5_1_ACCEPTANCE_REPORT.md
?? V0_1_5_ACCEPTANCE_REPORT.md
?? docs/dsh-desktop-reuse.md
?? docs/workbuddy-open-platform-questions.md
?? docs/workbuddy-real-setup.md
?? scripts/check_workbuddy_config.py
?? scripts/dsh_review_probe.py
?? scripts/dual_real_validation.py
?? scripts/workbuddy_auth.py
?? scripts/workbuddy_smoke_test.py
?? src/ai_team/orchestration/dual_real.py
?? src/ai_team/providers/diagnostics.py
?? src/ai_team/providers/dsh/review_probe.py
?? src/ai_team/providers/workbuddy/auth.py
?? src/ai_team/providers/workbuddy/client.py
?? src/ai_team/providers/workbuddy/config.py
?? src/ai_team/providers/workbuddy/probe.py
?? src/ai_team/providers/workbuddy/store.py
?? tests/unit/test_dsh_review_probe.py
?? tests/unit/test_dual_real.py
?? tests/unit/test_provider_diagnostics.py
?? tests/unit/test_workbuddy_api.py
?? tests/unit/test_workbuddy_preparation.py
```

完成核验：git diff --check 通过；本轮修改和新增文件常见私钥/API key/JWT 模式检查无告警，人工检查仅合成测试值及公开信息。扫描不能证明不存在所有类型的秘密。85 个其他既有文件哈希未改变，索引无暂存文件。
