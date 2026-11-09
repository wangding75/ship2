运行器修复定位，2026-11-09。

只读核对实际配置发现：

| 配置 | sandbox_mode | approval_policy | windows.sandbox |
| --- | --- | --- | --- |
| 本任务 codex-home/config.toml | workspace-write | never | elevated |
| 宿主 C:/Users/wangding/.codex/config.toml | danger-full-access | never | elevated |

证据说明：相同 Editor 可执行文件；宿主终端旧工程日志声明正常退出0；本任务直接访问 Unity-LicenseClient-wangding 和 Unity-LicenseClient-wangding-notifications 均报 UnauthorizedAccessException/0x80070005。运行器为任务生成了独立受限配置，没有沿用宿主的权限模式。具体 OS 拒绝规则仍未审计，不声称已经识别某个 ACL 条目。

修复位置是任务运行器的启动/权限策略，非 Unity 工程。应由有权管理运行器的操作者授权 Unity 子进程访问上述许可 IPC 并重新启动任务，或提供经批准的专用 Unity 执行环境。不能通过改项目包、复制许可证或修改旧工程解决。

当前会话强制 workspace-write、approval_policy=never；任务父级 codex-home 和宿主配置均不在允许写目录内。不能从任务内部修改/关闭执行隔离，不能借助计划任务、凭据切换或外部进程通道绕过限制。未修改全局或任务宿主配置，未重启daemon，未声称修复完成。

恢复验证：新任务上下文对两条许可管道不再出现访问拒绝；只启动本任务隔离工程的无窗口 Editor，确认许可成功、导入就绪，再继续T03。不得以旧工程或纯权限探针替代工程构建验收。
