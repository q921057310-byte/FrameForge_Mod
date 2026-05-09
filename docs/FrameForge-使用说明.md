# FrameForge 使用说明

> **免责声明**：本项目所有代码由 AI 生成。请在使用前检查代码逻辑，操作前先备份文件。AI 代码可能在特定场景下产生意外行为，建议逐个功能测试后再批量作业。

---

## Hole（打孔）

工具栏按钮：**Hole**

### 用法
1. 点型材**面**（决定钻孔方向 = 垂直面法向）
2. 点草图**点/圆/线**（定位）。圆取圆心，线取两端点
3. 调参数：HoleType（通孔/盲孔/沉头孔）、BoltSpec（M3~M12 + Pin2.5~10）
4. 点 **OK** → 自动 Part::Cut → 生成 `4040_Cut`（原材和 Hole 自动隐藏）

### Apply
- 点 **Apply** → 保存当前 + 清空选择 + 继续打下一个

### 方向旋转
面板底部的 RotX/Y/Z 下拉：-90/0/90/180 度，90 度一档。调整圆柱体方向。

---

## Connector（自动打孔 M,W / M,T）

工具栏按钮：**Connector**（下拉含 WhistleConnector + TJointConnector）

### WhistleConnector (M,W)
1. 点槽口面
2. 可选点端面（定位距离）
3. 自动检测 QY 规格
4. OK → 自动 Part::Cut

### TJointConnector (M,T)
1. 点 B 面（Connector 隐藏，不遮挡视图）
2. 点 A 端面 → 自动检测孔位 + 匹配螺丝规格
3. OK → 自动 Part::Cut

### Apply
保存当前 + 清空选择 + 继续。

---

## EndCap（封盖）

工具栏按钮：**EndCap**

1. 点型材端面
2. 调参数：Thickness（厚度）、Gap（平移距离）、CapType（Plate/Plug）
3. 可选：中心孔（勾选 HoleEnabled，选 HoleThreadSpec 自动填孔径）
4. 可选：倒角/圆角（勾选 ChamferEnabled/FilletEnabled）
5. **Apply**：保存当前 + 清空选择 + 继续；**OK**：保存并关闭

### 参数说明
| 参数 | 说明 |
|------|------|
| Thickness | 封盖厚度 |
| Gap | 从面偏移距离（平移）|
| PlugOffset | Plug 模式下缩小外形（间隙）|
| HoleThreadSpec | M3~M12 下拉，自动填孔径 |
| Chamfer/Fillet | 垂直边倒角/圆角（T 型槽已带圆角的边会自动跳过）|

---

## Gusset（角撑板）

工具栏按钮：**Gusset**

1. 点两个相邻面
2. 调厚度等参数
3. **Apply**：保存 + 清空 + 继续；**OK**：保存并关闭

---

## Trim（裁剪延伸）

工具栏按钮：**Trim Profile**

1. 点型材面 + 裁剪面
2. 选 CutType（Simple fit / Perfect fit）
3. **OK**：保存并关闭（无 Apply 按钮）

---

## 其他工具

| 按钮 | 说明 |
|------|------|
| Profile / Aluminum Library | 创建型材 |
| End Miter | 45°斜接 |
| Extrude Cutout | 草图拉伸切除 |
| Add Vent | 通风口 |
| Pattern Fill | 填充阵列 |
| Offset Plane | 偏移面 |
| BOM / Balloons | 物料清单/气球标注 |

---

## 快捷键

| 工具 | 快捷键 |
|------|--------|
| Connector (Whistle) | M, W |
| Connector (T-Joint) | M, T |

---

## 命名规则

- 打孔结果：`{SizeName}_Cut`（如 `4040_Cut`）
- 裁剪结果：`{SizeName}_Tr`（如 `4040_Tr`）
- 未匹配到 SizeName 时回退到 Label

---

## 已知限制

- **T 型槽封盖倒角**：型材截面已有圆角处无法倒角，会自动跳过
- **裁剪延伸 Apply**：已移除（存在循环依赖问题）
- **首选项面板**：FreeCAD 1.1 的 `addPreferencePage` API 暂不支持 Python 类
- **保存时 JSON 序列化警告**：`Part::Solid/Compound` 不可 JSON 化，不影响功能

---

## 已知 Bug

### 打孔 / 裁剪延伸偶尔会多出型材

**现象**：打完孔或裁剪后，树里多出一个未命名的型材或重复的 Cut 对象。

**可能原因**：
1. `make_cut` 操作依赖对象引用名，如果操作前未 `recompute`，可能导致引用了旧的 Shape
2. 低概率情况下 FreeCAD 的 Part::Cut 会产生两个结果（一个削去另一个保留）
3. 多次 Apply 后依赖链累积，recompute 时序不确定

**规避方法**：
- 每次 Apply 后手动 `Ctrl+R` 全局刷新
- 如果多出型材，直接删除多余的对象（不依赖链的可以安全删除）
- 打孔和裁剪尽量一次 OK 完成，减少 Apply 次数

### 裁剪延伸循环依赖（DAG 错误）

`The graph must be a DAG` 出现在多次裁剪同一型材时。由于 TrimmedProfile → TrimmedBody → 另一个 TrimmedProfile 形成闭环。暂时无解，建议不要在已裁剪的 TrimmedProfile 上再做裁剪。

### T 型槽封盖无法倒角

型材截面内部已带圆角，`makeChamfer`/`makeFillet` 对已圆角边无效。外侧直角边正常。
