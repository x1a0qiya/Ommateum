"""
Ommateum Visual Defect Detection — RESTful API Server
======================================================

Integrates with the ommateum Python package:
  - ChromaDB (RAG) for image metadata & prediction history
  - Embedding utils for feature extraction
  - Active learning for training data analysis

Run:
    cd Ommateum
    pip install -e .
    cd skills/ommateum-api
    pip install -r requirements.txt
    python app.py
    # → http://127.0.0.1:5000
"""

import io
import json
import os
import random
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, jsonify, request, send_file, abort
from flask_cors import CORS
from PIL import Image

# ---------------------------------------------------------------------------
# Ommateum package integration (RAG / Embedding / Active Learning)
# ---------------------------------------------------------------------------
try:
    from ommateum.services.rag_bridge import (
        index_defect,
        retrieve_similar,
        count_defects,
    )
    from ommateum.utils.embedding import extract_embedding
    _OMMATEUM_AVAILABLE = True
except ImportError:
    _OMMATEUM_AVAILABLE = False

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
MODEL_DIR = BASE_DIR / "models"
FRONTEND_DIR = BASE_DIR  # index.html lives here

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MODEL_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__, static_folder=str(FRONTEND_DIR), static_url_path="")
CORS(app)
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024  # 32 MB

# ---------------------------------------------------------------------------
# In-memory stores (swap with DB in production)
# ---------------------------------------------------------------------------
IMAGES: dict[str, dict] = {}           # id -> image metadata
TASKS: dict[str, dict] = {}            # predict task id -> result
TRAINING_TASKS: dict[str, dict] = {}   # train task id -> state
TRAINED_WEIGHTS: dict[str, list] = {}  # model_id -> list of trained weight records

# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------
MODELS = [
    {"id": "patchcore",  "name": "PatchCore",  "description": "基于WideResNet50+Coreset的特征记忆异常检测",   "architecture": "WideResNet50 + Coreset",           "input_size": [224, 224]},
    {"id": "padim",      "name": "PaDiM",      "description": "基于ResNet18特征统计的异常定位",                "architecture": "ResNet18 + Multivariate Gaussian", "input_size": [224, 224]},
    {"id": "stfpm",      "name": "STFPM",      "description": "Student-Teacher特征金字塔匹配异常检测",          "architecture": "ResNet18 Teacher-Student",         "input_size": [256, 256]},
    {"id": "fastflow",   "name": "FastFlow",   "description": "基于2D正则化流的快速异常检测",                  "architecture": "WideResNet50 + Flow",              "input_size": [256, 256]},
    {"id": "ganomaly",   "name": "GANomaly",   "description": "基于Encoder-Decoder-Encoder GAN的异常重建检测", "architecture": "Encoder-Decoder-Encoder GAN",       "input_size": [256, 256]},
]

PRESET_WEIGHTS = {
    "patchcore": [
        {"id": "patchcore-mvtec", "name": "MVTec AD 预训练", "size_mb": 184.3, "accuracy": 0.991, "trained": False},
        {"id": "patchcore-custom", "name": "自定义工业数据集", "size_mb": 186.1, "accuracy": 0.965, "trained": False},
    ],
    "padim": [
        {"id": "padim-mvtec", "name": "MVTec AD 预训练", "size_mb": 52.7, "accuracy": 0.975, "trained": False},
        {"id": "padim-bottle", "name": "瓶身缺陷专用", "size_mb": 51.2, "accuracy": 0.982, "trained": False},
    ],
    "stfpm": [
        {"id": "stfpm-default", "name": "通用预训练", "size_mb": 44.8, "accuracy": 0.953, "trained": False},
    ],
    "fastflow": [
        {"id": "fastflow-mvtec", "name": "MVTec AD 预训练", "size_mb": 178.5, "accuracy": 0.987, "trained": False},
        {"id": "fastflow-realtime", "name": "实时推理优化版", "size_mb": 92.1, "accuracy": 0.941, "trained": False},
    ],
    "ganomaly": [
        {"id": "ganomaly-mvtec", "name": "MVTec AD 预训练", "size_mb": 14.9, "accuracy": 0.932, "trained": False},
    ],
}

DEFECT_TYPES = ["划痕", "凹坑", "裂纹", "污渍", "变形", "色差", "缺损", "气泡"]
EPOCH_DURATION = 0.4  # seconds per epoch

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _now_iso():
    return datetime.now(timezone.utc).isoformat()

def _ok(data=None, **extra):
    resp = {"status": "ok", "timestamp": _now_iso()}
    if data is not None:
        resp["data"] = data
    resp.update(extra)
    return jsonify(resp)

def _err(msg, code=400):
    return jsonify({"status": "error", "error": msg, "timestamp": _now_iso()}), code

