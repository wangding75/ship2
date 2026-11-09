# S1-T01 输入核对、未知项/阻塞项清单与开发侧核对记录（v1.2.0）

## 1. 授权输入核对清单（Verified Authorized Inputs）

- **文档标识与规格版本**：`S1-INPUTS-UNKNOWNS-v1.2` / `v1.2.0`（候选标识：`S1-T01-CANDIDATE-v1.2-20261106`）
- **所属任务与返工单**：`S1-T01` / 返工单 `SHIP-10`（`01a1b071-19d9-7717-8d32-c00f2350ac5f`，幂等键 `T01-REWORK-1`，`child_key=S1-T01+c88eba1ea39699dc3895957d4544427d902c7041af049135134edbff508c33fa+1+A01+1`，`stage=31`，第 `1` 轮业务返工 / 最多 `2` 轮）
- **制作角色与当前 Run**：`A01 需求与玩法规格`（UUID：`df0859d2-a436-4389-9c83-da8890471e97`，当前 Run：`01a1b071-1d70-741a-9f14-2d64d5530ea8`）
- **独立验收角色**：`A02 需求与任务验收`（UUID：`1e385681-ce16-4e44-9db3-c82ea8dcd2e4`，新候选验收状态：`NOT_RUN`）

本任务在隔离只读目录（`inputs_readonly/`）对任务契约、前置依赖验收记录、冻结规格源包、用户图 4 原图（`figure04_ocean.png`）、前置 `SHIP-8` 独立审查记录以及 Owner 环境与平台输入登记（`project_inputs_20261106_registered.json`）进行了逐项字节与 SHA256 哈希实测核对，旧附件、旧 `FAIL` 与旧阻塞证据均只读保留不覆盖：

### 1.1 任务契约、前置审查记录、用户图 4 原图与 Owner 输入登记哈希核对

