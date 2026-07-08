"""
Ommateum Visual Defect Detection — RESTful API Server
=====================================================
Backend implementing the full RESTful API contract consumed by the
Ommateum frontend.  Provides model listing, weight listing, image upload
(normal / defect), training with user data, model export, online inference,
prediction, task polling, and statistics.

Run:
    pip install -r requirements.txt
    python app.py
    # → http://127.0.0.1:5000/api/health
"""

import os
import io
import json
import uuid
import time
import random
import hashlib
from datetime import datetime, timezone
from flask import Flask, request, jsonify, send_file, abort
from flask_cors import CORS
from PIL import Image
import io as _io

app = Flask(__name__)
CORS(app)

# ---------------------------------------------------------------------------
# Storage (in-memory for demo; swap with DB / filesystem in production)
# ---------------------------------------------------------------------------
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(MODEL_DIR, exist_ok=True)

IMAGES = {}            # id -> {id, name, type, url, size_kb, ...}
TASKS = {}             # predict task id -> {...}
TRAINING_TASKS = {}    # train task id -> {...}
TRAINED_WEIGHTS = {}   # model_id -> [ {id, name, size_mb, accuracy, trained, task_id, ...} ]

# ---------------------------------------------------------------------------
# Seed data — models & weights
# ---------------------------------------------------------------------------
MODELS = [
    {
        "id": "patchcore",
        "name": "PatchCore",
        "description": "基于特征嵌入的异常检测，适合表面缺陷定位",
        "architecture": "WideResNet50 + Coreset",
        "input_size": [224, 224],
    },
    {
        "id": "padim",
        "name": "PaDiM",
        "description": "基于预训练特征统计的异常定位方法",
        "architecture": "ResNet18 + Multivariate Gaussian",
        "input_size": [224, 224],
    },
    {
        "id": "stfpm",
        "name": "STFPM",
        "description": "Student-Teacher Feature Pyramid Matching 异常检测",
        "architecture": "ResNet18 Teacher-Student",
        "input_size": [256, 256],
    },
    {
        "id": "fastflow",
        "name": "FastFlow",
        "description": "基于 2D 正则化流的快速异常检测",
        "architecture": "WideResNet50 + Flow",
        "input_size": [256, 256],
    },
    {
        "id": "ganomaly",
        "name": "GANomaly",
        "description": "基于 GAN 的异常重建检测",
        "architecture": "Encoder-Decoder-Encoder GAN",
        "input_size": [256, 256],
    },
]

WEIGHTS = {
    "patchcore": [
        {"id": "patchcore-mvtec", "name": "MVTec AD 预训练", "size_mb": 184.3, "dataset": "MVTec AD", "accuracy": 0.991, "trained": False},
        {"id": "patchcore-custom", "name": "自定义工业数据集", "size_mb": 186.1, "dataset": "Custom", "accuracy": 0.965, "trained": False},
    ],
    "padim": [
        {"id": "padim-mvtec", "name": "MVTec AD 预训练", "size_mb": 52.7, "dataset": "MVTec AD", "accuracy": 0.975, "trained": False},
        {"id": "padim-bottle", "name": "瓶身缺陷专用", "size_mb": 51.2, "dataset": "Bottle-Defect", "accuracy": 0.982, "trained": False},
    ],
    "stfpm": [
        {"id": "stfpm-default", "name": "通用预训练", "size_mb": 44.8, "dataset": "MVTec AD", "accuracy": 0.953, "trained": False},
    ],
    "fastflow": [
        {"id": "fastflow-mvtec", "name": "MVTec AD 预训练", "size_mb": 178.5, "dataset": "MVTec AD", "accuracy": 0.987, "trained": False},
        {"id": "fastflow-realtime", "name": "实时推理优化版", "size_mb": 92.1, "dataset": "Industrial", "accuracy": 0.941, "trained": False},
    ],
    "ganomaly": [
        {"id": "ganomaly-mvtec", "name": "MVTec AD 预训练", "size_mb": 14.9, "dataset": "MVTec AD", "accuracy": 0.932, "trained": False},
    ],
}

DEFECT_TYPES = ["划痕", "凹坑", "裂纹", "污渍", "变形", "色差", "缺损", "气泡"]