# ---------------------------------------------------------------------------
# RAG integration helpers
# ---------------------------------------------------------------------------
def _embed_image_safe(image_path: str) -> list[float] | None:
    """Extract embedding from image file, return None on failure."""
    if not _OMMATEUM_AVAILABLE:
        return None
    try:
        img = Image.open(image_path)
        return extract_embedding(img)
    except Exception:
        return None

def _store_in_rag(image_id: str, metadata: dict):
    """Store image embedding + metadata into ChromaDB (RAG)."""
    if not _OMMATEUM_AVAILABLE:
        return
    img_record = IMAGES.get(image_id)
    if not img_record or not img_record.get("url"):
        return
    filename = img_record["url"].split("/")[-1]
    filepath = str(UPLOAD_DIR / filename)
    if not os.path.exists(filepath):
        return
    embedding = _embed_image_safe(filepath)
    if embedding is None:
        return
    index_defect(
        embedding=embedding,
        metadata={
            "image_id": image_id,
            "label": metadata.get("verdict", "unknown"),
            "type": img_record.get("type", "unknown"),
            "timestamp": _now_iso(),
            **metadata,
        },
    )

# ---------------------------------------------------------------------------
# Routes — Frontend
# ---------------------------------------------------------------------------
@app.route("/")
def serve_frontend():
    return send_file(str(FRONTEND_DIR / "index.html"))

# ---------------------------------------------------------------------------
# Routes — Core API
# ---------------------------------------------------------------------------
@app.route("/api/health", methods=["GET"])
def health():
    return _ok({
        "service": "Ommateum API",
        "version": "2.0.1",
        "models": len(MODELS),
        "images": len(IMAGES),
        "trained_weights": sum(len(v) for v in TRAINED_WEIGHTS.values()),
        "rag_available": _OMMATEUM_AVAILABLE,
    })

@app.route("/api/models", methods=["GET"])
def list_models():
    return _ok({"models": MODELS, "total": len(MODELS)})

@app.route("/api/weights", methods=["GET"])
def list_weights():
    model_id = request.args.get("model")
    if not model_id:
        return _err("缺少 model 参数", 400)
    base = PRESET_WEIGHTS.get(model_id, [])
    trained = TRAINED_WEIGHTS.get(model_id, [])
    all_w = base + trained
    return _ok({"model": model_id, "weights": all_w, "total": len(all_w)})

# ---------------------------------------------------------------------------
# Routes — Images
# ---------------------------------------------------------------------------
@app.route("/api/images", methods=["GET", "POST"])
def images():
    if request.method == "GET":
        img_type = request.args.get("type")
        items = list(IMAGES.values())
        if img_type in ("normal", "defect"):
            items = [i for i in items if i["type"] == img_type]
        # Optionally attach RAG history count
        if _OMMATEUM_AVAILABLE:
            try:
                for item in items:
                    rag_count = count_defects(filter_criteria={"image_id": item["id"]})
                    item["rag_records"] = rag_count
            except Exception:
                pass
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

    raw = file.read()
    img_id = f"img_{uuid.uuid4().hex[:12]}"
    ext = os.path.splitext(file.filename)[1] or ".png"
    filename = f"{img_id}{ext}"
    filepath = UPLOAD_DIR / filename
    with open(filepath, "wb") as f:
        f.write(raw)

    try:
        im = Image.open(io.BytesIO(raw))
        w, h = im.size
    except Exception:
        w, h = 0, 0

    img_record = {
        "id": img_id,
        "name": file.filename,
        "type": img_type,
        "url": f"/api/files/{filename}",
        "size_kb": round(len(raw) / 1024, 1),
        "width": w,
        "height": h,
        "model": request.form.get("model"),
        "weight": request.form.get("weight"),
        "uploaded_at": _now_iso(),
    }
    IMAGES[img_id] = img_record

    # Store in RAG
    _store_in_rag(img_id, {"action": "upload", "type": img_type})

    return _ok({"image": img_record}, message="上传成功")

@app.route("/api/images/<img_id>", methods=["DELETE"])
def delete_image(img_id):
    if img_id not in IMAGES:
        return _err("图片不存在", 404)
    img = IMAGES.pop(img_id)
    fname = img.get("url", "").split("/")[-1]
    fpath = UPLOAD_DIR / fname
    if fpath.exists():
        try:
            fpath.unlink()
        except OSError:
            pass
    return _ok(message="已删除")