| 输入对象 | 来源 Issue / 附件 ID | 文件名 / 标准仓库路径 | 实测字节数 | 实测 SHA256 哈希 | 核对结论 |
| --- | --- | --- | --- | --- | --- |
| **前置 `SHIP-8` 独立审查记录（`v1.1.0` `FAIL` 证据）** | `SHIP-10` 附件 `01a1b071-19ab-725c-9b46-0eeb75447797`（源：`SHIP-8` 评论 `01a1b06f-87b0-7e53-b09c-d1137260f409` / 附件 `01a1b06f-87a2-7c3b-9c5f-e4fbf45beb47`） | `t01-acc-a02-review-record.json` | `13,945` | `11662edf534e53f1b9594a8e0abfdc32c325276980438780cfda40dd98f1c676` | **已实读并匹配**（A02 Run `01a1b066-1a09-769a-8243-764a9441b2be` 对受拒候选 `S1-T01-CANDIDATE-v1.1-20261106` 给出独立 `FAIL`，指出 `fig4-obs-06` 来源表述错误与 `matrix-range-and-version` 两项最小返工点；只读保留） |
| **受拒 `v1.1.0` 候选压缩包（只读基线）** | `SHIP-10` 附件 `01a1b071-19b6-74f3-9b78-bbfebf77eaf6`（源附件 `01a1b062-9e63-79d3-98c8-e5e3cf54c67d`） | `S1-T01-product-specs-v1.1.zip` | `66,511` | `c88eba1ea39699dc3895957d4544427d902c7041af049135134edbff508c33fa` | **匹配**（内含 6 项平铺规格文件与 `SHA256SUMS.txt`；已在隔离目录归位至 `docs/product/` 并修复为 `v1.2.0`，原包只读不覆盖） |
| **用户图 4 原图（Owner 补充提供）** | `SHIP-6` 评论 `01a1b050-f123-701f-bdbc-e03015c8809f` / 附件 `01a1b050-f10f-7be8-a788-d954c2cb9dbf`；`SHIP-10` 附件 `01a1b071-19c2-7ba4-a9bc-31f379540788` | `figure04_ocean.png`<br>仓库目标路径：`references/style/figure04_ocean.png` | `269,377` | `47778e452a519f6482abfee15cdab3e202a3475f3186fac99c507693eb4cb0b2`<br>（Owner 报告原始 JPEG SHA256：`2ae118b72245e88b6b8eaee719b46061029adebe6b90a9e424e21f84804d320a`） | **已实读并匹配**（尺寸 `1006×303 px`，`Format24bppRgb`；图像无角度/比例标注，仅支持定性倾斜俯视观察，只读不修改） |
| **Owner 环境与平台输入登记** | `SHIP-10` 附件 `01a1b071-19ca-7c43-a79d-4d458df8e040`（同 `SHIP-8` 附件 `01a1b066-19de-7b40-ad00-fbdf4228c92c`） | `project_inputs_20261106_registered.json` | `2,327` | `03280271aadd21e89806f1b3d69924369f9856ad8f215a44d0a027e8c003cf2c` | **已实读并匹配**（记录 Owner 确认的 Windows-only `1920×1080`/`30fps`/`p95≤33.3ms`/低-中档、空仓库 `main`、Unity `6000.6.6f1`、Blender `5.2.3 LTS`；`SHIP-9` 独立审核与 G14 重签尚在进行，只读保留） |
| S1-T01 实例化任务契约 | `SHIP-6` / `01a1b039-3640-7bb3-9d01-7795e54ceae8` | `t01-contract-v1.json` | `2,629` | `eb16b7b6b7b10cac2a2fd73f250e4580b09f6a6cb8e794ac4baa2715c12b2947` | **匹配**（含 UTF-8 BOM `EF BB BF`，只读未修改，不改范围与验收编号） |
| S1-T01 契约 A02 独立审查记录 | `SHIP-6` / `01a1b045-a0c4-7b6c-8c14-875f5eccad05`（同 `SHIP-7` `01a1b044-375a-7f3e-8d95-0022d5840003`） | `t01-contract-acc-a02-review-record.json` | `10,260` | `6c48aa7bbb3c2074f9eb116810bbf882b43d42d543b180cc35c545f49aa614d2` | **匹配**（契约审查 `verdict: PASS`，G14 契约前置满足） |
| A00 制作放行登记记录 | `SHIP-1` / `01a1b045-f2cd-7d8e-b8ce-b4c9e18614a9` | `t01-production-release.json` | `982` | `757a6ee08bc54c0ad201501bb5d62c610028a3e2f6e81f4f115d3f7ef3800bd3` | **匹配**（记录契约 `PASS` 与 `product_acceptance: NOT_RUN`） |
| 唯一前置 S1-T00 独立验收记录 | `SHIP-5` / `01a1b037-3b73-7e6c-91e1-282262ef0a2e` | `t00-a13-review-record.json` | `13,602` | `ff41eaf2c6e79da9fa9020250f6128325d9b458de3740794dd2731d39595bbd9` | **匹配**（A13 独立签核 `S1-T00-AC01: PASS`，绑定候选 `8853cef2800d319b8589325311a46543c16cfab212b4f9d930b6728657c308d9`，保留历史 `SHIP-3` `FAIL`） |
| 冻结规格验证压缩包 | `SHIP-6` / `01a1b039-364d-7e94-b7d3-e861a7806854` | `t00-specs-verified.zip` | `32,148` | `870ee7637dee62bfea3f528c84193fb455a6cea1f00c87ffc798b9dae39f0215` | **匹配**（内含 10 项 `specs/` 文件与 `SHA256SUMS.txt`） |

### 1.2 冻结规格包内 10 项核心规格文件与 `SHA256SUMS.txt` 逐项核对

