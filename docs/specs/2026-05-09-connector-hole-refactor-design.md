# Connector 打孔功能重构设计

## 概述

将当前 WhistleConnector / T-Joint Connector（M,W / M,T）的自动检测代码替换为单一统一打孔特征：基于草图定位、手动输入参数、布尔切除，命名继承型材编号。

## 当前代码问题

- `whistle_connector.py`（873行）混杂了自动检测、基于面的定位、QY规格、T型接头孔检测和两种连接器模式
- `create_whistle_connector_tool.py`（570行）任务面板代码重复
- 无显式 Base 引用 — 父子链通过 `_get_body_to_cut()` 和 `_get_working_shape()` 隐式推断
- 自动检测（QY、系列、孔径）多余：用户需要完全手动控制
- 结果对象命名不继承型材信息

## 新设计

### 单一统一特征：`HoleFeature`

一个 FeaturePython 类，通过参数控制所有打孔类型。

### 属性

| 属性 | 类型 | 默认值 | 说明 |
|----------|------|---------|-------------|
| `Base` | Link | None | 要被切除的型材 |
| `Positions` | LinkSubList | [] | 草图顶点（点）或圆用于定位（可加选/减选） |
| `HoleType` | Enum | "Through" | 通孔 / 盲孔 / 沉头孔 |
| `BoltSpec` | Enum | "Custom" | 自定义 / M6 / M8 / M10（填充预设尺寸） |
| `HoleDiameter` | Length | 8.5 | 孔径 |
| `HoleDepth` | Length | 0.0 | 深度（0 = 通孔模式下自动穿透型材） |
| `CounterSinkDiameter` | Length | 14.0 | 沉头直径（仅沉头孔时生效） |
| `CounterSinkDepth` | Length | 8.0 | 沉头深度（仅沉头孔时生效） |
| `Reverse` | Bool | False | 反转钻孔方向 |

### BoltSpec 预设尺寸

| 规格 | 孔径 | 沉头直径 | 沉头深度 |
|------|-------------|---------------|------------|
| 自定义 | (手动) | (手动) | (手动) |
| M6 | 6.5 | 11.0 | 6.0 |
| M8 | 8.5 | 14.0 | 8.0 |
| M10 | 10.5 | 18.0 | 10.0 |

### Execute 逻辑

```
遍历 Positions 中的每个元素：
    如果是点（Vertex）：
        pos = vertex.Point
    如果是圆（Circle Edge）：
        pos = circle.Curve.Center
    否则：跳过

    确定切除深度：
        如果 HoleType == "Through" 或 "Counterbore"：
            cut_depth = Base.Shape.BoundBox.DiagonalLength * 2  （保证穿透）
        否则（盲孔）：
            cut_depth = HoleDepth

    在 pos 处创建圆柱：半径 = HoleDiameter/2，长度 = cut_depth
    
    如果 HoleType == "Counterbore"：
        在 pos 处创建沉头圆柱：半径 = CSinkDiameter/2，长度 = CSinkDepth

将所有圆柱融合为一个复合体
result = Base.Shape.cut(复合体)
Shape = result
```

### 命名规则

```
base_name = getattr(Base, "SizeName", None) 或 Base.Label
fp.Label = f"{base_name}_Hole"
# 如标签冲突，FreeCAD 自动追加编号
```

### 文件结构

**`connector_hole.py`** — FeaturePython 类 + 视图提供者
- `HoleFeature.__init__(obj)` — 注册属性
- `HoleFeature.execute(fp)` — 读取位置、创建圆柱、布尔切除、设置 Shape
- `ViewProviderHoleFeature` — 视图提供者

**`create_connector_hole_tool.py`** — 任务面板 + 命令
- `HoleFeatureTaskPanel` — UI：Base 选择、Positions 选择、HoleType/BoltSpec 下拉框、尺寸微调框
- `HoleFeatureCommand` — 命令（快捷键 `M, W`）

### UI 流程

1. 用户点击工具栏按钮 → 创建新 HoleFeature
2. 任务面板打开，包含：
   - Base 选择（在 3D 视图中点击型材）
   - Positions 选择（点击草图的点/圆，再次点击可移除）
   - HoleType 下拉框：通孔 / 盲孔 / 沉头孔
   - BoltSpec 下拉框：自定义 / M6 / M8 / M10
   - 尺寸微调框（BoltSpec 自动填充，可手动修改）
   - Reverse 复选框
3. 用户也可以先预选对象再点按钮

### 被移除的内容

- QY 自动检测
- 序列/系列自动检测
- T型接头自动检测
- 面上孔自动检测
- `_get_body_to_cut()` / `_get_working_shape()` / `_reapply_trims()`
- 旧 WhistleConnector 执行逻辑

### 保留的内容

- `BOLT_PRESETS` 数据表（从旧 CONNECTOR_SPECS / TJOINT_MATCH_TABLE 提取）
- `_register_profile_metadata` — 用于 BOM 集成

### FreeCAD 兼容性

全部使用标准 FeaturePython 能力：
- `PropertyLink` / `PropertyLinkSubList` 用于对象/子元素引用
- `Part::FeaturePython` + `execute()` 用于形状计算
- `Part.Circle` + `Face.extrude()` 创建圆柱
- `Shape.cut()` 布尔差集
- `Gui.Control.showDialog()` 任务面板

## 链式切除行为

- 每个 HoleFeature 对其 Base 执行一次布尔切除
- 链式：将一个 HoleFeature 的 Base 设为上一个 HoleFeature 的结果
- "一切多"：一次选择多个草图元素 → 一次切除所有孔
- FreeCAD 的重新计算引擎自动处理依赖图

## 命名继承示例

```
"4040_Hole"   （4040 型材上的第一个孔）
"4040_Hole1"  （标签冲突时自动编号）
```

SizeName 来自型材元数据。如不可用，回退到 Base.Label。
