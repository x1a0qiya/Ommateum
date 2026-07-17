<p align="center">
  <h1 align="center">Ommateum</h1>
  <p align="center">
    <a href="https://github.com/x1a0qiya/ommateum"><img alt="GitHub" src="https://img.shields.io/badge/version-0.1.0-4F46E5?style=flat-square"></a>
    <a href="https://www.python.org/downloads/"><img alt="Python" src="https://img.shields.io/badge/python-≥3.10-blue?style=flat-square&logo=python&logoColor=white"></a>
    <a href="https://pytorch.org/"><img alt="PyTorch" src="https://img.shields.io/badge/PyTorch-≥2.5.1-EE4C2C?style=flat-square&logo=pytorch&logoColor=white"></a>
    <a href="https://github.com/ultralytics/ultralytics"><img alt="YOLO" src="https://img.shields.io/badge/YOLO-v11-00CED1?style=flat-square"></a>
    <a href="https://github.com/facebookresearch/sam2"><img alt="SAM2" src="https://img.shields.io/badge/SAM2-LoRA%2FDoRA-7C3AED?style=flat-square"></a>
    <a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/license-MIT-green?style=flat-square"></a>
  </p>
  <p align="center">
    通用视觉缺陷检测平台 — 从数据上传、在线训练到像素级推理，一站式完成。
  </p>
</p>

---

## 目录