| 序号 | 规格包内相对路径 | 实测字节数 | 实测 SHA256 哈希 | 与 `SHA256SUMS.txt` 比对 |
| --- | --- | --- | --- | --- |
| 1 | `specs/S1_acceptance.json` | `4,422` | `2f4b70701b21610e5af2a55d1af7dd1e1f591ec07394dff2717f718a265dc441` | **一致** |
| 2 | `specs/S1_tasks.json` | `27,244` | `22d5eb65bfaafd00de9b337f24078c9bdf104807bdc2c2c6135c1b718de87ea7` | **一致**（匹配契约 `source_specs_sha256`） |
| 3 | `specs/S1任务与验收细则.txt` | `11,956` | `7d87681e14d5fe715fe601111fc44039c21ef7f2a1e35ec523ffbb0d32cd5df6` | **一致** |
| 4 | `specs/acceptance_gate_policy.json` | `2,811` | `fd2305a093b83bbc9ca47f1a911ec4eef4931caf901a6b4457388052056f9b15` | **一致** |
| 5 | `specs/agents_registry.json` | `42,406` | `3e859b313921a0a7d3d244c758cb2d69c3d94b77f28e0a3be8345ce9bfdf1a0e` | **一致** |
| 6 | `specs/review_record.schema.json` | `2,176` | `95b0c757e20ca02958c611a0e08f83486a33cf362a466a029ef6f763d2e2c113` | **一致** |
| 7 | `specs/task_acceptance.json` | `8,506` | `910ff7c765586a5696da7275d2165ad7ca703d1707b852d96e38b86a24cafe22` | **一致** |
| 8 | `specs/task_contract.schema.json` | `2,514` | `fddd2ae49c8869e2b98ba52c1784cfb9ae60c6caaa6a72c920f9d2456db17305` | **一致** |
| 9 | `specs/toolchain_lock.template.json` | `2,283` | `e0070c86b23a12059448b84f022e37580decce0ba1cfeefe7de9d265ac969de7` | **一致** |
| 10 | `specs/workflow_routing.json` | `3,523` | `3d8daf5c49592adca7f77e3f2343d94c79fcc2c15019cbf02c19343f245715d1` | **一致** |
| 11 | `specs/SHA256SUMS.txt` | `4,093` | `10e924ec4d9d3005948610a44375aea8ec62b704fb39a20f7d373dc4551c6270` | 清单本体（共记录 39 条目，其中 `specs/` 下 10 项全在包内） |

---

## 2. 输入状态变更、未知项与待补边界清单（Input Updates, Unknowns & Boundaries）

