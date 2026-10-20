# V0.1.3 双 AI 真实协作验证报告

## 验收结论

**整体 FAILED / 未完成验收**：DSH 真实规划成功，Codex 真实实现成功，TODO CLI 实际测试通过；DSH 独立审核任务出现 ProviderError，未获得有效 APPROVE 或 REQUEST_CHANGES。按用户要求立即停止，没有重跑、返工或额外模型调用。

基线 HEAD：479e433。开始时已有 V0.1.2 相关未提交修改，全部保留。此次没有提交、推送、重置、清理工作区或修改 DSH 安装目录；未运行以前的 DSH 单次验证脚本。没有重新申请 API Key、提取或复制私人凭证。

## 真实运行配置与阶段

DSH 使用官方 SDK 0.2.1rc2、自带 dsh.cmd、用户已有 .dsh home、独立 sdk profile、deepseek-account / deepseek-flash。启动前未检测到 DeepSeek Harness 桌面进程。Codex 使用现有官方 app-server Adapter 和 workspace-write 隔离目录。WorkBuddy 没有注册或调用，原有 MOCK Adapter 未修改。

项目 ID：909429deed4245999d473a928370c348。

| 阶段 | 任务 ID | 实际结果 |
| --- | --- | --- |
| DSH PLAN | fc7dafe937ad4b8299c541cc9eebff85 | 真实 PROPOSE；任务 COMPLETED |
| Codex IMPLEMENT | d3ba8800093a45a5ba0f3bf1de47813a | 真实 COMPLETE；因最终审核失败，任务仍处于 REVIEW，未标记验收完成 |
| DSH FINAL_REVIEW | 663544a72f994b48a13fd48983f2a883 | 任务 FAILED，ProviderError，无有效审核意见 |
| Codex REVISE / 二次审核 | 未创建 | 没有 REQUEST_CHANGES，因此未执行 |

本轮 DSH 规划能力 REAL，Codex 实现能力 REAL；DSH 审核能力本轮未通过。不能把先前的 REAL 标签或本次测试通过等同于完整协作 PASS。

## Blackboard 与证据

- 规划 decision ID：ab7de08a632e467f8717584638927b7a。
- 规划正文 SHA-256：cf39937630671c473cf4908641a40ae1f15c4a0859834166c341cd76a2099735。
- 规划保存到 decisions，真实 PROPOSE 保存到 messages；独立打开数据库验证两者内容一致，并记录 BLACKBOARD_VERIFIED 事件。
- 从数据库重新读取 decision，导出到隔离目录 blackboard-plan.json。Codex 任务要求读取该文件，其真实 COMPLETE 明确引用上述 decision ID；运行时验证导出未被修改，并记录 ENGINEER_PLAN_REFERENCE。此为文件交付与引用确认，不声称具备每次文件读取的操作系统审计记录。
- DSH 审核输入包含原始需求、Blackboard 快照、实际 todo.py、test_todo.py、test_runtime_contract.py、USAGE.md 和 tests-1.txt；没有只提交工程师总结。
- 审核输入完整快照保存到 review-evidence-1.json，且与持久化审核任务 description 中的证据一致。5 个文件的 SHA-256 已保存到 artifacts，运行结束后逐个核对全部匹配。
- 结束后数据库可独立只读打开，无残留 WAL；3 个任务、6 条消息、1 条 decision、5 个 artifacts、26 个 events 已持久化。失败任务和失败事件也可追溯。

证据目录（Git 忽略，不应提交私人运行数据）：

- `runs/v013-dual-real/summary.json`
- `runs/v013-dual-real/blackboard.sqlite`
- `runs/v013-dual-real/workspace/blackboard-plan.json`
- `runs/v013-dual-real/workspace/review-evidence-1.json`
- `runs/v013-dual-real/workspace/tests-1.txt`
- `runs/v013-dual-real/workspace/todo.py`、`test_todo.py`、`USAGE.md`

## TODO CLI 测试

真实 Codex 返回：已实现代码、测试和文档；其报告自行运行 10 项测试通过。运行时随后独立实际执行 `python -I -m unittest discover -v`，14 项通过，耗时 11.140 秒，退出码 0。

包含 Codex 编写的 10 项测试及运行时提供的 4 项独立契约测试。覆盖添加、列出、删除、JSON 持久化、稳定 ID、不复用 ID、空白输入与不存在 ID 拒绝、Unicode、异常存储保留、原子替换失败清理等。TODO CLI 的这些已测行为标记 PASS；不能扩展为所有可能输入或并发写入均安全。

## 调用控制

- 整体真实流程：仅 1 次。
- 应用层 DSH 任务尝试：2 次（规划、审核）。
- 应用层 Codex 任务尝试：1 次（实现）。
- 返工：0 次；应用层自动重试：0 次。
- 核心任务上限 5，DSH 最多 3 次，Codex 最多 2 次；仅当第一次审核返回 REQUEST_CHANGES 才允许一次返工。本轮错误路径没有触发该分支。
- 入口以固定运行目录的排他创建防止误重跑，不要删除该目录来绕过本次运行限制。
- SDK/服务端可能有内部重试，DSH 工具调用和模型内部轮次未独立计数；不能把应用层次数当作底层 HTTP/推理请求次数，也没有据此估算费用。

## 失败与已知限制

审核任务在 2026-10-19 12:48:10 UTC 记录 PROVIDER_FAILURE，类别 ProviderError；随后记录 DUAL_VALIDATION_FAILED。没有有效 APPROVE、REQUEST_CHANGES 或审核 decision，不能编造审核意见。

当前启动器仅保存异常类型，原 Adapter 对部分 SDK 错误作脱敏；本轮没有保存足以进一步分类的安全错误码。因此不能确定是响应格式不符合 Result、模型轮次未完成、运行时通信或服务端问题；也不能断言 DSH 完全没有生成任何文字。未为诊断重新调用模型或读取私人账户文件。后续应先增强白名单错误分类，再由用户授权新的有限审核验证。

summary 的审核阶段记录停留 STARTED，表示没有收到已验证的返回；应以数据库任务 FAILED 和 summary 总状态 FAILED 判断最终状态。实施任务保留 REVIEW，保留待审核语义，没有伪造完成。

首次审核失败使真实返工分支没有覆盖。新增离线测试只验证 Mock 拒绝、调用上限和异常不重试，不声称整个新流程所有分支已被测试。共享 home 的状态并发、凭证过期以及底层重试仍依赖官方运行时；本项目没有复制凭证或覆盖 desktop profile。

## 测试和 Git

- 真实流程前必要轻量测试：18 passed。
- 真实流程后完整既有回归及新增测试仅运行一次：62 passed，8.38 秒。包含原有 59 项（之前 56 是不含 3 项 E2E 的单元/集成计数）以及新增 3 项离线控制测试。
- 回归中的既有 E2E 使用 Mock，不是第二次真实模型流程，也未接入真实 WorkBuddy。
- 本轮新增文件：src/ai_team/orchestration/dual_real.py、scripts/dual_real_validation.py、tests/unit/test_dual_real.py、本报告。既有未提交修改保留。
- Git diff 检查通过；.env 与 runs/ 继续被忽略，无真实密钥、Token 或私人配置加入源码。HEAD 仍为 479e433；所有变更未提交、未推送。

下一步：先补充脱敏错误分类与离线失败分支测试，再单独请求一次有限审核调用的授权。本轮不继续消耗模型额度。
