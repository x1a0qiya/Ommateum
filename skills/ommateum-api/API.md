# Ommateum API 文档

> 视觉缺陷检测平台 — RESTful API 接口规范 v2.0.0

---

## 目录

- [基本信息](#基本信息)
- [通用约定](#通用约定)
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
- [常见用法示例](#常见用法示例)

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
  "message": "操作成功（可选）",
  "data": { ... }
}
```

### 错误响应格式

```json
{
  "status": "error",
  "message": "具体的错误描述",
  "code": 400
}
```

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
    "version": "2.0.0",
    "models": 5,
    "images": 12,
    "trained_weights": 2
  }
}
```

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
        "id": "patchcore",
        "name": "PatchCore",
        "description": "基于 WideResNet50 + Coreset 采样的特征记忆方法",
        "architecture": "WideResNet50 + Coreset",
        "input_size": [224, 224],
        "category": "feature-bank"
      }
    ],
    "total": 5
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
| `models[].category` | string | 模型分类 |
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
| `model` | string | 是 | 模型 ID，如 `patchcore` |

**请求示例**：

```bash
curl "http://localhost:5000/api/weights?model=patchcore"
```

**响应示例**：

```json
{
  "status": "ok",
  "data": {
    "model": "patchcore",
    "weights": [
      {
        "id": "patchcore_mvtec",
        "name": "MVTec AD 预训练权重",
        "size_mb": 182.5,
        "trained": false
      },
      {
        "id": "trained_abc123",
        "name": "用户训练权重 · 30正常+15缺陷 · 20epoch",
        "size_mb": 85.3,
        "dataset": "用户数据 (30正常 + 15缺陷)",
        "accuracy": 0.937,
        "trained": true,
        "task_id": "train_abc123",
        "epochs": 20,
        "lr": 0.001,
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
| `weights[].trained` | boolean | 是否为用户训练产出 |
| `weights[].accuracy` | number | （训练权重）准确率 |
| `weights[].task_id` | string | （训练权重）关联的训练任务 ID |
| `weights[].epochs` | number | （训练权重）训练轮数 |
| `weights[].lr` | number | （训练权重）学习率 |
| `weights[].created_at` | string | （训练权重）创建时间 ISO 8601 |

---

### 4. 获取图片列表

获取已上传的图片列表，可按类型筛选。

```
GET /api/images?type={normal|defect}
```

**查询参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `type` | string | 否 | 筛选 `normal`（正常）或 `defect`（缺陷），不填返回全部 |

**请求示例**：

```bash
curl "http://localhost:5000/api/images?type=normal"
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
        "type": "normal",
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

| 字段 | 类型 | 说明 |
|------|------|------|
| `images[].id` | string | 图片唯一标识符 |
| `images[].name` | string | 原始文件名 |
| `images[].type` | string | `normal` 或 `defect` |
| `images[].size_kb` | number | 文件大小（KB） |
| `images[].url` | string | 图片访问 URL |
| `images[].width` | number | 图片宽度（px） |
| `images[].height` | number | 图片高度（px） |
| `images[].uploaded_at` | string | 上传时间 ISO 8601 |

---

### 5. 上传图片

上传正常样本或缺陷样本图片。

```
POST /api/images
Content-Type: multipart/form-data
```

**表单字段**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `file` | File | 是 | 图片文件（支持 jpg / png / webp） |
| `type` | string | 是 | `normal`（正常样本）或 `defect`（缺陷样本） |
| `model` | string | 否 | 关联模型 ID（可选） |
| `weight` | string | 否 | 关联权重 ID（可选） |

**请求示例**：

```bash
curl -X POST http://localhost:5000/api/images \
  -F "file=@./defect_001.jpg" \
  -F "type=defect"
```

**响应示例**：

```json
{
  "status": "ok",
  "message": "上传成功",
  "data": {
    "image": {
      "id": "img_x1y2z3w4",
      "name": "defect_001.jpg",
      "type": "defect",
      "size_kb": 312,
      "url": "/api/files/img_x1y2z3w4.jpg",
      "width": 224,
      "height": 224,
      "uploaded_at": "2026-07-08T12:00:00Z"
    }
  }
}
```

**前端 JavaScript 调用方式**：

```javascript
const fd = new FormData();
fd.append('file', file);        // File 对象
fd.append('type', 'normal');    // 'normal' | 'defect'
if (modelId) fd.append('model', modelId);
if (weightId) fd.append('weight', weightId);

const res = await fetch('/api/images', {
  method: 'POST',
  body: fd
});
const data = await res.json();
const uploadedImage = data.data.image;
```

