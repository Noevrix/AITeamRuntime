# DSH 模型授权配置（V0.1.2 准备阶段）

## 桌面账户复用调查更新（基线 479e433）

本机桌面 profile 的默认路由实际是 `deepseek-account` / `deepseek-flash`。
下文 API Key 要求、隐藏输入 PowerShell 脚本和 CONFIGURED 检测**仅适用于原有 `deepseek-official` 路径**；不能用于判断账户模型是否可用。Adapter 现在支持显式选择账户路由，未进行真实调用验证。
优先参阅 [桌面配置复用调查及单次验证方法](dsh-desktop-reuse.md)，无需现在申请新 Key。

本指南只配置和离线检查授权。当前不要启动完整 E2E；配置完成后，再单独批准一次最小规划验证。不要向聊天发送密钥、截图或包含密钥的终端输出。

## 新增：本地一次性真实规划验证脚本

按照后续确认的流程，现在已提供脚本。**运行下面这条命令会提交真实规划任务，可能产生 API 费用**；仅在你准备好自己的合法 Key 后，在自己的 PowerShell 中执行一次：

```powershell
Set-Location '<project-root>'
& '.\scripts\Test-DshPlan.ps1'
```

支持 Windows PowerShell 5.1 和 PowerShell 7。脚本先检查本地依赖，然后通过隐藏输入提示读取 Key；仅在当前进程环境临时设置，结束后恢复原环境。Key 不作为命令行参数，也不写入文件。可用 `-Python` 指定 Python 可执行文件，`-DshBin` 指定官方 CLI；默认优先使用已配置的 CLI，其次使用本机已知的安装位置。

该脚本调用 `scripts/dsh_plan_probe.py` → `run_probe` → `TeamKernel.execute` → **现有 DSHAdapter.send_task** → 官方 SDK。它不会调用 Codex，不导入 Mock Adapter，不运行 ThreeAgentWorkflow。只提交一个 PLAN，最多一次运行时调用，超时后停止，不自动重试；SDK/服务端内部请求次数不能由此保证恰好为一。

每次使用新的隔离 home 和工作目录。成功标准同时包含：Adapter 验证 completed、非空 JSON PROPOSE、非 Mock；规划消息及 decision 写入 SQLite；独立重新打开数据库后内容一致、任务 COMPLETED。仅连接成功或 CONFIGURED 不会产生 PASS。

终端只输出可分享的 JSON 摘要：status、phase、错误类别、验证布尔值、调用次数与本地证据目录名，不输出模型全文或 SDK 原始错误。只需反馈这个摘要即可。实际计划保存在 `runs/dsh-plan-*/blackboard.sqlite` 的 messages/decisions 中，摘要另存 summary.json；整个 runs 已被 Git 忽略。原始运行时会话属于本地资料，不要直接发送或发布。

失败时保留脱敏摘要并停止。`MODEL_TURN_FAILED` 表示已提交但未获得成功回答，可能需要进一步确认授权/额度/网络，不能凭这个类别直接断定原因；`INVALID_MODEL_JSON` 表示结果格式不符合约定。成功后再单独安排 Codex 读取计划，不在此脚本中继续联调。

当前脚本只经过模拟 SDK 测试、依赖预检及 PowerShell 语法检查。尚未进行真实规划验证，不据此将 DSH 标记为 REAL。

## 准确的 Provider 与授权入口

原有 Adapter 默认使用 Provider 路由 `deepseek-official`，默认请求模型 ID 为 `deepseek-v4-flash`。当前安装及上轮探测使用 DSH CLI 0.2.1-rc.2 / Python SDK 0.2.1rc2。

