# OPJU 可编辑图复现效果审查与 v3 修正说明

## 一、当前 v2 为什么仍然“能编辑但不像原图”

### 1. 没有定义源图坐标如何转换为 Origin 坐标

v2 中的 `origin_object.coordinates` 是最终数字，但没有保存这些数字是如何从原图像素得到的。只要页面尺寸、图层框、绘图区、轴范围或对数尺度稍有不同，箭头、文字和矩形就会漂移。

### 2. 所有复杂几何都倾向于使用 GraphObject

GraphObject 的 Page、Layer Frame、Layer and Scales 三种附着方式在图层移动、缩放和轴范围变化时行为不同。将箭头、边界、阴影区和多段路径全部作为 GraphObject，会放大坐标和缩放差异。

### 3. OPJU 回读验证太浅

v2 的回读主要确认：

- 项目能打开；
- 页面、图层和对象名称存在；
- 数量大致正确。

但没有严格核对：

- 页面和图层尺寸；
- 轴类型、范围、步长；
- Plot 数据绑定和绘制顺序；
- 对象坐标、附着方式、z-order；
- 字体、线宽、颜色和透明度。

因此视觉错误仍可能通过结构 gate。

### 4. 图像 QA 没有真正分离几何误差与样式误差

全图 MAE 或内容裁剪后的误差无法回答：到底是图层框错了、坐标轴错了，还是字体颜色错了。修正时容易同时修改很多参数，导致反复振荡。

## 二、v3 的核心修改

### 1. 增加源图像素空间

新增：

```yaml
reference_geometry:
  image: references/fig01.png
  size_px: [1200, 800]
  page_bbox_px: [0, 0, 1200, 800]
  panels:
    panel_a:
      frame_bbox_px: [100, 60, 1100, 700]
      plot_bbox_px: [120, 80, 1080, 680]
```

注释可以直接保存原图测量坐标：

```yaml
source_geometry:
  coordinate_space: source_px
  coordinates_px: [312, 200, 408, 560]
```

`compile_reference_geometry.py` 会将其转换为：

- Page normalized；
- Layer normalized；
- mm；
- 最终轴刻度坐标。

支持线性、log10、ln 和 log2 轴。

### 2. 按对象选择可编辑实现路线

新增 `editable_route`：

- `data_plot`：箭头、线段、边界、多边形、阈值线、阴影路径等需要严格跟随数据坐标的几何；
- `graph_object`：文字、简单页面装饰和固定于图层框的对象；
- `template_object`：已经在最小种子模板中验证稳定的对象。

建议将“几何重、文字轻”的对象拆开。几何对象优先用工作表数据驱动的 overlay plot，文字仍用命名 GraphObject。

### 3. 修正构建顺序

新的计划顺序是：

```text
加载最小种子
→ 先删除占位曲线
→ 设置页面和图层基础样式
→ 设置页面/图层几何
→ 添加真实 Plot 并立即设置 Plot 样式
→ 只 Rescale 一次
→ 设置最终轴范围、步长和样式
→ 冻结轴并保存轴快照
→ 添加 no-rescale overlay plot / GraphObject
→ 每添加一个对象都验证轴快照未变化
→ 导出、保存、重开、结构回读、再次导出
```

v2 中“先添加真实 Plot，再删除模板占位 Plot”的顺序存在误删或索引漂移风险，v3 已改为先清除占位对象。

### 4. 增加真实执行计划调度器

v2 只有 JSON 操作列表，没有真正的 dispatcher。v3 新增：

```text
scripts/execute_operation_plan.py
```

它要求项目本地提供经过 Origin 版本验证的 adapter，并逐条记录：

- 是否支持操作；
- 使用的 route；
- 返回状态；
- 异常和堆栈；
- 最终释放状态。

没有 adapter 时只能 `--dry-run`，不会再把“成功编译计划”误当作“成功生成 OPJU”。

### 5. OPJU 回读升级为数值契约

严格 v3 回读会比较：

- Page `size_mm`；
- Layer `bbox_mm`；
- X/Y 轴标题、scale、limits；
- Plot 类型、数据引用、列映射、draw order、部分样式；
- GraphObject 类型、attach、units、coordinates、z-order、文字和样式。

容差通过：

```yaml
contracts:
  tolerances:
    geometry_mm: 0.25
    coordinate: 0.0001
    style_numeric: 0.05
```

控制。

### 6. 图像 QA 升级为“几何 + 注册 + ROI”

`image_qa_v3.py` 增加：

- 从边缘估计背景，不再只假设纯白；
- 内容框几何差异；
- 小范围平移注册；
- MAE、RMSE、SSIM、edge F1、颜色直方图；
- 每个 panel 的 ROI 单独报告。

### 7. 修正过程按阶段冻结

`generate_visual_correction_plan.py` 强制顺序：

1. 结构；
2. 几何；
3. 字体和颜色。

结构失败时停止图像调参；几何通过后不再随意改变页面和轴；最后才调字体、线宽、颜色和透明度。

## 三、建议在 Windows + Origin 环境实现的 adapter 路由

推荐组合：

| 操作 | 首选 route |
|---|---|
| workbook、worksheet、matrix | `originpro` |
| 新建 graph、layer、普通 plot | `originpro` |
| 轴范围和基本标题 | `originpro` |
| 低层 Plot 样式、右轴、特殊刻度 | 经验证的 LabTalk |
| 命名 GraphObject | LabTalk `draw` / GObject 属性 |
| 保存、重开、导出 | `originpro` |
| 详细结构回读 | `originpro` 枚举 + LabTalk 属性读取 |

不要把整个流程固定为单一 MCP 或单一 Python API；以 capability profile 为准。

## 四、最优先落地顺序

1. 使用 `editable_reproduction_v3.yaml` 重写一个最典型、最难复现的图。
2. 实现一个只支持该图所需操作的 Origin 2022 adapter，不要一开始覆盖所有图型。
3. 生成真实 `opju_inspection.json`，先让详细结构契约通过。
4. 用重开后的第二次导出运行 `image_qa_v3.py`。
5. 根据 correction plan 每轮只修改一类参数。
6. 经过 2–3 个不同图型后，再将 adapter 中稳定的实现提升为通用能力。

## 五、当前包已经验证的内容

- v3 FigureSpec 严格校验；
- 源像素到轴刻度/图层归一化坐标转换；
- 占位 Plot 删除顺序；
- 冻结轴后添加 overlay 的计划顺序；
- 详细 OPJU 契约的通过与失败检测；
- 图像平移和内容框差异检测；
- v2 旧规格兼容；
- Python 脚本编译。

尚未在此环境验证的是实际 Origin 2022 adapter 对 COM、LabTalk、对象属性和 OPJU 回读的具体实现，这必须在安装了 Origin 的 Windows 环境中完成。