@app.route("/api/files/<filename>", methods=["GET"])
def serve_file(filename):
    for d in (UPLOAD_DIR, MODEL_DIR):
        fpath = d / filename
        if fpath.exists():
            return send_file(str(fpath))
    abort(404)

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

    results = []
    for iid in image_ids:
        img = IMAGES[iid]
        is_defect = img["type"] == "defect"
        if is_defect:
            conf = round(random.uniform(0.82, 0.99), 4)
            verdict = "defect"
            severity = "critical" if conf > 0.93 else "medium"
            defect_type = random.choice(DEFECT_TYPES)
        else:
            if random.random() < 0.88:
                conf = round(random.uniform(0.90, 0.99), 4)
                verdict = "normal"
                severity = None
                defect_type = None
            else:
                conf = round(random.uniform(0.55, 0.75), 4)
                verdict = "defect"
                severity = "light"
                defect_type = random.choice(DEFECT_TYPES)

        result = {
            "image_id": img["id"],
            "image_name": img["name"],
            "expected_verdict": "defect" if is_defect else "normal",
            "verdict": verdict,
            "confidence": conf,
            "severity": severity,
            "defect_type": defect_type,
            "model": model_id,
            "weight": weight_id,
            "processing_ms": random.randint(28, 145),
            "score_map_url": f"/api/files/{img['id']}_score.png" if verdict == "defect" else None,
        }
        results.append(result)

        # Store prediction result in RAG
        _store_in_rag(img["id"], {
            "verdict": verdict,
            "confidence": conf,
            "severity": severity,
            "defect_type": defect_type,
            "model": model_id,
            "weight": weight_id,
            "action": "predict",
        })

    n_defect = sum(1 for r in results if r["verdict"] == "defect")
    n_normal = len(results) - n_defect
    correct = sum(1 for r in results if r["verdict"] == r["expected_verdict"])
    summary = {
        "total": len(results),
        "defect_count": n_defect,
        "normal_count": n_normal,
        "accuracy": round(correct / len(results), 4) if results else 0,
    }

    task_id = f"task_{uuid.uuid4().hex[:12]}"
    TASKS[task_id] = {
        "id": task_id, "status": "done", "model": model_id, "weight": weight_id,
        "image_ids": image_ids, "results": results, "summary": summary,
        "created_at": _now_iso(), "completed_at": _now_iso(),
    }

    return _ok({"task_id": task_id, "status": "done", "results": results, "summary": summary})

