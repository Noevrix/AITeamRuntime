# AI Team Runtime V0.1 验收报告

日期：2026-10-19。结论：本地协作运行时 PoC 通过；真实 Codex 工程师 + DSH/WorkBuddy Mock 的完整流程已实际验证。

## 1. 完成内容

Provider 与 Agent 分离；角色、团队、项目和任务模型；确定性 Team Kernel；结构化消息；任务状态机；SQLite Blackboard；返工、委派、升级；官方 Codex app-server Adapter；DSH/WorkBuddy 明确降级；Rich CLI；TODO E2E；关键测试；Apache-2.0 许可证。

## 2. 项目目录

独立仓库 `AITeamRuntime/`，位于本次授权的本地协作工作区。绝对目录在交付消息中提供，公共仓库不记录私人用户目录。未在 DSH 安装目录开发，未修改两个客户端的安装文件。

## 3. Python

实际开发及测试：Python 3.14.6。项目声明支持 Python 3.11+；本轮未执行多版本矩阵。依赖为 pydantic、typer、rich，数据库使用标准库 sqlite3；测试使用 pytest 与 asyncio.run，无需 pytest-asyncio。

## 4. Codex 检测

检测到 codex-cli 0.153.4。官方 app-server 帮助、协议 schema 生成成功。受限执行环境最初出现 home 目录错误、初始化断开；正常权限下官方 `codex login status` 确认 ChatGPT 登录。随后真实 app-server 会话、实现和返工均成功。应用本身没有读取认证文件、提取令牌或操作 GUI。

## 5. DSH 检测

发现运行中的 Electron 客户端、dsh.cmd、Node/Python runtime 和 loopback 65000；CLI --help 成功。runtime 元数据显示 desktop 0.2.1-rc.2、Node 24.21.0、Python 3.12.14。官方 Python SDK 路径已确认，但当前开发解释器未安装 SDK，独立 SDK 授权未验证。因此本轮使用 Mock。详情见 docs/dsh-investigation.md。

## 6. WorkBuddy 检测

确认客户端运行、guest SDK 资源及 loopback 监听。没有将未文档化端口当作 API。查到官方 Open API，包含本地助理状态、消息、历史，需要注册开发者应用及 OAuth 授权。桌面已登录不等于本项目已获授权。本轮使用 Mock，详情见 docs/workbuddy-integration.md。

## 7. 真实 Adapter

CodexAdapter：官方 stdio JSON-RPC。connect、账户检查、create_session、send_task、close 已在真实混合 E2E 中使用；send_task 使用 send_message。resume_session、interrupt、异常状态已实现并通过模拟协议测试，未单独验证真实中断与恢复。仅声明完成消息消费，不声明流式 UI 能力。

## 8. Mock Adapter

DSHMockAdapter、WorkBuddyMockAdapter；离线演示另有 DemoEngineer。Mock 标签进入 Provider 信息和消息 metadata。DSHAdapter、WorkBuddyAdapter 返回 NOT_CONFIGURED，未伪装连接成功。Mock 审核是确定性检查，不是独立 AI 质量审核。

## 9. E2E 结果

两次成功演示：全 Mock，以及 Codex REAL + DSH MOCK + WorkBuddy MOCK。

真实混合运行依次完成 PLAN → IMPLEMENT → REVIEW → REVISE → REVIEW → FINAL_REVIEW，最终 ACCEPTED。6 个任务、18 条消息、1 次返工、6 次运行时调用，其中真实 Codex 2 次；耗时 113.013 秒。代码实现、测试和使用说明均已生成。

本地证据目录：`runs/d0b4df25231b46499b97b47c3a65c1e0/`，包含 summary.json、blackboard.sqlite、workspace/todo.py、test_todo.py、USAGE.md、两轮测试日志。该目录已排除 Git。

SQLite 实测：projects 1、teams 1、providers 3、agents 3、sessions 3、tasks 6、messages 18、events 54、artifacts 6、decisions 1。任务最终全部 COMPLETED。

## 10. 测试结果

运行时测试：20 passed，最后一轮 9.94 秒。涵盖状态转换、消息序列化和路由、Agent 注册、能力声明、Blackboard CRUD、深度/返工/调用限制、超时、Mock、Codex 模拟协议、失败处理及完整工作流。

真实 TODO 第一轮 11 tests OK（5.146 秒）；返工后第二轮 11 tests OK（4.926 秒）。其中 4 项为运行时提供的独立契约测试，7 项为 Codex 编写的测试。未将 Mock 输出文字当作测试通过证据。

CLI 帮助和项目打包元数据验证通过；未安装到全局 Python，未制作面向用户的安装程序。

## 11. 已知限制

- 单进程顺序 PoC；数据库记录与事件尚未组成完整原子事务，不支持生产级崩溃恢复或多调度器并发。
- 12 次调用、2 次返工、3 层委派有硬限制；限制统计运行时调用，并不等价于底层模型 token 或工具迭代限制。
- DSH/WorkBuddy 尚未真实接入，真实 AI 审核质量未验证。
- Codex 真实运行需要可访问官方登录环境的正常终端；嵌套受限沙箱可能无法初始化。
- 持久会话 ID 已保存，完整工作流断点恢复尚未实现。
- TODO 测试在独立目录由本机 Python 执行，不是用于运行任意不可信代码的安全沙箱。
- 模型消息和本地运行证据可能含项目内容，运行目录不应发布。公共文件检查未发现明显密钥或私人 home 路径；这不是专业安全审计。

## 12. 下一阶段

优先验证 Codex 真实中断/恢复；接入独立配置的 DSH 官方 SDK；申请并实现 WorkBuddy OAuth Open API；补充事务、恢复与供应商调用预算。暂不扩展 GUI、安装包或更多 Provider。

## 13. 启动命令

在项目目录的正常 PowerShell 终端执行：

```powershell
python -m pip install -e ".[test]"
ai-team doctor
ai-team demo --mode mock
ai-team demo --mode real
python -m pytest -q
```

mock 不调用模型。real 要求 Codex 可用，不允许自动降级。auto 仅在连接阶段失败时明确降级，真实任务执行失败不会被 Mock 成功掩盖。每次运行创建新的 runs 子目录。

无需安装包的启动方式：

```powershell
$env:PYTHONPATH = "src"
python -m ai_team.cli demo --mode mock
```

## 14. Git

已分阶段提交。验收代码提交：`58b9891af8dfd41bd560d7de85567aa0f031f2ed`。本报告作为后续文档提交，最终 HEAD 可由 `git rev-parse HEAD` 查询，避免报告自引用哈希。最终工作区状态在交付时再次核对。

## 15. GitHub 就绪情况

适合作为明确标注限制的 V0.1 PoC 推送。包含许可证、独立项目声明、忽略规则、环境示例、文档及测试；未包含客户端、模型、Cookie、API 密钥或私人登录信息。尚未配置远端，也未向 GitHub 发布。不是 Production Ready。