# Training duration per epoch (seconds) — controls simulation speed
EPOCH_DURATION = 0.4


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _ok(data=None, **extra):
    payload = {"status": "ok", "timestamp": _now_iso()}
    if data is not None:
        payload.update(data if isinstance(data, dict) else {"data": data})
    payload.update(extra)
    return jsonify(payload)


def _err(message, code=400):
    return jsonify({"status": "error", "error": message, "timestamp": _now_iso()}), code


def _save_image(file_storage, img_type, model, weight):
    """Save uploaded image to disk and return metadata dict."""
    raw = file_storage.read()
    h = hashlib.md5(raw).hexdigest()[:12]
    img_id = f"img_{h}"
    ext = os.path.splitext(file_storage.filename)[1] or ".png"
    filename = f"{img_id}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    if img_id not in IMAGES:
        with open(filepath, "wb") as f:
            f.write(raw)
        try:
            im = Image.open(_io.BytesIO(raw))
            w, hgt = im.size
        except Exception:
            w, hgt = 0, 0
        IMAGES[img_id] = {
            "id": img_id,
            "name": file_storage.filename,
            "type": img_type,
            "url": f"/api/files/{filename}",
            "size_kb": round(len(raw) / 1024, 1),
            "width": w,
            "height": hgt,
            "model": model,
            "weight": weight,
            "uploaded_at": _now_iso(),
        }
    return IMAGES[img_id]


def _mock_predict_single(img, model_id, weight_id):
    """Generate a mock prediction result for an image."""
    is_defect_img = img["type"] == "defect"
    if is_defect_img:
        confidence = round(random.uniform(0.82, 0.99), 4)
        verdict = "defect"
        severity = "critical" if confidence > 0.93 else "minor"
        defect_type = random.choice(DEFECT_TYPES)
    else:
        if random.random() < 0.88:
            confidence = round(random.uniform(0.90, 0.99), 4)
            verdict = "normal"
            severity = None
            defect_type = None
        else:
            confidence = round(random.uniform(0.55, 0.75), 4)
            verdict = "defect"
            severity = "minor"
            defect_type = random.choice(DEFECT_TYPES)

    expected = "defect" if is_defect_img else "normal"

    return {
        "image_id": img["id"],
        "image_name": img["name"],
        "expected_verdict": expected,
        "verdict": verdict,
        "confidence": confidence,
        "severity": severity,
        "defect_type": defect_type,
        "model": model_id,
        "weight": weight_id,
        "processing_ms": random.randint(28, 145),
        "score_map_url": f"/api/files/{img['id']}_score.png" if verdict == "defect" else None,
    }


def _generate_model_file(weight_id, model_id, accuracy):
    """Generate a mock model weights file with metadata."""
    model_path = os.path.join(MODEL_DIR, f"{weight_id}.omt")
    meta = {
        "format": "ommateum-model",
        "version": "1.0",
        "model": model_id,
        "weight_id": weight_id,
        "accuracy": accuracy,
        "created_at": _now_iso(),
        "layers": random.randint(50, 200),
        "parameters": random.randint(1_000_000, 50_000_000),
    }
    # Write metadata header + some padding bytes to simulate a real file
    with open(model_path, "wb") as f:
        f.write(b"OMMATEUM_MODEL_V1\n")
        f.write(json.dumps(meta, ensure_ascii=False).encode("utf-8"))
        f.write(b"\n---WEIGHTS---\n")
        # Write a few KB of pseudo-weight data
        for _ in range(256):
            f.write(hashlib.sha256(os.urandom(16)).digest())
    return model_path, meta


# ---------------------------------------------------------------------------
# Routes — Core
# ---------------------------------------------------------------------------
@app.route("/api/health", methods=["GET"])
def health():
    return _ok({
        "service": "Ommateum API",
        "version": "2.0.0",
        "models": len(MODELS),
        "images": len(IMAGES),
        "trained_weights": sum(len(v) for v in TRAINED_WEIGHTS.values()),
    })


@app.route("/api/models", methods=["GET"])
def list_models():
    return _ok({"models": MODELS, "total": len(MODELS)})


