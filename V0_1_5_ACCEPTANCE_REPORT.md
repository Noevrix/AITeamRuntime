# AI Team Runtime V0.1.5 — WorkBuddy Real Integration

日期：2026-10-20。Git HEAD：`479e433`。本报告记录本轮实际实现，不替换历史验收与失败记录。

## 验收结果

```text
AI Team Runtime V0.1.5
DSH: REAL
Codex: REAL
WorkBuddy Adapter: PARTIAL
WorkBuddy OAuth: REQUIRED
WorkBuddy Smoke Test: NOT_RUN
Three-Agent E2E: NOT_RUN
Offline Tests: 132 passed
Git: dirty
```

DSH/Codex 的 REAL 来自此前分阶段验收，本轮没有重新调用或验证。WorkBuddy 已从空占位扩展为官方 HTTP/OAuth 客户端和受控消息观察入口，但**没有完成真实 Reviewer 接入**。当前工作流默认仍为 MOCK。不能把离线测试、配置模板或官方接口存在等同于真实任务成功。

## 实际完成的功能

1. 分离 WorkBuddyAdapter、官方 API Client、OAuth/TokenProvider 和加密存储模块。
2. 实现官方在线查询、text 提交和按消息游标读取；严格校验响应结构、限制响应大小，拒绝重定向，不重试 HTTP 请求。
3. 实现授权 URL/state、精确回调与 state 校验、授权码单次换取、过期检测、刷新及旋转保存；401 后使当前授权失效，不重放任务。
4. Windows 当前用户 DPAPI 加密存储；写盘前加密，替换采用原子写入。不读取 WorkBuddy 安装目录/客户端认证文件，不保存应用 secret。
5. 增加配置检查、可信部署手动授权工具和单次消息观察脚本；默认不联网，缺配置明确拒绝。
6. 观察入口最多一次 POST、有限轮询、总超时、消息去重和本地取消等待；不声称支持远端取消。
7. 复用现有 Kernel、Task Manager、Message Bus、Event Bus、Blackboard 记录合成观察证据，离线测试验证独立重开 SQLite 后持久化。
8. 增加显式 `--workbuddy-mode real` 工作流选项及前置协议 gate：当前在启动 DSH/Codex 之前阻断，避免先消耗模型额度再发现 WorkBuddy 无法验收。
9. 正式非 Mock reviewer 输入路径准备实际代码、测试日志、原始需求/规划快照，并保存审核内容；既有返工限制和 Mock 默认保留。该分支没有进行真实三方验收。

未重写 Kernel/Provider 基类，未修改 DSH/Codex Adapter、Mock Adapter、安装目录或账户设置。

## 官方协议依据与限制

