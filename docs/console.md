# AI Team Console — V0.2.0

本地 React 控制台读取现有运行记录；模型执行与 OAuth 均禁用。新增草稿通过现有 TaskManager / EventBus 保存，不调度 Agent。

## 启动

在自己的 PowerShell 中运行：

```powershell
Set-Location '<project-root>\console'
npm.cmd ci --ignore-scripts
npm.cmd run build
Set-Location ..
python .\scripts\team_console.py --port 8765
```

打开 <http://127.0.0.1:8765>。当前机器已经安装前端依赖并完成构建，日常只需执行最后的 Python 命令。
Python 环境须具备项目原有依赖；使用 Python 3.11+。前端使用 Node 24 和锁文件中的版本。本地服务应由具有项目运行记录读取权限的用户启动。

开发时保持 Python 服务运行，在另一个终端执行：

```powershell
Set-Location '<project-root>\console'
npm.cmd run dev
```

此命令监听并重建前端文件；修改后手动刷新浏览器。所有页面和 API 使用同一个回环地址，没有跨域开发代理。停止服务使用 Ctrl+C。

## 数据和任务

- 从 `runs/*/blackboard.sqlite` 读取已有数据库，不复制数据库，不修改历史状态。
- 首次明确提交草稿时才创建 `runs/console/blackboard.sqlite`，沿用现有每次运行一个数据库的结构、原有表和 TaskManager。它是草稿所属运行的唯一记录，不是另一套任务数据库或镜像。
- 草稿状态为 PENDING，阶段为 DRAFT。页面没有启动模型、授权、取消现有工作流或执行任意命令的入口。
- REAL_VERIFIED 表示有历史真实消息及验收任务引用；实时在线状态独立显示 UNKNOWN。
- 事件只来自已保存的 Event Bus 数据。缺少时间、关联或重试计数时显示无记录；不从报告制造事件。
- 产物核验只按已登记资源 ID 对允许的 workspace 文件计算 SHA-256；不返回文件原文。
- 配置检查只查看非敏感存在性信息，不解密凭证、不启动客户端、不检查模型余额。

## 桌面封装

**V0.2.1 更新：** 桌面端现已改为自行管理打包后端和动态端口。下方为
V0.2.0 的历史限制；当前构建与启动步骤以 [windows-desktop.md](windows-desktop.md)
和根目录 README 为准。仍未在本机验证 Rust 构建或桌面启动。

`console/src-tauri` 提供最小 Tauri 2 外壳，加载同一个回环服务，不暴露系统命令。当前机器没有 Cargo，尚未编译和验证 WebView 行为；不能视为可发布桌面应用。

未来按 [Tauri 官方 Windows 前置条件](https://v2.tauri.app/start/prerequisites/) 配置 Rust、MSVC 和 WebView2 后，在 Python 服务已启动的情况下运行 `npm.cmd run desktop`。此路径本轮未验证，服务目前需独立管理。没有制作安装包。

## 离线测试

```powershell
Set-Location '<project-root>'
python -m pytest tests/unit tests/integration -q -k 'not test_dpapi_synthetic_memory_roundtrip' -p no:cacheprovider
Set-Location console
npm.cmd run test
```

排除项是 Windows 原生 DPAPI 的合成内存往返测试，不是模型测试；本轮沿用此前隔离范围。前端测试全部使用 Mock 网络。没有运行 E2E。