---

### 6. 删除图片

删除已上传的图片及其文件。

```
DELETE /api/images/{img_id}
```

**路径参数**：

| 参数 | 说明 |
|------|------|
| `img_id` | 图片唯一标识符 |

**请求示例**：

```bash
curl -X DELETE http://localhost:5000/api/images/img_a1b2c3d4
```

**响应示例**：

```json
{
  "status": "ok",
  "message": "已删除"
}
```

**前端 JavaScript 调用方式**：

```javascript
const res = await fetch(`/api/images/${imageId}`, { method: 'DELETE' });
const data = await res.json();
// 成功后从本地列表中移除该图片
```

---

### 7. 执行缺陷检测

对指定图片执行缺陷检测推理（当前为 Mock 模拟，替换后端逻辑后前端零改动）。

```
POST /api/predict
Content-Type: application/json
```

**请求体**：

```json
{
  "model": "patchcore",
  "weight": "patchcore_mvtec",
  "image_ids": ["img_a1b2c3d4", "img_e5f6g7h8"]
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `model` | string | 是 | 模型 ID |
| `weight` | string | 是 | 权重 ID |
| `image_ids` | string[] | 是 | 待检测图片 ID 列表 |

**请求示例**：

```bash
curl -X POST http://localhost:5000/api/predict \
  -H "Content-Type: application/json" \
  -d '{"model":"patchcore","weight":"patchcore_mvtec","image_ids":["img_a1b2c3d4","img_e5f6g7h8"]}'