需要 **DeepSeek 开放平台 API Key**，从官方 [API Keys 页面](https://platform.deepseek.com/api_keys) 登录并创建。入口来自 [官方 API 入门文档](https://api-docs.deepseek.com/)。这不是 ChatGPT/OpenAI 的密钥，也不是 DSH 桌面 Cookie 或登录 Token。API 账户的授权及可用额度需要独立确认，桌面登录不作授权证明。

当前官方 API 文档说明旧模型名 deepseek-v4-flash 仍被接受，服务端映射到现行 Flash 模型。本次不更改项目模型选择，也不声称已经验证实际服务端模型。

## 官方支持与本项目采用的方法

[官方 DSH Python SDK 文档](https://github.com/deepseek-ai/deepseek-harness/blob/master/python/sdk/README.md) 支持：

- 启动环境中的 `DEEPSEEK_API_KEY`。
- SDK 的 `api_key` 参数，内部会设置子进程的同名环境变量；本项目不提供密钥参数入口，避免它进入配置对象或日志。
- SDK 支持 `DEEPSEEK_BASE_URL` / `base_url`，但本次官方服务接入不需要自定义端点。不要为解决授权错误随意改成第三方地址。
- SDK 要求明确的 `DSH_HOME`；它是运行时状态目录，不能代替 API Key。

上轮官方运行时错误也提示可以通过官方凭证服务设置 Key。本项目不会探测该服务的私人存储，不能离线确认那里是否配置成功，也不提供猜测的凭证文件路径或命令。**本次受支持的可检查路径是启动环境变量。** 即使另一个客户端已存储凭证，本项目仍要求自己的启动环境包含上述变量。

本项目不自动加载 `.env`。仅创建 `.env` 文件不会使检测通过；不要把真实 Key 写到源码、README、日志或测试报告中。`.env` 已被 Git 忽略，`.env.example` 只有注释和占位符。

## 安全配置：只作用于当前终端

打开你自己的正常 PowerShell 终端，进入项目目录。不要把真实 Key 写在命令行字面量中，避免留在历史记录。以下命令由你手动执行，提示输入时内容被遮挡。

**PowerShell 7.1+：**

```powershell
Set-Location '<project-root>'
$env:DEEPSEEK_API_KEY = Read-Host '在本地输入 DeepSeek API Key（不发送到聊天）' -MaskInput
$env:DSH_HOME = Join-Path (Get-Location) 'runs/dsh-home'
$env:AI_TEAM_DSH_BIN = '<dsh-install-dir>\resources\runtime\cli\bin\dsh.cmd'
$env:PYTHONPATH = 'src'
python -m ai_team.providers.dsh.auth
```

**Windows PowerShell 5.1** 没有 `-MaskInput`，将第二行替换为：

```powershell
$dshSecureInput = Read-Host '在本地输入 DeepSeek API Key（不发送到聊天）' -AsSecureString
try {
    $env:DEEPSEEK_API_KEY = (New-Object System.Net.NetworkCredential('', $dshSecureInput)).Password
} finally {
    $dshSecureInput.Dispose()
    Remove-Variable dshSecureInput
}
```

这些步骤只设置当前 PowerShell 的进程环境，不写用户级或系统级环境变量。后续 DSH 子进程必须能继承此终端环境。关闭终端后，此次设置消失；不要通过打印变量来检查。

## 离线验证：不启动 DSH、不请求模型

```powershell
python -m ai_team.providers.dsh.auth
```

只会输出下面之一：

- `CONFIGURED`（退出码 0）：启动环境中变量非空且不是示例占位符。
- `NOT_CONFIGURED`（退出码 1）：未设置、为空白或仍为示例占位符。

检测不会输出 Key、前后缀、长度、指纹、目录或账户信息，不读取 `.env`、桌面文件或凭证库，不联网。`CONFIGURED` **不能证明密钥真实有效、额度充足或模型可用**；这些只能在你确认后的一次真实请求中验证。真实 SDK 创建入口也有同样的缺失检查，缺失时直接 NOT_CONFIGURED，不启动运行时。

## 是否需要重启

需要重新启动 DSH SDK 运行时：已启动的子进程不会收到父终端后来更改的环境变量。停止旧运行时后，从设置过变量的同一个终端重新启动即可，不需要重启整个 Windows，也不需要重启正在使用的 DSH 桌面客户端。

已经打开的 Codex 桌面任务或另一个终端也不会自动继承这些变量。配置后可以只回复“已配置，检测为 CONFIGURED”，不要贴 Key。下一步若由代理执行，需要它运行在能继承该环境的执行上下文中；否则由你在这个终端执行之后提供的一次性验证命令。不要假设给本终端设置变量后，当前桌面任务立即获得了授权。

## 启动环境与后续验证顺序

V0.1.1 的 SDK 隔离安装在忽略目录 `runs/dsh-sdk`。本轮离线检测不需要 SDK。后续实际调用如沿用该隔离安装，可在同一终端设置：

```powershell
$env:PYTHONPATH = 'src;runs/dsh-sdk'
```

也可在项目虚拟环境安装声明的可选 DSH 依赖。本轮无需安装或启动任何新服务。

授权配置后按顺序：一次最小 DSH PLAN → 检查真实非空结构化结果及完成原因 → 保存 Blackboard → Codex 读取该计划完成简单任务。之后再决定是否需要完整 E2E。不要现在运行 `demo --mode real --dsh-mode real`，它会启动完整工作流。

完成验证或不再需要时，关闭授权终端；也可在停止相关运行时后清除当前终端变量：

```powershell
Remove-Item Env:DEEPSEEK_API_KEY -ErrorAction SilentlyContinue
```

## 常见问题

| 情况 | 处理 |
| --- | --- |
| NOT_CONFIGURED | 在执行检测的同一终端设置准确变量名；检查是否仍是占位符，不要打印值。 |
| .env 中有 Key，但检测失败 | 本项目不自动加载 .env，按上述隐藏输入方式设置进程环境。 |
| 已登录 DSH，但模型无授权 | 客户端登录与独立 SDK API 授权不同；使用开放平台 API Key。 |
| CONFIGURED，但服务端拒绝 | 检测只验证存在性；检查官方平台中的密钥状态及账户情况，不要循环重试。 |
| 额度、限流、网络或模型错误 | 在第一次真实请求失败后记录不含密钥的错误类别，停止重试，再查官方平台/网络设置。 |
| 当前终端通过，代理仍未配置 | 两者环境不共享；在同一授权终端执行后续验证，或从该环境启动执行上下文。 |
| SDK unavailable | 检测不依赖 SDK；实际调用时才使用项目可选依赖或已有隔离安装。 |

本指南核对了已安装 SDK 的配置字段与启动环境继承代码，没有打开任何私人认证文件。本轮到授权准备为止，DSH 仍不标记为 REAL。
