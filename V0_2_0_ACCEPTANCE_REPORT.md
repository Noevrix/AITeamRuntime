# V0.2.0 — AI Team Console 验收报告

日期：2026-10-20。Git HEAD：479e433。工作区保留所有历史未提交修改，未提交、未推送。

## 实际交付

| 项目 | 状态 | 范围 |
| --- | --- | --- |
| Team Console | IMPLEMENTED | 可启动的 React 本地控制台、深色界面、六页导航 |
| Task Board | IMPLEMENTED | 读取、筛选、详情、关联记录、明确提交的草稿创建；没有工作流执行入口 |
| Agent Management | IMPLEMENTED | 三个 Provider 的历史证据、配置状态、能力、限制、失败记录和任务 |
| Workflow Timeline | IMPLEMENTED | 仅展示持久化事件、真实/Mock/未知标识、关联详情 |
| Blackboard Explorer | IMPLEMENTED | 项目、任务、消息、规划/决策、产物、受控详情与哈希核验 |
| Settings & Diagnostics | IMPLEMENTED | 数据目录、读取状态、配置存在性检查、固定报告入口 |
| Security Checks | PASS | 本报告列明的本地访问及脱敏离线测试通过；不等同于独立安全认证 |
| Offline Tests | 159 passed | 后端 153，前端 6；另有 1 项原生 DPAPI 测试排除 |
| Desktop Build | NOT_AVAILABLE | 无 Cargo；Tauri 外壳未编译，Windows WebView 未验收 |
| WorkBuddy | PARTIAL / AUTH_REQUIRED | 本轮未改变原有授权和协议阻塞 |
| Git | dirty | 保留历史修改及本轮新增文件 |

没有重新运行 DSH、Codex、WorkBuddy、OAuth 或完整 E2E。模型调用次数为 0。未将历史分阶段验收改写为连续工作流成功。

## 页面与数据

总览显示三个 Agent、各状态任务计数、最近工作流、事件和产物。计数包括历史真实与 Mock 记录，不代表实时运行监控。

任务页可按状态、Agent 筛选，展示创建/更新时间、阶段、输入输出消息、明确关联的决策、产物与失败事件。历史没有记录的重试数显示无记录；应用层次数来自 TURN_RESERVED 事件，不能当作 SDK 内部请求次数。

Agent 页面区分历史 REAL_VERIFIED、配置授权和当前在线 UNKNOWN。DSH 展示规划、独立审核及 4096 输出预算历史问题；Codex 展示代码、测试与返工接口；WorkBuddy 展示已有代码能力、部分实现和授权/终态协议限制，不执行在线探测。

时间线不从最终报告反推事件。消息只有显式 `metadata.mock=false` 才标注 REAL_OUTPUT，显式 true 标注 MOCK，其余 UNKNOWN。事件点击可查看实际记录及任务、决策引用。

Blackboard 原始消息、规划/决策和产物分开浏览；存在一条决策不自动等于验收通过。只根据任务 ID 和事件中的 decision_id 建立关联。历史跨运行引用保留原始内容，不猜测缺失关系。

设置页以固定报告入口提供版本测试结果，不声称后台自动执行测试；日志通过运行选择、任务和时间线浏览，不开放任意日志文件读取。

## 架构与本地 API

React → 回环 HTTP API → 原有 TaskManager / EventBus / SQLite。前端不访问 SQLite、不复制工作流逻辑；现有 Kernel、工作流和三个 Adapter 本轮均未修改。

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | /api/session | 控制台会话及写入防伪标识；不是 Provider 凭证 |
| GET | /api/overview | 历史总览 |
| GET | /api/agents | 配置存在性和历史证据 |
| GET | /api/diagnostics | 本地诊断及报告列表 |
| GET | /api/runs/{run} | 允许的 Blackboard 表快照 |
| GET | /api/runs/{run}/tasks/{task} | 任务及显式关联 |
| GET | /api/runs/{run}/artifacts/{artifact}/hash | 受控产物 SHA-256 |
| GET | /api/reports/{index} | 固定白名单报告 |
| POST | /api/drafts | 创建幂等草稿，PENDING / DRAFT |

