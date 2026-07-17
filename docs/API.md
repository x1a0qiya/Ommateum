# Ommateum API 文档

> 版本：1.0.0  
> 基础 URL：`http://localhost:5000/api`  
> 最后更新：2026-07-17

---

## 目录

- [概述](#概述)
- [通用约定](#通用约定)
- [系统](#系统)
- [模型与权重](#模型与权重)
- [数据集管理](#数据集管理)
- [缺陷检测](#缺陷检测)
- [训练](#训练)
- [日志](#日志)
- [错误处理](#错误处理)

---

## 概述

Ommateum API 提供视觉缺陷检测全流程 RESTful 接口：数据集管理、模型训练、缺陷推理、结果导出。训练与检测均以异步后台线程执行，通过 `task_id` 追踪状态。

| 属性 | 说明 |
|------|------|
| 数据格式 | JSON（上传为 `multipart/form-data`） |
| 编码 | UTF-8 |
| CORS | 全局启用 |
| 认证 | 当前无需认证 |
| 异步 | 训练/检测均通过后台线程执行，SSE 实时推送 |

---

## 通用约定

**成功响应**

```json
{
  "status": "ok",
  "timestamp": "2026-07-17T08:30:00+00:00",
  "data": { ... }
}
```

**错误响应**

```json
{
  "status": "error",
  "timestamp": "2026-07-17T08:30:00+00:00",
  "error": "错误描述"
}
```

`status` 恒为 `"ok"` 或 `"error"`，`data` 仅在成功时存在。`timestamp` 为 ISO 8601 UTC。

---

## 系统

### `GET /api/health` — 健康检查

```bash
curl http://localhost:5000/api/health
```

```json
{
  "status": "ok",
  "data": {
    "service": "Ommateum API",
    "version": "1.0.0",
    "models": 1,
    "images": 3,
    "trained_weights": 2,
    "rag_available": true
  }
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `models` | number | `weights/` 目录下模型数量 |
| `images` | number | `dataset/` 目录下批次数量 |
| `trained_weights` | number | 已训练权重总数 |
| `rag_available` | boolean | RAG 检索增强是否可用 |

### `GET /api/stats` — 全局统计

```bash
curl http://localhost:5000/api/stats
```

```json
{
  "status": "ok",
  "data": {
    "recent_accuracy": 0.0,
    "trained_weights": 2,
    "total_batches": 3
  }
}
```

| 字段 | 说明 |
|------|------|
| `recent_accuracy` | 最近训练准确率（当前预留字段，固定 0.0） |
| `total_batches` | 数据批次总数 |

---

## 模型与权重

### `GET /api/models` — 模型列表

扫描 `weights/` 下所有包含 `config.json` 的子目录。

```bash
curl http://localhost:5000/api/models
```

```json
{
  "status": "ok",
  "data": {
    "models": [
      {
        "id": "pretrained",
        "name": "pretrained",
        "description": "预训练基础模型"
      },
      {
        "id": "a1b2c3d4",
        "name": "用户训练模型",
        "description": "基于用户数据集微调"
      }
    ]
  }
}
```

### `GET /api/weights?model=<id>` — 权重列表

扫描 `weights/<model_id>/yolo/` 下所有 `.pt` 文件。

```bash
curl "http://localhost:5000/api/weights?model=pretrained"
```

```json
{
  "status": "ok",
  "data": {
    "model_id": "pretrained",
    "models": [
      {
        "id": "yolo11n",
        "name": "yolo11n.pt",
        "size_mb": 5.4,
        "trained": false
      },
      {
        "id": "a1b2c3d4",
        "name": "a1b2c3d4_best.pt",
        "size_mb": 5.5,
        "trained": true
      }
    ]
  }
}
```

| 字段 | 说明 |
|------|------|
| `models[].id` | 权重 ID（文件名去后缀） |
| `models[].size_mb` | 文件大小（MB） |
| `models[].trained` | 是否训练产出（文件名含 `_best` 为 `true`） |

---

## 数据集管理

### `GET /api/dataset` — 数据集列表

```bash
curl http://localhost:5000/api/dataset
```

```json
{
  "status": "ok",
  "data": {
    "dataset": [
      {
        "id": "a1b2c3d4e5f6",
        "size_kb": 18432.5,
        "can_train": true,
        "image_count": 30,
        "masks_info": {
          "name": "masks.zip",
          "size_kb": 5120.0,
          "mask_count": 30
        },
        "has_annotation": true
      }
    ],
    "total": 1
  }
}
```

| 字段 | 说明 |
|------|------|
| `dataset[].id` | 批次 UUID（去连字符） |
| `dataset[].can_train` | 是否存在 `annotation.json`，决定是否可训练 |
| `dataset[].image_count` | `images/` 下图片数量 |
| `dataset[].masks_info` | 掩码信息，无掩码时为 `null` |
| `dataset[].has_annotation` | 是否存在标注文件 |

### `POST /api/dataset` — 上传数据集

```
Content-Type: multipart/form-data
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `images_zip` | File | **是** | 图片压缩包（`.zip`） |
| `annotation_json` | File | 否 | COCO 格式标注文件 |
| `masks_zip` | File | 否 | 掩码图片压缩包 |

```bash
curl -X POST http://localhost:5000/api/dataset \
  -F "images_zip=@images.zip" \
  -F "annotation_json=@annotations.json" \
  -F "masks_zip=@masks.zip"
```

```json
{
  "status": "ok",
  "data": {
    "batch_id": "a1b2c3d4e5f6",
    "uploaded_at": "2026-07-17T08:30:00Z",
    "images_file": {
      "name": "images.zip",
      "size_kb": 15360.0,
      "image_count": 30
    },
    "annotation_file": {
      "name": "annotation.json",
      "size_kb": 128.0
    },
    "masks_file": {
      "name": "masks.zip",
      "size_kb": 5120.0,
      "mask_count": 30
    }
  }
}
```

`annotation_file` 和 `masks_file` 仅在对应文件上传时才出现在响应中。

> `POST /api/upload` 为历史保留路由，逻辑同上。

### `GET /api/images?name=<batch>` — 批次图片列表

```bash
curl "http://localhost:5000/api/images?name=a1b2c3d4e5f6"
```

```json
{
  "status": "ok",
  "data": {
    "images": [
      {
        "id": "e3b0c442...",
        "name": "sample_001.jpg",
        "batch_name": "a1b2c3d4e5f6",
        "size_kb": 245.0,
        "url": "/api/files/sample_001.jpg",
        "width": 1920,
        "height": 1080,
        "uploaded_at": "2026-07-17T08:30:00Z"
      }
    ],
    "total": 1
  }
}
```

| 字段 | 说明 |
|------|------|
| `images[].id` | SHA-256 标识符（基于文件名） |
| `images[].url` | 图片访问 URL |
| `images[].width / height` | 图片尺寸（px） |

`name` 参数为空时返回 `"'Name' must be unempty."` 错误。

### `GET /api/preview/<batch>/<image>` — 图片预览

返回原始图片二进制流，供 `<img src>` 直接使用。

```bash
curl http://localhost:5000/api/preview/a1b2c3d4e5f6/sample_001.jpg
```

图片不存在时返回 HTTP 404 + `{"status":"error","error":"Image not found: ..."}`。

### `DELETE /api/batches/<id>` — 删除批次

删除指定批次目录及全部文件。

```bash
curl -X DELETE http://localhost:5000/api/batches/a1b2c3d4e5f6
```

```json
{
  "status": "ok",
  "data": { "id": "a1b2c3d4e5f6" }
}
```

---

## 缺陷检测

检测流程：提交 → 后台线程执行 YOLO 检测 → SAM2 分割 → 结果写入 `exp/annotation.json`。通过 `task_id` 轮询或 SSE 获取结果。

### `POST /api/predict` — 提交检测任务

```
Content-Type: application/json
```

**请求体**

```json
{
  "batch_name": "a1b2c3d4e5f6",
  "weight": "pretrained"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `batch_name` | string | **是** | 待检测批次 ID |
| `weight` | string | **是** | 权重 ID |

**可选覆盖参数**

| 字段 | 默认值 | 说明 |
|------|--------|------|
| `conf` | 0.25 | YOLO 置信度阈值 |
| `iou` | 0.7 | NMS IoU 阈值 |
| `imgsz` | 自动 | 推理尺寸（取批次最大图片尺寸） |
| `device` | `"cpu"` | 推理设备（`cpu` / `cuda`） |
| `model_confidence_threshold` | 0.5 | SAM2 置信度阈值 |
| `sam2_model_path` | `"facebook/sam2-hiera-tiny"` | SAM2 模型 |
| `slice_height / slice_width` | 256 | SAHI 切片尺寸 |
| `overlap_height_ratio / overlap_width_ratio` | 0.2 | 切片重叠比例 |

```bash
curl -X POST http://localhost:5000/api/predict \
  -H "Content-Type: application/json" \
  -d '{"batch_name":"a1b2c3d4e5f6","weight":"pretrained","conf":0.3}'
```

**响应**

```json
{
  "status": "ok",
  "data": {
    "task_id": "f3e8a1b2",
    "image_path": null
  }
}
```

`image_path` 在单图上传模式下返回图片保存路径，批次模式为 `null`。

### `GET /api/task/<task_id>` — 任务状态与结果

```bash
curl http://localhost:5000/api/task/f3e8a1b2
```

**处理中**

```json
{
  "status": "ok",
  "data": {
    "task_id": "f3e8a1b2",
    "status": "processing",
    "task_type": "test",
    "error": null,
    "results": []
  }
}
```

**已完成**

```json
{
  "status": "ok",
  "data": {
    "task_id": "f3e8a1b2",
    "status": "completed",
    "task_type": "test",
    "error": null,
    "results": [
      {
        "image_name": "sample_001.jpg",
        "verdict": "defect",
        "confidence": 0.87,
        "defect_type": 1,
        "bbox": [120, 200, 85, 110]
      }
    ]
  }
}
```

| 字段 | 说明 |
|------|------|
| `results[].verdict` | `"defect"` 或 `"normal"`（score > 0.3 为 defect） |
| `results[].confidence` | 置信度（0~1） |
| `results[].defect_type` | 缺陷类别 ID（来自 COCO annotation） |
| `results[].bbox` | 边界框 `[x, y, w, h]` |

### `GET /api/task-stream/<task_id>` — SSE 实时流

无需轮询，服务端推送任务状态变更。

```javascript
const es = new EventSource(`/api/task-stream/${taskId}`);
es.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.status === 'completed') { console.log('完成'); es.close(); }
  if (data.status === 'failed')    { console.error(data.error); es.close(); }
};
```

**事件序列**

```
data: {"status":"ok","message":"Progressing..."}

// 完成
data: {"task_id":"f3e8a1b2","status":"completed","error":null}

// 失败
data: {"task_id":"f3e8a1b2","status":"failed","error":"ValueError(...)""}

// 超时（3600 秒）
data: {"status":"error","error":"Time out."}
```

### `GET /api/upload_image` — 单图上传即检测

```
Content-Type: multipart/form-data
```

| 字段 | 说明 |
|------|------|
| `data` | JSON 字符串，含 `batch_name`、`weight` 等 |
| `image` | 图片文件 |

```javascript
const fd = new FormData();
fd.append('data', JSON.stringify({ batch_name: 'temp', weight: 'pretrained' }));
fd.append('image', file);
// 返回检测结果图片二进制流
```

---

## 训练

训练流程：COCO→YOLO 转换 →（可选 SDG 增强）→ 生成 `data.yaml` → YOLO 微调 → SAM2 LoRA 微调。权重输出至 `weights/<task_id>/yolo/` 和 `weights/<task_id>/sam2/`。

### `POST /api/train` — 启动训练

```
Content-Type: application/json
```

**请求体**

```json
{
  "batch_name": "a1b2c3d4e5f6",
  "use_SDG": true,
  "params": {
    "yolo_epochs": 50,
    "imgsz": 640,
    "yolo_batch_size": 16,
    "freeze": 20,
    "sam2_epochs": 8,
    "lora_rank": 16
  }
}
```

| 顶层字段 | 类型 | 必填 | 说明 |
|----------|------|------|------|
| `batch_name` | string | **是** | 训练批次 ID |
| `use_SDG` | boolean | 否 | 启用 SDG 数据增强 |
| `params` | object | 否 | 超参容器，不传则全部默认 |

**YOLO 参数**

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `yolo_epochs` | 50 | 训练轮数 |
| `imgsz` | 640 | 输入图像尺寸 |
| `yolo_batch_size` | 16 | 批大小 |
| `yolo_lr` | 0.001 | 初始学习率 |
| `freeze` | 20 | 冻结 backbone 前 N 层 |
| `patience` | 10 | 早停耐心值 |
| `workers` | 4 | 数据加载线程数 |
| `lrf` | 0.1 | 最终学习率因子 |
| `cos_lr` | true | Cosine 衰减 |
| `pretrained` | — | 预训练权重路径 |
| `full_train` | false | 全量训练模式 |

**SAM2 参数**

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `sam2_epochs` | 8 | 训练轮数 |
| `sam2_batch_size` | 8 | 批大小 |
| `lora_rank` | 16 | LoRA rank |
| `use_dora` | true | 启用 DoRA |
| `sam2_lr` | 0.0002 | 学习率 |
| `weight_decay` | 0.01 | 权重衰减 |

**SDG 参数**

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `num_aug` | 3 | 每张图生成增强样本数 |

**响应**

```json
{
  "status": "ok",
  "data": { "task_id": "c7d2e9f1" }
}
```

**前置条件**：批次必须包含 `annotation.json`，否则返回 `"The dataset don't have any annotation file"`。

### `GET /api/train/<task_id>` — 训练进度

```bash
curl http://localhost:5000/api/train/c7d2e9f1
```

```json
{
  "status": "ok",
  "data": {
    "task_id": "c7d2e9f1",
    "status": "done",
    "progress": 1.0,
    "current_epoch": 0,
    "stage": "completed",
    "loss": null,
    "val_loss": null,
    "accuracy": 1.0,
    "final_accuracy": 1.0,
    "error": null
  }
}
```

| 字段 | 说明 |
|------|------|
| `status` | `"processing"` \| `"done"` \| `"failed"` |
| `progress` | 0.0 ~ 1.0 |
| `stage` | 当前阶段描述 |
| `error` | 失败时含异常信息 |

> 当前 `progress`、`loss`、`accuracy` 为占位值，仅在完成时切换终态。

### `GET /api/training-history` — 训练历史

返回内存中所有训练任务记录。

```json
{
  "status": "ok",
  "data": {
    "tasks": [
      {
        "id": "c7d2e9f1",
        "status": "done",
        "accuracy": 1.0,
        "epochs": 0,
        "normal_count": 0,
        "defect_count": 0,
        "model": "c7d2e9f1",
        "weight_id": "c7d2e9f1",
        "timestamp": "2026-07-17T08:42:00+00:00"
      }
    ]
  }
}
```

### `GET /api/export/<task_id>` — 导出模型

下载训练产出的 ZIP 压缩包。训练任务导出 `weights/<task_id>/`，检测任务导出 `dataset/<batch_name>/`。下载完成后临时文件自动删除。

```bash
curl -OJ http://localhost:5000/api/export/c7d2e9f1
```

响应为 `application/zip` 二进制流，文件名为 `task_<task_id>.zip`。

---

## 日志

### `GET /api/logs/errors?limit=50` — 查询错误日志

```json
{
  "status": "ok",
  "data": {
    "errors": [
      {
        "timestamp": "2026-07-17T08:30:00+00:00",
        "request_id": "a1b2c3d4e5f6",
        "endpoint": "/api/predict",
        "method": "POST",
        "client_ip": "127.0.0.1",
        "error_type": "ValueError",
        "error_message": "模型权重文件不存在",
        "traceback": ["Traceback...", "  File..."]
      }
    ],
    "total": 5
  }
}
```

`limit` 默认 50 条，最多保留 500 条。每条含完整 Traceback。

### `DELETE /api/logs/errors` — 清空错误日志

```bash
curl -X DELETE http://localhost:5000/api/logs/errors
```

```json
{ "status": "ok" }
```

---

## 错误处理

### 常见错误

| 场景 | 响应 |
|------|------|
| 图片压缩包缺失 | `"images_zip is required and must not be empty."` |
| JSON 解析失败 | `"Json Error."` |
| 训练缺少标注 | `"The dataset don't have any annotation file"` |
| 任务不存在 | `"Task xxx not found."` |
| 图片不存在 | HTTP 404 + `"Image not found: xxx"` |
| SSE 超时 | `"Time out."` |

### 前端错误处理模板

```javascript
async function apiCall(url, options) {
  const res = await fetch(url, options);
  const data = await res.json();
  if (data.status === 'error') {
    throw new Error(data.error);
  }
  return data.data;
}
```

---

## 端点速查

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/health` | 健康检查 |
| `GET` | `/api/stats` | 全局统计 |
| `GET` | `/api/models` | 模型列表 |
| `GET` | `/api/weights?model=<id>` | 权重列表 |
| `GET` | `/api/dataset` | 数据集列表 |
| `POST` | `/api/dataset` | 上传数据集 |
| `GET` | `/api/images?name=<batch>` | 批次图片列表 |
| `GET` | `/api/preview/<batch>/<filename>` | 图片预览 |
| `DELETE` | `/api/batches/<id>` | 删除批次 |
| `POST` | `/api/predict` | 提交检测任务 |
| `GET` | `/api/task/<id>` | 检测任务状态 |
| `GET` | `/api/task-stream/<id>` | SSE 检测实时流 |
| `GET` | `/api/upload_image` | 单图上传即检测 |
| `POST` | `/api/train` | 启动训练 |
| `GET` | `/api/train/<id>` | 训练进度 |
| `GET` | `/api/training-history` | 训练历史 |
| `GET` | `/api/export/<id>` | 导出模型 ZIP |
| `GET` | `/api/logs/errors` | 错误日志 |
| `DELETE` | `/api/logs/errors` | 清空错误日志 |
