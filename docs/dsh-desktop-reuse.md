# DSH 桌面账户配置复用调查

基线：479e433。此次仅调查、代码准备和离线测试；真实运行时启动、模型调用、完整 E2E 均为 0。不将 DSH 标记为 REAL。

## 本机证据与边界

- 安装内 runtime.json：桌面 0.2.1-rc.2；项目官方 Python SDK 0.2.1rc2。
- 安装自带 dsh.cmd 通过 Electron 的 Node 模式调用官方 desktop-host CLI，不是界面自动化。
- 在 `%USERPROFILE%\.dsh\profiles\desktop` 找到桌面 profile；bundle 为 dsh-base 与 dsh-web-app。用户级和系统级 DSH_HOME 均未设置，检查的进程命令行没有 home 覆盖标记。这与官方默认 home 规则一致；未读取进程环境或通过认证 Host 查询其实时 home，因此不将该推断冒充实时 Host 证明。
- 仅提取 profile YAML 的非敏感配置：默认 Provider 为 `deepseek-account`，模型 `deepseek-flash`。这是账户模型路由，不是开放平台 API Key 路由。未读取会话历史，不能据此确认任意已有会话的覆盖选择。用户报告桌面已正常回复；本轮没有独立验证账户授权有效性。
- 未打开 `.credentials.yaml`，未读取/提取 Cookie、Token、密码或 Key；未复制任何私人配置。调查日志和本文不保存账号身份信息。

## 为什么项目此前 NOT_CONFIGURED

| 配置 | 桌面默认 | 项目原有探针 |
| --- | --- | --- |
| home | 默认用户 `.dsh`（上述证据） | 每次新建 `runs/dsh-plan-*/dsh-home`，更早使用 `runs/dsh-home` |
| profile | desktop | sdk |
| Provider | deepseek-account | deepseek-official |
| 模型 | deepseek-flash | deepseek-v4-flash |
| 授权入口 | DSH 官方账户授权服务 | 启动环境 DEEPSEEK_API_KEY 检查 |

隔离 home 没有桌面已有账户状态，而且项目把 API Key 检测作为所有启动的前置条件。NOT_CONFIGURED 不能代表桌面账户模型不可用。`dsh_auth_configured` 和 auth 命令仍只检测原有 API Key 环境变量，不读取账户凭证。

## 官方接口与安全结论

已检查本机 app.asar 中相同版本的官方包 README 和 bundle patch（只读）：

- dsh-client-connection：已有 Host 支持 Remote/HTTP/WebSocket，但 API Peer 需要官方 `/connect` 授权交换。知道端口不足以获得访问权。当前 Python SDK 是独立 stdio 子进程接口，没有现成 attach Host 入口。本轮没有可用的、无需获取连接凭证的直接附着方案，因此未探测私有 RPC、提取启动 Token 或 Cookie。
- dsh-base 同时装配 deepseek-account-platform、credentials-local 和账户模型支持；dsh-sdk-app 叠加 SDK 服务，关闭生成会话标题及 HMR。SDK 可通过 provider/model 指定已装配路由。
- 桌面 profile 由桌面专属拥有；官方支持 CLI/桌面共享 home 中的产品数据，但 profile 独立。项目明确使用 sdk，拒绝 desktop profile，使用新会话，不恢复私人会话。
- credentials-local 的更新有跨进程锁。但这不等于全部共享状态都已验证并发安全。账户服务可能迁移状态、在 issuer 不匹配或授权被拒绝时删除失效授权。因此新运行时不是只读检查，首次试验建议先彻底退出桌面及其 Host，不并行启动多个 SDK 运行时，不做登出或设置更改。
- 账户授权由官方运行时在同一个 home 内解析，项目不读取、复制或转换凭证。能否在 SDK 模式成功推理仍需一次实测；账户有效性、额度和网络均未确认。无需现在申请新的 API Key，账户路径失败也不自动回退到 Key 路径。

在线官方参考（本机打包文档作为准确版本依据，在线 master 可能更新）：

- [Desktop profile 与共享产品数据](https://github.com/deepseek-ai/deepseek-harness/blob/master/apps/desktop/README.md)
- [Python SDK](https://github.com/deepseek-ai/deepseek-harness/blob/master/python/sdk/README.md)
- [账户授权服务](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/credentials/deepseek-account-platform/README.md)
- [凭证子系统](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/subsystems/credentials.md)

## 已准备的最小变更

DSHAdapter 增加显式 provider 选项，默认保持原有行为。账户路径默认模型 deepseek-flash，要求调用者明确提供已存在的 home；不自动发现桌面 home。runtime 对账户路径不再要求 DEEPSEEK_API_KEY，不声称授权已配置；由官方 SDK 处理真实授权错误。其他未知 Provider 和非 sdk profile 启动被拒绝。

一次规划探针新增 `--account-home`，仍调用现有 Adapter → TeamKernel → Blackboard，只有实际 completed、非 Mock、合法 PROPOSE 和数据库重新读取验证全部通过才输出 PASS。原 Test-DshPlan.ps1 保留作为 API Key 专用入口，账户复用不要运行这个隐藏输入脚本。

## 后续由用户主动执行一次验证（本轮未执行）

先保存桌面任务并彻底退出 DSH，确认没有该桌面的 Host 或其他 SDK 正在运行。若你的桌面实际设置了其他 DSH_HOME，请使用那个路径，勿复制其凭证文件。正常退出不会主动登出账户。

在项目根目录的 PowerShell 中执行，**会提交一次真实规划任务，可能消耗账户额度**：

```powershell
$previousDshBin = $env:AI_TEAM_DSH_BIN
try {
    $env:AI_TEAM_DSH_BIN = '<dsh-install-dir>\resources\runtime\cli\bin\dsh.cmd'
    python .\scripts\dsh_plan_probe.py --account-home (Join-Path $env:USERPROFILE '.dsh')
} finally {
    if ($null -eq $previousDshBin) { Remove-Item Env:AI_TEAM_DSH_BIN -ErrorAction SilentlyContinue }
    else { $env:AI_TEAM_DSH_BIN = $previousDshBin }
}
```

不输入 Key，不设置系统环境变量。SDK 可能创建/维护 home 下自己的 sdk profile 和共享产品状态，但不会由本项目覆盖 desktop profile。探针最多提交一个 PLAN，不自动重试，不调用 Codex 或 WorkBuddy；官方运行时内部可能有请求重试，不能承诺底层仅一次 HTTP 请求。

成功必须同时看到 status=PASS、model_result_verified=true、blackboard_verified=true、turns=1。只分享 summary.json 摘要，不分享原始会话、日志或私人配置。失败即停止；脱敏错误可能不能区分登录失效、网络或额度，需要后续针对性诊断。成功后才考虑受控的 Codex 读取计划验证。

## 验证记录

DSH 相关离线测试：37 passed（含新增 7 项），使用 Fake SDK，不证明真实账户可用。最初测试临时目录被环境权限阻止；改用工作区父目录的新临时目录后通过，未放宽文件权限。

单元与集成回归：56 passed，保留原有 49 个非 E2E 用例并新增 7 个；其余 3 个 E2E 本轮未运行。git diff --check 通过；.env 和 runs/ 仍被忽略。变更不包含密钥、私人配置或安装文件；未提交或推送。

变更文件：adapter.py、runtime.py、probe.py、scripts/dsh_plan_probe.py、两份 DSH 单元测试、本说明、授权指南及 V0.1.2 报告。WorkBuddy、工作流和配置检测函数未修改。