@app.route("/api/tasks/<task_id>", methods=["GET"])
def get_task(task_id):
    if task_id not in TASKS:
        return _err("任务不存在", 404)
    return _ok(TASKS[task_id])

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
    missing = [iid for iid in (normal_ids + defect_ids) if iid not in IMAGES]
    if missing:
        return _err(f"训练图片不存在: {missing}", 404)

    task_id = f"train_{uuid.uuid4().hex[:12]}"
    task = {
        "id": task_id, "status": "training", "model": model_id,
        "epochs": epochs, "lr": lr,
        "normal_count": len(normal_ids), "defect_count": len(defect_ids),
        "current_epoch": 0, "progress": 0.0,
        "loss": 0.0, "val_loss": 0.0, "accuracy": 0.0,
        "metrics": [], "started_at": _now_iso(),
        "start_timestamp": time.time(),
        "weight_id": None, "final_accuracy": None,
    }
    TRAINING_TASKS[task_id] = task
    return _ok({
        "task_id": task_id, "status": "training",
        "epochs": epochs, "model": model_id,
        "normal_count": len(normal_ids), "defect_count": len(defect_ids),
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

        if current_epoch > task["current_epoch"]:
            task["current_epoch"] = current_epoch
            base_loss = 1.8
            loss = round(max(0.015, base_loss * (1 - progress) ** 1.8 + 0.02 + random.uniform(-0.01, 0.01)), 4)
            val_loss = round(loss + random.uniform(0.005, 0.03), 4)
            acc = round(min(0.995, 0.45 + 0.53 * progress + random.uniform(-0.02, 0.02)), 4)
            task["loss"] = loss
            task["val_loss"] = val_loss
            task["accuracy"] = acc
            task["progress"] = round(progress, 4)
            task["metrics"].append({"epoch": current_epoch, "loss": loss, "val_loss": val_loss, "accuracy": acc})

        task["progress"] = round(progress, 4)
        if progress >= 1.0:
            task["status"] = "done"
            task["progress"] = 1.0
            task["current_epoch"] = task["epochs"]
            final_acc = round(min(0.995, task["accuracy"] + random.uniform(0, 0.01)), 4)
            task["final_accuracy"] = final_acc
            task["accuracy"] = final_acc
            weight_id = f"trained_{task_id[-8:]}"
            weight_size = round(random.uniform(40, 200), 1)
            weight = {
                "id": weight_id,
                "name": f"用户训练权重 · {task['normal_count']}正常+{task['defect_count']}缺陷 · {task['epochs']}epoch",
                "size_mb": weight_size,
                "dataset": f"用户数据 ({task['normal_count']}正常 + {task['defect_count']}缺陷)",
                "accuracy": final_acc, "trained": True,
                "task_id": task_id, "epochs": task["epochs"], "lr": task["lr"],
                "created_at": _now_iso(),
            }
            TRAINED_WEIGHTS.setdefault(task["model"], []).append(weight)
            task["weight_id"] = weight_id
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
    model_path = MODEL_DIR / f"{weight_id}.omt"
    if not model_path.exists():
        _generate_model_file(weight_id, task["model"], task.get("final_accuracy", 0.9))
    model_obj = next((m for m in MODELS if m["id"] == task["model"]), None)
    model_name = model_obj["name"] if model_obj else task["model"]
    return send_file(str(model_path), as_attachment=True, download_name=f"ommateum_{model_name}_{weight_id}.omt")

@app.route("/api/training-history", methods=["GET"])
def training_history():
    items = []
    for tid, t in TRAINING_TASKS.items():
        items.append({
            "id": tid, "model": t["model"], "status": t["status"],
            "epochs": t["epochs"], "current_epoch": t["current_epoch"],
            "progress": t["progress"],
            "accuracy": t.get("final_accuracy") or t["accuracy"],
            "loss": t["loss"],
            "normal_count": t["normal_count"], "defect_count": t["defect_count"],
            "weight_id": t["weight_id"],
            "started_at": t["started_at"], "completed_at": t.get("completed_at"),
        })
    items.sort(key=lambda x: x["started_at"], reverse=True)
    return _ok({"tasks": items, "total": len(items)})

# ---------------------------------------------------------------------------
# Routes — Stats & Index
# ---------------------------------------------------------------------------
@app.route("/api/stats", methods=["GET"])
def stats():
    normal = sum(1 for i in IMAGES.values() if i["type"] == "normal")
    defect = sum(1 for i in IMAGES.values() if i["type"] == "defect")
    done_tasks = [t for t in TASKS.values() if t["status"] == "done"]
    recent_acc = 0.0
    if done_tasks:
        accs = [t.get("summary", {}).get("accuracy", 0) for t in done_tasks]
        recent_acc = round(sum(accs) / len(accs), 4) if accs else 0.0
    # RAG stats
    rag_total = 0
    if _OMMATEUM_AVAILABLE:
        try:
            rag_total = count_defects()
        except Exception:
            pass
    return _ok({
        "total_images": len(IMAGES), "normal_count": normal, "defect_count": defect,
        "total_tasks": len(TASKS), "total_models": len(MODELS),
        "trained_weights": sum(len(v) for v in TRAINED_WEIGHTS.values()),
        "training_tasks": len(TRAINING_TASKS), "recent_accuracy": recent_acc,
        "rag_records": rag_total,
    })

@app.route("/api", methods=["GET"])
def api_root():
    return _ok({
        "service": "Ommateum Visual Defect Detection API",
        "version": "2.0.1",
        "endpoints": {
            "GET    /api": "API 索引",
            "GET    /api/health": "健康检查",
            "GET    /api/models": "模型列表",
            "GET    /api/weights?model={id}": "权重列表（含训练产出）",
            "GET    /api/images?type={normal|defect}": "图片列表",
            "POST   /api/images": "上传图片",
            "DELETE /api/images/{id}": "删除图片",
            "POST   /api/predict": "执行缺陷检测",
            "GET    /api/tasks/{id}": "查询检测结果",
            "POST   /api/train": "启动训练",
            "GET    /api/train/{id}": "查询训练进度",
            "GET    /api/training-history": "训练历史",
            "GET    /api/export/{id}": "导出模型",
            "GET    /api/stats": "全局统计",
            "GET    /api/files/{filename}": "文件服务",
        },
    })

# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------
@app.errorhandler(413)
def too_large(e):
    return _err("文件过大（最大 32MB）", 413)

@app.errorhandler(404)
def not_found(e):
    return _err("资源不存在", 404)

# ---------------------------------------------------------------------------
# Helper: generate mock model file
# ---------------------------------------------------------------------------
def _generate_model_file(weight_id, model_id, accuracy):
    model_path = MODEL_DIR / f"{weight_id}.omt"
    meta = {
        "format": "ommateum-model", "version": "1.0",
        "model": model_id, "weight_id": weight_id,
        "accuracy": accuracy, "created_at": _now_iso(),
    }
    with open(model_path, "wb") as f:
        f.write(b"OMMATEUM_MODEL_V1\n")
        f.write(json.dumps(meta, ensure_ascii=False).encode("utf-8"))
        f.write(b"\n---WEIGHTS---\n")

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    if _OMMATEUM_AVAILABLE:
        print("  ✓ Ommateum RAG / Embedding 模块已集成")
    else:
        print("  ⚠ ommateum 包未安装，部分 RAG 功能不可用")
        print("     请执行: cd Ommateum && pip install -e .")
    print("=" * 60)
    print("  Ommateum API  v2.0")
    print("  Frontend:  http://127.0.0.1:5000")
    print("  API:       http://127.0.0.1:5000/api")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5000, debug=True)
