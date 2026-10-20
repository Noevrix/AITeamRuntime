# V0.1.4 — WorkBuddy Integration Investigation

调查日期：2026-10-20。HEAD：`479e433`。

## 验收结论

**官方接入路线调查与离线准备完成；WorkBuddy 真实接入未实施、未验收。**

DSH 与 Codex 保持此前分阶段 REAL 验收结论，详见 [V0.1.3 最终报告](V0_1_3_FINAL_ACCEPTANCE_REPORT.md)。本轮未重新验证或调用它们。WorkBuddy 工作流继续使用 MOCK；真实 Adapter 是 NOT_CONFIGURED 占位实现，不能标记 REAL。没有执行三方或完整 E2E。

## 官方证据与本机环境

找到可靠的官方 [Open API 文档](https://open.workbuddy.cn/docs/openapi)：提供本地助理在线查询、消息提交及游标增量读取。它是平台 HTTPS 接口，不是已证实的本机 localhost 服务。公开消息读取不等于已确认每个任务的最终完成、原生会话隔离和取消协议。

根据 [第三方应用指南](https://open.workbuddy.cn/docs/third-party-app)，该路线涉及开发者应用、审核、用户 OAuth 授权及受保护的应用密钥。现有桌面登录不能代替第三方授权。纯本地开源工具适合的应用类型、账号适用性、无服务端公共客户端授权方式尚未确认；不要求用户冒用硬件应用类型。详细路径、scopes、能力映射、文档差异和限制见 [接入调查文档](docs/workbuddy-integration.md)。

只读本机证据：

- 安装路径 `<workbuddy-install-dir>\WorkBuddy.exe`；PE ProductVersion 5.8.3.0 / FileVersion 5.8.3，腾讯公司元数据。
- 调查时 7 个同名进程正在运行。该事实不证明 Open API online 或用户拥有调用权限。
- 当前 PATH 未找到 workbuddy/codebuddy 命令；安装根目录无 bin。仅列出根目录及 resources 第一层，未执行未知入口、未分析内部包、未扫描端口。
- 未核实套餐、账号地域、开发者资格及已授予 scopes；未访问登录数据或私人配置。未发现足以确认公开 WorkBuddy 本地 CLI/SDK 控制入口的证据。

## 架构和修改范围

统一 Provider 接口足以容纳后续最小实现，无需重写 Kernel。未来可以在 Adapter 内轮询，但必须明确远端状态与本地等待状态、超时与取消区别。没有官方依据的原生会话和取消能力应保持关闭。完整映射与错误分类设计见调查文档。

本轮仅修改/新增四个文件：

| 文件 | 原因 |
| --- | --- |
| docs/workbuddy-integration.md | 更新原占位说明，记录官方路线、证据、授权边界和 V0.1.5 前置条件 |
| src/ai_team/providers/workbuddy/adapter.py | 仅修正过时类注释；实际行为不变 |
| tests/unit/test_workbuddy_preparation.py | 新增 8 项离线测试，保证占位拒绝、能力关闭和 Mock 标记 |
| V0_1_4_ACCEPTANCE_REPORT.md | 本报告 |

没有新增猜测性的环境变量或 OAuth 实现。配置模块、Provider 基类、Mock Adapter、DSH/Codex Adapter 和 Kernel 本轮均未修改。现有占位实现已经安全拒绝未配置调用，因此不为增加代码而改变它。

## 测试与调用控制

按顺序执行：

1. 轻量测试：`python -m pytest tests/unit/test_workbuddy_preparation.py tests/unit/test_core.py -q -p no:cacheprovider --basetemp "<workspace>\pytest-v014-light-fixed"` — **19 passed，0.71 秒**。
2. 离线回归：`python -m pytest tests/unit tests/integration -q -p no:cacheprovider --basetemp "<workspace>\pytest-v014-regression"` — **98 passed，3.32 秒**，包括已有 90 项和新增 8 项。

首次轻量运行为 8 failed / 11 passed：新增禁止网络的测试夹具误阻止 Windows asyncio 创建内部 socketpair，尚未进入 Provider 操作。已将事件循环初始化移到网络禁用前；被测操作期间仍禁止连接。修正后得到以上通过结果。没有为修正测试而放宽 Provider 行为。

新增覆盖：全部能力关闭、health=false、NOT_CONFIGURED、重复 close；connect/create_session/send_message/send_task/interrupt/resume_session 拒绝；Mock 的 READY/CLOSED 及 REQUEST_CHANGES/APPROVE 均带 mock=true。暂未实现真实 HTTP 状态机，不将这些测试宣传成 OAuth/远端消息协议测试。

所有测试使用离线占位、Mock 或 Fake；官方网页阅读是公开资料检索，不是模型调用。真实 WorkBuddy/DSH/Codex 任务数均为 **0**，OAuth 操作数 **0**。没有运行 tests/e2e 或实现 TODO 任务。

## 阻塞点、用户最少步骤与 V0.1.5

目前阻塞：

1. 平台是否允许此独立本地开源应用申请两个本地助理 scopes，以及正确应用类型、用户账号适用范围。
2. 获准的 OAuth 部署/回调方案；不能将统一应用密钥嵌入开源客户端。纯本地公共客户端方案尚无已确认依据。
3. 本次请求与返回消息的可靠关联、最终完成及错误/审批等待语义。随机关联标识可辅助校验，不能冒充原生任务隔离。
4. 客户端最低版本、多设备选择、精确速率/配额、取消支持仍需官方确认。

**用户现在最少只需向[开放平台](https://open.workbuddy.cn/)或[官方联系渠道](https://www.workbuddy.cn/docs/workbuddy/Contact)确认前 3 项。** 说明要让独立本地开源应用调用本人 PC 助理，并取得应用类型、回调/授权部署、回复关联与终态的非敏感说明。不要提供密钥、授权码、Token、Cookie 或账户截图。

V0.1.5 的执行顺序：

1. 根据官方答复确定准入与授权契约；不支持时停留 MOCK，不使用内部接口兜底。
2. 在 WorkBuddy 模块实现可注入 transport/授权提供器、非敏感参数校验；离线验证消息关联、状态错误、总超时、去重与不重发。
3. 获准后由用户亲自注册/审核应用、配置批准的回调与最小权限，并在下一阶段明确授权后完成 OAuth；本轮不代办。
4. 授权就绪先只读查询 online，再经用户授权仅提交一个无工具/无文件写入的短文本任务。提交不明或失败不自动重试。
5. 严格核实相关最终回复，再持久化任务、消息及决策并重读 Blackboard。缺少终态或关联证据时不得标记完整 REAL 接入。

可进入 V0.1.5 的协议澄清和离线实现准备；**尚不具备立即执行真实最小接入验收的全部条件**。

## Git 与保护情况

HEAD 保持 `479e433`，索引无暂存变更；未重置、清理、提交或推送。原有未提交工作保留。`.env` 和 `runs/` 仍被忽略。最终 diff 检查没有空白错误；本轮内容只含公开接口、安装元数据及合成测试，没有新增真实凭证或私人配置。未访问客户端认证文件，未修改安装目录及设置。

当前完整未提交清单（M 为已跟踪修改，?? 为未跟踪；其中仅上述四个文件属于本轮）：

```text
 M V0_1_2_ACCEPTANCE_REPORT.md
 M docs/dsh-auth-setup.md
 M docs/workbuddy-integration.md
 M scripts/dsh_plan_probe.py
 M src/ai_team/kernel/team_kernel.py
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
?? docs/dsh-desktop-reuse.md
?? scripts/dsh_review_probe.py
?? scripts/dual_real_validation.py
?? src/ai_team/orchestration/dual_real.py
?? src/ai_team/providers/diagnostics.py
?? src/ai_team/providers/dsh/review_probe.py
?? tests/unit/test_dsh_review_probe.py
?? tests/unit/test_dual_real.py
?? tests/unit/test_provider_diagnostics.py
?? tests/unit/test_workbuddy_preparation.py
```
