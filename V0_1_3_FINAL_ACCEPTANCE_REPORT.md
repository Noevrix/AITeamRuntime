# V0.1.3 双 AI 真实协作最终验收报告

## 最终结论与范围

**双 AI 真实协作验证通过。** 已核实真实 DSH 规划 → Blackboard 持久化 → Codex 读取规划并实现 TODO CLI → 实际测试 → DSH 独立审核 APPROVE → 审核决策持久化之间的完整引用链。

这是**首次工作流失败后，通过独立审核入口完成的分阶段验收**，不是一次无人干预、连续运行的完整 E2E PASS。原始流程仍保留 FAILED 结论：其 IMPLEMENT 任务处于 REVIEW，首次 FINAL_REVIEW 任务处于 FAILED。本轮不修改历史数据库状态，不将失败调用改写成成功。

DSH：真实规划和独立审核均已验证 REAL。Codex：读取规划、实际实现已验证 REAL。WorkBuddy：仍为 MOCK，未接入、未调用；三方真实协作尚未验收。

本轮没有任何新的真实模型调用，没有重新实现或重新测试 TODO CLI，没有运行完整 E2E。仅只读复核运行证据、运行必要离线单元测试并创建本报告。

## A. 成功阶段与任务标识

| 阶段 | 标识 | 验证结果 |
| --- | --- | --- |
| 原项目 | 909429deed4245999d473a928370c348 | 真实规划、实现、测试的来源项目 |
| DSH PLAN | fc7dafe937ad4b8299c541cc9eebff85 | COMPLETED，PROPOSE，消息 mock=false |
| 规划 decision | ab7de08a632e467f8717584638927b7a | 与真实 PROPOSE 内容一致 |
| Codex IMPLEMENT | d3ba8800093a45a5ba0f3bf1de47813a | 返回真实 COMPLETE，确认上述规划 decision ID；历史任务仍为 REVIEW |
| 实际 TODO 测试 | 原项目 TEST_RESULT，关联 IMPLEMENT 任务 | 14 项通过，exit_code=0；日志 Ran 14 tests / OK |
| 独立审核项目 | ef50d7fb196641f1916d1e42882b22a8 | 新项目，显式引用原项目和产物 |
| DSH 独立审核 | 18e6faac47e7484083e0388b2a68c523 | COMPLETED，APPROVE，消息 mock=false |
| 审核 decision | 67051cfdf5fe4e0cabfacf4f94a98371 | 与 APPROVE 消息完全一致，独立只读复核通过 |

独立审核任务完成时间：2026-10-19 13:16:38.308072 UTC。

## 证据关联复核方法和结果

对两份 Blackboard SQLite 数据库分别使用只读 immutable 连接，确认无残留 WAL。没有启动 Provider 或访问账户凭证。

1. 原项目中找到 COMPLETED 的 PLAN 任务及 mock=false 的 PROPOSE 消息；内容与规划 decision 相同。规划 SHA-256 为 `cf39937630671c473cf4908641a40ae1f15c4a0859834166c341cd76a2099735`。
2. 原工作目录 `blackboard-plan.json` 的 decision 与数据库完全一致。Codex IMPLEMENT 任务描述要求读取该导出并返回 decision ID；真实 COMPLETE 消息明确引用该 ID。该证据证明任务交付和工程师引用确认，不冒充逐次文件读取的操作系统审计。
3. 新审核数据库的 source_references decision 与 REVIEW_REFERENCES 事件一致，显式包含原 project_id、plan_task_id、decision_id、规划 SHA-256 以及 5 个原 artifact_id、task_id、文件名和 SHA-256。
4. 五条产物引用均追溯到原 Codex IMPLEMENT 任务。当前历史文件字节的 SHA-256 与原数据库 artifacts、新审核引用逐一匹配；新输入文件中的对应文本与实际文件逐一相同。因此没有将另一份 TODO 程序或仅工程师总结交给 DSH。
5. 新任务 description 与 `workspace/review-input.json` 完全一致，该输入的 SHA-256 与新数据库 artifact 一致。输入 requirement 等于原项目 goal；plan_excerpt 逐字对应原真实规划第 2 节 CLI contract 和第 11 节 Acceptance checklist，并非生成摘要。
6. 输入包含完整 `todo.py`、`test_todo.py`、`test_runtime_contract.py`、`USAGE.md`、`tests-1.txt`，以及原始需求、规划节选和测试摘要。日志明确为 14 项通过，原 TEST_RESULT 事件关联同一 IMPLEMENT 任务、同一日志且 exit_code=0。
7. 新审核的任务、APPROVE 消息、decision 均属于用户提供的新 project_id。消息 mock=false；内容与 decision 相等。REVIEW_RESULT 事件同时引用审核 task_id、decision_id，其 diagnostic 与终端 summary 一致，finish_reason=completed。
8. 新审核数据库共有 1 个任务、2 条消息、2 条 decisions（来源引用、审核结果）、1 个输入 artifact、9 个事件、1 个 Provider、1 个 session。原、新项目 Provider 记录均非 Mock。

产物哈希核对表（均与原实现任务关联）：

| 文件 | SHA-256 |
| --- | --- |
| todo.py | 2545ca99b94379035c9660245b503039620e5384481a2eb726a9e3d8ec7ca7ec |
| test_todo.py | f4e54f9d0386bccdb9160d14f0561784aab157f47d14600f077dc3a0e4807571 |
| test_runtime_contract.py | fe0326f716794024ab9b6726b919125bb004b1464830076cc32ca370a8f25f11 |
| USAGE.md | 9cf3d93db3d3023dba9ef29f9013b8d610a8f11c0a5ef5586bb43c08b5171db5 |
| tests-1.txt | 56bf7913af556f697bdcfb38bae32d0019de32526e737ec0d543728777b52207 |

