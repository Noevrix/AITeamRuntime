# V0.1.5 WorkBuddy 官方接口实现与安全启动

本版本实现了可调用的 HTTP/OAuth 客户端和独立消息观察工具，**不是已验收的真实 Reviewer**。正式任务完成仍受官方协议缺口阻塞。安装目录 `<workbuddy-install-dir>` 不作为授权来源，也不需要修改或退出客户端；未来执行在线查询时应保持 WorkBuddy 运行、联网，并暂停其他本地助理任务，避免单会话串扰。

## 实现边界

官方依据：[Open API](https://open.workbuddy.cn/docs/openapi)、[第三方应用](https://open.workbuddy.cn/docs/third-party-app)。具体端点和权限见 [V0.1.4 调查](workbuddy-integration.md)，本轮重新核对。

分层：`WorkBuddyAdapter → WorkBuddyClient → TokenProvider → 官方 HTTPS API`。OAuth 授权码和刷新逻辑独立在 `auth.py`，用于获准的可信部署；不会从桌面客户端发现或导入凭证。请求禁止重定向、不使用环境代理、限制响应体、没有自动 HTTP 重试。企业代理场景目前不支持，不建议关闭 TLS 或其他安全措施。

能力事实：

- 可以检查 online、提交一次 text 消息、按提交的 message_id 读取后续消息。每次读取有超时，观察整体也有时限及页数限制。
- 本地 handle 只作项目内关联，不代表远端 session，也不承诺 workspace 路由。
- 没有已确认的 Local Assistant 最终完成/回复所属请求字段。即使 metadata 出现 completed、文本为 APPROVE，也不接受为官方终态。不能照搬云端 tasks 的状态。
- `send_task/send_message` 在远端提交前返回 `COMPLETION_UNSUPPORTED`；capabilities 全部 false。独立 `observe_once` 是诊断出口，收到正确 nonce 回显也仅返回 `COMPLETION_UNCONFIRMED`。
- `interrupt` 明确返回 `CANCEL_UNSUPPORTED`；`cancel_wait` 仅停止本地等待，不能取消远端任务。超时/取消后底层线程中的单次 HTTP 操作可能仍结束于其网络超时，绝不因此再次提交任务。

## 配置和凭证边界

以下是**本项目定义**的环境变量，不是声称 WorkBuddy 桌面程序支持这些变量：

| 名称 | 内容 |
| --- | --- |
| AI_TEAM_WORKBUDDY_CLIENT_ID | 用户获批应用的公开 ID |
| AI_TEAM_WORKBUDDY_REDIRECT_URI | 注册的精确 HTTPS 回调 URL；不能自行猜测 localhost |
| AI_TEAM_WORKBUDDY_DEPLOYMENT_APPROVED | 默认未设置；只有官方确认应用类型、部署和权限之后才由用户设置为 1 |

所需最小权限为 `user.localassistant.readable` 和 `user.localassistant.invokable`。模板仅占位，不自动加载 .env。此配置标志是操作者声明，不是平台资格证明。

凭证存储为 `%LOCALAPPDATA%\AITeamRuntime\workbuddy-oauth\` 内本应用新建的 `token.dpapi`/`pending.dpapi`，不接触 WorkBuddy 目录。采用当前 Windows 用户 DPAPI，加密后才写盘，临时文件也是密文；不使用机器级所有用户解密模式，无新增依赖。依据：[Microsoft CryptProtectData](https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata)。同用户恶意进程仍在 DPAPI 的信任边界内；Python 内存中的所有副本不能保证清零。

配置检查只查询文件存在，不解密。显式在线/发送入口才加载本应用经合法授权保存的 token。401 后当前 provider 失效，不刷新并重放任务。已过期 token 在桌面侧返回 AUTH_REQUIRED；可信 OAuth 组件支持刷新和旋转后原子保存，不能把应用密钥下发到普通桌面客户端。跨主机授权代理与 token 交付尚未实现，不能把本工具当作完整 OAuth 服务端产品。

## 现在可直接运行：无网络配置检查

```powershell
Set-Location -LiteralPath '<project-root>'
python .\scripts\check_workbuddy_config.py
python .\scripts\workbuddy_smoke_test.py
```

预期当前返回 NOT_CONFIGURED，退出码 2；这不是产品测试失败，也不表示客户端未登录。默认入口不会发 HTTP 请求。

## 必须先由用户完成的事项

通过 [开放平台](https://open.workbuddy.cn/)确认本地开源应用的合适应用类型、账号资格、两个 scopes 和可信授权部署；在获准后亲自注册/审核，配置精确回调。不要把公开客户端里的共享 client_secret 当作安全实现；不要盲目选择硬件应用类型。

同时向官方确认本地助手的请求关联与终态契约。它是正式 Reviewer 和三 Agent 验收的独立前置条件，OAuth 完成不能解除这个阻塞。

用户只需反馈获批方案的非敏感说明，不要发送 client_secret、Token、授权码、Cookie 或回调完整地址到聊天中。

## 获准可信 Windows OAuth 部署上的操作（现在不要执行）

这里只提供手动操作入口，不创建回调监听、不自动打开浏览器、不执行授权。必须先部署平台批准的 HTTPS 回调接收端；以下操作应由其操作者在可信环境执行。纯本地电脑是否可担任该角色仍需平台确认。

设置三个非敏感变量为获批真实值后：

```powershell
python .\scripts\workbuddy_auth.py begin --approved-trusted-server
# 操作者手动访问输出的授权 URL，并在官方页面亲自同意。
python .\scripts\workbuddy_auth.py exchange --approved-trusted-server
# 后续仅在可信组件需要更新令牌时：
python .\scripts\workbuddy_auth.py refresh --approved-trusted-server
```

密钥及回调地址通过隐藏提示输入，不放入命令行历史。exchange 检查回调 origin/path、注册 query、随机 state、10 分钟窗口，校验后单次换取；pending 在尝试前消耗，失败不会自动再用授权码。工具不输出 token。不得将 DPAPI 文件复制给普通分发客户端来代替受支持的授权代理。

## 授权完成后的只读连接与一次消息观察

仅在获准部署中、本应用 token 已合法配置后：

```powershell
python .\scripts\check_workbuddy_config.py --online
python .\scripts\workbuddy_smoke_test.py --send-once
```

第二条会消耗**最多一次应用层任务提交尝试**。测试文本只要求回显 `WORKBUDDY_CONNECTIVITY_OK` 和随机标识，明确禁止工具与文件操作。只有 role=assistant、text、单元素 content 与本次随机回显完全相同才记为观察证据；不保存不相关消息、私人历史、服务端原始错误或 metadata。

预算：默认 60 秒总观察时限、每次 HTTP 20 秒、最多 20 次读取、间隔 2 秒；一次 POST，不自动重试。保留原提交游标并去重，避免猜测增量列表的排序和截断语义。大批消息导致超过内存限制时安全失败，可能漏掉回复但不误判成功。

即使收到回显，退出码仍为 2、状态为 COMPLETION_UNCONFIRMED。这表示观察有效但尚无官方完成/关联保证，不是 Smoke PASS。没有收到回显或协议错误则 FAILED；收到回显的任务为 ESCALATED，等待协议澄清，绝不写 APPROVE/COMPLETE。

每次使用唯一 `runs/workbuddy/<id>/`，通过现有 Kernel、Message Bus、Task Manager、Blackboard 保存请求、应用层预算、过滤后的回显和观察决策，再独立重开 SQLite 验证。外部消息 ID 只保存 SHA-256 引用，真实任务 ID 是本地任务标识。调用过但返回不确定时应先检查该目录，不能为追求 PASS 自动重跑。

## 团队入口

`ai-team demo --workbuddy-mode mock` 保持现有默认。`--workbuddy-mode real` 已增加显式入口，但当前会在启动 Codex/DSH 前返回 COMPLETION_UNSUPPORTED，避免浪费模型额度。未来协议确认后才可解除 gate；真实 reviewer 分支已准备实际源代码、原始需求/规划、测试日志输入与 Blackboard 审核记录，返工继续使用原有限额。

## 下一步

1. 确认获准应用和授权部署，完成回调服务/token 交付的部署方案。
2. 获得官方本地任务关联与完成协议；补充相应成功/失败/审批终态离线用例后才能开启 review 能力。
3. 先做一次真实受控观察并核对持久化；只有能确认官方终态才升级 Smoke PASS。
4. 通过以上门槛后，才考虑一次隔离目录三 Agent 联调。
