# V0.1.2 授权准备阶段报告

## 追加：桌面账户复用准备（基线 479e433）

- 桌面默认 profile 配置确认是 deepseek-account / deepseek-flash；原项目 deepseek-official + 独立 home + API Key 前置检测不能复用这一授权路线。下文早期 API Key 结论仅适用于原路线。
- 已增加 Adapter 的显式账户路线和单次探针 --account-home；固定独立 sdk profile，不附着或修改 desktop profile。账户有效性由官方运行时判断，不读取或复制私人凭证。
- 已有 Host 接口需要官方连接授权；本轮未提取 Token/Cookie，因此采用官方 SDK 共享 home、独立 profile 的待验证方案。首次测试建议先退出桌面，避免未经验证的共享状态并发。
- DSH 相关离线测试 37 passed；单元与集成回归 56 passed（原有非 E2E 49 项及新增 7 项）。保留原测试，未执行其余 3 项 E2E，未声称完整 59 项已通过。
- 真实模型调用 0 次，真实 SDK 启动 0 次，完整 E2E 0 次。Codex：沿用之前 REAL 验收、本轮未调用；DSH：账户复用未验证，默认工作流仍 MOCK；WorkBuddy：MOCK，未修改。
- 安装目录和桌面设置未修改；不要求重新申请 Key。修改文件与后续一次验证命令见 [调查报告](docs/dsh-desktop-reuse.md)。本轮代码尚未提交，未推送 GitHub。

以下为此前阶段历史记录。

基线：b3f6f0f。开始时工作区干净。本次仅完成用户指定的第一至第五部分，不代表真实调用验收或完整 V0.1.2 发布；未更改项目包版本。

## 已完成

- 核对现有 DSH Adapter、配置、相关测试及 V0.1.1 报告。
- 根据官方 SDK 文档、已安装 0.2.1rc2 SDK 配置及启动代码，确认路由 deepseek-official、授权变量 DEEPSEEK_API_KEY 与子进程环境继承方式。
- 官方申请入口为 https://platform.deepseek.com/api_keys（由官方 API 入门文档链接）；需要 DeepSeek 开放平台 API Key，不使用桌面登录凭证。
- 创建 docs/dsh-auth-setup.md，说明配置、环境继承、重启、无模型验证及常见错误。
- 新增 dsh_auth_configured：只返回布尔值；不返回值、长度、指纹或账户信息。
- 新增离线命令 python -m ai_team.providers.dsh.auth：仅输出 CONFIGURED / NOT_CONFIGURED，退出码分别为 0 / 1。
- 真实 SDK 创建入口缺少环境授权时立即失败，不启动运行时。Fake SDK 测试仍然完全离线。
- .env 已被 git check-ignore 确认为忽略；未被跟踪。没有读取真实 .env。示例只添加注释占位符。

## 验证结果

相关测试先运行：25 passed，0.20 秒。

完整测试随后运行：47 passed，7.32 秒。保留原有 35 项，新增 12 个配置检测测试用例；所有凭证测试值均为合成字符串。

实际离线检测：NOT_CONFIGURED，退出码 1，这是预期的缺失状态，不是连接成功。

本轮 DSH 运行时启动 0 次、真实模型调用 0 次、真实 E2E 0 次。仅完整测试套件包含既有 Mock 工作流。未读取私人认证文件、修改安装目录或设置用户级/系统级环境变量。

## 当前状态

| 项目 | 状态 |
| --- | --- |
| 授权准备与离线检查 | PASS |
| Kernel / SQLite 回归 | PASS |
| Codex | REAL 能力沿用此前结果，本轮未重新推理 |
| DSH | 当前环境 NOT_CONFIGURED；默认 MOCK，未升级为 REAL |
| WorkBuddy | MOCK，未修改 |
| 真实协作验证 | 等待用户本地配置后再执行 |

CONFIGURED 只证明环境变量非空且不是示例占位符，不验证密钥真伪、权限、余额或模型可用性。为避免读取私人凭证库，本项目这次的预检查只支持启动环境变量路径，不探测官方 credential service 存储。

## 修改范围

- src/ai_team/config.py
- src/ai_team/providers/dsh/runtime.py
- src/ai_team/providers/dsh/auth.py
- tests/unit/test_dsh_auth.py
- .env.example
- docs/dsh-auth-setup.md
- V0_1_2_ACCEPTANCE_REPORT.md

未更改现有 workflow、Codex、WorkBuddy 或模型选择。

## 暂停点

按用户要求停在第五部分。用户在本地通过隐藏输入设置 DEEPSEEK_API_KEY，运行离线检查，只需报告状态，不发送密钥。已经打开的桌面任务不自动继承另一个终端的环境；后续执行必须使用能继承该变量的上下文。

用户确认配置完成后才执行一次最小 DSH PLAN；成功后验证 Blackboard 写入和 Codex 读取计划，最后决定是否需要完整 E2E。真实调用成功前不改变 DSH 标记。

检查补丁和测试后新增提交，不覆盖既有历史，不推送 GitHub。提交哈希见交付消息或 git log -1。

## 后续补充：一次性本地验证脚本已准备

根据后续确认的流程，新增 scripts/Test-DshPlan.ps1 与 scripts/dsh_plan_probe.py，调用 src/ai_team/providers/dsh/probe.py。脚本隐藏输入 API Key，临时设置进程环境并在结束时恢复，通过现有 DSHAdapter 提交一次 PLAN，再独立重开 SQLite 验证 messages、decisions 和任务完成状态。不启动 Codex 或完整三 Agent 工作流，不自动重试。

新增 tests/unit/test_dsh_probe.py：5 项 Fake SDK 测试通过，验证调用链、单次提交、落库及失败无重试。随后完整测试 52 passed（8.18 秒）。Python 本地依赖预检和 PowerShell 语法检查通过，未运行隐藏输入脚本，也未发起真实模型调用。

授权指南已补充运行命令、验收标准及可分享的摘要格式。当前仍等待用户在自己的 PowerShell 中手动运行一次；真实 DSH 模型状态保持未验证，不把模拟测试当作联调成功。