以上证据支持两项目间的产物关联与最终验收，不仅依赖 summary 的 APPROVE 或 blackboard_verified 字段。

## 实际功能、测试和审核内容

TODO CLI 支持添加、列出和删除任务，JSON 持久化、稳定正整数 ID、删除后不复用 ID、空白任务文本及未知删除 ID 拒绝。历史运行时实际执行 unittest，14 项通过，11.140 秒，其中 Codex 编写的 10 项测试及运行时提供的 4 项契约测试。当前文件哈希未变，本轮没有重新执行这些测试。

DSH 的真实审核摘要认可 argparse 调用形式、持久化、原子写入、稳定 ID、列表格式、错误退出码、标准库测试和使用文档。DSH 明确说明其读取了 14 项通过的测试证据，但没有重新运行测试；本报告不将它的审核当作新一次测试执行。

DSH 返回 APPROVE，同时留下三条非阻断性发现：

- 测试使用源码目录内的 TemporaryDirectory，需要该目录可写。
- JSON 存储校验较严格，会拒绝额外字段和空白文本。
- 同一数据文件的并发 CLI 写入没有串行化，可能丢失更新；USAGE.md 明确要求同一文件一次只运行一个实例。

本次通过范围是上述既定 TODO CLI 需求和双 AI 协作证据链，不包含并发写入安全、任意数据迁移或生产部署保证。没有收到 REQUEST_CHANGES，因此没有发起返工。

## B. 首次失败与后续成功

首次审核任务 `663544a72f994b48a13fd48983f2a883` 确实 FAILED。已保存会话证据及 V0.1.3.1 离线诊断确认：outputTokens=4096、finish_reason=max-tokens，只有 reasoning，没有最终文本；Adapter 在 JSON 解析前拒绝结果。

随后进行了脱敏诊断修复和独立审核入口准备。用户在之后执行独立审核：使用新项目、新会话，保留 max_tokens=4096，显式 reasoning_effort=off，减少重复输入，约束简短机器可解析结果。该独立调用成功，未重新运行规划、Codex 实现或旧完整工作流。

最新已持久化诊断：input_chars=17296、input_bytes=17320、response_chars=778、output_tokens=179、finish_reason=completed，application_attempts=1，blackboard_verified=true。与用户提供的 JSON 一致。

失败记录及准备阶段报告均保留原样，作为当时事实；本最终报告记录后续完成的验收，不回写历史状态。

## C. 调用与预算

| 范围 | DSH 应用层任务 | Codex 应用层任务 | 说明 |
| --- | --- | --- | --- |
| 首次 V0.1.3 流程 | 2 | 1 | 规划成功、审核失败；实现成功 |
| 后续独立审核 | 1 | 0 | APPROVE，4096 / off |
| 本次报告整理 | 0 | 0 | 仅离线核验及测试 |
| 本验收证据链合计 | 3 | 1 | 共 4 个任务尝试，含失败审核 |

原数据库 TURN_RESERVED 为 3 条，新数据库为 1 条，与各自 summary 的调用计数相符。没有审核意见驱动的 Codex 返工。更早的 DSH 单次规划探针不属于此条验收链，不计入上表；上表不是账户所有历史用量。

没有证据可精确确定 SDK、模型服务端内部的请求/重试次数，不能将 3 次 DSH 应用层任务写成 3 次底层 HTTP 请求，也不据此计算费用或宣称底层零重试。

## 本轮离线回归

仅运行 DSH 独立审核入口、Provider 诊断及 Adapter 的必要离线单元测试：**44 passed，2.03 秒**。使用合成数据/Fake SDK，不启动真实 Provider。

V0.1.3.2 的历史单元与集成回归为 90 passed，本轮没有重跑这 90 项，不将其写成本轮结果。没有运行完整 E2E、WorkBuddy 或 TODO 实现任务。

## 证据位置

原运行：

- `runs/v013-dual-real/blackboard.sqlite`
- `runs/v013-dual-real/summary.json`
- `runs/v013-dual-real/workspace/blackboard-plan.json`
- `runs/v013-dual-real/workspace/review-evidence-1.json`
- `runs/v013-dual-real/workspace/` 下上述 5 个已核验文件。

独立审核：

- `runs/v0132-dsh-review/blackboard.sqlite`
- `runs/v0132-dsh-review/summary.json`
- `runs/v0132-dsh-review/workspace/review-input.json`

运行目录仍由 Git 忽略；本报告只记录非敏感标识、摘要和哈希，不复制私人会话或凭证。

## Git 状态与下一阶段

HEAD 保持 `479e433`。本轮只新增本报告，所有已有未提交代码、测试、文档保持原样；未清理、重置、提交或推送。git diff --check 通过，.env 和 runs/ 仍被忽略。已检查 diff 和本轮新增内容，没有将真实密钥、Token、Cookie 或私人配置加入版本控制；没有访问凭证文件、修改安装目录。

**可以进入下一阶段 WorkBuddy 真实接入的调查与准备**，以官方程序化接口、独立授权边界和受控调用为前提。本轮没有接入 WorkBuddy，也没有授予未来模型调用的自动执行权限。当前双 AI 验收通过不等于三方真实协作或连续自动化 E2E 已通过；这些需要各自的后续验收。