历史数据库使用 SQLite `mode=ro` 和 `query_only`，不经会初始化表的 Database 构造器读取。只枚举 runs 下一级已知布局，不遍历 SDK home 或磁盘。

草稿沿用原有每运行一个 SQLite 的模式，明确提交后才使用 `runs/console/blackboard.sqlite`；复用 Database、TaskManager、EventBus、原有 Task 状态和事件，不复制历史数据库。request_id 同时作为 task_id，相同请求重发不创建第二条任务；同 ID 不同内容拒绝。

## 历史真实状态依据

DSH 的历史任务 `fc7dafe937ad4b8299c541cc9eebff85` 和 `18e6faac47e7484083e0388b2a68c523`；Codex 的历史任务 `d3ba8800093a45a5ba0f3bf1de47813a`，结合数据库 Agent/Provider 对应关系、显式真实消息标记和 PROPOSE / COMPLETE / APPROVE 消息确认。任务 ID 白名单来自已有验收，不能仅凭任意消息声称 REAL_VERIFIED。

浏览器实际读取了 `v013-dual-real`、`v0132-dsh-review` 等既有记录。DSH/Codex 历史真实状态与当前在线 UNKNOWN 分列。最新实际总览为 15 已完成、1 失败、0 运行中、0 待处理，包含历史 Mock 数据。

## 安全边界

- 仅监听 127.0.0.1；校验 Host、Origin 和 Fetch-Site，不启用 CORS。
- API 需要控制台随机会话 Cookie；写入额外要求同源 Origin 和防伪标识。Cookie 为 HttpOnly / SameSite=Strict。
- 无模型、OAuth、shell、任意文件或任意命令 API；关闭 UI 不调用取消接口。
- 对传入 ID、请求类型、字段和长度校验；资源必须来自数据库引用，限制 workspace 路径、扩展名、大小和符号链接。
- 不返回 sessions 表；provider 字段白名单；敏感字段、已知凭证格式及敏感赋值行脱敏；不回传异常原文和堆栈。
- React 使用文本渲染；CSP 限制来源；响应不缓存。
- .gitignore 增加 node_modules 和 Tauri target；已有 .env、runs、SQLite、dist 忽略继续有效。
- 本地同一用户进程不是强隔离边界；未实现多用户登录、TLS 或对本机恶意程序的防护。脱敏是防御措施，无法保证识别任意无标签秘密；不要把凭证写入任务正文。

## 测试与构建

1. 后端轻量：`tests/unit/test_console.py` — **15 passed**。
2. 前端轻量：`npm.cmd run test` — **6 passed**，jsdom / Mock fetch；六页、空状态、任务字段、真实/Mock标记、刷新不提交、明确草稿提交、错误不改状态。
3. 完整必要离线回归：`python -m pytest tests/unit tests/integration -q -k 'not test_dpapi_synthetic_memory_roundtrip' -p no:cacheprovider` — **153 passed, 1 deselected**。
4. 排除项为 Windows 原生 DPAPI 合成数据往返测试，沿用此前隔离范围；不能声称本轮该项通过。
5. `npm.cmd run build` — **PASS**。React/Vite 生产资源生成成功。锁文件固定版本；安装审计为 0 vulnerabilities。
6. 本地浏览器实际展示已有历史、任务、时间线、Blackboard 和配置诊断；草稿写入通过临时 SQLite 的自动化测试验证，没有向用户历史记录插入演示任务。
7. 测试覆盖只读数据库、显式关系、脱敏、路径拒绝、幂等草稿、Host/Origin/Cookie/防伪、未知接口拒绝、错误与刷新不改变任务。

初次 Windows HTTP 测试发现拒绝请求时未读请求体会触发连接重置，已修复为有界读取后拒绝，随后通过。沙箱运行 npm 缓存写入和读取历史 WAL 数据库曾遇权限限制；在当前普通用户上下文构建、启动后成功。后端轻量测试有不影响结果的 pytest 缓存权限警告，回归关闭缓存。

## 启动与桌面限制