@app.route("/api/weights", methods=["GET"])
def list_weights():
    model_id = request.args.get("model")
    if not model_id:
        return _err("缺少 model 参数", 400)
    base_weights = WEIGHTS.get(model_id, [])
    trained = TRAINED_WEIGHTS.get(model_id, [])
    all_weights = base_weights + trained
    return _ok({"model": model_id, "weights": all_weights, "total": len(all_weights)})


@app.route("/api/images", methods=["GET", "POST"])
def images():
    if request.method == "GET":
        img_type = request.args.get("type")
        items = list(IMAGES.values())
        if img_type in ("normal", "defect"):
            items = [i for i in items if i["type"] == img_type]
        return _ok({"images": items, "total": len(items)})

    # POST — upload
    if "file" not in request.files:
        return _err("缺少 file 字段", 400)
    file = request.files["file"]
    if not file or file.filename == "":
        return _err("文件名为空", 400)

    img_type = request.form.get("type", "normal")
    if img_type not in ("normal", "defect"):
        return _err("type 必须为 normal 或 defect", 400)

    model = request.form.get("model")
    weight = request.form.get("weight")

    try:
        img = _save_image(file, img_type, model, weight)
    except Exception as e:
        return _err(f"图片保存失败: {e}", 500)

    return _ok({"image": img}, message="上传成功")


@app.route("/api/images/<img_id>", methods=["DELETE"])
def delete_image(img_id):
    if img_id not in IMAGES:
        return _err("图片不存在", 404)
    img = IMAGES.pop(img_id)
    fname = img.get("url", "").split("/")[-1]
    fpath = os.path.join(UPLOAD_DIR, fname)
    if os.path.exists(fpath):
        try:
            os.remove(fpath)
        except OSError:
            pass
    return _ok(message="已删除")


@app.route("/api/files/<filename>", methods=["GET"])
def serve_file(filename):
    # Search in uploads first, then models
    for d in (UPLOAD_DIR, MODEL_DIR):
        fpath = os.path.join(d, filename)
        if os.path.exists(fpath):
            return send_file(fpath)
    abort(404)


# ---------------------------------------------------------------------------
# Routes — Training
# ---------------------------------------------------------------------------
@app.route("/api/train", methods=["POST"])
def start_training():
    data = request.get_json(silent=True) or {}
    model_id = data.get("model")
    epochs = int(data.get("epochs", 20))
    lr = float(data.get("lr", 0.001))
    normal_ids = data.get("normal_image_ids", [])
    defect_ids = data.get("defect_image_ids", [])

    if not model_id:
        return _err("缺少 model 参数", 400)
    if model_id not in {m["id"] for m in MODELS}:
        return _err(f"模型 '{model_id}' 不存在", 404)
    if epochs < 1 or epochs > 200:
        return _err("epochs 范围 1-200", 400)
    if not normal_ids and not defect_ids:
        return _err("至少需要上传一张训练图片", 400)

    # Validate image IDs exist
    all_ids = normal_ids + defect_ids
    missing = [iid for iid in all_ids if iid not in IMAGES]
    if missing:
        return _err(f"训练图片不存在: {missing}", 404)

    task_id = f"train_{uuid.uuid4().hex[:12]}"
    task = {
        "id": task_id,
        "status": "training",
        "model": model_id,
        "epochs": epochs,
        "lr": lr,
        "normal_count": len(normal_ids),
        "defect_count": len(defect_ids),
        "current_epoch": 0,
        "progress": 0.0,
        "loss": 0.0,
        "val_loss": 0.0,
        "accuracy": 0.0,
        "metrics": [],
        "started_at": _now_iso(),
        "start_timestamp": time.time(),
        "weight_id": None,
        "final_accuracy": None,
    }
    TRAINING_TASKS[task_id] = task

    return _ok({
        "task_id": task_id,
        "status": "training",
        "epochs": epochs,
        "model": model_id,
        "normal_count": len(normal_ids),
        "defect_count": len(defect_ids),
        "estimated_seconds": round(epochs * EPOCH_DURATION, 1),
    })


