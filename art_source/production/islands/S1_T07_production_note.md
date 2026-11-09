# S1 T07 岛屿与港口模块

这是制作候选，不是验收结论。视觉由 A07 看，模块数据和技术约束由 A04 看。

- 作者 UUID `913948fc-cfc0-41f2-a6fd-c7f661450afd`
- 作者 Run `01a1c14f-e6ce-7db0-9fd7-e8e7644df216`
- Grok 会话 `01a1c14f-ed14-7ae3-be8f-3e25ec19af15`
- 实际模型 grok-4.7 / high。平台身份说明里的 gpt-6.1-sol 名称没有沿用。
- Blender 5.2.3 LTS，构建哈希 e13b728c6880。
- 基线 `ca391a4f341f25d7a99aa27a35de678fd684eaf4` 在 `refs/heads/t06/ship-assets-rework-1`，`refs/heads/main` 是 `bddd5441777b521045edd0549958704b23d82036`。该基线不是 main 已合并。
- 已验收舰船目录没有修改。
- 模块包 `data/island_module_package.json` 的 geometry_sha `efa7240dc363e00de8b56b48d35c9861285c6e1f02d9dbe0eb24e1b825c57038`。

## 冻结数字

ISL-S / ISL-M / ISL-L 的陆地包围直径是 48 / 110 / 200 米，取模块原点到陆地外环的最大半径的两倍。三角上限是 1500/600/200、3500/1400/400、7000/2500/700。港口附加件上限 2500/900/300。材质槽是岛 3、港口 2。LOD0 与 LOD1 共用一张 1024 图，LOD2 用一张 512 图。没有给 LOD1 另造贴图上限。

锚点净空下限是 1.5 × R_nav,max = 12 米。重型船船长 32 米、R_nav 8 米，轴向胶囊中心线半长 8 米，艏艉尖端距枢轴 16 米。本模块把锚点放到实测净空大于 16 米的可航水里，使允许的全部朝向都放得下这只胶囊。16 米是这只已验收船的几何结果，不是新的冻结阈值，也不把 12 米下限降掉。

LOD 切换建议仍是相机高度 50 米和 140 米。预制件里的 screenRelativeHeight 只是按这个建议和假定垂直 FOV 60° 换算，大岛在 140 米高度仍可能铺满画面，不把建议写成硬阈值。

## 图4 和 T05

图4 右图是圆岛、沙、草、树、岸沫和水深，没有港口建筑。灯塔、木棚和短栈桥来自 T05 的港口方案。本模块不做 T08 水面 shader，也不做 T09 的 12 岛装配。

## 模块数据

导出的是 IslandModulePackage，不是 WorldNavigationData。polygon.kind 只有 land、shallow、reef。浅滩的孔是陆地环的反向。栈桥多边形 kind 为 land，覆盖桩柱之间的空档，船不能从桩间穿过。地标 ID 是 LM-PORT-01，锚点 ID 是 ANCHOR-PORT-01。

浅滩宽度、山高、海滩高度、裙边深度、栈桥长度和树的个数是生产选择，写在包内 production_choices_not_thresholds。岸线、浅滩、泡沫环、深度外环和禁航多边形都在同一份 canonical_integers 里，geometry_sha 只覆盖这份整数文档。

## 实测

锚点实测到陆地、浅滩、礁和栈桥的最小距离是 17.0000 米。

- ISL-S 三角 1160 / 360 / 160
- ISL-M 三角 1776 / 652 / 248
- ISL-L 三角 2640 / 880 / 400
- PORT 三角 758 / 382 / 254

## Unity 导入

隔离工程在 `C:\t07isl\client\UnityProject`。Unity 6000.6.6f1（d20c9ac777da），URP Lit，batchmode，没有使用 `-nographics`。命令和退出码在 `evidence/unity-command.txt`，编辑器日志在 `evidence/unity-editor.log`。导入脚本留在 `art_source/production/islands/unity/T07Import.cs`，没有放进仓库的 `Assets/Game/Editor`。

FBX 使用 globalScale 1、useFileScale、关闭 bakeAxisConversion、materialImportMode None。实测导入网格是 `(-x, -z, y)`。预制件子网格使用 Rx(-90) 且 `localScale.x = -1` 后，包围盒与模块 Unity 空间的误差约 1e-5 米。根节点保持单位变换。地标 `LM-PORT-01` 和锚点 `ANCHOR-PORT-01` 挂在根上，不跟着网格镜像。这是这次 FBX 轴烘焙的测量结果，不是新阈值。

子网格按 UV 排成砂、草、岩和木、墙，序号分别是 0/1/2 和 0/1。Unity 三角与 Blender 一致。LOD0/LOD1 用 1024 图，LOD2 用 512 图。`screenRelativeHeight` 仍按建议高度 50 米、140 米和假定垂直 FOV 60° 换算。

导入图在 `evidence/unity-turntable`。这份记录是 DEVELOPMENT_OK，验收 NOT_RUN。资产分支没有合并进 main。