| 编号 | 项目名称 | 核查范围与现状证据 | 当前状态与对 `S1-T01` 的影响 | 后续处理规则与防臆造边界 |
| --- | --- | --- | --- | --- |
| `U-01` | **用户图 4 原图状态与来源归属边界**（`references/style/figure04_ocean.png`） | Owner 已提供 `figure04_ocean.png`（`SHIP-6` 附件 `01a1b050-f10f-7be8-a788-d954c2cb9dbf` / 本单 `SHIP-10` 附件 `01a1b071-19c2-7ba4-a9bc-31f379540788`，`269,377` 字节，`1006×303 px`，`Format24bppRgb`，PNG SHA256 `47778e452a519f6482abfee15cdab3e202a3475f3186fac99c507693eb4cb0b2`；Owner 报告原始 JPEG SHA256 `2ae118b72245e88b6b8eaee719b46061029adebe6b90a9e424e21f84804d320a`）。 | **已解除原图缺失 `BLOCKED`，并修正 `FIG4-OBS-06` 来源归属**：<br>1. **从图像直接观察到的定性特征**：左图为 `平坦水面示意`（单一青绿、碎白高光、生硬直岸、无船无尾迹）；右图为 `丰富水面示意`（四层水深色彩过渡、水下礁石暗影、连续白色岸线泡沫、圆润小岛+植被+海岸礁石、1 艘 3D 帆船+弯曲白色尾迹，以及**高于海平面的倾斜俯视构图**）。<br>2. **非图像测量而是规格目标的数值来源**：PNG 原图**无相机元数据、无角度标注、无几何比例尺**。因此，`55.0° ± 2.0°` 明确来自 **Owner 方向与冻结 `S1-AC02` / `S1-T05` / `S1-T10` 的起测目标**（非图像测量）；中景默认相机高度 `85.0 m`（及近景 `35.0 m`、远景 `220.0 m`）与常规水道宽度约 `4～8` 倍船宽明确来自 **`A01` 在 `S1-T01` 给出的类别 B 设计建议初值**（非从图读得）。 | 1. **入库安排**：`S1-T03`（负责人 `A14`）初始化 Git 仓库 `main` 分支后，将该图提交到 `references/style/figure04_ocean.png` 并纳入版本管理。<br>2. **图中不存在的细节保持 `null`（严禁臆造）**：`figure04_ocean.png` 中无 HUD 界面（`hud_elements_in_figure04 = null`）、无港口地标建筑（`port_landmark_architecture_in_figure04 = null`）、未并列展示 3 种船型（`three_ship_types_lineup_in_figure04 = null`），这些未展示项保持 `null`，由下游任务按文字规格补齐。 |
| `U-02` | `SHA256SUMS.txt` 中非 `specs/` 目录的 29 项外部文档未随包分发 | `SHA256SUMS.txt` 共列出 39 个文件哈希，其中 `specs/` 下 10 个核心文件已包含在 `t00-specs-verified.zip` 中并 100% 校验通过；其余 29 项未附在当前工作目录。 | **不阻塞 `S1-T01`**：10 项核心规格文件与已提供的 `figure04_ocean.png`、`project_inputs_20261106_registered.json` 已完整涵盖 `S1-T01` 所需的全部权威输入。 | 无需额外操作。 |
| `U-03` | **Owner 环境登记、Windows-only 方向与未过 G14 修订的冲突保留说明**（`project_inputs_20261106_registered.json`） | 1. 当前工作目录无 `.git`（`candidate_commit = NOT_APPLICABLE_NO_GIT`）。<br>2. 本单所附 `project_inputs_20261106_registered.json`（SHA256 `03280271aadd21e89806f1b3d69924369f9856ad8f215a44d0a027e8c003cf2c`）已登记 Owner 宿主实测输入：Git 空仓库 `https://github.com/wangding75/ship2.git`（`ls-remote exit0`，`S1-T03` 初始化 `main` 默认分支）；Unity `6000.6.6f1`（`6000.6.6f1_d20c9ac777da`）；Blender `5.2.3 LTS`；核显 `AMD Radeon(TM) Graphics`（`0x1638`，共享内存上限报告值 `512 MB`，`discrete_gpu: null`，MuMu 虚拟适配器不当 GPU）；平台方向 `Windows-only`（`android_registration: false`, `android_device_lease: false`），性能目标 `1920×1080`、最低 `30 fps`、`p95_max_ms: 33.3`、画质 `低-中（须锁定可复现具体档位）`、`memory_metric_threshold: 待修订明确，不擅自删除内存检查或把Android PSS等同Windows指标`。<br>3. 但对应规格修订单 `SHIP-9` 独立审核与修订契约 G14 签核**尚在进行中（未完成 G14 重签）**。 | **不阻塞 `S1-T01`，且严格遵守未签核不提前变更原则**：<br>1. 本次 `T01-REWORK-1` **不借返工实施未签核的 Windows-only 阈值变更**。<br>2. 保留当前平台冲突说明与原 Android 冻结规格历史（6GB Android 真机、`720p`、30 运动船、预热 5 分钟后测 30 分钟、`p95 ≤ 33.3 ms`、总 PSS 峰值 `≤ 1.2 GiB / 1228.8 MiB`）。<br>3. **四不原则**：不降低 `33.3 ms`、不删除 PSS/内存检查、不直接把 Android PSS 等同替换为 Windows 指标、不把 `S1-T03` 负责人从 `A14` 改为其他角色。 | **后续门禁与恢复条件**：<br>1. `S1-T03` 负责人固定为 `A14`（审查者 `A04`、`A13`），须在 `S1-T02` 独立 `PASS` **且**最终修订契约经 G14 独立签核通过后才可启动。<br>2. 若后续收到经 `A00` 与 G14 正式签核的修订版本，再按批准范围同步，不在本 Run 自行混入改变验收口径的内容。 |
| `U-04` | 自动 Gate 门禁校验程序尚未实现 | `specs/acceptance_gate_policy.json` 状态为 `"implementation_required"`，计划在 `S1-T03` 由 `A14` 实现并经 `A04/A13` 独立验证。 | **不阻塞 `S1-T01`**：遵循 `specs/workflow_routing.json` 的 `bootstrap` 规则（`T00-T02` 使用平台可追溯作者/审查者身份与独立签核记录）。本任务记录 `gate_program: NOT_RUN`。 | 待 `S1-T03`（`A14`）完成 Gate 程序并通过 `A04`/`A13` 受控负例验证后启用自动 Gate。 |
| `U-05` | 角色注册表素材线勘误与费用预算上限字段 | `t01-contract-v1.json` 中 `budget.max_cost_cny` 为 `null`（原规格未登记具体金额），`max_run_minutes` 为 `120`，`max_repair_attempts` 为 `2`（本次为第 `1` 轮业务返工，此前握手 EOF、图 4 补充和基础设施恢复均不计入业务返工）。 | **不阻塞 `S1-T01`**：预算沿原已签核 `T01` 模板执行，不将 `T00` 专属无限时长条款扩展到 `T01`；本 Run 未发生新增采购、付费 API 调用或外部工具安装。 | 费用金额保持 `null`（未知/未登记金额不编造具体数值）。 |