@app.route("/api/train/<task_id>", methods=["GET"])
def get_training_status(task_id):
    if task_id not in TRAINING_TASKS:
        return _err("训练任务不存在", 404)

    task = TRAINING_TASKS[task_id]

    if task["status"] == "training":
        elapsed = time.time() - task["start_timestamp"]
        total_duration = task["epochs"] * EPOCH_DURATION
        progress = min(elapsed / total_duration, 1.0)
        current_epoch = min(int(progress * task["epochs"]) + 1, task["epochs"])

        # Only update if epoch advanced
        if current_epoch > task["current_epoch"]:
            task["current_epoch"] = current_epoch
            # Simulate decreasing loss, increasing accuracy
            base_loss = 1.8
            loss = round(max(0.015, base_loss * (1 - progress) ** 1.8 + 0.02 + random.uniform(-0.01, 0.01)), 4)
            val_loss = round(loss + random.uniform(0.005, 0.03), 4)
            accuracy = round(min(0.995, 0.45 + 0.53 * progress + random.uniform(-0.02, 0.02)), 4)
            task["loss"] = loss
            task["val_loss"] = val_loss
            task["accuracy"] = accuracy
            task["progress"] = round(progress, 4)
            task["metrics"].append({
                "epoch": current_epoch,
                "loss": loss,
                "val_loss": val_loss,
                "accuracy": accuracy,
            })

        task["progress"] = round(progress, 4)

        if progress >= 1.0:
            task["status"] = "done"
            task["progress"] = 1.0
            task["current_epoch"] = task["epochs"]
            final_acc = round(min(0.995, task["accuracy"] + random.uniform(0, 0.01)), 4)
            task["final_accuracy"] = final_acc
            task["accuracy"] = final_acc

            # Create trained weight entry
            weight_id = f"trained_{task_id[-8:]}"
            weight_size = round(random.uniform(40, 200), 1)
            weight = {
                "id": weight_id,
                "name": f"用户训练权重 · {task['normal_count']}正常+{task['defect_count']}缺陷 · {task['epochs']}epoch",
                "size_mb": weight_size,
                "dataset": f"用户数据 ({task['normal_count']}正常 + {task['defect_count']}缺陷)",
                "accuracy": final_acc,
                "trained": True,
                "task_id": task_id,
                "epochs": task["epochs"],
                "lr": task["lr"],
                "created_at": _now_iso(),
            }
            if task["model"] not in TRAINED_WEIGHTS:
                TRAINED_WEIGHTS[task["model"]] = []
            TRAINED_WEIGHTS[task["model"]].append(weight)
            task["weight_id"] = weight_id

            # Generate model file
            _generate_model_file(weight_id, task["model"], final_acc)

            task["completed_at"] = _now_iso()

    return _ok(task)


@app.route("/api/export/<task_id>", methods=["GET"])
def export_model(task_id):
    if task_id not in TRAINING_TASKS:
        return _err("训练任务不存在", 404)
    task = TRAINING_TASKS[task_id]
    if task["status"] != "done":
        return _err("训练尚未完成，无法导出", 400)

    weight_id = task["weight_id"]
    model_path = os.path.join(MODEL_DIR, f"{weight_id}.omt")
    if not os.path.exists(model_path):
        _generate_model_file(weight_id, task["model"], task.get("final_accuracy", 0.9))

    model_obj = next((m for m in MODELS if m["id"] == task["model"]), None)
    model_name = model_obj["name"] if model_obj else task["model"]
    download_name = f"ommateum_{model_name}_{weight_id}.omt"

    return send_file(model_path, as_attachment=True, download_name=download_name)


@app.route("/api/training-history", methods=["GET"])
def training_history():
    """List all training tasks (done or in-progress)."""
    items = []
    for tid, t in TRAINING_TASKS.items():
        items.append({
            "id": tid,
            "model": t["model"],
            "status": t["status"],
            "epochs": t["epochs"],
            "current_epoch": t["current_epoch"],
            "progress": t["progress"],
            "accuracy": t.get("final_accuracy") or t["accuracy"],
            "loss": t["loss"],
            "normal_count": t["normal_count"],
            "defect_count": t["defect_count"],
            "weight_id": t["weight_id"],
            "started_at": t["started_at"],
            "completed_at": t.get("completed_at"),
        })
    # Sort by started_at desc
    items.sort(key=lambda x: x["started_at"], reverse=True)
    return _ok({"tasks": items, "total": len(items)})


