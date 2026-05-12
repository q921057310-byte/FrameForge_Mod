# FrameForge_Mod / 型材框架工作台 (v0.1)

[FrameForge] modified version — AI-assisted FreeCAD workbench for aluminum profile frame design.

[FrameForge] 修改版本 — AI 协作开发的 FreeCAD 工作台，用于铝型材框架设计。

> ⚠️ This mod code is AI(Claude) generated. AI may have inaccurate understanding of FreeCAD API. Test before use, backup files before operations.
> ⚠️ 本 Mod 代码由 AI (Claude) 辅助生成。AI 对 FreeCAD API 的理解可能不准确，使用前请先测试，操作前备份文件。

[功能演示视频](https://github.com/user-attachments/assets/9b82ec2a-d3f6-48d9-b804-f1c74c3f432c)  [功能演示视频2](https://github.com/user-attachments/assets/7afd0c91-624a-48f2-9319-2409226ca223)

---

## Installation / 安装

```
%APPDATA%/FreeCAD/v1-1/Mod/FrameForge_mod/
```

Launch FreeCAD, switch workbench to **FrameForge_mod**.

启动 FreeCAD，工作台下拉选择 **FrameForge_mod**。

## Dependencies / 依赖

- FreeCAD ≥ 1.0

---

## Features / 功能列表

### Aluminium Profile Library / 铝型材库（freely editable / 可以随意编辑修改添加）

Select profiles via `.FCStd` cross-section files (AGB 20~60 series, Chinese/European standard).

通过 `.FCStd` 截面文件选择型材（20/30/40/45/50/60 系列，国标/欧标）。

**Profile location / 轮廓库位置：**
- Aluminum / 铝：`C:\Users\<user>\AppData\Roaming\FreeCAD\v1-1\Mod\FrameForge_mod\freecad\frameforgemod\resources\profiles\aluminum`
- Steel / 钢：`C:\Users\<user>\AppData\Roaming\FreeCAD\v1-1\Mod\FrameForge_mod\freecad\frameforgemod\resources\profiles\steel`

- Each `.FCStd` file is one profile cross-section; filename = model name / 每个 `.FCStd` 文件是一个型材截面，文件名即型号名
- Simple preview (lightweight box) or full preview (real FeaturePython objects) / 简易预览（轻量盒子）或全预览（完整 FeaturePython 对象）
- Simple preview does NOT support miter/gap preview / 简单预览不支持斜角、间隙预览
- Corner mode: Miter / A-over-B / B-over-A / Gap — visible in full preview only / 角模式：斜接 / A叠B / B叠A / 间隙 —— 仅完整预览可见
- Curved profile support (creates Part::Sweep) / 支持弯曲型材（创建 Part::Sweep）
- Rotation (0/90/180/270) / 旋转（0/90/180/270）
- Option A: in-place update — no new objects created when changing params / Option A 原地更新：改参数时不新建对象

### Known Bugs / 已知问题

- `shape` temporary files may remain in the design tree / shape 临时文件残留设计树
- After drilling (MT), auto-face-hide may not work; manual Space-hide needed / MT 打孔后自动隐藏失效，需手动空格隐藏
- Creating profiles may occasionally produce extra profiles / 创建型材时可能产生多余的型材

### Create Profile / 创建型材（标准 Profile）

- Create parametric aluminum profiles from sketch edges / wires / 从草图边或边线创建参数化铝型材
- `PropertyLinkSub` → linked to skeleton edge / 关联到骨架边线
- End bevel cuts, mirror, anchor alignment, rotation / 支持 bevel 切割（两端）、镜像、锚点对齐、旋转角
- Cross-section types: V-Slot, T-Slot (multi-groove), Chinese/European standard / 截面类型：V-Slot、T-Slot（多种槽布局）、国标/欧标系列

### Create Custom Profile / 自定义型材

- Select any sketch as profile cross-section / 用户选择任意草图作为型材截面
- Links `Part::Feature` as Shape source / 关联 Part::Feature 作为 Shape 源

### End Miter / 端部斜接

- Select two adjacent faces → auto-calculates miter angle / 选择两个相邻面 → 自动计算斜接角度
- Creates `TrimmedProfile` (`_Mt`), supports Gap / 创建 TrimmedProfile（\_Mt），支持 Gap
- Auto-hides original profile / 自动隐藏原型材

### End Trim / 端部裁切

- Select profile face + trimming boundary face → creates TrimmedProfile (`_Tr`) / 选择被裁型材面 + 裁切边界面 → 创建 TrimmedProfile（\_Tr）
- Auto-hides original profile / 裁切后自动隐藏原型材

### Adjust Ends / 调整端头

- Multi-select profiles, click target face → auto-detect A/B end / 多选型材，点击目标面自动检测 A/B 端
- Positive = extend, negative = shorten / 正值延伸、负值缩短
- Supports multiple target faces / 支持多点目标面累积

### Hole Feature / 打孔

- Select profile face + sketch points/circles/edges → auto boolean cut / 选择型材面 + 草图点/圆/线 → 自动布尔裁切
- Hole type: Through / Blind / Counterbore / 孔类型：Through / Blind / Counterbore
- Bolt presets: M3~M12, Pin2.5~Pin10 / 螺栓预设：M3~M12、Pin2.5~Pin10
- Edit hole size: double-click `HoleFeature` / 编辑孔尺寸：双击 HoleFeature
- `CutResult` removed (DAG cycle fix) / CutResult 已移除（修复 DAG 循环）

### Whistle Connector / 哨子连接器

- Select groove face + end face → auto-calculate hole position / 选择凹槽面 + 端面 → 自动计算孔位置
- QY built-in connector model selector (Auto or QY16-8-30/QY20-8-40/QY20-10-45) / QY 内置连接件规格选择
- Connector specs: M6/M8/M10 / 连接器规格：M6/M8/M10

### T-Joint Connector / T 型连接器

- Select B side face + A end face → auto-detect end face hole / 选择 B 侧面 + A 端面 → 自动检测端面孔
- Screw size match: M6/M8/M10/M12/M14 / 匹配螺丝规格：M6/M8/M10/M12/M14
- Manual select / auto match / 手动选择/自动匹配

### End Cap / 端盖

- Plate / Plug type, adjustable thickness / 板式 / 插入式，厚度可调
- Edge chamfer / fillet / 边线倒角 / 圆角
- Center threaded hole: M3~M14 / 中心螺纹孔：M3~M14
- Counterbore / through hole / 沉头 / 通孔

### Gusset / 角撑板

- Two adjacent faces → triangular support plate / 两个相邻面 → 三角支撑板
- Right-angle chamfer + acute-angle chamfer / 直角边倒角 + 锐角边倒角
- Optional center hole / 中心孔可选
- Position alignment (left/center/right), thickness alignment (front/center/rear) / 位置对齐（左/中/右）、厚度对齐（前/中/后）

### Extruded Cutout / 拉伸切空

- Select profile face + sketch → boolean cut along normal / 选择型材面 + 草图 → 沿法向拉伸布尔裁切
- Through All / specified depth / Through All / 指定深度

### Vent / 通风口

- Select body + sketch in tree, click Vent toolbar / 设计树选择实体+草图，点击工具栏 Vent
- Boundary + rib edges → opening + reinforcing bars / 选择边界 + 肋条边线 → 开孔 + 加强筋
- Rib width, fillet / 肋宽、圆角

### Pattern Fill / 填充阵列

- Select body + sketch in tree, click Fill toolbar / 设计树选择实体+草图，点击工具栏 Fill
- Circle / Hexagon / User sketch pattern fill / 圆形 / 六边形 / 用户草图阵列填充
- Grid mode: Staggered / Rectangular / 网格模式：Staggered（交错）/ Rectangular（矩形）
- Gradient scale (center to edge) / 渐变缩放（中心→边缘）
- Debounced: smooth param dragging / 防抖优化：拖参数不卡

### Offset Plane / 偏移基准面

- Select face → creates PartDesign::Plane at specified distance / 选择面 → 创建指定距离的 PartDesign::Plane

### BOM / 物料清单

- Generates Spreadsheet: Parent, ID, Family, SizeName, Length, CutAngle1, CutAngle2, Drill/Cutout, Qty, Material, Weight, UnitPrice, Name / 生成 Spreadsheet
- Cut List: stock optimization (first-fit-decreasing algorithm) / Cut List：余料优化
- Stock length (default 6000mm) / Kerf (default 1mm) / Stock 长度（默认 6000mm）/ Kerf（默认 1mm）

### Populate IDs / ID 自动编号

- ID assignment: numbers / letters / combined / 型材 ID 分配策略：数字/字母/组合
- Group identical profiles: same ID + xN count / 分组：相同型材同 ID + xN 计数
- Mode: fill_selection / fill_document / continue_document / start_at / 模式

### Dynamic Data (DD) / 动态数据

This mod bundles the Dynamic Data addon for attaching custom properties to any object. / 本 Mod 集成了动态数据插件，可为任意对象附加自定义属性。

**Common usage / 常用场景：**
- Drive sketch dimensions via DD properties (e.g. `dd.x`, `dd.y`) / 通过 DD 属性驱动草图尺寸
- Store BOM-related data (part number, supplier, note) / 存储 BOM 相关信息
- Create configurations for different frame variants / 创建不同配置方案

**How to use / 使用：**
1. Click Dynamic Data → Create Object / 点击创建对象
2. Right-click the `dd` object → Add Property / 右键添加属性
3. Set a value (e.g. `x = 500`)
4. In Sketch constraint expression: `dd.x` / 在草图约束表达式中引用：`dd.x`
5. DD object auto-refreshes on document open / 自动刷新

### TechDraw Balloons / 技术图纸标注

- Create / refresh balloon annotations, auto-linked to profile IDs / 创建/刷新气球标注，自动关联型材 ID

### Isolate / 隔离显示

- Selected → hide all others / 选中对象 → 其余全部隐藏
- Exit isolate: configurable skip keywords (Constraint/Joint/Revolute/Slider/Plane/Origin/Link etc.) / 退出时配置跳过关键词
- Assembly support: parent container + LinkedObject auto-kept visible / 支持装配体
- Settings: customize skip keywords / Settings：定制跳过关键词

### Parametric Line / 参数化线

- Select two vertices → creates Part::LineSegment / 选择两个顶点 → 创建 Part::LineSegment

### Attached Link / 附着链接

- Creates App::Link + Part::AttachExtensionPython, with PID / 创建 App::Link + Part::AttachExtensionPython，带 PID

### Recompute / 强制更新

- Recursively recompute all Profile / TrimmedProfile / ExtrudedCutout / 递归重新计算

### Export TechDraw / 导出技术图纸

- Export all TechDraw pages to PDF / 所有 TechDraw 页面导出为 PDF

---

## How to Add Profiles / 如何添加型材轮廓

### Getting Cross-Sections / 获取截面

- **Draw your own sketch** — Create a Sketcher sketch with a closed wire cross-section, save as `.FCStd` / 自己画草图，保存为 .FCStd
- **Extract from STP/IGS** — Open STP, create sketch from end face (Part → Create sketch from face), clean up and save / 从 STP 提取端面草图
- **Same series in one file** — Recommend putting same-series profiles in the same `.FCStd` / 同系列截面建议放同一个文件

### File Location / 文件位置

```
resources/profiles/
├── aluminum/        ← Aluminum profiles (AGB 20~60 series, CN/EU standard) / 铝型材
├── steel/           ← Steel profiles (tube, rectangular tube, light rail etc.) / 钢材
└── aluminium_extrusion.json  ← Aluminium dimension definitions / 铝型材尺寸定义
    metal.json                ← Metal structural shapes (EN standard) / 金属型材尺寸
    wood.json                 ← Timber sections (EN standard) / 木材型材
```

### Profile Families / 截面类型

#### Aluminum (JSON + .FCStd) / 铝型材

Aluminum has many specifications; currently includes AGB 20~60 series, Chinese/European standard with various groove widths. / 铝型材规格非常多，目前包含 AGB 20~60 系列、国标/欧标多种槽宽。

| Series / 系列 | Size range / 尺寸范围 | Source / 来源 |
|------|---------|---------|
| CN 30 series(6.3) | 25×25 | aluminium_extrusion.json |
| EU 20 series | 20×20 ~ 20×80 | aluminium_extrusion.json |
| EU 30 series(8.2) | 30×30, 30×60 | aluminium_extrusion.json |
| EU 40 series(10.2) | 40×40, 40×80 | aluminium_extrusion.json |
| AGB series | 20~60 series, various groove widths | `.FCStd` files |

#### Steel (.FCStd) / 钢材

Steel profiles are currently few, and any help adding more is welcome. / 钢材目前很少，后续可补充，有帮助更好。

| Profile / 型材 | File / 文件 |
|------|------|
| Square tube 40×40×1.5 | st4040-1.5.FCStd |
| Rectangular tube 50×30×2.6 | 矩型管 50 X 30 X 2.6.FCStd |
| Light rail 9kg | 轻轨 轻轨9.FCStd |
| Location / 位置：resources/profiles/steel/ | |

#### Metal structural shapes (JSON) / 金属型材

| Series / 系列 | Size range / 尺寸 | Note / 说明 |
|------|---------|------|
| Equal Leg Angles | 16×16×3 ~ 250×250×35 | EN 10056-1 |
| Unequal Leg Angles | 30×20×3 ~ 250×150×15 | EN 10056-1 |
| Flat Sections | 10×3 ~ 200×65 | EN10025 |

#### V-Slot / T-Slot (parametric / 程序生成)

| Type / 类型 | Size / 尺寸 | Note / 说明 |
|------|------|------|
| V-Slot 20 | 20×20 ~ 20×80 | Generated / 程序生成 |
| T-Slot 20 | 20×20 (1~3 grooves, symmetrical/opposing) | Generated / 程序生成 |
| CN/EU standard | 20/30/40/45 series | Generated / 程序生成 |

---

## Toolbar Layout / 工具栏布局

| Toolbar / 工具栏 | Commands / 命令 |
|--------|------|
| Drawing Primitives | Sketcher_NewSketch, Part_Box, ParametricLine, SubShapeBinder |
| Frameforge | AluminumProfileLibrary ▼, Trim ▼, EndMiter, ExtrudedCutout, EndCap, Gusset, H |
| Profile Group | Std_Group, Std_Part |
| Part Primitives | AttachedLink, Part_Fuse, Part_Cut, PartDesign_Body |
| FrameForge output | PopulateIDs, ResetIDs, CreateBalloons, RefreshBalloons, CreateBOM |
| Dynamic Data | CreateObject, AddProperty, CopyProperty, CreateConfiguration |
| Other Tools | AddVent, PatternFill, OffsetPlane |
| Utilities | Recompute, ExportTechDraw, Isolate, IsolateSettings |

---

## Usage Notes / 使用备注

This plugin code was generated with AI (Claude) assistance. Known AI issues / 已知 AI 常见问题：

- FreeCAD API misunderstanding (e.g. `Part.makeRegularPolygon` doesn't exist) / API 理解偏差
- `addObject` + transaction missmatching (`abortTransaction` not paired) / 事务管理遗漏
- Frequent `recompute()` causing lag / 频繁 recompute 导致卡顿
- Bad cache design → stale geometry / 缓存设计不合理
- Edge cases not covered (null selection, shapeless objects) / 边界情况未覆盖

Recommendations / 操作建议：
1. Verify on small models first / 先在小模型上验证
2. Save/backup before operations / 操作前保存/备份
3. Turn off FreeCAD auto-save or shorten interval / 关闭自动保存或缩短间隔

---

## Maintainer / 维护者

xingxing — q921057310@gmail.com

## Credits / 致谢

| Project | Author | Description |
|---------|--------|-------------|
| [FrameForge](https://github.com/lukh/frameforge) | lukh | Original workbench / 原始工作台 |
| [MetalWB](https://framagit.org/Veloma/freecad_metal_workbench) | Veloma | FrameForge predecessor / FrameForge 前身 |
| [Dynamic Data](https://github.com/mwganson/DynamicData) | Mark Ganson | Dynamic properties (v2.78, bundled) / 动态属性系统 |
| [EasyProfileFrame](https://github.com/ovo-Tim/EasyProfileFrame) | ovo-Tim | Profile frame workbench (code referenced) / 型材框架工作台（参考代码） |
| [BOLTS](https://github.com/boltsparts/BOLTS) | Johannes Reinhardt | Open Technical Specs library / 开源技术规格库 |

### Special thanks / 特别感谢
- **大海** — Provided aluminum extrusion profile library / 提供铝合金型材轮廓库
- Vincent B, Quentin Plisson, rockn, Jonathan Wiedemann
- [FreeCAD forum thread](https://forum.freecad.org/viewtopic.php?style=5&t=72389)

## License / 许可证

LGPL-3.0-only
