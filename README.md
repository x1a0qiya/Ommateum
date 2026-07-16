<p align="center">
  <h1 align="center">Ommateum</h1>
  <p align="center">通用视觉缺陷检测算法库 &mdash; 从训练到推理，开箱即用。</p>
</p>

[![Python](https://img.shields.io/badge/Python-3.10+-blue)](https://www.python.org/)
[![YOLOv11](https://img.shields.io/badge/YOLO-v11-green)](https://github.com/ultralytics/ultralytics)
[![SAM2](https://img.shields.io/badge/SAM2-Facebook%20Research-blue)](https://github.com/facebookresearch/sam2)
[![PEFT](https://img.shields.io/badge/PEFT-LoRA%2FQLoRA-orange)](https://github.com/huggingface/peft)
[![Docker](https://img.shields.io/badge/Docker-CUDA%2012.1-lightblue)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## 目录

- [项目简介](#项目简介)
- [核心功能](#核心功能)
- [技术架构](#技术架构)
- [项目结构](#项目结构)
- [快速开始](#快速开始)
- [API 文档](#api-文档)
- [相关文档](#相关文档)
- [许可证](#许可证)

---

## 项目简介

Ommateum 是一个面向缺陷检测场景的视觉算法库，整合了 YOLOv11 目标检测、SAM2 像素级分割、SAHI 切片推理等能力，并附带一个轻量 Web 前端（Flask API + 单文件 HTML）用于可视化操作与演示。

### 核心能力

| 能力 | 说明 |
|:---|:---|
| 缺陷检测 | 基于 YOLOv11 的目标检测，定位缺陷区域并输出边界框与置信度 |
| 缺陷分割 | 基于 SAM2 的 LoRA/QLoRA 参数高效微调，生成像素级缺陷掩码 |
| 数据增强 | 基于 albumentations 的在线增强管道，YOLO 标注同步变换，快速扩充小样本数据集 |
| 切片推理 | SAHI 切片辅助超推理，保持高分辨率原图不丢失小目标 |
| 可视化操作 | Flask API + 单文件 HTML 前端，提供训练、推理、结果管理的图形化界面 |

### 适用场景

- 小样本缺陷检测（几十张图片即可启动 YOLO 微调）
- 需要像素级分割的精细质检任务
- 本地 GPU/CPU 训练与推理，无需云端依赖

---

## 核心功能

### 缺陷检测 (YOLOv11)

- 小样本微调策略：默认冻结 backbone + neck（`freeze=20`），仅训练检测头，防止灾难性遗忘
- 低学习率 + cosine 衰减，关闭 mosaic/mixup 等强数据增强，保留适度 HSV 抖动和翻转
- 验证阶段 NMS IoU 阈值可通过 `--iou` 参数控制

### 缺陷分割 (SAM2 + LoRA)

- 通过 PEFT（LoRA/QLoRA）注入适配器（rank=16, DoRA），仅训练约 1% 参数，大幅降低显存占用
- QLoRA 选项（`use_quant=True`）支持 4-bit 量化，进一步降低硬件门槛
- 复合损失函数：Sigmoid Focal Loss（×20）+ Dice Loss（×1）+ IoU Prediction Loss（×1）
- YOLO 标注格式自动转换为 SAM2 prompt 格式，无需额外标注工作

### SAHI 切片推理

- 针对高分辨率（如 256×1600 钢带）图像，将原图切分成小块分别推理再合并，保持原始分辨率不丢失小目标
- 可配置切片尺寸（默认 640）和重叠比例（默认 0.2），NMS 去重合并

### 数据增强

- 基于 albumentations 的在线增强管道，自动同步变换 YOLO 标注（bbox）
- 几何变换：水平/垂直翻转、仿射变换（旋转 ±15°、缩放 0.85-1.1）
- 颜色/光照增强：亮度对比度、色相饱和度、高斯噪声、运动模糊
- 每张原图可生成 N 个增强变体，快速扩充小样本数据集

### 模型训练

- YOLO 检测模型：`scripts/identify/train.sh`，支持配置数据路径、实验名称、训练轮数
- SAM2 分割模型：`scripts/sam2/fine-tuning.sh`，LoRA/QLoRA 微调

---

## 技术架构

```
┌─────────────────────────────────────────────────────────────┐
│              可视化操作层 （Flask API + 单文件 HTML）           │
│         训练配置 / 样本管理 / 推理演示 / 结果查看                │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                      核心算法层                                │
│  ┌──────────┐   ┌──────────┐   ┌──────────────┐             │
│  │ YOLOv11  │   │  SAM2    │   │ SAHI 切片推理  │             │
│  │ 目标检测  │   │ 像素分割  │   │ 高分辨率适配   │             │
│  │ freeze=20│   │LoRA/QLoRA│   │ 切片+重叠+NMS │             │
│  └──────────┘   └──────────┘   └──────────────┘             │
│  ┌──────────────┐  ┌──────────────────┐                     │
│  │ 数据增强      │  │ 标注转换 / 评估    │                     │
│  │ albumentations│  │ YOLO↔SAM2↔COCO  │                     │
│  └──────────────┘  └──────────────────┘                     │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│              运行环境（本地 GPU/CPU 训练与推理）                  │
│         Docker (CUDA 12.1 + PyTorch 2.5.1) 或 pip 安装        │
└─────────────────────────────────────────────────────────────┘
```

详细架构设计见 [架构设计报告.md](docs/架构设计报告.md)。

### 技术栈明细

| 层级 | 技术 | 说明 |
|:---|:---|:---|
| 检测模型 | Ultralytics YOLOv11 | 目标检测，冻结 backbone 小样本微调 |
| 分割模型 | SAM2 + PEFT (LoRA/QLoRA) | 像素级掩码生成，~1% 参数微调 |
| 切片推理 | SAHI | 高分辨率图像分块推理，NMS 合并 |
| 数据增强 | albumentations | YOLO bbox 同步变换 |
| 深度学习框架 | PyTorch 2.5.1 + CUDA 12.1 | 本地 GPU/CPU 训练与推理 |
| 可视化操作 | Flask + 原生 HTML/CSS/JS | 训练配置、推理演示、结果查看 |
| 容器化 | Docker + docker-compose | 一键启动，GPU 直通 |

---

## 项目结构

```
Ommateum/
├── src/ommateum/              # 核心 Python 库
│   ├── models/                # YOLOv11 检测 + SAM2 分割训练与推理
│   │   ├── identify/          # YOLO 检测：train / evaluate / generate_result / augment_dataset
│   │   └── sam2/              # SAM2 分割：train / dataset / loss / config / test
│   └── utils/                 # SAHI 切片推理、工具函数
├── scripts/                   # 示例脚本
├── skills/ommateum-api/       # Flask API 服务 + Web 前端
│   ├── app.py                 # Flask 后端（15 个端点）
│   ├── index.html             # 单文件前端
│   ├── css/                   # 样式
│   └── js/                    # 前端逻辑 + 动态粒子背景动画
├── tests/                     # 单元测试
├── docs/                      # 架构与设计文档
│   ├── umls/                  # PlantUML 架构图（源码 + PNG）
│   └── *.md                   # 设计报告、数据模型、API 文档等
├── data/                      # 运行时数据（图片上传、训练集）
├── weights/                   # 模型权重（预训练 + 微调产出）
├── Dockerfile                 # CUDA 12.1 + PyTorch 2.5.1 镜像
├── docker-compose.yml         # GPU 直通单容器部署
├── requirements.txt           # 生产依赖
├── requirements-dev.txt       # 开发依赖
├── pyproject.toml             # 项目配置
└── LICENSE                    # MIT
```

---

## 快速开始

### 环境要求

| 依赖 | 版本 |
|:---|:---|
| Python | 3.10+ |
| Docker（推荐） | 20.10+（需 NVIDIA Container Toolkit） |
| CUDA | 12.1（GPU 推理/训练） |
| pip | 最新版 |

### Docker（推荐，支持 GPU）

```bash
docker-compose up -d
```

首次构建可启用开发依赖：

```bash
INSTALL_DEV=true docker compose build
```

### 本地安装

```bash
# 克隆仓库
git clone https://github.com/x1a0qiya/Ommateum.git
cd Ommateum

# 安装
pip install -e .
```

---

## 使用

### 训练

```bash
# YOLO 检测模型（小样本微调，冻结 backbone）
bash scripts/identify/train.sh \
    --data dataset/data.yaml \
    --name my_experiment \
    --epochs 100

# SAM2 分割模型（LoRA 微调）
bash scripts/sam2/fine-tuning.sh
```

### 推理

```python
from ultralytics import YOLO

model = YOLO("weights/yolo/trained/my_experiment_best.pt")
results = model("defect_image.jpg")
```

### API

```bash
cd skills/ommateum-api
pip install -r requirements.txt
python app.py
# → http://127.0.0.1:5000/api
```

---

## API 文档

| 方法 | 路径 | 说明 |
|:---|:---|:---|
| `GET` | `/api/models` | 可用模型列表 |
| `GET` | `/api/weights` | 可用权重列表（含训练产出） |
| `POST` | `/api/images` | 上传图片（正常/缺陷） |
| `POST` | `/api/train` | 启动训练任务 |
| `GET` | `/api/train/{id}` | 查询训练进度与指标 |
| `GET` | `/api/export/{id}` | 导出训练模型（.omt） |
| `POST` | `/api/predict` | 执行缺陷检测 |
| `GET` | `/api/tasks/{id}` | 查询检测结果 |
| `GET` | `/api/stats` | 数据集统计 |

完整 API 文档见 [docs/API.md](docs/API.md)。

---

## 相关文档

| 文档 | 说明 |
|:---|:---|
| [架构设计报告](docs/架构设计报告.md) | 系统架构总览、模块详解、全流程图、关键设计决策 |
| [数据模型设计](docs/数据模型设计.md) | 运行时内存模型（5 类记录）、持久化文件模型（YOLO/SAM2 格式） |
| [API 文档](docs/API.md) | 接口规范、请求/响应格式 |

---

## 许可证

[MIT](LICENSE) © 2026 x1a0qiya

---

<p align="center">
  <b>Ommateum</b> — 让每一处缺陷，无处遁形
</p>
