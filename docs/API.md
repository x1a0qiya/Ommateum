# Ommateum API 文档
---
## 目录

- [Ommateum API 文档](#ommateum-api-文档)
  - [目录](#目录)
  - [基本信息](#基本信息)
  - [通用约定](#通用约定)
    - [认证](#认证)
    - [成功响应格式](#成功响应格式)
    - [错误响应格式](#错误响应格式)
    - [HTTP 状态码](#http-状态码)
  - [API 总览](#api-总览)
  - [详细接口说明](#详细接口说明)
    - [1. 健康检查](#1-健康检查)
    - [2. 获取模型列表](#2-获取模型列表)
    - [3. 获取权重列表](#3-获取权重列表)
    - [4. 获取图片列表](#4-获取图片列表)
    - [5. 上传图片](#5-上传图片)
    - [6. 删除图片](#6-删除图片)
    - [7. 执行缺陷检测](#7-执行缺陷检测)
    - [8. 查询检测任务结果](#8-查询检测任务结果)
    - [9. 启动训练](#9-启动训练)
    - [10. 查询训练进度](#10-查询训练进度)
    - [11. 获取训练历史](#11-获取训练历史)
    - [12. 导出训练模型](#12-导出训练模型)
    - [13. 数据统计](#13-数据统计)
    - [14. 获取静态文件](#14-获取静态文件)
    - [15. API 索引](#15-api-索引)
  - [错误处理](#错误处理)
    - [常见错误码](#常见错误码)
    - [错误响应格式](#错误响应格式-1)
    - [前端错误处理示例](#前端错误处理示例)

---

## 基本信息

| 项目 | 说明 |
|------|------|
| **基础 URL** | `http://localhost:80/api`（生产） / `http://localhost:5000/api`（开发） |
| **数据格式** | 请求与响应均为 JSON（上传图片除外） |
| **字符编码** | UTF-8 |
| **文件上传限制** | 单文件最大 **32MB** |
| **CORS** | 已启用，支持跨域请求 |

---

## 通用约定

### 认证

当前版本无需认证。后续接入可在请求头 `Authorization` 中携带 Token。

### 成功响应格式

```json
{
  "status": "ok",
  "timestamp": "2026-07-11T01:23:45+00:00",
  "data": { ... }
}
```

> 所有响应均含 `timestamp`（ISO 8601 UTC）。`message` 字段仅个别接口（如上传成功）返回，并非每个接口都有。

### 错误响应格式

```json
{
  "status": "error",
  "error": "具体的错误描述",
  "timestamp": "2026-07-11T01:23:45+00:00"
}
```

> 错误类型由 **HTTP 状态码**区分，响应体中**不含 `code` 字段**（前端应读取 `error` 字段，而非 `message`）。

### HTTP 状态码

| 状态码 | 含义 |
|--------|------|
| 200 | 请求成功 |
| 400 | 请求参数缺失或格式错误 |
| 404 | 资源不存在 |
| 413 | 上传文件超过大小限制 |
| 500 | 服务端内部错误 |

---

## API 总览

| 方法 | 路径 | 用途 |
|------|------|------|
| `GET` | `/api` | API 索引（列出所有端点） |
| `GET` | `/api/health` | 健康检查 |
| `GET` | `/api/models` | 获取可用模型列表 |
| `GET` | `/api/weights?model={id}` | 获取指定模型的权重列表 |
| `GET` | `/api/images?type={normal\|defect}` | 获取图片列表 |
| `POST` | `/api/images` | 上传图片 |
| `DELETE` | `/api/images/{img_id}` | 删除图片 |
| `POST` | `/api/predict` | 执行缺陷检测 |
| `GET` | `/api/tasks/{task_id}` | 查询检测任务结果 |
| `POST` | `/api/train` | 启动训练 |
| `GET` | `/api/train/{task_id}` | 查询训练进度 |
| `GET` | `/api/training-history` | 获取训练历史 |
| `GET` | `/api/export/{task_id}` | 导出训练模型文件 |
| `GET` | `/api/stats` | 数据统计 |
| `GET` | `/api/files/{filename}` | 获取静态文件 |

---

## 详细接口说明

### 1. 健康检查

检测 API 服务是否正常运行。

```
GET /api/health
```

**请求示例**：

```bash
curl http://localhost:5000/api/health
```

**响应示例**：

```json
{
  "status": "ok",
  "data": {
    "service": "Ommateum API",
    "version": "2.0.1",
    "models": 1,
    "images": 12,
    "trained_weights": 0
  }
}
```

> 以上数值为运行时实时计数（随上传/训练变化），示例仅供参考。

| 字段 | 类型 | 说明 |
|------|------|------|
| `models` | number | 可用模型数量 |
| `images` | number | 已上传图片总数 |
| `trained_weights` | number | 已训练权重数量 |

---

### 2. 获取模型列表

获取平台支持的所有缺陷检测模型。

```
GET /api/models
```

**请求示例**：

```bash
curl http://localhost:5000/api/models
```

**响应示例**：

```json
{
  "status": "ok",
  "data": {
    "models": [
      {
        "id": "yolov11",
        "name": "YOLOv11",
        "description": "轻量级实时目标检测与分割",
        "architecture": "Ultralytics YOLOv11",
        "input_size": [640, 640]
      }
    ],
    "total": 1
  }
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `models[].id` | string | 模型唯一标识符 |
| `models[].name` | string | 模型展示名称 |
| `models[].description` | string | 模型简介 |
| `models[].architecture` | string | 网络架构描述 |
| `models[].input_size` | number[] | 输入图片尺寸 `[宽, 高]` |
| `total` | number | 模型总数 |

---

### 3. 获取权重列表

获取指定模型的所有可用权重（含系统预制权重 + 用户训练产出）。

```
GET /api/weights?model={model_id}
```

**查询参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `model` | string | 是 | 模型 ID，如 `yolov11` |

**请求示例**：

```bash
curl "http://localhost:5000/api/weights?model=yolov11"
```

**响应示例**：

```json
{
  "status": "ok",
  "data": {
    "model_id": "yolov11",
    "models": [
      {
        "id": "yolov11n",
        "name": "yolo11n 默认权重",
        "size_mb": 5.4,
        "accuracy": 0.952,
        "trained": false
      },
      {
        "id": "trained_abc123",
        "name": "用户训练权重 · 30正常+15缺陷 · 20epoch",
        "size_mb": 85.3,
        "accuracy": 0.937,
        "dataset": "用户数据 (30正常 + 15缺陷)",
        "trained": true,
        "task_id": "train_abc123",
        "epochs": 20,
        "lr": 0.001,
        "path": "/models/trained_abc123.pt",
        "created_at": "2026-07-08T12:00:00Z"
      }
    ],
    "total": 2
  }
}
```

**字段说明**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `weights[].id` | string | 权重唯一标识符 |
| `weights[].name` | string | 权重名称 |
| `weights[].size_mb` | number | 文件大小（MB） |
| `weights[].accuracy` | number | 权重准确率（预置与训练产出均包含） |
| `weights[].trained` | boolean | 是否为用户训练产出 |
| `weights[].dataset` | string | （训练权重）训练所用数据集描述 |
| `weights[].task_id` | string | （训练权重）关联的训练任务 ID |
| `weights[].epochs` | number | （训练权重）训练轮数 |
| `weights[].lr` | number | （训练权重）学习率 |
| `weights[].path` | string | （训练权重）权重文件相对路径 |
| `weights[].created_at` | string | （训练权重）创建时间 ISO 8601 |

---

### 4. 获取图片列表

获取已上传的图片列表，可按批次名称进行筛选。

```
GET /api/images?name={batch_name}
```

**查询参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | 是 | 筛选指定批次名称（如 `batch_20260714`）|

**请求示例**：

```bash
curl "http://localhost:5000/api/images?name=batch_20260714"
```

**响应示例**：

```json
{
  "status": "ok",
  "data": {
    "images": [
      {
        "id": "img_a1b2c3d4",
        "name": "sample_001.jpg",
        "batch_name": "batch_20260714",
        "size_kb": 245,
        "url": "/api/files/img_a1b2c3d4.jpg",
        "width": 224,
        "height": 224,
        "uploaded_at": "2026-07-08T11:30:00Z"
      }
    ],
    "total": 1
  }
}
```

**响应字段说明**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `images[].id` | string | 图片唯一标识符 |
| `images[].name` | string | 原始文件名 |
| `images[].batch_name` | string | 批次名称 |
| `images[].size_kb` | number | 文件大小（KB） |
| `images[].url` | string | 图片访问 URL |
| `images[].width` | number | 图片宽度（px） |
| `images[].height` | number | 图片高度（px） |
| `images[].uploaded_at` | string | 上传时间 ISO 8601 |

---

### 5. 上传训练文件

上传正常样本图片包、COCO 格式标注文件，以及可选的 Mask 图像包。
如果不上传标注文件则标记为测试数据集.

```
POST /api/dataset
Content-Type: multipart/form-data
```

**表单字段 (Form Data)**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `images_zip` | File | 是 | 正常图片压缩包（`.zip` 格式，支持内含 jpg / png / webp 格式图片） |
| `annotation_json` | File | 否 | COCO 格式的标注文件（`.json` 格式） |
| `masks_zip` | File | 否 | 对应的 Mask 图像压缩包（`.zip` 格式，支持内含掩码图片） |

**请求示例**：

```bash
curl -X POST http://localhost:5000/api/dataset \
  -F "images_zip=@./normal_images.zip" \
  -F "annotation_json=@./coco_annotations.json" \
  -F "masks_zip=@./mask_images.zip"
```

**响应示例**：

```json
{
  "status": "ok",
  "data": {
    "batch_id": "batch_x1y2z3w4",
    "uploaded_at": "2026-07-08T12:00:00Z",
    "images_file": {
      "name": "normal_images.zip",
      "size_kb": 15360,
      "image_count": 30
    },
    "annotation_file": {
      "name": "coco_annotations.json",
      "size_kb": 128
    },
    "masks_file": {
      "name": "mask_images.zip",
      "size_kb": 8192,
      "mask_count": 30
    }
  }
}
```

**响应字段说明**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `batch_id` | string | 本次上传生成的批次唯一标识符 |
| `uploaded_at` | string | 上传时间 (ISO 8601 格式) |
| `images_file.name` | string | 正常图片压缩包的文件名 |
| `images_file.size_kb` | number | 正常图片压缩包文件大小（KB） |
| `images_file.image_count` | number | 压缩包内解析出的图片数量 |
| `annotation_file.name` | string | 标注 json 文件名 |
| `annotation_file.size_kb` | number | 标注 json 文件大小（KB） |
| `masks_file` | object | 可选 Mask 图像压缩包的信息（未上传时该字段为 `null`） |
| `masks_file.name` | string | Mask 图像压缩包的文件名 |
| `masks_file.size_kb` | number | Mask 图像压缩包文件大小（KB） |
| `masks_file.mask_count` | number | 压缩包内解析出的 Mask 图片数量 |

---

### 6. 删除批次数据

删除指定 `name` 的批次数据，包括该批次下的所有图片、标注及关联文件。

```
DELETE /api/batches/{name}
```

**路径参数**：

| 参数 | 说明 |
|------|------|
| `name` | 批次名称（支持中英文、数字、下划线等标识符） |

**请求示例**：

```bash
curl -X DELETE http://localhost:5000/api/batches/batch_20260714
```

**响应示例**：

```json
{
  "status": "ok",
  "data": {
    "id": "batch_20260714"
  }
}
```

**前端 JavaScript 调用方式**：

```javascript
const batchName = 'batch_20260714';
const res = await fetch(`/api/batches/${encodeURIComponent(batchName)}`, { method: 'DELETE' });
const data = await res.json();
```

---

### 7. 执行缺陷检测

对指定图片执行缺陷检测推理。后端会调用真实的 YOLO 检测（`models/identify/generate_result.py`）与可选的 SAM2 分割评估（`models/sam2/test.py`，需配置 `OMMATEUM_SAM2_MODEL` 等环境变量）。

```
POST /api/predict
Content-Type: application/json
```

**请求体**：

```json
{
  "model": "yolov11",
  "weight": "yolov11n-default",
  "batch_name": "x1y2z3"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `model` | string | 是 | 模型 ID |
| `weight` | string | 是 | 权重 ID |
| `batch_name` | string[] | 是 | 待检测图片批次名称 |
| `conf` | number | 否 | 置信度阈值，默认 `0.25` |
| `iou` | number | 否 | NMS IoU 阈值，默认 `0.7` |
| `imgsz` | number | 否 | 推理输入尺寸，默认 `640` |

**请求示例**：

```bash
curl -X POST http://localhost:5000/api/predict \
  -H "Content-Type: application/json" \
  -d '{"model":"yolov11","weight":"yolov11n-default","batch_name":"x1y2z3"}'
```

**响应示例**：

```json
{
  "status": "ok",
  "data": {
      "task_id": "x1y2z3",
  }
}
```

**前端 JavaScript 调用方式**：

```javascript
const res = await fetch('/api/predict', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    model: 'yolov11',
    weight: 'yolov11n-default',
    image_ids: ['img_a1b2c3d4', 'img_e5f6g7h8']
  })
});
const data = await res.json();
const results = data.data.results;
const summary = data.data.summary;
```

---

### 8. 查询检测任务结果

查询异步检测任务的状态与结果（当前 Mock 同步返回，预留轮询机制）。

```
GET /api/tasks/{task_id}
```

**路径参数**：

| 参数 | 说明 |
|------|------|
| `task_id` | 检测任务 ID（`/predict` 返回的 `task_id`） |

**请求示例**：

```bash
curl http://localhost:5000/api/tasks/task_a1b2c3d4e5f6
```

**响应示例**

```json
{
  "status": "ok",
  "message": "Progressing..."
}
```

---

### 9. 启动训练

使用用户上传的数据启动模型训练。

```
POST /api/train
Content-Type: application/json
```

**请求体**：

```json
{
  "params": {
    "yolo_epochs": 50,
    "sam2_epochs": 8,
    "yolo_lr": 0.001,
    "pretrained": "yolo11n.pt"
  },
  "batch_name": "x1y2z3"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `params` | object | 否 | 训练超参容器（见下） |
| `params.yolo_epochs` | number | 否 | YOLO 训练轮数，范围 1~200，默认 `50` |
| `params.sam2_epochs` | number | 否 | SAM2 训练轮数，默认 `8`（需配置 SAM2 才生效） |
| `params.yolo_lr` | number | 否 | YOLO 学习率，默认 `0.001` |
| `params.pretrained` | string | 否 | 预训练权重名，默认 `yolo11n.pt` |
| `batch_name` | string | 是 | 训练图片批次 |

> 至少需要一张训练图片。`yolo_epochs` 越界（<1 或 >200）会返回 400。

**请求示例**：

```bash
curl -X POST http://localhost:5000/api/train \
  -H "Content-Type: application/json" \
  -d '{"params":{"yolo_epochs":50,"yolo_lr":0.001},"normal_image_ids":["img_n1"],"defect_image_ids":["img_d1"]}'
```

**响应示例**：

```json
{
  "status": "ok",
  "data": {
    "task_id": "train_a1b2c3d4e5f6",
    "status": "training",
    "epochs": 50,
    "normal_count": 1,
    "defect_count": 1,
    "estimated_seconds": 23.2
  }
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `task_id` | string | 训练任务 ID，用于后续轮询进度 |
| `status` | string | 任务状态：`training` |
| `estimated_seconds` | number | 预估训练时长（秒） |

**前端 JavaScript 调用方式**：

```javascript
const res = await fetch('/api/train', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    params: { yolo_epochs: 50, yolo_lr: 0.001 },
    normal_image_ids: ['img_n1'],
    defect_image_ids: ['img_d1']
  })
});
const data = await res.json();
const taskId = data.data.task_id;

// 然后用 taskId 轮询训练进度
```

---

### 10. 查询训练进度

查询训练任务的当前进度与指标。

```
GET /api/train/{task_id}
```

**路径参数**：

| 参数 | 说明 |
|------|------|
| `task_id` | 训练任务 ID |

**请求示例**：

```bash
curl http://localhost:5000/api/train/train_a1b2c3d4e5f6
```

**响应示例（训练中）**：

```json
{
  "status": "ok",
  "data": {
    "id": "train_a1b2c3d4e5f6",
    "status": "training",
    "model": "yolov11",
    "current_epoch": 7,
    "progress": 0.35,
    "loss": 0.4532,
    "val_loss": 0.4710,
    "accuracy": 0.718,
    "epochs": 20,
    "metrics": [
      { "epoch": 1, "loss": 1.723, "val_loss": 1.745, "accuracy": 0.461 },
      { "epoch": 2, "loss": 1.235, "val_loss": 1.267, "accuracy": 0.538 }
    ],
    "started_at": "2026-07-08T12:00:00Z",
    "weight_id": null,
    "final_accuracy": null
  }
}
```

**响应示例（训练完成）**：

```json
{
  "status": "ok",
  "data": {
    "id": "train_a1b2c3d4e5f6",
    "status": "done",
    "model": "yolov11",
    "current_epoch": 20,
    "progress": 1.0,
    "loss": 0.0183,
    "val_loss": 0.0241,
    "accuracy": 0.974,
    "epochs": 20,
    "metrics": [ ... ],
    "started_at": "2026-07-08T12:00:00Z",
    "completed_at": "2026-07-08T12:00:08Z",
    "weight_id": "trained_b0ae95ef",
    "final_accuracy": 0.974
  }
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `status` | string | `training`（训练中）/ `done`（已完成）/ `error`（失败） |
| `stage` | string | 当前阶段：`准备中` / `YOLO 训练` / `SAM2 训练` |
| `current_epoch` | number | 当前训练轮数 |
| `progress` | number | 进度，范围 0~1.0 |
| `loss` | number | 当前训练损失 |
| `val_loss` | number | 当前验证损失 |
| `accuracy` | number | 当前准确率（mAP@0.5） |
| `weight_id` | string\|null | 训练完成后的权重 ID，未完成时为 `null` |
| `final_accuracy` | number\|null | 最终准确率，仅 `done` 时有值 |
| `completed_at` | string\|null | 完成时间 ISO 8601 |

**前端轮询逻辑**：

```javascript
async function pollTraining(taskId) {
  while (true) {
    const res = await fetch(`/api/train/${taskId}`);
    const data = (await res.json()).data;

    // 更新进度 UI
    const pct = Math.round(data.progress * 100);
    document.getElementById('tpFill').style.width = pct + '%';
    document.getElementById('tpEpoch').textContent = data.current_epoch;
    document.getElementById('tpLoss').textContent = data.loss.toFixed(4);
    document.getElementById('tpAcc').textContent =
      (data.accuracy * 100).toFixed(1) + '%';

    if (data.status === 'done') {
      console.log(`训练完成！准确率 ${(data.final_accuracy * 100).toFixed(1)}%`);
      break;
    }
    await new Promise(r => setTimeout(r, 800));
  }
}
```

---

### 11. 获取训练历史

获取所有训练任务的记录列表。

```
GET /api/training-history
```

**请求示例**：

```bash
curl http://localhost:5000/api/training-history
```

**响应示例**：

```json
{
  "status": "ok",
  "data": {
    "tasks": [
      {
        "id": "train_a1b2c3d4e5f6",
        "model": "yolov11",
        "status": "done",
        "epochs": 20,
        "current_epoch": 20,
        "progress": 1.0,
        "accuracy": 0.974,
        "loss": 0.0183,
        "normal_count": 1,
        "defect_count": 1,
        "weight_id": "trained_b0ae95ef",
        "started_at": "2026-07-08T12:00:00Z",
        "completed_at": "2026-07-08T12:00:08Z"
      }
    ],
    "total": 1
  }
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `tasks[].id` | string | 训练任务 ID |
| `tasks[].model` | string | 模型 ID |
| `tasks[].status` | string | `training` 或 `done` |
| `tasks[].accuracy` | number | 准确率（最终值） |
| `tasks[].weight_id` | string\|null | 产出权重的 ID |
| `tasks[].normal_count` | number | 正常样本数 |
| `tasks[].defect_count` | number | 缺陷样本数 |
| `tasks[].started_at` | string | 开始时间 |
| `tasks[].completed_at` | string\|null | 完成时间 |

---

### 12. 导出训练模型

下载训练完成的模型权重文件（`.omt` 格式）。

```
GET /api/export/{task_id}
```

**路径参数**：

| 参数 | 说明 |
|------|------|
| `task_id` | 已训练完成的 task_id |

**请求示例**：

```bash
curl -OJ http://localhost:5000/api/export/train_a1b2c3d4e5f6
```

**响应**：返回二进制 `.omt` 文件下载，响应头含 `Content-Disposition: attachment`。

**前端触发下载**：

```javascript
const a = document.createElement('a');
a.href = '/api/export/train_a1b2c3d4e5f6';
a.download = 'ommateum_YOLOv11_trained_b0ae95ef.omt';
document.body.appendChild(a);
a.click();
document.body.removeChild(a);
```

---

### 13. 数据统计

获取平台全局统计数据。

```
GET /api/stats
```

**请求示例**：

```bash
curl http://localhost:5000/api/stats
```

**响应示例**：

```json
{
  "status": "ok",
  "data": {
    "total_images": 10,
    "normal_count": 6,
    "defect_count": 4,
    "total_tasks": 3,
    "total_models": 5,
    "trained_weights": 2,
    "training_tasks": 3,
    "recent_accuracy": 0.925
  }
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `total_images` | number | 图片总数 |
| `normal_count` | number | 正常样本数 |
| `defect_count` | number | 缺陷样本数 |
| `total_tasks` | number | 检测任务总数 |
| `total_models` | number | 可用模型数 |
| `trained_weights` | number | 已训练权重数 |
| `training_tasks` | number | 训练任务总数 |
| `recent_accuracy` | number | 最近平均检测准确率 |


---

### 14. 获取静态文件

获取图片或模型文件。

```
GET /api/files/{type}/{filename}     # 推荐：明确图片类别
GET /api/files/{filename}            # 兼容：自动在 normal / defect / models 目录中查找
```

**路径参数**：

| 参数 | 说明 |
|------|------|
| `type` | 可选，图片类别 `normal` 或 `defect` |
| `filename` | 文件名，如 `img_a1b2c3d4.jpg` |

> 上传图片返回的 `url` 即为 `/api/files/{type}/{filename}` 形式。

直接返回二进制文件。前端中可直接用于 `<img>` 标签：

```html
<img src="/api/files/normal/img_a1b2c3d4.jpg">
```

---

### 15. API 索引

列出所有可用端点。

```
GET /api
```

**响应示例**：

```json
{
  "status": "ok",
  "data": {
    "service": "Ommateum Visual Defect Detection API",
    "version": "2.0.1",
    "endpoints": {
      "GET    /api/health": "健康检查",
      "GET    /api/models": "获取可用模型列表",
      "GET    /api/weights?model={id}": "获取指定模型的权重列表（含训练产出）",
      "GET    /api/images?type={normal|defect}": "获取图片列表",
      "POST   /api/images": "上传图片 (multipart: file, type, model, weight)",
      "DELETE /api/images/{id}": "删除图片",
      "POST   /api/train": "使用用户数据训练模型",
      "GET    /api/train/{id}": "查询训练任务进度与状态",
      "GET    /api/training-history": "获取训练历史列表",
      "GET    /api/export/{id}": "导出训练后的模型权重文件",
      "POST   /api/predict": "执行缺陷检测",
      "GET    /api/tasks/{id}": "查询检测任务状态与结果",
      "GET    /api/stats": "数据集与训练统计",
      "GET    /api/files/{filename}": "获取图片/模型文件"
    }
  }
}
```

---

## 错误处理

### 常见错误码

| HTTP 状态码 | 错误原因 | 示例 message |
|------------|----------|-------------|
| `400` | 请求参数缺失或无效 | `"缺少 model 参数"` / `"yolo_epochs 范围 1-200"` / `"type 必须为 normal 或 defect"` |
| `404` | 资源不存在 | `"模型 'xxx' 不存在"` / `"图片不存在"` / `"训练任务不存在"` |
| `413` | 文件过大 | `"文件过大（最大 32MB）"` |
| `500` | 服务端内部错误 | `"检测执行失败: ..."` / `"训练任务 xxx 失败: ..."` |

### 错误响应格式

```json
{
  "status": "error",
  "error": "具体的错误描述",
  "timestamp": "2026-07-11T01:23:45+00:00"
}
```

### 前端错误处理示例

```javascript
async function apiCall(url, options) {
  const res = await fetch(url, options);
  const data = await res.json();

  if (data.status === 'error') {
    console.error(`[API ${res.status}] ${data.error}`);
    throw new Error(data.error);
  }
  return data.data;
}
```

---