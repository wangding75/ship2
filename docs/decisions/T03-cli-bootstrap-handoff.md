T03 CLI/Pipeline 恢复执行记录，2026-11-09。状态 BLOCKED；不是完整候选或验收结论。此次执行使用官方 CLI/Pipeline，未接入 MCP。

实际产物：client/UnityProject 从本机 com.unity.template.urp-blank 生成的 URP 3D 工程骨架、模板资源与 meta、Packages/manifest.json、ProjectSettings；补写准确 ProjectVersion 6000.6.6f1 (d20c9ac777da)，增加生成缓存忽略规则。Pipeline installer 成功写入依赖 0.8.0-exp.1。包解析/首次完整导入未完成，所以这不是已验证可打开工程。没有复制旧 ship 工程的业务源码、场景或 2D 模板。

PROVISIONAL：Editor 锁 6000.6.6f1；模板 manifest 请求 URP 17.6.0、Input System 1.20.0、uGUI 2.6.0，Pipeline 请求 0.8.0-exp.1。这些是声明版本，不是 packages-lock.json 已解析版本；URP/Core/ShaderGraph 内容锁仍 NOT_RUN。模板默认项目设置可替换，不代表 owner 冻结最终画质。最终内存、画质、20:9 和 T04 CAT-02 继续挂起，旧 FAIL 不变。

命令：`unity projects create UnityProject --path <workspace>/client --editor-version 6000.6.6f1 --template com.unity.template.urp-blank --bare --no-cloud --non-interactive --format json`。当前 CLI 1.0.0-beta.15。本地 CreateNew/FileShare.None 原子文件 guard 覆盖此次创建；它不是已完成的跨工作树 Unity/GPU 租约服务，也不代表 G12 PASS。

CLI 真实启动了本工程 Editor PID 47676，03:01:51.5922893Z，MainWindowHandle=0；本项目 UPM 日志明确绑定 `server -s 47676`。原 Editor 日志显示 LicenseClient-wangding 通道连接被拒绝、许可初始化/重连超时、全局许可 mutex 已被既有客户端持有、BIOS 查询被拒绝，以及 `com.unity.editor.headless was not found`。这确认当前启动上下文的许可 IPC/初始化失败；不能单独据此断言 owner 没激活或缺少某种商业授权。创建未就绪，超过180秒后按 PID、精确启动时间、exe路径和项目日志核实所有权，停止且等待这个 Editor 退出。CLI 最后返回6/PROJECTS_CREATE_ERROR（子进程-1）；这个退出发生在主动收束后，不伪称自然退出码。未再启动同一故障路径。

随后补 ProjectVersion 后，`unity pipeline install --project-path <workspace>/client/UnityProject --version 0.8.0-exp.1 --format json` 返回0、success=true，仅证明 installer 写入 manifest；不冒充 Editor桥接已连接。没有 run_script/脚本内部结果，动态工具/项目/场景读取仍 NOT_RUN。

清理：47676 已退出，UPM/DataStore 没有留下可见进程；保留宿主既有 Hub helper 48472 和 Licensing Client 27840。项目残留 UnityLockfile 在确认 Editor PID退出、独占打开成功后移除；本地 bootstrap guard 已释放。没有启动可见窗口、桌面控制、GPU测量、第二个Editor，或关闭 owner 进程。工作目录外无主动配置修改。Unity工具自身启动行为见原始日志。

最小恢复：由运行时 owner/A00 让本任务的无窗口 Editor 在能访问已存在 `LicenseClient-wangding` IPC 的同账户执行上下文运行，并具备 Unity许可初始化所需系统查询权限；不要求接 MCP、升级 CLI 或手动打开 GUI。对该任务执行上下文恢复权限后，A14 从本骨架继续同单的受控启动、动态工具发现、版本解析、基础场景生成与构建。若需调整宿主执行令牌/沙箱或许可服务权限，超出当前 workspace-write/never 可用能力，交运行时 owner 处理。

未完成：可打开基础场景证明、Windows开发包/真实图形截图、干净检出构建、编译错误红/回滚绿、Gate负例、完整共享租约与权限隔离、独立A04/A13验收均 NOT_RUN；本骨架不能交 in_review。没有 Git 初始化/commit/push，没有移动旧工作或强推。当前远端查询无ref。基础设施恢复不计业务返工，计数仍0。

原始证据：附件 cli-bootstrap 目录的 create-command.json、原生 CLI stdout/stderr、owned-editor 指纹与回收记录、Editor许可错误原行及日志源SHA、Pipeline installer结果、cleanup.json。完整原日志可能含宿主身份字段，仅保留本地，不上传；附件提供未改写的故障原行。所有验收PASS仍由独立角色后续判定。