---

## 3. `v1.1.0` → `v1.2.0`（`T01-REWORK-1`）新旧差异对照表

| 变更项 | 受拒 `v1.1.0`（`S1-T01-CANDIDATE-v1.1-20261106`）原表述 | 修复后 `v1.2.0`（`S1-T01-CANDIDATE-v1.2-20261106`）新表述 | 关联修复文件 |
| --- | --- | --- | --- |
| **修复项 1：`FIG4-OBS-06` 及关联参数来源归属** | 将 `约 55°`（`55.0° ± 2.0°`）、中景相机高度 `85 m`（“对齐图 4 右图海岛与帆船比例”）及“中央水道宽度约为船体宽度的 4～8 倍”放在从图 4 直接读出/导出的观测集合内。 | 1. 明确声明 `figure04_ocean.png` 无相机元数据、无角度标注、无几何比例尺，**图像本身仅支持定性确认倾斜俯视视角（Elevated Oblique View）**及多岛/水道/3D 帆船/弯曲白尾迹构图；<br>2. 明确标注 `55.0° ± 2.0°` 来自 **Owner 方向与冻结 `S1-AC02` / `S1-T05` / `S1-T10` 起测目标**（非图像测量）；<br>3. 明确标注相机高度 `85.0 m`（及 `35.0 m`/`220.0 m`）与常规水道视觉宽度 `4～8` 倍船宽来自 **`A01` 在 `S1-T01` 给出的类别 B 设计建议初值**（非从图读得）；<br>4. 其余 `FIG4-OBS-01`～`05` 定性观察与图中未出现项 `null`（统一键名 `hud_elements_in_figure04`、`port_landmark_architecture_in_figure04`、`three_ship_types_lineup_in_figure04`）完整保留。 | `S1_requirements_baseline.md`（第 1、2.1、4 `PARAM-07`、5.1、5.2 `FIG4-OBS-06`、5.3 节）<br>`S1_behavior_and_exception_spec.md`（第 1、4.1、7 `FIG4-OBS-06` 节）<br>`S1_acceptance_traceability_matrix.md`（`REQ-S1-002`、`REQ-S1-006`、`REQ-S1-018`、`S1-AC02`）<br>`S1_acceptance_traceability_matrix.json`（`figure04_reference`、`camera_and_hud`、`requirements`）<br>`S1_inputs_unknowns_and_blockers.md`（`U-01`）<br>`S1_T01_deliverable_manifest.json` |
| **修复项 2：追踪矩阵需求编号范围与明确版本标识** | `S1_acceptance_traceability_matrix.md` 第 5 行与第 11 行误写为 `REQ-S1-001 ～ REQ-S1-028`（而表格实际为 `001 ～ 026` 共 26 条），且该 Markdown 文件缺少明确的规格版本标识。 | 1. 将 `S1_acceptance_traceability_matrix.md` 全部范围表述统一修正为实际的 **`REQ-S1-001` ～ `REQ-S1-026`（共 `26` 条）**，不编造 `027`/`028`；<br>2. 在 `S1_acceptance_traceability_matrix.md` 标题与第 1 节新增明确的版本元数据表（`document_id: S1-TRACE-MATRIX-v1.2`，`spec_version: v1.2.0`，`candidate_id: S1-T01-CANDIDATE-v1.2-20261106`），与 JSON 矩阵及其他 4 份文档 100% 同步。 | `S1_acceptance_traceability_matrix.md`<br>`S1_acceptance_traceability_matrix.json`<br>`S1_T01_deliverable_manifest.json` |
| **输入登记与平台冲突保留更新** | 仅登记 `v1.1.0` 时点的 `U-03` 工具链待锁状态，未登记 `SHIP-8` 独立 `FAIL` 记录与 `project_inputs_20261106_registered.json`。 | 完整登记 `SHIP-8` 独立 `FAIL` 审查记录（SHA256 `11662edf534e53f1b9594a8e0abfdc32c325276980438780cfda40dd98f1c676`）与 `project_inputs_20261106_registered.json`（SHA256 `03280271aadd21e89806f1b3d69924369f9856ad8f215a44d0a027e8c003cf2c`）；明确在 `SHIP-9` 独立审核与 G14 重签完成前保留原 Android 冻结条款与冲突说明，不降低 `33.3 ms`、不删 PSS/内存项、不将 PSS 直接换为 Windows 指标、不改 `T03` 负责人 `A14`。 | `S1_inputs_unknowns_and_blockers.md`<br>`S1_requirements_baseline.md`<br>`S1_acceptance_traceability_matrix.json`<br>`S1_T01_deliverable_manifest.json` |
| **仓库目录结构与 ZIP 打包复现改进** | `v1.1.0` ZIP 根目录平铺存放 6 个文件，而 `SHA256SUMS.txt` 记录 `docs/product/` 前缀，解压后需手动移动至 `docs/product/` 才能运行 `sha256sum -c`。 | 工作目录内严格置于 `docs/product/`；新候选 `S1-T01-product-specs-v1.2.zip` 内直接按 `docs/product/<文件名>` 目录层级封装并附根目录 `SHA256SUMS.txt`（及 `docs/product/SHA256SUMS.txt`），解压即与 `SHA256SUMS.txt` 路径 100% 匹配。 | `S1-T01-product-specs-v1.2.zip`<br>`docs/product/SHA256SUMS.txt` |

