T03 恢复诊断，2026-11-09；状态 BLOCKED。本文补充上轮预检，不改原始记录。

当前约束：优先 MCP、不占用宿主桌面、不改已有工程、不改宿主 MCP 配置。已执行的传输是本地文件/Git 只读访问及 Unity CLI 只读诊断，没有成功调用 Unity MCP，也没有启动或停止 Editor、Hub 或 owner 进程。

发现与判断：

- 本 Run 工具目录中 Unity/Coplay MCP 方法匹配数为 0；资源模板列表无条目。两份现有 Codex config.toml 仅发现 node_repl 的 MCP server 节，没有 Unity 服务。没有向未知默认端口发请求，也没有扫描端口。已知 Unity MCP URL、服务名和能力响应均为空，不能声称服务已连接。
- 截图工程 D:/github/apps/ship/client/UnityProject 存在，ProjectVersion 为 6000.6.6f1；其 Git 根为 D:/github/apps/ship，HEAD dce9225f304eb1dcc6c5e2e4d0ffb2029a0270c8，git remote 输出为空，git status 有大量修改及未跟踪文件，包括 MvpShowcase.unity、场景/联网代码和美术审计材料。不能将它认定为本单 https://github.com/wangding75/ship2.git 的空仓初始化目标；未采用、覆盖、迁移或修改它。
- 该旧工程 manifest 声明并在缓存中找到 com.unity.pipeline 0.8.0-exp.1；URP 17.6.0、Input System 1.20.0、uGUI 2.6.0、test-framework 1.8.0 是旧工程观察值，不是新工程已解析版本锁。manifest 中未发现 Coplay Unity MCP 依赖。Pipeline 是另一套桥接，不能把它隐瞒替代冻结架构中的 Coplay 标识。
- 未找到旧工程 Library/Pipeline/.unity-pipeline-port 和 ProjectSettings/Packages/com.unity.pipeline/EditorPipelineConfig.json。它们是缓存包实现给出的具体位置；缺文件不能证明宿主绝无运行实例。unity status 指定旧工程返回退出码 12 / STATUS_NO_INSTANCES，并明确警告无法检查运行中的 Editor，不能据空列表断言未启动。
- unity license status 再次返回退出码 6 / LICENSING_CLIENT_UNAVAILABLE；但许可日志 02:37Z 存在 Hub 与许可客户端成功 IPC、激活管理调用成功记录。应归为当前沙箱 CLI 检测不可达/许可可用性未确认，不能认定 owner 未激活许可。没有索取、输出或传送许可证、访问令牌和账号凭据。

最小恢复步骤：A00 与运行时 owner 确认继续契约的 ship2 隔离工程，并把已授权 Unity MCP 服务暴露给 A14 Run，提供脱敏服务名/端点及只读项目、Editor、场景查询能力。凭据只通过运行时秘密配置注入，不贴评论。若服务需要新增宿主配置/插件或新开 Editor，先提交具体启动命令、包版本/commit、目标工程路径及不可见运行方式供确认；本轮不代为执行。只有明确选择复用旧工程时才重新确认目录授权及未提交工作保护。随后 A14 验证实际响应身份与独占租约，继续原 T03。CLI 升级不再列为必要前置；不能用“存在更新”要求宿主升级。

所有工程生成、构建、干净检出、编译红绿、Gate和租约受控负例、Windows启动截图与独立验收仍 NOT_RUN；没有新候选/提交/推送，不计业务返工。owner 挂起项和历史 FAIL 保留。采集辅助程序在原生命令已完成后未及时返回，两次均通过会话中断收束；原生命令 UTC/退出码与 stdout/stderr 保留，诊断摘要另行生成，不把采集器退出当作业务结果。

附件记录位于包内 t03-mcp-diagnostic，包含原始命令输出、旧工程状态、许可日志非秘密摘录和摘要。没有附加完整宿主配置、完整许可日志或任何用户未提交源码。
