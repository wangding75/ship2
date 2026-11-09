# S1-T07 模块数据适配说明

版本 `S1-T07-MODULE-1`。这份说明告诉 T09 怎样把模块数据放进已冻结的 `WorldNavigationData`。它不修改 `data.schema.json`，也不给冻结记录加字段或新的 `polygon.kind`。

## 本轮交付的不是世界记录

`data/island_module_package.json` 的 `record_type` 是 `IslandModulePackage`。它不是 `WorldNavigationData`。冻结世界记录要求恰好 12 个岛屿、`scenario_seed`、世界边界 `[-1024, 1024]` 和唯一港口。那些属于 T09。本轮没有造最终世界，也没有 12 个实例。

## 可以直接抄进冻结多边形的部分

每个多边形只有 `polygon_id`、`kind`、`outer`、`holes`。`kind` 只有 `land`、`shallow`、`reef`。外环逆时针，孔环顺时针，首尾不重复。坐标是模块局部 XZ 米，`+Y` 向上，水位 `Y=0`。小数来自 `1e-5` 米整数，回读误差不超过一个量化步。

T09 把实例的平面位置和 Y 轴朝向作用到这些环上。只平移可视网格、不变换这些环，会使岸线和导航分开，不能这么做。

## 港口只挂在一个 ISL-L 实例上

`PORT-PIER-LAND` 的 kind 是 `land`。矩形盖住整段栈桥，包括桩柱之间的空档，船不能从桩间穿过。它不要复制到其他 ISL-L 实例。

地标 ID 是 `LM-PORT-01`。锚点 ID 是 `ANCHOR-PORT-01`。两者坐标不同。锚点是水域点，不是灯塔或栈桥的 Transform。

## geometry_sha

`geometry_sha` 是 `canonical_integers` 的 UTF-8、键排序、紧凑 JSON 的 SHA256，不包含 sha 自身。岸线、浅滩、礁、栈桥、泡沫环和浅滩外环都在这份整数文档里。LOD 只减表现网格，不改这份环。

T09 装配出世界记录后，要按冻结规则重算世界自己的 `geometry_sha`。导航、岸沫和深度过渡绑定那份世界 sha。本模块 sha 不能冒充世界 sha。

## 锚点净空

合同下限仍是 `1.5 × R_nav,max = 12` 米。重型船船长 32 米，`R_nav` 8 米，胶囊中心线半长 `max(0, 16-8) = 8` 米，艏艉尖端距枢轴 16 米。模块里的锚点实测距离大于 16 米，所以全部朝向的胶囊都在可航水里。这没有把 12 米改成新的阈值。

世界边界里的“最大船包络仍在 `[-1024, 1024]` 内”要等 T09 放好实例后再查。模块局部锚点本身不在世界坐标里。

## 没有提前做的事

没有 T08 水面 shader 或泡沫网格。泡沫环和浅滩外环只是后继输入。没有 T09 地图。LOD 相机高度 50 米和 140 米仍是建议。Windows 最终内存、画质档、20:9、生产 Gate、G10、G12 和 T04 CAT02 继续挂起。