# ---------------------------------------------------------------------------
# Routes — Prediction
# ---------------------------------------------------------------------------
@app.route("/api/predict", methods=["POST"])
def predict():
    data = request.get_json(silent=True) or {}
    model_id = data.get("model")
    weight_id = data.get("weight")
    image_ids = data.get("image_ids", [])

    if not model_id:
        return _err("缺少 model 参数", 400)
    if not weight_id:
        return _err("缺少 weight 参数", 400)
    if not image_ids:
        return _err("缺少 image_ids 或为空", 400)

    missing = [iid for iid in image_ids if iid not in IMAGES]
    if missing:
        return _err(f"图片不存在: {missing}", 404)

    task_id = f"task_{uuid.uuid4().hex[:12]}"
    task = {
        "id": task_id,
        "status": "running",
        "model": model_id,
        "weight": weight_id,
        "image_ids": image_ids,
        "created_at": _now_iso(),
        "results": [],
    }
    TASKS[task_id] = task

    results = []
    for iid in image_ids:
        img = IMAGES[iid]
        results.append(_mock_predict_single(img, model_id, weight_id))

    task["results"] = results
    task["status"] = "done"
    task["completed_at"] = _now_iso()

    n_defect = sum(1 for r in results if r["verdict"] == "defect")
    n_normal = len(results) - n_defect
    correct = sum(1 for r in results if r["verdict"] == r["expected_verdict"])
    task["summary"] = {
        "total": len(results),
        "defect_count": n_defect,
        "normal_count": n_normal,
        "accuracy": round(correct / len(results), 4) if results else 0,
    }

    return _ok({
        "task_id": task_id,
        "status": "done",
        "results": results,
        "summary": task["summary"],
    })


@app.route("/api/tasks/<task_id>", methods=["GET"])
def get_task(task_id):
    if task_id not in TASKS:
        return _err("任务不存在", 404)
    return _ok(TASKS[task_id])


@app.route("/api/stats", methods=["GET"])
def stats():
    normal = sum(1 for i in IMAGES.values() if i["type"] == "normal")
    defect = sum(1 for i in IMAGES.values() if i["type"] == "defect")
    done_tasks = [t for t in TASKS.values() if t["status"] == "done"]
    recent_acc = 0.0
    if done_tasks:
        accs = [t.get("summary", {}).get("accuracy", 0) for t in done_tasks]
        recent_acc = round(sum(accs) / len(accs), 4)
    trained_total = sum(len(v) for v in TRAINED_WEIGHTS.values())
    return _ok({
        "total_images": len(IMAGES),
        "normal_count": normal,
        "defect_count": defect,
        "total_tasks": len(TASKS),
        "total_models": len(MODELS),
        "trained_weights": trained_total,
        "training_tasks": len(TRAINING_TASKS),
        "recent_accuracy": recent_acc,
    })


@app.route("/api", methods=["GET"])
def api_root():
    """API index — list all endpoints."""
    return _ok({
        "service": "Ommateum Visual Defect Detection API",
        "version": "2.0.0",
        "endpoints": {
            "GET    /api/health": "健康检查",
            "GET    /api/models": "获取可用模型列表",
            "GET    /api/weights?model={id}": "获取指定模型的权重列表（含训练产出）",
            "GET    /api/images?type={normal|defect}": "获取图片列表",
            "POST   /api/images": "上传图片 (multipart: file, type, model, weight)",
            "DELETE /api/images/{id}": "删除图片",
            "POST   /api/train": "使用用户数据训练模型 ({model, epochs, lr, normal_image_ids, defect_image_ids})",
            "GET    /api/train/{id}": "查询训练任务进度与状态",
            "GET    /api/training-history": "获取训练历史列表",
            "GET    /api/export/{id}": "导出训练后的模型权重文件",
            "POST   /api/predict": "执行缺陷检测 ({model, weight, image_ids})",
            "GET    /api/tasks/{id}": "查询检测任务状态与结果",
            "GET    /api/stats": "数据集与训练统计",
            "GET    /api/files/{filename}": "获取图片/模型文件",
        },
    })


@app.errorhandler(413)
def too_large(e):
    return _err("文件过大（最大 32MB）", 413)


if __name__ == "__main__":
    print("=" * 60)
    print("  Ommateum Visual Defect Detection API  v2.0")
    print("  Listening on http://127.0.0.1:5000")
    print("  API index: http://127.0.0.1:5000/api")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5000, debug=True)