---

## 4. A01 开发侧完整性自检记录（Producer Self-Verification Record）

> **重要声明**：以下检查表仅为制作角色 `A01`（`df0859d2-a436-4389-9c83-da8890471e97`，当前 Run `01a1b071-1d70-741a-9f14-2d64d5530ea8`）在提交 `v1.2.0` 候选前的开发侧核对记录，**绝不代替 `A02`（`1e385681-ce16-4e44-9db3-c82ea8dcd2e4`）对 `S1-T01-AC01` 的独立产物验收**。`S1-T01-AC01` 的正式验收状态在本单提交时严格保持为 `NOT_RUN`。

| 自检项 ID | 检查内容 | 开发侧核对结果 | 对应产物文件与章节位置 |
| --- | --- | --- | --- |
| `SELF-01` | 是否仅在授权目录 `docs/product/` 下生成正式交付产物，旧附件/旧 FAIL/旧阻塞证据在隔离目录只读保留未覆盖，且未触碰代码、Git 初始化、Unity、GPU 或 Android 设备？ | **已核对满足** | 正式产物全部位于 `docs/product/`；只读输入位于隔离目录且 SHA256 与下载前完全一致。 |
| `SELF-02` | 是否完整保持了已核准的世界与航行范围（`2048×2048 m`、`X/Z` 平面、3 种基础岛型、12 个岛屿实例、1 个港口地标、1 个水域合法停泊锚点、固定 `scenario_seed` 重建）？ | **已核对满足** | `docs/product/S1_requirements_baseline.md` 第 2、3、4 节；`docs/product/S1_acceptance_traceability_matrix.json` `frozen_parameters.world`。 |
| `SELF-03` | 是否完整保持了全部可操作旅程（选船、点目的地、绕岛寻路、到达容差与 5-tick 防抖、主动停止、动态改目标、重复命令幂等、不可达与越界反馈、驶回港口锚点、俯视相机、最小航行 HUD、UI 防穿透、20 次重入与最小状态恢复）？ | **已核对满足** | `docs/product/S1_behavior_and_exception_spec.md` 第 2、3、4、5 节。 |
| `SELF-04` | 是否明确冻结了到达容差比例（$D_{\text{arr}} = 0.50 \times R_{\text{nav}}$，$v \le 0.20\text{ m/s}$）与连续停留防抖步数（$N_{\text{arrive}} = 5\text{ ticks}$，单次命令仅触发 1 次到达事件）及船体扫掠区域验证要求？ | **已核对满足** | `docs/product/S1_behavior_and_exception_spec.md` 第 3.3 节；`docs/product/S1_requirements_baseline.md` `PARAM-04`。 |
| `SELF-05` | 是否明确冻结了 100 条合法路线样本配额（`15 + 15 + 20 + 15 + 20 + 15 = 100` 条，`R001`～`R100`）及独立不可达负例口径（`6 + 5 + 4 + 5 = 20` 条，单独计数不混入合法路线成功率，禁止实现自报可达）？ | **已核对满足** | `docs/product/S1_behavior_and_exception_spec.md` 第 6 节；`docs/product/S1_acceptance_traceability_matrix.json` `routes_100_sample_spec`。 |
| `SELF-06` | 是否明确区分了用户硬要求与 T01 建议初值，并显式声明全部数值为冻结设计目标而非已实测结果（`numbers_are_targets_not_results = true`）？ | **已核对满足** | `docs/product/S1_requirements_baseline.md` 第 1、4 节；`docs/product/S1_T01_deliverable_manifest.json`。 |
| `SELF-07` | **【修复项 2 验证】** `S1_acceptance_traceability_matrix.md` 标题与正文需求范围是否已全部修正为实际的 `REQ-S1-001` ～ `REQ-S1-026`（共 26 条，未编造 `027`/`028`），且补齐了明确的 `v1.2.0` / `S1-TRACE-MATRIX-v1.2` 版本标识并与 JSON 及其他文档同步？ | **已核对满足** | 全文检索 `REQ-S1-027`、`REQ-S1-028` 计数为 `0`；`S1_acceptance_traceability_matrix.md` 与 `.json` 均为 `26` 条（`REQ-S1-001`～`REQ-S1-026`），且均明确标注 `v1.2.0` / `S1-TRACE-MATRIX-v1.2`。 |
| `SELF-08` | **【修复项 1 验证】** `FIG4-OBS-06` 及所有关联表述（基线 `5.2`/`U-01`/`PARAM-07`/行为规格/追踪矩阵/JSON/清单）是否已明确说明 PNG 仅支持定性倾斜俯视观察（无角度/比例标注），`55.0°±2.0°` 源自 Owner 方向与冻结 `S1-AC02` 起测目标，`85.0 m` 相机高度与水道 `4～8` 倍船宽源自 `T01` 设计建议初值（非从图读得），且其余观察与未出现细节 `null` 保留？ | **已核对满足** | `docs/product/S1_requirements_baseline.md` 第 4、5.1、5.2、5.3 节；`docs/product/S1_behavior_and_exception_spec.md` 第 1、4.1、7 节；`docs/product/S1_acceptance_traceability_matrix.json` `figure04_reference` & `camera_and_hud`；`U-01`。 |
| `SELF-09` | **【平台冲突保留验证】** 是否已按 `project_inputs_20261106_registered.json` 登记 Owner 授权输入与待签核状态，同时保留原 Android 冻结条款与冲突说明，未降低 `33.3 ms`、未删 PSS/内存项、未直接把 PSS 换为 Windows 指标、未修改 `S1-T03` 负责人 `A14`？ | **已核对满足** | `docs/product/S1_inputs_unknowns_and_blockers.md` 第 1.1 节、`U-03`；`docs/product/S1_acceptance_traceability_matrix.json` `performance_baseline.pending_windows_amendment_hold`。 |
| `SELF-10` | **【路径与哈希一致性验证】** 6 份 `docs/product/` 文件的字节数与 SHA256 是否与 `S1_T01_deliverable_manifest.json` 及 `SHA256SUMS.txt` 完全一致？ | **已核对满足** | 见 `docs/product/S1_T01_deliverable_manifest.json` 与 `docs/product/SHA256SUMS.txt`。 |
