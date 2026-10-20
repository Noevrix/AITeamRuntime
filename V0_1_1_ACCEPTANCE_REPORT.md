# AI Team Runtime V0.1.1 验收报告

日期：2026-10-19。基线：`df67739`，开始时工作区干净。

结论：真实 DSH Adapter 已实现，官方 SDK/CLI 传输验证通过；**DSH 模型规划未成功，真实双 AI 协作尚未通过验收**。阻塞是独立运行时缺少授权 API key，默认继续使用 DSH Mock，不影响原有运行入口。

## DSH 接入方式与实测证据

- 只读检查确认 desktop/CLI 0.2.1-rc.2，Node 24.21.0、附带 Python 3.12.14；客户端运行，loopback 65000 存在但未调用未文档化接口。
- 同版本官方 Python SDK 0.2.1rc2 隔离安装到已忽略的 runs/dsh-sdk，使用公开 dsh_bin 选项调用现有 dsh.cmd，以 sdk profile 和 stdio JSON-RPC 通信。
- 使用项目 runs 下新建的独立 DSH home，不修改安装目录、桌面 profile，不读取或提取桌面 Token、Cookie、密码或私人凭证。
- 一次真实规划探测：初始化、工作目录 RPC 成功；规划返回 finish_reason=error，回答为空。仅检查该次新生成的隔离会话日志，确认 provider route deepseek-official 没有 API key。未伪造 PROPOSE 或成功结果。
- 新 DSHAdapter 另外执行一次无推理连接检查：connect、health_check、session handle、READY 状态通过。READY 仅表示运行时连接就绪，不表示模型授权通过。
- 本地证据：runs/dsh-probe-v011/probe.json、adapter-transport.json，均不提交。

## Provider 状态

| Provider | 运行状态 | 本轮验证范围 |
| --- | --- | --- |
| Codex | REAL，沿用 V0.1 验证 | Adapter 未改动；本轮没有真实推理调用 |
| DSH | 模型 UNAVAILABLE；默认 MOCK | 官方传输 REAL，通过；模型规划因缺少授权失败 |
| WorkBuddy | MOCK | Adapter 未改动 |

## 实现内容

DSHAdapter 支持连接、健康检查、独立会话标识、恢复接口、任务提交、结构化结果、状态和关闭。限制请求超时、输出 token 上限，超时或取消时关闭 SDK runtime；拒绝错误完成原因、会话不匹配、无效 JSON、空内容、伪 Mock 标签及阶段不匹配的决策。没有声称支持 per-session interrupt 或 streaming。

CLI 新增 --dsh-mode mock|real，默认为 mock。原命令 --mode real 继续使用 Codex REAL + DSH MOCK。显式 DSH real 失败会报错，不冒充成功。未自动重试模型。

DSH PLAN 结果沿用现有消息、decision 和任务 description 传递给工程师。FINAL_REVIEW 现在通过持久化任务接收实际源码、测试源码、使用说明、测试日志、测试事件和 Blackboard；文件哈希在最终审核前入库。证据体积上限 128 KB，缺失证据拒绝审核。

## 测试与额度

1. 先运行相关 unit/integration：32 passed，1.08 秒。
2. 再运行完整测试：35 passed，7.34 秒。原有 20 项全部保留，新增 15 项；包含一次完整 Mock E2E，不调用模型。
3. CLI demo --help 验证新增选项。
4. 真实 DSH 规划提交 1 次（失败）；额外无推理传输检查 1 次；Codex 模型调用 0 次。
5. 完整真实 E2E 0 次。授权失败后不浪费模型额度继续联调，因此不能报告 DSH REAL + Codex REAL 联调成功。

新增测试均使用 Fake SDK，覆盖连接、会话、恢复接口、失败响应、非法 JSON、阶段决策、超时取消、诊断脱敏、计划落库和证据传递；不将模拟测试视为真实模型验证。

## 修改文件清单

- .env.example
- pyproject.toml（版本 0.1.1、可选 SDK 依赖）
- src/ai_team/providers/dsh/adapter.py
- src/ai_team/providers/dsh/runtime.py
- src/ai_team/cli.py
- src/ai_team/orchestration/workflow.py
- tests/unit/test_dsh_adapter.py
- tests/unit/test_review_evidence.py
- tests/e2e/test_workflow.py
- docs/dsh-investigation.md
- README.md
- V0_1_1_ACCEPTANCE_REPORT.md

## 已知问题和下一步

优先通过正常环境变量或 DSH 官方配置流程，为独立 home 提供合法的 DEEPSEEK_API_KEY。项目没有提供密钥，也不会提取桌面登录凭证。配置后先验证一次真实规划，再运行一次 --mode real --dsh-mode real 验证双 AI 协作。

真实 session resume、断线恢复与模型运行期间取消尚未单独联调；目前对应验证仅限 Fake SDK。SDK 的文件/执行工具仍然存在，“不使用工具”是提示约束而非系统沙箱。运行时异步包装依赖官方 SDK 的有界关闭行为。V0.1 的单进程及数据库非原子事务限制继续存在。

## 启动与回退

在现有项目目录执行：

```powershell
$env:PYTHONPATH = "src"
python -m ai_team.cli demo --mode real
# DSH 正式授权配置完成后，才显式启用：
python -m ai_team.cli demo --mode real --dsh-mode real
python -m pytest -q
```

可选 SDK 安装和环境配置见 README；本轮隔离安装不改变全局 Python。

## Git 与公开范围

仅在检查 diff、测试通过后新增提交，不覆盖 df67739 及旧提交；最终提交哈希见交付消息或 git log -1。未修改 WorkBuddy Adapter，未推送 GitHub。runs 中 SDK 包、临时脚本、运行时配置、会话和日志全部排除提交；公共补丁不含密钥、Token 或私人配置。
