# Ommateum 视觉缺陷检测平台

基于 RESTful API 的视觉缺陷检测平台，支持选择模型、选择权重、上传正确图片与缺陷图片、**使用用户数据训练专属模型**、**导出训练成果**、**在线使用训练模型推理**。浅色清新主题。

> 参考项目：[github.com/x1a0qiya/Ommateum](https://github.com/x1a0qiya/Ommateum)（仓库当前不可访问，本实现基于功能需求设计完整 API 契约）
> 前端设计方法论参考：[garden-skills / web-design-engineer](../garden-skills/skills/web-design-engineer)

## 架构

```
┌─────────────────────────────────────────────────┐
│                 浏览器 (localhost:80)              │
│  nginx 静态托管 html/ommateum/index.html          │
│         + /api/ 反向代理 → Flask :5000            │
└────────────────────┬────────────────────────────┘
                     │ HTTP
┌────────────────────▼────────────────────────────┐
│           Flask API Server (:5000)               │
│  GET  /api/models      模型列表                   │
│  GET  /api/weights     权重列表                   │
│  POST /api/images      图片上传 (normal/defect)   │
│  POST /api/predict     缺陷检测推理               │
│  GET  /api/tasks/{id}  任务状态                   │
│  GET  /api/stats       统计                       │
└──────────────────────────────────────────────────┘
```

## 文件结构

```
skills/
├── nginx-1.31.2/
│   ├── conf/nginx.conf          ← 已配置静态托管 + API 反向代理
│   └── html/ommateum/
│       └── index.html           ← 前端网页（单文件，无构建步骤）
└── ommateum-api/
    ├── app.py                   ← Flask 后端 API
    ├── requirements.txt         ← Python 依赖
    └── uploads/                 ← 上传图片存储（自动创建）
```

## 快速启动

### 方式一：一键脚本（Windows PowerShell）

```powershell
cd c:\Users\ZCY\Desktop\skills
.\start.ps1
```

脚本会自动：安装 Python 依赖 → 启动 Flask 后端 → 启动 nginx。

### 方式二：手动分步

**1. 启动后端 API**

```bash
cd ommateum-api
pip install -r requirements.txt
python app.py
# → http://127.0.0.1:5000/api  (API 索引)
```

**2. 启动 nginx**

```bash
cd nginx-1.31.2
nginx
# → http://localhost  (前端页面)
```

> 如果 nginx 未编译，Windows 上可直接使用预编译版，或执行 `start nginx.exe`。
> 首次需确保 `conf/nginx.conf` 已更新为本项目提供的版本。

**3. 打开浏览器**

访问 **http://localhost** 即可使用。

## 功能说明

| 功能 | 操作 |
|------|------|
| 选择模型 | 左侧面板点击模型卡片（PatchCore / PaDiM / STFPM / FastFlow / GANomaly） |
| 选择权重 | 选择模型后自动加载该模型可用权重，点击切换（含训练产出） |
| 上传正确图片 | 点击/拖拽到「正确图片」上传区（绿色） |
| 上传缺陷图片 | 点击/拖拽到「缺陷图片」上传区（琥珀色） |
| **训练模型** | 在「训练与导出」面板选择模型、调整 epochs/学习率，点击「使用我的数据开始训练」 |
| **查看训练进度** | 训练中实时显示 epoch 进度、训练损失、验证损失、准确率 |
| **导出模型** | 训练完成后在已训练模型列表点击「导出模型」下载权重文件（.omt） |
| **在线使用训练模型** | 点击「在线使用」自动切换到训练权重，即可直接执行检测 |
| 执行检测 | 点击「执行缺陷检测」按钮，查看结果面板 |
| 查看结果 | 结果面板显示每张图的判定（正常/缺陷）、置信度、缺陷类型 |
| 删除图片 | 鼠标悬停图片卡片，点击右上角删除按钮 |

## RESTful API 接口

### 健康检查
```
GET /api/health
→ { "status": "ok", "service": "Ommateum API", "version": "2.0.0", ... }
```

### 获取模型列表
```
GET /api/models
→ { "models": [ { "id": "patchcore", "name": "PatchCore", ... } ], "total": 5 }
```

### 获取权重列表（含训练产出）
```
GET /api/weights?model=patchcore
→ { "weights": [ { "id": "patchcore-mvtec", "trained": false, ... }, { "id": "trained_xxx", "trained": true, ... } ] }
```

### 上传图片
```
POST /api/images (multipart/form-data)
  file: <图片>  type: normal|defect  model: patchcore (可选)  weight: patchcore-mvtec (可选)
→ { "image": { "id": "img_abc", "type": "defect", "url": "/api/files/img_abc.png", ... } }
```

### 删除图片
```
DELETE /api/images/{id}
```

### 使用用户数据训练模型
```
POST /api/train
{ "model": "patchcore", "epochs": 20, "lr": 0.001, "normal_image_ids": [...], "defect_image_ids": [...] }
→ { "task_id": "train_xxx", "status": "training", "estimated_seconds": 8.0 }
```

### 查询训练进度
```
GET /api/train/{task_id}
→ { "status": "training|done", "current_epoch": 15, "epochs": 20, "progress": 0.75, "loss": 0.05, "val_loss": 0.07, "accuracy": 0.92, "metrics": [...] }
```

### 获取训练历史
```
GET /api/training-history
→ { "tasks": [ { "id": "train_xxx", "model": "patchcore", "status": "done", "accuracy": 0.98, "weight_id": "trained_xxx", ... } ] }
```

### 导出训练后模型
```
GET /api/export/{task_id}
→ 文件下载 (ommateum_PatchCore_trained_xxx.omt)
```

### 执行缺陷检测
```
POST /api/predict
{ "model": "patchcore", "weight": "trained_xxx", "image_ids": ["img_abc"] }
→ { "task_id": "task_xxx", "results": [ { "verdict": "defect", "confidence": 0.95, ... } ], "summary": { ... } }
```

### 查询检测任务 / 数据集统计
```
GET /api/tasks/{id}    查询检测任务状态
GET /api/stats         数据集与训练统计
GET /api/files/{name}  获取图片/模型文件
```

## 接入真实模型

当前后端为 Mock 实现（训练模拟进度，检测随机生成结果）。接入真实推理引擎时：

1. 在 `app.py` 的 `MODELS` / `WEIGHTS` 中替换为真实模型清单
2. 修改 `_mock_predict_single()` 为真实 PyTorch/ONNX 推理函数
3. 修改 `start_training()` + `get_training_status()` 接入真实训练循环
4. 修改 `_generate_model_file()` 导出真实权重格式（.pth/.onnx）
5. 返回相同 JSON 结构，前端无需改动

## 技术栈

- **前端**：原生 HTML + CSS + JavaScript（无构建步骤，无框架依赖），浅色清新主题
- **后端**：Python Flask + Flask-CORS + Pillow
- **部署**：nginx 反向代理 + 静态托管
- **设计**：清新天空蓝强调色，参考 garden-skills web-design-engineer 方法论

## 许可

MIT
