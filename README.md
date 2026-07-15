<p align="center">
  <h1 align="center">Ommateum</h1>
  <p align="center">通用视觉缺陷检测平台 &mdash; 从训练到推理，一站式完成。</p>
</p>

---

## 特性

- **缺陷检测** &nbsp;基于 YOLOv11 的目标检测，精确定位缺陷区域
- **缺陷分割** &nbsp;SAM2 的 LoRA/QLoRA 微调，输出像素级掩码
- **用户数据训练** &nbsp;上传自己的正常/缺陷图片，在线训练专属模型
- **RESTful API** &nbsp;完整的模型管理、训练、推理接口，可集成到任意前端
- **Web 前端** &nbsp;内置单文件 HTML 界面，浅色清新主题，零构建步骤

## 快速开始

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
# Python ≥ 3.10
pip install -e .
```

```bash
# Windows 一键启动
start.bat        # CMD
# 或
.\start.ps1      # PowerShell
```

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

| 端点 | 说明 |
|---|---|
| `GET /api/models` | 可用模型列表 |
| `GET /api/weights` | 可用权重列表（含训练产出） |
| `POST /api/images` | 上传图片（正常/缺陷） |
| `POST /api/train` | 使用用户数据训练模型 |
| `GET /api/train/{id}` | 查询训练进度 |
| `GET /api/export/{id}` | 导出训练好的模型 |
| `POST /api/predict` | 执行缺陷检测 |
| `GET /api/stats` | 数据集与训练统计 |

完整 API 文档见 [docs/API.md](docs/API.md)。

## 项目结构

```
ommateum/
├── src/ommateum/
│   ├── models/           # YOLOv11 + SAM2 训练与推理
│   ├── utils/            # SAHI 切片推理
├── scripts/              # 训练 / 评估 / 数据合成脚本
├── skills/ommateum-api/  # Flask API + Web 前端
├── tests/                # 单元测试
├── docs/                 # 架构与设计文档
├── Dockerfile
└── docker-compose.yml
```

## 技术栈

- **检测 / 分割** — YOLOv11、SAM2
- **后端** — Python Flask
- **前端** — 原生 HTML + CSS + JavaScript（零框架）
- **部署** — Docker + nginx 反向代理

## 许可证

[MIT](LICENSE) © 2026 x1a0qiya