```

**响应示例**：

```json
{
  "status": "ok",
  "data": {
    "task_id": "task_a1b2c3d4e5f6",
    "status": "done",
    "results": [
      {
        "image_id": "img_a1b2c3d4",
        "image_name": "sample_001.jpg",
        "verdict": "normal",
        "confidence": 0.962,
        "severity": null,
        "defect_type": null,
        "score_map_url": "/api/files/score_img_a1b2c3d4.png",
        "processing_ms": 47.2,
        "expected_verdict": "normal"
      },
      {
        "image_id": "img_e5f6g7h8",
        "image_name": "defect_001.jpg",
        "verdict": "defect",
        "confidence": 0.937,
        "severity": "medium",
        "defect_type": "scratch",
        "score_map_url": "/api/files/score_img_e5f6g7h8.png",
        "processing_ms": 51.8,
        "expected_verdict": "defect"
      }
    ],
    "summary": {
      "total": 2,
      "defect_count": 1,
      "normal_count": 1,
      "accuracy": 1.0
    }
  }
}
```

**结果字段说明**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `results[].image_id` | string | 图片 ID |
| `results[].image_name` | string | 图片文件名 |
| `results[].verdict` | string | 判定结果：`normal`（正常）或 `defect`（缺陷） |
| `results[].confidence` | number | 置信度，范围 0~1 |
| `results[].severity` | string\|null | 严重程度：`light` / `medium` / `critical`，正常时为 `null` |
| `results[].defect_type` | string\|null | 缺陷类型：如 `scratch`、`dent`、`crack` 等 |
| `results[].score_map_url` | string\|null | 热力图 URL（如支持） |
| `results[].processing_ms` | number | 单张处理耗时（毫秒） |
| `results[].expected_verdict` | string | 期望结果（上传时指定的 type） |
| `summary.total` | number | 检测总数 |
| `summary.defect_count` | number | 缺陷数 |
| `summary.normal_count` | number | 正常数 |
| `summary.accuracy` | number | 整体准确率 |

**前端 JavaScript 调用方式**：

```javascript
const res = await fetch('/api/predict', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    model: 'patchcore',
    weight: 'patchcore_mvtec',
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

**响应示例**（与 `/predict` 返回的 `data` 结构一致）：

```json
{
  "status": "ok",
  "data": {
    "id": "task_a1b2c3d4e5f6",
    "status": "done",
    "model": "patchcore",
    "weight": "patchcore_mvtec",
    "image_ids": ["img_a1b2c3d4", "img_e5f6g7h8"],
    "results": [],
    "created_at": "2026-07-08T12:00:00Z",
    "completed_at": "2026-07-08T12:00:00Z",
    "summary": {
      "total": 0,
      "defect_count": 0,
      "normal_count": 0,
      "accuracy": 0
    }
  }
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
  "model": "patchcore",
  "epochs": 20,
  "lr": 0.001,
  "normal_image_ids": ["img_n1", "img_n2"],
  "defect_image_ids": ["img_d1", "img_d2"]
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `model` | string | 是 | 模型 ID |
| `epochs` | number | 否 | 训练轮数，范围 1~200，默认 20 |
| `lr` | number | 否 | 学习率，默认 0.001 |
| `normal_image_ids` | string[] | 是 | 正常样本图片 ID 列表 |
| `defect_image_ids` | string[] | 是 | 缺陷样本图片 ID 列表 |

**请求示例**：

```bash
curl -X POST http://localhost:5000/api/train \
  -H "Content-Type: application/json" \
  -d '{"model":"patchcore","epochs":20,"lr":0.001,"normal_image_ids":["img_n1"],"defect_image_ids":["img_d1"]}'
```

**响应示例**：

```json
{
  "status": "ok",
  "data": {
    "task_id": "train_a1b2c3d4e5f6",
    "status": "training",
    "epochs": 20,
    "model": "patchcore",
    "normal_count": 1,
    "defect_count": 1,
    "estimated_seconds": 8.0
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
    model: 'patchcore',
    epochs: 20,
    lr: 0.001,
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
    "model": "patchcore",
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
    "model": "patchcore",
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
| `status` | string | `training`（训练中）或 `done`（已完成） |
| `current_epoch` | number | 当前训练轮数 |
| `progress` | number | 进度，范围 0~1.0 |
| `loss` | number | 当前训练损失 |
| `val_loss` | number | 当前验证损失 |
| `accuracy` | number | 当前准确率 |
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
        "model": "patchcore",
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
a.download = 'ommateum_PatchCore_trained_b0ae95ef.omt';
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
GET /api/files/{filename}
```

**路径参数**：

| 参数 | 说明 |
|------|------|
| `filename` | 文件名，如 `img_a1b2c3d4.jpg` |

直接返回二进制文件。前端中可直接用于 `<img>` 标签：

```html
<img src="/api/files/img_a1b2c3d4.jpg">
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
    "version": "2.0.0",
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
| `400` | 请求参数缺失或无效 | `"缺少 model 参数"` / `"epochs 范围 1-200"` |
| `404` | 资源不存在 | `"模型 'xxx' 不存在"` / `"图片不存在"` |
| `413` | 文件过大 | `"文件过大（最大 32MB）"` |
| `500` | 服务端内部错误 | `"图片保存失败: ..."` |

### 错误响应格式

```json
{
  "status": "error",
  "message": "具体的错误描述",
  "code": 400
}
```

### 前端错误处理示例

```javascript
async function apiCall(url, options) {
  const res = await fetch(url, options);
  const data = await res.json();

  if (data.status === 'error') {
    console.error(`[API Error ${data.code}] ${data.message}`);
    throw new Error(data.message);
  }
  return data.data;
}
```

---

## 常见用法示例

### 完整工作流

```javascript
// 1. 检查服务状态
const health = await (await fetch('/api/health')).json();
if (health.status !== 'ok') return;

// 2. 获取模型列表
const models = (await (await fetch('/api/models')).json()).data.models;

// 3. 获取指定模型的权重
const weights = (await (await fetch(`/api/weights?model=${models[0].id}`)).json()).data.weights;

// 4. 上传图片
const fd = new FormData();
fd.append('file', fileInput.files[0]);
fd.append('type', 'normal');
const upload = await (await fetch('/api/images', { method: 'POST', body: fd })).json();
const newImage = upload.data.image;

// 5. 执行检测
const predict = await (await fetch('/api/predict', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    model: models[0].id,
    weight: weights[0].id,
    image_ids: [newImage.id]
  })
})).json();
const results = predict.data.results;

// 6. 查看统计
const stats = (await (await fetch('/api/stats')).json()).data;
```

### cURL 速查

```bash
# 健康检查
curl http://localhost:5000/api/health

# 上传正常图片
curl -X POST http://localhost:5000/api/images -F "file=@good.jpg" -F "type=normal"

# 上传缺陷图片
curl -X POST http://localhost:5000/api/images -F "file=@bad.jpg" -F "type=defect"

# 检测
curl -X POST http://localhost:5000/api/predict \
  -H "Content-Type: application/json" \
  -d '{"model":"patchcore","weight":"patchcore_mvtec","image_ids":["img_xxx"]}'

# 启动训练
curl -X POST http://localhost:5000/api/train \
  -H "Content-Type: application/json" \
  -d '{"model":"patchcore","epochs":20,"lr":0.001,"normal_image_ids":["img_n1"],"defect_image_ids":["img_d1"]}'

# 查询训练进度
curl http://localhost:5000/api/train/train_xxx

# 导出模型
curl -OJ http://localhost:5000/api/export/train_xxx

# 统计
curl http://localhost:5000/api/stats
```