- [特性](#特性)
- [快速开始](#快速开始)
- [使用指南](#使用指南)
  - [训练](#训练)
  - [推理](#推理)
  - [SAHI 切片推理](#sahi-切片推理)
  - [数据增强](#数据增强)
  - [格式转换](#格式转换)
- [Web 前端](#web-前端)
- [API 参考](#api-参考)
- [项目结构](#项目结构)
- [技术栈](#技术栈)
- [开发](#开发)
- [许可](#许可)

## 特性

| 模块 | 能力 | 实现方式 |
|------|------|----------|
| **缺陷检测** | 目标检测，输出边界框与类别 | YOLOv11 微调，支持冻结 backbone |
| **缺陷分割** | 像素级语义掩码，精确描绘缺陷轮廓 | SAM2 + LoRA / DoRA 参数高效微调 |
| **SAHI 切片** | 超大分辨率图像滑动窗口推理 | 自动切块 → 逐块检测 → NMS 合并 |
| **在线训练** | Web 端上传数据集，一键训练 | Flask + 后台线程 + SSE 实时进度推送 |
| **数据增强** | 自动合成缺陷样本，扩充小数据集 | SDG（Copy-Paste 策略）+ Albumentations |
| **格式转换** | COCO ↔ YOLO 标注格式互转 | `coco2yolo` 工具函数 |
| **单图识别** | 上传单张图片即时判定 | 前端自动压缩 → 上传 → SSE 返回结果 |
| **模型管理** | 权重视图/选择/导出，训练历史追溯 | 文件树扫描 + RESTful 接口 |

### 核心工作流

```
上传数据集  →  数据增强（可选）  →  YOLO 检测模型微调  →  SAM2 分割模型微调
                                                ↓
                           Web 前端推理 / API 调用  ←  导出权重
```

Ommateum 将检测 YOLO 模型与分割 SAM2 模型串联：YOLO 定位缺陷区域后，SAM2 在候选区域内生成高质量像素级掩码。训练阶段支持冻结主干、LoRA/DoRA 等高效微调策略，大幅降低显存占用与训练时间。

## 快速开始

### 环境要求

- **操作系统**：Windows / Linux / macOS
- **Python**：≥ 3.10
- **PyTorch**：≥ 2.5.1（GPU 训练需 CUDA 12.1+）
- **硬件**：
  - 推理：CPU 可用，GPU 推荐
  - 训练（YOLO）：≥ 8 GB 显存
  - 训练（SAM2 LoRA）：≥ 12 GB 显存

### Docker（推荐，支持 GPU）

`Dockerfile` 基于 `pytorch/pytorch:2.5.1-cuda12.1-cudnn9-devel` 构建，预装 OpenCV 等系统依赖。

```bash
# 启动容器（含 GPU 直通）
docker-compose up -d

# 带开发依赖构建（pytest、ruff、mypy 等）
INSTALL_DEV=true docker compose build
```

容器映射端口：

| 端口 | 服务 |
|------|------|
| `5000` | Flask Web API + 前端界面 |
| `7860` | Gradio 交互式标注演示 |
| `8000` | 预留服务端口 |

容器内 `/Ommateum` 目录与宿主机实时同步，可边开发边调试。

### 本地安装

```bash
# 1. 创建虚拟环境
python -m venv venv
source venv/bin/activate      # Linux / macOS
venv\Scripts\activate         # Windows

# 2. 安装核心库
pip install -e .

# 3. 安装完整开发依赖
pip install -r requirements-dev.txt
```

`requirements-dev.txt` 包含全部依赖：`ultralytics`、`peft`、`transformers`、`accelerate`、`Flask`、`gradio`、`albumentations`、`sahi` 等。

### 启动 Web 服务

```bash
cd skills/ommateum-api
python app.py
```

首次启动会自动下载 YOLOv11 预训练权重到 `weights/pretrained/` 目录。服务运行在：

- **Web 前端**：http://127.0.0.1:5000
- **API**：http://127.0.0.1:5000/api
- **健康检查**：http://127.0.0.1:5000/api/health

## 使用指南

### 训练

#### YOLO 检测模型

小样本场景下冻结 backbone 底层，仅微调高层与检测头：

```bash
# 使用脚本一键训练
bash scripts/identify/train.sh \
    --data dataset/data.yaml \
    --name my_experiment \
    --epochs 100 \
    --batch 16
```

或通过 Python 直接调用：

```python
from src.ommateum.models.train import train_model
from argparse import Namespace

train_model(Namespace(
    data_yaml="dataset/data.yaml",
    weights_output_path="weights/yolo/my_model",
    yolo_epochs=100,
    imgsz=640,
    yolo_batch_size=16,
    device="cuda",
    freeze=20,          # 冻结前 20 层
    patience=10,        # 10 epoch 无提升则早停
))
```

#### SAM2 分割模型

在 YOLO 检测结果的基础上，对候选区域进行像素级分割微调：

```bash
bash scripts/sam2/fine-tuning.sh
```

关键参数说明：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `lora_rank` | 16 | LoRA 低秩矩阵维度，越大拟合能力越强 |
| `use_dora` | True | 是否启用 DoRA（Directional LoRA），通常精度更高 |
| `sam2_lr` | 0.0002 | SAM2 微调学习率 |
| `sam2_epochs` | 8 | 分割模型训练轮数 |
| `sam2_batch_size` | 8 | 分割模型批大小 |

### 推理

#### 命令行

```bash
# 批量检测
bash scripts/identify/test.sh
```

#### Python API

```python
from ultralytics import YOLO

# 加载训练好的 YOLO 模型
model = YOLO("weights/yolo/trained/best.pt")
results = model("defect_image.jpg")

for r in results:
    for box in r.boxes:
        print(f"类别: {r.names[int(box.cls)]}, 置信度: {box.conf:.3f}, 坐标: {box.xyxy[0].tolist()}")
```

#### 端到端分割推理

```python
from src.ommateum.models.test import segment
from argparse import Namespace

segment(Namespace(
    images_dir="dataset/batch_xxx/images",
    yolo_model_path="weights/yolo/trained/best.pt",
    sam2_model_path="facebook/sam2-hiera-tiny",
    lora_path="weights/sam2_lora",
    output_mask_path="dataset/batch_xxx/masks",
    device="cuda",
    imgsz=1024,
))
```

### SAHI 切片推理

适用于分辨率极高（如 4000×3000 以上）的工业图像。SAHI 将原始图像切为带重叠的切片，在每一切片上独立检测，最后用 NMS 合并全局结果：

```python
from src.ommateum.utils.sahi import slice_inference

# 自定义切片参数
slice_inference(
    image_path="large_image.jpg",
    model_path="weights/yolo/best.pt",
    slice_height=640,
    slice_width=640,
    overlap_ratio=0.2,       # 切片之间的重叠比例
    confidence_threshold=0.25,
)

# 或直接运行示例脚本
python scripts/test_sahi.py
```

### 数据增强

SDG（Synth to Defect Generation）模块可将正常样本通过 Copy-Paste 策略合成缺陷样本，解决小样本场景下缺陷数据不足的问题：

```python
from src.ommateum.utils.augment_dataset import sdg
from argparse import Namespace

sdg(Namespace(
    images="dataset/batch_xxx/images",     # 正常样本目录
    labels="dataset/batch_xxx/labels",     # YOLO 标签目录（可选）
    masks="dataset/batch_xxx/masks",       # 掩码目录（可选）
    output="dataset/batch_xxx/augmented",  # 增强输出目录
    num_aug=5,                             # 每张原始图生成 5 张增强图
))
```

模块底层使用 `albumentations` 实现丰富的图像变换（随机旋转、翻转、亮度/对比度调整、弹性变形等），并支持掩码同步变换。

### 格式转换

```python
from src.ommateum.utils.coco2yolo import coco2yolo

# COCO JSON → YOLO 标注
coco2yolo("dataset/annotations.json")
# 在 colabels/ 目录下生成 .txt 标签文件
```

## Web 前端

内置的单页管理面板通过锚点分屏滚动实现多视图切换，主要功能模块：

### 训练面板

- 上传图片压缩包（ZIP）+ 标注 JSON + 掩码 ZIP
- 批次管理：选择、删除、查看文件详情
- 超参数配置面板（YOLO + SAM2 双组参数），含实时的输入范围校验
- 训练进度实时轮询，进度条 + 当前 Epoch / Stage 展示
- 训练完成后自动刷新权重列表

### 推理面板

- **批次检测**：选择已有数据批次 → 选模型权重 → 一键执行，SSE 实时推送状态
- **单图识别**：拖拽 / 点击上传单张图片，前端自动 ZIP 打包上传，即时返回判读结果（正常/缺陷、置信度、缺陷类型）
- **结果导出**：JSON 报告下载 / 模型权重 ZIP 导出

### 模型管理

- 模型卡片 + 权重视图，支持切换与反选
- 训练产出一键导出模型文件
- 训练历史列表，含“在线使用”快捷跳转

### 界面特性

- 复眼主题 Splash Screen 启动动画（Canvas 绘制六边形网格，带呼吸感与视点追踪）
- 动态粒子背景（带阻尼衰减，鼠标斥力交互）
- 卡片 3D Tilt 悬停效果
- Scroll Reveal 入场动画
- Toast 通知系统
- 实时 API 在线状态指示
- 错误日志面板（时间 / 类型 / 端点 / Traceback）

## API 参考

所有 API 以 `/api` 为前缀，返回统一的 JSON 格式：

```json
{
  "status": "ok",
  "timestamp": "2026-07-17T12:00:00",
  "data": { ... }
}
```

错误响应：

```json
{
  "status": "error",
  "timestamp": "2026-07-17T12:00:00",
  "error": "错误描述"
}
```

### 系统

| 方法 | 端点 | 说明 |
|------|------|------|
| `GET` | `/api/health` | 服务健康检查，返回版本号与各模块状态 |

### 模型与权重

| 方法 | 端点 | 参数 | 说明 |
|------|------|------|------|
| `GET` | `/api/models` | — | 扫描 `weights/` 目录，返回所有模型配置列表 |
| `GET` | `/api/weights` | `?model=<id>` | 查询指定模型下的所有权重文件（含训练产出） |

### 数据集

| 方法 | 端点 | 参数 | 说明 |
|------|------|------|------|
| `GET` | `/api/dataset` | — | 列出所有已上传的数据批次及文件信息 |
| `POST` | `/api/dataset` | FormData: `images_zip`（必选）、`annotation_json`（可选）、`masks_zip`（可选） | 上传数据集，返回批次 ID |
| `GET` | `/api/images` | `?name=<batch>` | 查询指定批次的图片列表 |
| `GET` | `/api/preview/<batch>/<filename>` | — | 预览批次中某张原始图片 |
| `DELETE` | `/api/batches/<id>` | — | 删除指定批次及其全部文件 |

### 检测

| 方法 | 端点 | 请求体 | 说明 |
|------|------|------|------|
| `POST` | `/api/predict` | `{"batch_name":"...", "weight":"..."}` | 提交异步检测任务，返回 `task_id` |
| `GET` | `/api/task/<id>` | — | 查询任务状态与结果（含缺陷/正常判读） |
| `GET` | `/api/task-stream/<id>` | — | SSE 事件流，任务完成时推送 `completed` / `failed` |

### 训练

| 方法 | 端点 | 请求体 | 说明 |
|------|------|------|------|
| `POST` | `/api/train` | `{"batch_name":"...", "params":{...}}` | 提交异步训练任务，返回 `task_id` |
| `GET` | `/api/train/<id>` | — | 查询训练进度（当前 epoch / 阶段 / 损失） |
| `GET` | `/api/training-history` | — | 获取所有已完成/进行中训练任务的摘要 |
| `GET` | `/api/export/<id>` | — | 下载训练产出的 ZIP 压缩包 |

### 统计与日志

| 方法 | 端点 | 参数 | 说明 |
|------|------|------|------|
| `GET` | `/api/stats` | — | 汇总：已训练权重数、数据批次总数等 |
| `GET` | `/api/logs/errors` | `?limit=50` | 查看最近 N 条服务端错误日志 |
| `DELETE` | `/api/logs/errors` | — | 清空全部错误日志 |

## 项目结构

```
ommateum/
├── src/ommateum/
│   ├── __init__.py
│   ├── config.py               # 全局配置
│   ├── main.py                 # CLI 入口
│   ├── models/
│   │   ├── __init__.py
│   │   ├── test.py             # 统一推理入口（YOLO → SAM2 串联）
│   │   ├── train.py            # 统一训练入口（数据集预检 → YOLO → SAM2）
│   │   ├── identify/           # YOLOv11 检测子模块
│   │   │   ├── train.py        # 训练流程（冻结 backbone、早停、学习率调度）
│   │   │   ├── evaluate.py     # mAP / 精确率 / 召回率评估
│   │   │   └── generate_result.py  # 检测结果 JSON 生成
│   │   └── sam2/               # SAM2 分割子模块
│   │       ├── config.py       # SAM2 模型配置（tiny / small / base+ / large）
│   │       ├── dataset.py      # 掩码数据集加载器
│   │       ├── loss.py         # Dice + BCE 混合损失
│   │       ├── tools.py        # 辅助工具函数
│   │       ├── train.py        # LoRA / DoRA 微调训练流程
│   │       └── test.py         # 分割推理与掩码后处理
│   └── utils/
│       ├── __init__.py
│       ├── augment_dataset.py  # SDG 数据增强（Copy-Paste + Albumentations）
│       ├── coco2yolo.py        # COCO JSON ↔ YOLO .txt 格式转换
│       ├── generate_data_yaml.py   # 自动生成 dataset data.yaml
│       └── sahi.py             # SAHI 切片推理封装
│
├── scripts/                    # Shell 训练 / 测试 / 切片脚本
│   ├── identify/
│   │   ├── train.sh            # YOLO 检测训练
│   │   └── test.sh             # YOLO 检测测试
│   ├── sam2/
│   │   ├── fine-tuning.sh      # SAM2 LoRA 微调
│   │   └── test.sh             # SAM2 分割测试
│   ├── segment.sh              # 端到端检测 + 分割
│   ├── train.sh                # 统一训练入口
│   ├── test.sh                 # 统一测试入口
│   └── test_sahi.py            # SAHI 切片推理示例
│
├── skills/ommateum-api/        # Flask API + Web 前端
│   ├── app.py                  # Flask 路由注册（26 个端点）
│   ├── serves.py               # 业务逻辑（健康检查、训练/推理任务调度）
│   ├── api_utils.py            # 文件上传/扫描/删除、数据读取等工具
│   ├── logger_config.py        # 错误日志持久化与查询
│   ├── models.py               # Pydantic 数据模型
│   ├── index.html              # SPA 单页前端
│   ├── css/style.css           # 浅色主题样式
│   ├── js/main.js              # 前端逻辑（粒子背景、API 调用、UI 交互）
│   ├── favicon.svg             # 站点图标
│   ├── weights/                # 预训练与训练产出权重
│   │   └── pretrained/         # YOLO 初始权重（首次启动自动下载）
│   └── dataset/                # 用户上传的数据集批次
│
├── tests/                      # 单元测试
│   ├── conftest.py
│   ├── test_main.py
│   └── __init__.py
│
├── docs/                       # 架构设计文档（PlantUML + Markdown）
├── pyproject.toml              # 项目元数据与工具配置
├── requirements.txt            # 生产依赖
├── requirements-dev.txt        # 开发依赖
├── Dockerfile                  # Docker 镜像构建
├── docker-compose.yml          # Docker 编排（GPU 直通 + 端口映射）
└── LICENSE                     # MIT 许可证
```

## 技术栈

| 层次 | 技术 | 版本要求 |
|------|------|----------|
| 目标检测 | [Ultralytics YOLOv11](https://github.com/ultralytics/ultralytics) | ≥ 8.3.0 |
| 语义分割 | [SAM2](https://github.com/facebookresearch/sam2) (LoRA / DoRA) | — |
| 参数高效微调 | [PEFT](https://github.com/huggingface/peft) | ≥ 0.12.0 |
| 数据增强 | [Albumentations](https://albumentations.ai/) | ≥ 1.4.0 |
| 切片推理 | [SAHI](https://github.com/obss/sahi) | latest |
| 标注工具 | [supervision](https://supervision.roboflow.com/) | ≥ 0.19.0 |
| 图像处理 | OpenCV、Pillow、scikit-image | — |
| 深度学习框架 | PyTorch、Accelerate | PyTorch ≥ 2.5.1 |
| 后端框架 | Flask + flask-cors | ≥ 3.0 |
| 实时推送 | Server-Sent Events (SSE) | 原生实现 |
| 前端 | 原生 HTML5 + CSS3 + ES6 JavaScript | 零框架依赖 |
| 容器化 | Docker + docker-compose | NVIDIA Container Toolkit |
| 测试 | pytest + pytest-cov | ≥ 8.0 |
| 代码质量 | ruff、mypy | ≥ 0.5 / ≥ 1.10 |

## 开发

```bash
# 安装开发依赖
pip install -r requirements-dev.txt

# 运行测试
pytest tests/ -v --cov=src

# 代码检查
ruff check src/ tests/ scripts/
mypy src/
```

## 许可

[MIT](LICENSE) © 2026 x1a0qiya
