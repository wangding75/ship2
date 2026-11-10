T07 v3 首做续作完成候选（开发侧自检 `DEVELOPMENT_OK`；独立验收 `NOT_RUN`，待 A00 派发 A07/A04 独立复验）。

契约：`T07-rescue-contract-v3-owner-S-exemption.json`，SHA256 `9ac4402b92cb04f4c474b08e8c1c188367e29fdc20cf1a6d1c340a629d6f8034`（SHIP-63 A02 独立 G14 PASS Run `01a1c454-3f82-77cc-a13d-4a511e464093`）。
Runtime/模型切换会签：`owner-runtime-switch-countersign-routing33.json`，SHA256 `d175eee8c8769507f927bb80d70e764be82972cebb95274088bbd82a8255ff47`。
作者：AAA `1997d691-07fa-4689-9a15-54851a3e2909`；前序中断 Run `01a1c45f-45b5-7a17-bb9d-47029f757b64`，当前完成 Run `01a1c52a-f78f-7b37-8eaf-cac40e6fd039`（Antigravity `fd1ac914-6358-4bb5-aa2f-7cb659141a1f` / `Gemini 4 Argon (High)`）。
计数：原普通返工 2/2（SHIP-57 `54137f483e1ce956fb5f76878085ee069217abe9`）、救火首做 1/1（本候选完成）、救火修复 0/2 不重置，历史 FAIL/BLOCKED 原样保留。`ISL-S` 三档保留显式空 `Trees` 对象；`ISL-M`/`ISL-L` 四件均非空。

## 离线生产与可保存确定性重组（Blender）

以仓库根为工作目录；用已安装 Blender 5.2.3 LTS（`e13b728c6880`）的真实路径替代 `blender`：

```text
blender -b art_source/production/islands/source/S1_T07_islands.blend --python-exit-code 1 --python art_source/production/islands/assemble_island_parts.py -- --output art_source/production/islands/source/S1_T07_reassembled.blend --export-dir art_source/production/islands/export/reassembled --report art_source/production/islands/evidence/part_reassembly.json
```

若不带 `--` 参数直接执行 `blender -b <blend> --python assemble_island_parts.py`，默认对 `S1_T07_islands.blend` 输出到 `source/S1_T07_reassembled.blend`、`export/reassembled` 与 `evidence/part_reassembly.json`（若输入为其他临时 `.blend` 副本则原地保存到该副本并重开校验）。

先在输入 blend 编辑并保存命名分件，再执行入口。输出含九个真实合并网格 `{asset}_LOD{0,1,2}_Assembled`，原可编辑分件仍保留；生成九份 FBX。输出 blend 可再次作为输入。隐藏仅控制预览，隐藏件仍参与组装。修改器需先明确应用、面需预先三角化；不静默丢弃修改器、UV层或材质映射。固定 `Beach/Grass/Trees/Reef` 顺序，角点独立保留 UV/自定义法线；烘焙对象世界变换，负行列式镜像反转面绕序，法线用逆转置。三角数受冻结上限约束，保持三槽。

Blender Python Console 可使用同目录 `persistent_assembly.preview('ISL-M', 1, 'parts')` 或 `preview('ISL-M', 1, 'assembled')`。每次只启用一套、一个 LOD，状态序列化在 scene，自带入口保存为 `assembled:LOD0`。

测试与精度入口（输出写指定隔离目录）：

```text
blender -b art_source/production/islands/source/S1_T07_islands.blend --python-exit-code 1 --python art_source/production/islands/test_persistent_assembly.py -- <隔离测试目录>
blender -b --factory-startup --python-exit-code 1 --python art_source/production/islands/verify_saved_precision.py -- art_source/production/islands <精度证据目录>
```

## Unity 生产入口与实测验证

编辑器工具位于 `Assets/Game/Art/Islands/Editor/T07IslandAssembly.cs`；`art_source/production/islands/unity/T07Import.cs` 为导入与证据生成脚本（通过环境变量 `T07_PATHS_JSON` 读取路径配置，不写任何工作区外共享目录）。

1. 在 Prefab Mode 编辑 `SemanticParts/{asset}_LOD{n}_Parts` 下对象的变换或网格，保存后退出 Prefab Mode。
2. Project 窗口选中 `ISL-S/M/L` prefab，选择 `Game/T07/Selected Saved Prefab/Rebuild`；或调用 `T07IslandAssembly.Rebuild(path)`。全量重组用 `Game/T07/Rebuild Saved Island Prefabs`；`Game/T07/Reassemble Island Parts` 委托到同一真实生产入口。
3. 原地更新 `Models/{asset}_LOD{n}_slots.asset`（通过 `EditorUtility.CopySerialized` 保留既有 GUID 与 `fileID: 4300000`）并写回 prefab 的 `MeshFilter` 与 `LODGroup` 包围盒，不删除原 prefab。未改动的分件直接走精确恒等映射（0 bit 坐标损耗），编辑过的分件按局部矩阵、逆转置法线与行列式符号绕序重建。导入器 readability 在 `finally` 恢复。
4. 选中保存的 prefab，使用 `Preview Parts LOD0/1/2` 或 `Preview Automatic LOD`（或调用 `T07IslandAssembly.SavePreview(path, mode)`）。切分件预览时先关闭 `LODGroup` 与全部合并渲染器，仅启用单档分件渲染器；切回自动 LOD 时关闭 `SemanticParts` 及全部分件渲染器，启用 `LODGroup` 并恢复 `ForceLOD(-1)`，状态持久化到 prefab，零双套叠加渲染。
5. 自然 LOD 距离扫描（`ForceLOD(-1)`）：`ISL-M` 过渡阈值设为 `0.60 / 0.22 / 0.01`（与 `ISL-S` `0.681 / 0.243`、`ISL-L` `0.55 / 0.20`、`PORT` `0.511 / 0.182` 保持一致的 ~2.75x LOD1 带宽比），在 `FOV=50` 与 `FOV=60` 距离倍率扫描下，`ISL-S`、`ISL-M`、`ISL-L`、`PORT` 均通过独立 RGB 标识像素计数与 `ForceLOD(0/1/2)` 像素比对验证完整跨越 `LOD0 -> LOD1 -> LOD2`。
6. 长路径规避：Windows 下原工程根路径（109 字符）叠加 `Library/PackageCache/com.unity.render-pipelines.core@e18bd88df4e3/.../RenderPipelineConverterVisualElementListFilter.uxml`（161 字符）达 271 字符（超过 `MAX_PATH = 260`）。在工作区内使用短路径隔离副本 `<workdir>/u`（85 字符，总长 247 字符 `< 260`）执行 Unity 6000.6.6f1 + D3D11 GPU 批处理，Editor 日志中 `DirectoryNotFoundException = 0`、`Asset import failed = 0`。