当前已构建，PowerShell：

```powershell
Set-Location '<project-root>'
python .\scripts\team_console.py --port 8765
```

打开 <http://127.0.0.1:8765>。如端口已有本轮预览服务，直接打开即可。完整安装和开发命令见 [docs/console.md](docs/console.md)。

Tauri 2 最小工程已准备，无系统命令插件；需单独启动 Python 服务。当前缺少 Cargo，MSVC/WebView2 未验证，不标记桌面构建通过。依赖依据：[Tauri Windows prerequisites](https://v2.tauri.app/start/prerequisites/)、[Vite guide](https://vite.dev/guide/)。没有安装系统工具或制作安装包。

## 已知限制与后续

- 无安全工作流调度入口，因此只开放草稿与只读历史，未来执行需另行设计额度提示、授权、去重及取消协议。
- 快照每表最多最近 1000 行，截断时明确提示；长文本最多 32000 字符。暂不提供分页、全文检索、实时推送或跨表事务快照。
- 历史可能缺少关联或时间字段，保留无记录，不修补数据库。历史成功不证明当前凭证、额度或客户端在线。
- 产物核验仅允许登记在同一运行 workspace 内的文件；跨运行引用可读记录，但不任意读取外部路径。
- WorkBuddy 仍需官方确认消息关联和终态规则，并完成用户自己的应用/OAuth 配置；本版本没有推进实际授权和 Smoke Test。

## 修改及 Git 保护

本轮仅修改原有 `.gitignore`；新增 `console/` 前端与 Tauri 工程、`src/ai_team/console/`、`scripts/team_console.py`、`tests/unit/test_console.py`、`docs/console.md` 和本报告。

所有开始时已存在的受版本管理文件及未提交源文件已记录 SHA-256 基线，最终复核除预期的 .gitignore 外保持一致。以下清单包含历史修改，不能全部归因于本轮。最终清单和检查结果附后。

最终复核：91 个原有文件中仅 `.gitignore` 变化；19 个本轮新增文件。`git diff --check` 通过。新增文件的常见密钥/JWT/私钥特征扫描无命中，未读取私人凭证；这不替代上述访问边界。node_modules、dist、runs 和 .env 确认忽略。HEAD 未变。

全部未提交文件（M 为原有已跟踪修改，?? 为未跟踪）：

```text
 M .env.example
 M .gitignore
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
?? V0_2_0_ACCEPTANCE_REPORT.md
?? console/index.html
?? console/package-lock.json
?? console/package.json
?? console/src-tauri/Cargo.toml
?? console/src-tauri/build.rs
?? console/src-tauri/src/main.rs
?? console/src-tauri/tauri.conf.json
?? console/src/App.jsx
?? console/src/App.test.jsx
?? console/src/main.jsx
?? console/src/style.css
?? console/vite.config.js
?? docs/console.md
?? docs/dsh-desktop-reuse.md
?? docs/workbuddy-open-platform-questions.md
?? docs/workbuddy-real-setup.md
?? scripts/check_workbuddy_config.py
?? scripts/dsh_review_probe.py
?? scripts/dual_real_validation.py
?? scripts/team_console.py
?? scripts/workbuddy_auth.py
?? scripts/workbuddy_smoke_test.py
?? src/ai_team/console/__init__.py
?? src/ai_team/console/server.py
?? src/ai_team/console/service.py
?? src/ai_team/orchestration/dual_real.py
?? src/ai_team/providers/diagnostics.py
?? src/ai_team/providers/dsh/review_probe.py
?? src/ai_team/providers/workbuddy/auth.py
?? src/ai_team/providers/workbuddy/client.py
?? src/ai_team/providers/workbuddy/config.py
?? src/ai_team/providers/workbuddy/probe.py
?? src/ai_team/providers/workbuddy/store.py
?? tests/unit/test_console.py
?? tests/unit/test_dsh_review_probe.py
?? tests/unit/test_dual_real.py
?? tests/unit/test_provider_diagnostics.py
?? tests/unit/test_workbuddy_api.py
?? tests/unit/test_workbuddy_preparation.py
```
