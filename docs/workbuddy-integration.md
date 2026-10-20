# WorkBuddy 接入调查（V0.1.4）

后续实现状态：见 [V0.1.5 实现与启动](workbuddy-real-setup.md)。下文保留 V0.1.4 调查时的历史状态，不能据此判断后续代码仍是空占位。

调查日期：2026-10-20。结论：找到官方公开接口，但本项目仍未授权、未实现、未验证真实 WorkBuddy 调用。Windows 客户端运行不等于第三方接口在线或已授权。

## 官方依据

### 1. Open API：已确认的最小接口面

基址为 `https://www.workbuddy.cn/openapi/v2`，不是 localhost 服务：

| 方法与路径 | 用途 / 最小 scope |
| --- | --- |
| GET /authorize、POST /token | OAuth 授权码、换取/刷新访问凭证 |
| GET /localassistant | online；user.localassistant.readable |
| POST /localassistant/message | content、msg_type=text → message_id；user.localassistant.invokable |
| GET /localassistant/message | message_id 游标增量读取；user.localassistant.readable |

历史消息 content 为数组；分页默认 20、上限 100。公开本地助理字段未定义最终完成标记、任务状态、会话创建/切换、取消或回复所属请求 ID。云端 tasks/ACP 是另一组能力，不能据此声称本地助理具备同样语义。公开返回码包含 401/403、429、5xx，但未找到具体 QPS/账户配额。本项目不将空轮询或 HTTP 200 当作任务完成。依据：[Open API 接口](https://open.workbuddy.cn/docs/openapi)。

### 2. 应用资格与授权边界

官方流程要求开发者账号、应用注册/审核、用户 OAuth 授权；client_secret 不得放进分发客户端。第三方页列出硬件接入、积分兑换，API 准备说明另提 Buddy 应用。因此“纯本地开源桌面工具应选哪类应用”仍需平台确认。公开文档未给出该调用方向的无密钥公共客户端 PKCE 或 loopback 回调承诺；不能由 OAuth 2.1 名称自行推定。

另有 Windows/macOS 分享接入，但分享不等于可等待最终结果的 Agent Provider。第三方页 token 有效期说明与 API 示例存在差异；未来应读取实际 expires_in，不硬编码。依据：[第三方应用](https://open.workbuddy.cn/docs/third-party-app)。

### 3. 客户端能力不等于调用协议

官方助理指南说明助理使用专属工作目录和单一会话、保留历史；需要电脑开机且客户端运行。这使独立 workspace 隔离和同时发送任务成为需要特别验证的问题。相关行为应由获准 Open API 实测确认，不能照搬普通桌面任务的多会话能力。依据：[助理功能说明](https://www.workbuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Assistant)。

Windows 产品受到官方支持；安装指南没有承诺本机账号的开放平台资格或具体 Open API 最低版本。依据：[Windows 安装指南](https://www.workbuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Installation-Win-Guide)。

CodeBuddy Code 另有公开 CLI HTTP API，但它是 CodeBuddy Code 产品接口，不能用其文档为 WorkBuddy.exe 的私有端口背书。本阶段不切换产品，也不采用社区凭证代理。依据：[CodeBuddy Code HTTP API](https://www.codebuddy.ai/docs/cli/http-api)。

MCP 连接器是 WorkBuddy 调用外部工具的方向，不能用它的 OAuth 支持证明外部程序可无密钥控制 WorkBuddy。依据：[连接器文档](https://open.workbuddy.cn/docs/connector)。

## 本机只读调查

- 进程可执行文件：`<workbuddy-install-dir>\WorkBuddy.exe`，调查时发现 7 个同名进程。
- PE 元数据：ProductVersion 5.8.3.0、FileVersion 5.8.3；公司 Tencent Technology (Shenzhen) Company Limited。
- 安装根目录无 bin；当前 PATH 未发现 workbuddy 或 codebuddy 命令。仅检查安装根目录和 resources 第一层名称，未运行未知 CLI。
- resources 中可见 wb-guest-sdk 和 editor-sdk-supervisor 等名称，但没有据此认定为官方第三方控制入口；未反向分析 app.asar、内部 RPC 或监听端口。根目录 version 文本为 37.10.3-42，不用它覆盖 PE 产品版本。
- 未读取用户配置、账户类型、认证数据、消息历史或令牌。用户此前登录由用户陈述提供，本轮不独立验证登录身份、套餐或 scopes。
- 未找到“此安装提供某个公开本地 HTTP 服务”的证据；没有端口扫描。优先路线是已公开的 HTTPS Open API，经平台转达 PC 助理。

## 与现有 Provider 的映射（以下为本项目设计评估，尚未实现）

| 项目方法 | 最小设计 / 尚存约束 |
| --- | --- |
| connect | 注入合法授权提供器和 HTTP transport；检查所需 scopes、可用性；不从客户端文件发现凭证 |
| health_check | 授权有效且本地 online 才为 true；不发送模型任务 |
| create_session | 可创建项目内关联 ID，但不能称为 WorkBuddy 原生隔离会话；不得承诺 cwd 生效 |
| send_message / send_task | 一次提交后保存 message_id，轮询后续消息；结合本次随机关联标识及严格 JSON 验证，避免接收历史无关回复 |
| get_status | 区分本地适配器 READY/WAITING/TIMED_OUT 等状态与供应商未提供的任务终态，不能把“online”当作 COMPLETE |
| 增量与最终结果 | 可以在 Adapter 内轮询、累积、去重；AgentProvider 目前只返回最终 Result，不必为最小接入重写 Kernel |
| interrupt | 未证实远端取消；task_cancel=false。停止本地等待不等于停止远端任务；超时后不得自动再提交 |
| close | 关闭本项目 HTTP 资源，不终止 WorkBuddy、不注销用户账户 |
| capabilities | 实现之前全部 false。未来只有经证实的 review 能力可开启；persistent_session、streaming、task_cancel、任意文件访问均不凭产品介绍打开 |
| 错误处理 | 在 Adapter 内分类配置缺失、授权失败、权限不足、离线、限流、服务错误、协议错误、超时；仅保留白名单状态/错误码，复用已有 ProviderError 和安全诊断机制 |

当前 WorkBuddyAdapter 继承 UnconfiguredProvider：connect/send/create 均拒绝，health=false，status=NOT_CONFIGURED，close 无外部副作用。现有 cli 工作流明确选用 WorkBuddyMockAdapter。`is_mock=False` 的占位对象也不意味着 REAL，必须以真实任务验证为准。

此次仅修正过时的“未确认公开 API”类注释，并添加占位拒绝行为/Mock 标记的离线测试；不新增无依据的环境变量，不实现虚假的 OAuth、会话和配置成功状态。Mock Adapter、Provider 基类和 Kernel 均不改动。

## 未解决的准入与协议问题

1. **应用资格**：本地开源工具是否可获批需要的两个 scopes，适合哪种应用类型？用户现有个人/企业、国内/国际账号是否适用？本轮未获确认。
2. **授权部署**：不能把统一 client_secret 内置到开源客户端。候选是获准的服务端授权代理；若要求完全本地，需要平台明确支持公共客户端方案。未确认回调规则前不提供猜测的 localhost 地址。
3. **相关性与完成语义**：消息游标不等于专属回复关系。只靠提示中回显随机 ID 能帮助业务校验，但不等于供应商协议隔离；需要平台给出终态/关联字段或认可的方案。
4. **状态与取消**：缺少已核实的本地任务状态/取消协议。审批或 AskQuestion 不能自动代答；等待授权时应停下并提示用户。
5. **配额和兼容性**：精确限流、额度计费、版本下限、多设备路由、账号适用性仍需官方说明及后续受控验证。不能把分享功能的版本/企业条件套用到 Local Assistant。

## 用户现在只需做什么

先通过[开放平台](https://open.workbuddy.cn/)或[官方联系渠道](https://www.workbuddy.cn/docs/workbuddy/Contact)确认上面 1–3 项，并说明项目是独立本地开源应用，希望调用本人已登录 PC 助理。请反馈应用类型、资格、回调支持方式、回复关联/终态说明和额度限制等**非敏感信息**。无需发送 Key、client_secret、授权码、Token 或账户截图。

确认获准路线后，才由用户亲自注册/审核应用，配置平台批准的回调和最小两个 scopes；由用户在下一阶段明确同意后完成授权。现在不要求用户盲目注册硬件应用，也不自动打开授权页。

## V0.1.5 实施顺序与停止条件

1. 用官方答复锁定资格、授权部署和回复终态契约；若纯本地方案不被支持，保留 MOCK 并报告阻塞，不用私有接口兜底。
2. 只在 WorkBuddy 模块增加可注入 HTTP transport / 授权提供器与非敏感配置校验。非敏感参数包括获批 client_id、精确 redirect_uri、scope 集合、API 基址，以及项目自定总超时、轮询间隔、最大页数。这些项目参数不是声称存在同名官方环境变量。
3. 离线覆盖成功回复关联、无关消息排除、去重、401/403/429/5xx、缺字段、审批等待、总超时和取消本地等待。POST 结果不明确时不重发；GET 轮询有总时限及次数上限；限流停止或按已批准策略延迟读取，不重复创建任务。
4. 授权完成后先进行只读 online 检查；不读全部私人历史。经用户另行授权，仅提交一个无文件写入、无工具需求的短文本任务。
5. 获得与本次请求关联的最终合法回复后，才通过 Kernel 保存任务、消息、request/message ID 与白板 decision，并独立重读数据库验收。无法可靠确认最终回复时记录“已收到消息，完成未确认”，不得标记 REAL 完整接入。
6. 此最小接入通过后再讨论 WorkBuddy 审核角色与三方流程；不得直接重跑现有双 AI 验收。

当前具备 V0.1.5 **协议澄清和离线实现准备**条件，不具备立即执行真实最小接入验收的完整条件。
