# FrameForge2 / 型材框架工作台

FrameForge2 is a FreeCAD workbench for designing beams and frames with cut, miter joins, BOM export, and more.

FrameForge2 是一个 FreeCAD 工作台，用于设计梁和框架结构，支持切割、斜接、BOM 导出等功能。

---

## Features / 功能

- **Create Beams** from sketches or edges / 从草图或边创建梁（金属、木材）
- **Trim, offset, cut, miter cut** / 修剪、偏移、切割、斜接切割
- **Cutout (make holes)** from a sketch / 基于草图的切除（打孔）
- **Custom Profiles** / 自定义型材
- **Aluminum Extrusion Library** / 铝合金挤压型材库
- **End Miter & End Trim** / 端部斜接与端部修剪
- **Gusset / Corner Bracket** / 角撑板
- **Whistle Connector** / 哨子连接器（销钉连接）
- **End Cap** / 端盖
- **Vent / Louver** / 通风口
- **Pattern Fill** / 图案填充
- **Offset Plane** / 偏移平面
- **Export BOM with cut angles, length, material** / 导出物料清单（含切割角度、长度、材料）
- **TechDraw Balloons** with auto-update / 技术图纸气球标注（自动更新）
- **Populate IDs** for profile management / 型材 ID 自动编号管理
- **Dynamic Data** integration (bundled) / 集成动态数据插件
- **Price / Weight tracking** / 价格/重量追踪

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/L3L41KKMJR)

---

## Prerequisite / 前置要求

- FreeCAD ≥ v0.21.x

---

## Installation / 安装

FrameForge2 can be installed via the FreeCAD **Addon Manager**.

FrameForge2 可通过 FreeCAD **插件管理器** 安装。

**WARNING / 警告**: When migrating from 0.1.x to 0.2.x, back up your projects! Internal data structures were modified.

从 0.1.x 升级到 0.2.x 时请备份项目！内部数据结构已更改。

---

## Quick Start / 快速开始

### Create the skeleton / 创建骨架

Beams are mapped onto Edges or ParametricLine (from a Sketch for instance).

梁映射到边或参数化线（例如来自草图）。

1. Switch to the **FrameForge2** workbench / 切换到 FrameForge2 工作台
2. Create a [Sketch](https://wiki.freecad.org/Sketcher_NewSketch) (choose XY orientation) / 创建草图（选择 XY 方向）
3. Draw a simple square — this is your skeleton / 绘制一个正方形作为骨架
4. Close the Sketch editor / 关闭草图编辑

![Create Skeleton](docs/images/02-create-frame-skeleton.png)

### Create the frame / 创建框架

1. Launch the **FrameForge Profile** tool / 启动型材工具

![profile](docs/images/10-profiles.png)

2. Select a profile from the lists (Material / Family / Size) / 从列表中选择型材（材料/系列/尺寸）

![profile](docs/images/10-profiles-task.png)

3. In the 3D view, select edges to apply the profile / 在 3D 视图中选择要应用型材的边

![Edge Selection](docs/images/13-edge-selection.png)

4. Press **OK** — you now have profiles! / 点击确定，型材已创建！

![Profiles](docs/images/14-profiles-done.png)

**Voila! Your first frame! / 第一个框架完成！**

For more details, see the [tutorial](docs/tutorial.md) / 更多详情请参阅[教程](docs/tutorial.md)。

---

## Maintainer / 维护者

Vivien HENRY  
vivien.henry@inductivebrain.fr

---

## Credits / 致谢

This workbench is built upon the work of several open-source projects:

本工作台基于以下开源项目构建：

| Project / 项目 | Author / 作者 | Description / 说明 |
|---|---|---|
| [FrameForge2](https://github.com/inductivebrain/FrameForge2) | Vivien HENRY | Main workbench / 主工作台 |
| [MetalWB](https://framagit.org/Veloma/freecad_metal_workbench) | Veloma | Original base workbench / 原始基础工作台 |
| [Dynamic Data (动态数据)](https://github.com/mwganson/DynamicData) | Mark Ganson (TheMarkster) | Dynamic properties system (v2.78, bundled) / 动态属性系统（v2.78，已集成） |
| [EasyProfileFrame](https://github.com/ovo-Tim/EasyProfileFrame) | ovo-Tim | Profile frame workbench (design reference) / 型材框架工作台（设计参考） |
| [BOLTS](https://github.com/boltsparts/BOLTS) | Johannes Reinhardt | Open Library of Technical Specifications (extrusion geometry) / 开源技术规格库（挤压型材几何） |
| [MakerWorkbench](https://github.com/URJCMakerGroup/MakerWorkbench) | URJCMakerGroup | Icon resources / 图标资源 |

### Special thanks / 特别感谢

- Vincent B
- Quentin Plisson
- rockn
- Jonathan Wiedemann

And many others from the [FreeCAD forum thread](https://forum.freecad.org/viewtopic.php?style=5&t=72389)

以及 FreeCAD 论坛相关讨论中的众多贡献者。

---

## LICENSE / 许可证

FrameForge2 is licensed under the [GPLv3 / LGPLv3](LICENSE).