本轮重新读取 [Open API](https://open.workbuddy.cn/docs/openapi) 和 [第三方应用](https://open.workbuddy.cn/docs/third-party-app)。准确端点、scopes 和部署边界详见 [实现与启动指南](docs/workbuddy-real-setup.md)。

关键限制仍未消失：Local Assistant 文档没有明确可用于当前任务的最终完成标识和回复所属请求字段，也未给出独立 session/远端取消接口。云端 tasks 的 completed 状态不适用于本地助手。

因此：

- connect/health_check 只说明可访问且 online，不意味着 review 可用。
- create_session 生成本地 handle，记录 remote_session=false，不冒充远端独立会话或工作目录绑定。
- 正式 send_task/send_message 返回 COMPLETION_UNSUPPORTED，**远端提交前停止**；capabilities 全部 false。
- observe_once 可以观察严格匹配本次随机 nonce 的安全回显。它只构成应用层对应证据，不是官方 reply-to 关联保证。
- 即使观察到正确回应，也返回 COMPLETION_UNCONFIRMED，task 为 ESCALATED，绝不生成 APPROVE/COMPLETE 或 Smoke PASS。
- 未关联内容、私人消息、原始错误正文、metadata 不进入 Blackboard；外部 message_id 只保留 SHA-256 引用。

这不是实现疏漏的成功掩饰：若要可靠完成正式审核，必须先取得官方终态/关联契约，再编写相应解析和测试，不能猜测响应字段。

## OAuth 与本机检查

本机只读核实 `<workbuddy-install-dir>\WorkBuddy.exe` 的 ProductVersion 为 5.8.3.0。未启动或修改客户端。

本轮默认配置检查实际返回：

```json
{
  "status": "NOT_CONFIGURED",
  "client_id_present": false,
  "redirect_uri_present": false,
  "deployment_approved_by_operator": false,
  "encrypted_token_present": false,
  "token_validity_verified": false,
  "completion_supported": false
}
```

只检查本项目配置及本应用加密文件是否存在，不扫描其他账号或客户端内部授权。该结果不能推断用户是否在其他系统拥有开发者应用。

`workbuddy_smoke_test.py` 无 --send-once 返回 NOT_CONFIGURED / application_attempts=0；`workbuddy_auth.py begin` 无批准部署标志返回 DEPLOYMENT_UNCONFIRMED，未提示密钥、未打开浏览器、未联网。在线状态未实测，真实消息发送/读取未执行。

OAuth 代码仅供平台认可的可信部署使用，不把共享 secret 放入开源分发客户端。纯本地应用资格、批准的回调服务、跨主机 token 交付/授权代理仍未完成；本仓库不是已部署的 OAuth 服务。存储中只保存本应用合法取得的 token 和 pending state，不能以复制桌面内部凭证替代授权。

## 状态、错误与预算

已离线覆盖 NOT_CONFIGURED、AUTH_REQUIRED、AUTH_FAILED、FORBIDDEN、RATE_LIMITED、SERVER_ERROR、HTTP_ERROR、INVALID_RESPONSE、CONNECTION_ERROR、TIMEOUT、OFFLINE、CANCELLED 以及协议不支持。

一次观察默认：60 秒总时限、HTTP 20 秒、最多 20 次轮询、间隔 2 秒；应用层 POST 在发送前预留次数，超时/连接错误包括结果不确定的情况均不重发。刷新失败在 TokenProvider 实例内锁定，不能循环刷新；明确 401 不自动刷新再提交。

本地 cancel_wait/close 只能停止等待；没有远端取消能力。被取消的 to_thread HTTP 操作可能继续到其网络超时；不能将本地取消标为远端任务取消成功。

未使用供应商 SDK，无应用层自动 HTTP 重试。真实请求数本轮为 0；本实现的无重试策略不能证明供应商内部零重试。

## Blackboard 验证范围

离线观察测试通过现有组件创建项目/任务/消息/事件及 CONNECTIVITY_OBSERVATION 决策，再重开数据库核对任务状态和 decision 内容。

已验证：

- 与本次 nonce 不符的回复不会写成当前任务回复。
- 重复回显只记录一次。
- 回显不等于官方完成；状态为 ESCALATED，completion_verified=false。
- 超时、离线、提交不确定失败有可追溯任务记录，不会误写 APPROVE。
- 正式 Kernel 调用受阻后任务为 FAILED，没有虚假审核决策。

以上均为合成 HTTP fixture，不是真实 WorkBuddy 输出。诊断中 mock=false 表示选择真实 Adapter 代码路径，不能脱离测试来源宣称模型真实调用成功。

## 测试结果和修正记录

本轮最终轻量测试：

```powershell
python -m pytest tests/unit/test_workbuddy_api.py tests/unit/test_workbuddy_preparation.py tests/unit/test_review_evidence.py tests/unit/test_core.py -q -p no:cacheprovider --basetemp '<workspace>\pytest-v015-light-user'
```

**55 passed，1.52 秒。**

完整必要离线回归（不含 tests/e2e）：

```powershell
python -m pytest tests/unit tests/integration -q -p no:cacheprovider --basetemp '<workspace>\pytest-v015-regression'
```

**132 passed，3.71 秒。** 包含原 98 项及本轮新增 34 项。协议测试用 Fake transport 并禁止网络连接；DPAPI 单项仅使用内存合成字符串，不读取真实凭证。

开发过程中的真实失败记录：

- 三个新脚本首次直接启动因未安装包而 ModuleNotFoundError；已按项目已有脚本方式加入相对 src 搜索路径，重新执行默认入口返回预期脱敏状态。
- 最初增加的原生 DPAPI 测试在受限进程内失败：Windows 错误 2。正常用户上下文中单独运行该合成测试通过（1 passed）；随后轻量及回归均在正常用户上下文通过。不能将受限环境失败隐藏为从未发生。

未运行完整 E2E、三 Agent 流程、DSH/Codex 模型或任何真实 WorkBuddy 任务。

## 用户下一步与准确入口

当前可安全执行：

```powershell
Set-Location -LiteralPath '<project-root>'
python .\scripts\check_workbuddy_config.py
```

用户需要亲自通过 [开放平台](https://open.workbuddy.cn/)确认本地开源应用可申请的应用类型、账户资格、授权部署及两个本地助手权限，随后注册/审核应用、配置批准的 HTTPS 回调和完成用户授权。官方文档提到硬件/Buddy 应用，但本报告不擅自指定用户必须选其中某类。

非敏感配置为 AI_TEAM_WORKBUDDY_CLIENT_ID、AI_TEAM_WORKBUDDY_REDIRECT_URI、AI_TEAM_WORKBUDDY_DEPLOYMENT_APPROVED。这些是项目自定义变量。不要向聊天提供密钥、Token 或回调中的授权码。

具体可信部署授权、只读 online 和单次观察命令详见 [启动指南](docs/workbuddy-real-setup.md)。现在不建议直接执行 --send-once：授权缺失且正式任务完成协议仍未确认。

下一阶段先补齐平台准入/授权交付和终态协议，再测试一次真实观察；只有确认可靠关联、完成及持久化后才考虑单次三 Agent 联调。当前不具备三 Agent 真实验收条件。

## 本轮文件清单

修改已有文件：

- `.env.example`：仅非敏感占位模板。
- `docs/workbuddy-integration.md`：新增后续实现文档链接，保留 V0.1.4 原文。
- `src/ai_team/cli.py`：可选 WorkBuddy 模式及启动前 gate。
- `src/ai_team/orchestration/workflow.py`：非 Mock reviewer 实际证据输入、审核内容持久化。
- `src/ai_team/providers/workbuddy/adapter.py`：正式任务阻断及受控观察实现。

新增文件：

- `src/ai_team/providers/workbuddy/client.py`
- `src/ai_team/providers/workbuddy/auth.py`
- `src/ai_team/providers/workbuddy/config.py`
- `src/ai_team/providers/workbuddy/store.py`
- `src/ai_team/providers/workbuddy/probe.py`
- `scripts/check_workbuddy_config.py`
- `scripts/workbuddy_auth.py`
- `scripts/workbuddy_smoke_test.py`
- `tests/unit/test_workbuddy_api.py`
- `docs/workbuddy-real-setup.md`
- `V0_1_5_ACCEPTANCE_REPORT.md`

## Git 与已有工作保护

HEAD 仍为 `479e433`，工作区 dirty，索引无暂存变更。进入本轮时对 78 个已有版本控制/未跟踪项目文件计算哈希；最终比较只变更上述 5 个已有文件，其余已有文件字节保持不变，包括 DSH/Codex Adapter、Kernel 及全部历史验收报告。

`git diff --check` 通过；检查本轮 diff、新文件及常见私钥/API key/JWT 模式未发现凭证。模板和合成测试不含真实凭证；运行目录仍由 Git 忽略。没有读取客户端认证配置，没有修改任何安装目录或用户设置，没有重置、清理、提交或推送。

本版本结论为 **PARTIAL 实现 + 离线回归通过 + 真实授权/完成协议待解决**，不能将它标记为 WorkBuddy REAL 或三 Agent E2E PASS。
