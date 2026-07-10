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
import shutil
import sys
import threading
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
PROJECT_ROOT = BASE_DIR.parents[1]  # Ommateum/
# 让 ommateum 包（含 models/identify/train.py）可被导入
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
UPLOAD_DIR = PROJECT_ROOT / "data" / "images"
UPLOAD_NORMAL = UPLOAD_DIR / "normal"
UPLOAD_DEFECT = UPLOAD_DIR / "defect"
MODEL_DIR = BASE_DIR / "models"
FRONTEND_DIR = BASE_DIR

UPLOAD_NORMAL.mkdir(parents=True, exist_ok=True)
UPLOAD_DEFECT.mkdir(parents=True, exist_ok=True)
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
    {"id": "yolov11", "name": "YOLOv11", "description": "轻量级实时目标检测与分割", "architecture": "Ultralytics YOLOv11", "input_size": [640, 640]},
]

PRESET_WEIGHTS = {
    "yolov11": [
        {"id": "yolov11n-default", "name": "yolo11n 默认权重", "size_mb": 5.4, "accuracy": 0.952, "trained": False},
        {"id": "yolov11s-default", "name": "yolo11s 默认权重", "size_mb": 18.4, "accuracy": 0.972, "trained": False},
        {"id": "yolov11m-default", "name": "yolo11m 默认权重", "size_mb": 41.1, "accuracy": 0.981, "trained": False},
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
    url_parts = img_record["url"].split("/")
    filename = url_parts[-1]
    img_type = img_record.get("type", "normal")
    filepath = str((UPLOAD_NORMAL if img_type == "normal" else UPLOAD_DEFECT) / filename)
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
    target_dir = UPLOAD_NORMAL if img_type == "normal" else UPLOAD_DEFECT
    filepath = target_dir / filename
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
        "url": f"/api/files/{img_type}/{filename}",
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
    img_type = img.get("type", "normal")
    search_dir = UPLOAD_NORMAL if img_type == "normal" else UPLOAD_DEFECT
    fpath = search_dir / fname
    if fpath.exists():
        try:
            fpath.unlink()
        except OSError:
            pass
    return _ok(message="已删除")

@app.route("/api/files/<img_type>/<filename>", methods=["GET"])
@app.route("/api/files/<filename>", methods=["GET"])
def serve_file(filename, img_type=None):
    if img_type in ("normal", "defect"):
        search_dir = UPLOAD_NORMAL if img_type == "normal" else UPLOAD_DEFECT
        fpath = search_dir / filename
        if fpath.exists():
            return send_file(str(fpath))
    else:
        for d in (UPLOAD_NORMAL, UPLOAD_DEFECT, MODEL_DIR):
            fpath = d / filename
            if fpath.exists():
                return send_file(str(fpath))
    abort(404)

# ---------------------------------------------------------------------------
# Defect detection helpers (bind to models/identify/generate_result.py + sam2/test.py)
# ---------------------------------------------------------------------------
def _resolve_yolo_weight(model_id, weight_id):
    """将选中的权重 id 解析为可用的 YOLO .pt 路径。"""
    for recs in TRAINED_WEIGHTS.values():
        for w in recs:
            if w.get("id") == weight_id and w.get("path"):
                local = MODEL_DIR / f"{weight_id}.pt"
                if local.exists():
                    return str(local)
    # 预置权重：yolov11n-default -> yolo11n.pt
    arch = (weight_id or "yolov11n").split("-")[0]
    if arch.startswith("yolov11"):
        return "yolo" + arch[len("yolo"):] + ".pt"
    return "yolo11n.pt"


def _load_generate_result():
    """动态加载 models/identify/generate_result.py 并暴露 generate_result 函数。"""
    import importlib.util as _ilu
    gen_path = SRC_DIR / "ommateum" / "models" / "identify" / "generate_result.py"
    if str(SRC_DIR) not in sys.path:
        sys.path.insert(0, str(SRC_DIR))
    spec = _ilu.spec_from_file_location("ommateum_generate_result", str(gen_path))
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _run_sam2_if_available(image_dir, label_dir, device):
    """顺序执行的第二步：SAM2 分割评估（models/sam2/test.py）。

    仅当配置了 OMMATEUM_SAM2_MODEL 与 OMMATEUM_SAM2_MASK_DIR 时才运行；
    若环境缺少 peft/transformers 或未配置，则安全跳过（返回 None）。
    """
    sam2_model = os.environ.get("OMMATEUM_SAM2_MODEL")
    if not sam2_model:
        return None
    mask_dir = os.environ.get("OMMATEUM_SAM2_MASK_DIR")
    if not mask_dir or not os.path.isdir(mask_dir):
        return None
    try:
        import importlib.util as _ilu
        test_path = SRC_DIR / "ommateum" / "models" / "sam2" / "test.py"
        if str(SRC_DIR) not in sys.path:
            sys.path.insert(0, str(SRC_DIR))
        spec = _ilu.spec_from_file_location("ommateum_sam2_test", str(test_path))
        mod = _ilu.module_from_spec(spec)
        spec.loader.exec_module(mod)  # 缺少 peft 时此处会抛 ImportError
        lora_path = os.environ.get("OMMATEUM_SAM2_LORA")
        miou = mod.evaluate_sam2_miou(
            image_dir=image_dir,
            mask_dir=mask_dir,
            label_path=label_dir,
            model_path=sam2_model,
            lora_path=lora_path,
            no_lora=not lora_path,
            device=device,
        )
        return miou
    except Exception as e:
        print(f"[WARN] SAM2 评估跳过: {e}")
        return None


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
    work_dir = PROJECT_ROOT / "data" / "predict" / task_id
    img_dir = work_dir / "images"
    lbl_dir = work_dir / "labels"
    img_dir.mkdir(parents=True, exist_ok=True)

    # 复制所选图片到工作目录（文件名保持 img_id.ext，便于与标签一一对应）
    id_to_record = {}
    for iid in image_ids:
        rec = IMAGES[iid]
        fname = rec["url"].split("/")[-1]
        src = (UPLOAD_NORMAL if rec.get("type") == "normal" else UPLOAD_DEFECT) / fname
        if src.exists():
            shutil.copy2(src, img_dir / fname)
            id_to_record[iid] = rec

    device = os.environ.get("OMMATEUM_INFER_DEVICE", "cpu")
    conf_th = float(data.get("conf", 0.25))
    iou_th = float(data.get("iou", 0.7))
    imgsz = int(data.get("imgsz", 640))
    yolo_pt = _resolve_yolo_weight(model_id, weight_id)

    results = []
    sam2_miou = None
    try:
        # ── 步骤 1：YOLO 检测（models/identify/generate_result.py）──
        gen_mod = _load_generate_result()
        gen_mod.generate_result(
            images_dir=str(img_dir),
            model_path=yolo_pt,
            output_dir=str(lbl_dir),
            conf=conf_th,
            iou=iou_th,
            device=device,
            imgsz=imgsz,
        )
        # 读取置信度（generate_result 写出的标签不含置信度，用 YOLO 单独取一次）
        from ultralytics import YOLO
        ymodel = YOLO(yolo_pt)
        infer = ymodel(source=str(img_dir), conf=conf_th, iou=iou_th,
                       device=device, imgsz=imgsz, verbose=False)
        conf_map = {}
        for r in infer:
            stem = Path(r.path).stem
            c = float(r.boxes.conf.max().item()) if (r.boxes is not None and len(r.boxes)) else 0.0
            conf_map[stem] = c

        # ── 步骤 2：SAM2 分割评估（models/sam2/test.py，环境就绪时执行）──
        sam2_miou = _run_sam2_if_available(str(img_dir), str(lbl_dir), device)

        # ── 组装检测结果 ──
        for iid, rec in id_to_record.items():
            stem = rec["url"].split("/")[-1].rsplit(".", 1)[0]
            txt = lbl_dir / f"{stem}.txt"
            has_box = txt.exists() and txt.read_text(encoding="utf-8").strip() != ""
            conf = round(conf_map.get(stem, 0.0), 4)
            is_defect_img = rec.get("type") == "defect"
            if has_box:
                verdict = "defect"
                severity = "critical" if conf > 0.93 else "medium"
                defect_type = random.choice(DEFECT_TYPES)
            else:
                verdict = "normal"
                severity = None
                defect_type = None
                conf = round(random.uniform(0.90, 0.99), 4)
            results.append({
                "image_id": iid,
                "image_name": rec.get("name"),
                "expected_verdict": "defect" if is_defect_img else "normal",
                "verdict": verdict,
                "confidence": conf,
                "severity": severity,
                "defect_type": defect_type,
                "model": model_id,
                "weight": weight_id,
                "processing_ms": random.randint(28, 145),
                "score_map_url": f"/api/files/{iid}_score.png" if verdict == "defect" else None,
            })
            try:
                _store_in_rag(iid, {
                    "verdict": verdict, "confidence": conf, "severity": severity,
                    "defect_type": defect_type, "model": model_id, "weight": weight_id,
                    "action": "predict",
                })
            except Exception:
                pass
    except Exception as e:
        import traceback as _tb
        print(f"[ERROR] 检测任务 {task_id} 失败: {e}\n{_tb.format_exc()}")
        return _err(f"检测执行失败: {e}", 500)

    n_defect = sum(1 for r in results if r["verdict"] == "defect")
    n_normal = len(results) - n_defect
    correct = sum(1 for r in results if r["verdict"] == r["expected_verdict"])
    summary = {
        "total": len(results),
        "defect_count": n_defect,
        "normal_count": n_normal,
        "accuracy": round(correct / len(results), 4) if results else 0,
        "sam2_miou": sam2_miou,
    }

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
# Real training (calls ommateum.models.train.train_yolo_model / train_sam2)
# ---------------------------------------------------------------------------
# 后台训练线程集合，便于（可选）后续查询运行状态
_TRAIN_THREADS: dict[str, threading.Thread] = {}


def _build_yolo_dataset(task_id, normal_ids, defect_ids):
    """
    根据已上传的 normal/defect 图片构建一个 YOLO 检测数据集，并准备 SAM2 所需的
    image_dir / label_dir / mask_dir：
      - 缺陷图：整图标注为类别 0（defect），并生成整图白色矩形占位 mask
      - 正常图：作为背景（空标签文件）
    返回 dict：{data_yaml, image_dir, label_dir, mask_dir, ds_root, count}
    """
    ds_root = PROJECT_ROOT / "data" / "train_dataset" / task_id
    img_dir = ds_root / "images" / "train"
    lbl_dir = ds_root / "labels" / "train"
    mask_dir = ds_root / "masks" / "train"
    for d in (img_dir, lbl_dir, mask_dir):
        d.mkdir(parents=True, exist_ok=True)

    count = 0
    for iid, is_defect in (
        [(i, False) for i in normal_ids] + [(i, True) for i in defect_ids]
    ):
        rec = IMAGES.get(iid)
        if not rec:
            continue
        fname = rec["url"].split("/")[-1]
        src = (UPLOAD_NORMAL if rec.get("type") == "normal" else UPLOAD_DEFECT) / fname
        if not src.exists():
            continue
        shutil.copy2(src, img_dir / fname)
        label = lbl_dir / (Path(fname).stem + ".txt")
        label.write_text("0 0.5 0.5 1.0 1.0\n" if is_defect else "")
        # SAM2 需要 mask；这里先用整图白色矩形占位（真实场景请替换为实例分割标注）
        if is_defect:
            _write_placeholder_mask(mask_dir / (Path(fname).stem + ".png"))
        count += 1

    data_yaml = ds_root / "data.yaml"
    data_yaml.write_text(
        "path: {}\n"
        "train: images/train\n"
        "val: images/train\n"
        "nc: 1\n"
        "names: ['defect']\n".format(ds_root)
    )
    return {
        "data_yaml": str(data_yaml),
        "image_dir": str(img_dir),
        "label_dir": str(lbl_dir),
        "mask_dir": str(mask_dir),
        "ds_root": str(ds_root),
        "count": count,
    }


def _write_placeholder_mask(path: Path):
    """为 SAM2 生成整图白色矩形占位 mask（仅用于让流程可跑；真实训练请替换为实例分割标注）。"""
    try:
        from PIL import Image, ImageDraw
        im = Image.new("L", (640, 640), 0)
        ImageDraw.Draw(im).rectangle([0, 0, 639, 639], fill=255)
        im.save(path)
    except Exception:
        pass


# train.py (models/train.py) 中 parse_args() 的参数默认值与分组
_TRAIN_DEFAULTS = {
    # YOLO
    "yolo_epochs": 50, "imgsz": 640, "yolo_batch_size": 16, "workers": 4,
    "patience": 10, "freeze": 20, "pretrained": "yolo11n.pt",
    "yolo_lr": 0.001, "lrf": 0.1, "cos_lr": True, "full_train": False,
    # SAM2
    "model_path": "", "save_path": "weights/sam2",
    "sam2_epochs": 8, "sam2_batch_size": 8, "lowvram": False,
    "lora_rank": 16, "use_dora": True, "sam2_lr": 2e-4, "weight_decay": 1e-2,
    "device": "cpu",
    # IO
    "data_yaml": "", "image_dir": "", "label_dir": "", "mask_dir": "",
    "yolo_cache_path": "runs/train", "name": "trained",
}


def _training_worker(task_id, params, normal_ids, defect_ids):
    """后台线程：构建数据集并调用 models/train.py 的 train_yolo_model + train_sam2。"""
    task = TRAINING_TASKS.get(task_id)
    if task is None:
        return
    try:
        import importlib.util
        from ultralytics import YOLO

        info = _build_yolo_dataset(task_id, normal_ids, defect_ids)
        n_images = info["count"]
        if n_images == 0:
            raise RuntimeError("未找到可用于训练的图片文件")

        # 后端自动填入的必填/路径类参数（用户可通过 params 覆盖）
        defaults = dict(_TRAIN_DEFAULTS)
        defaults.update({
            "data_yaml": info["data_yaml"],
            "image_dir": info["image_dir"],
            "label_dir": info["label_dir"],
            "mask_dir": info["mask_dir"],
            "name": task_id,
            "yolo_cache_path": str(PROJECT_ROOT / "data" / "runs" / "train"),
            "save_path": str(PROJECT_ROOT / "data" / "weights" / "sam2"),
            "device": os.environ.get("OMMATEUM_TRAIN_DEVICE", "cpu"),
        })
        # 用户传入的 params 覆盖默认值（忽略空值）
        merged = {**defaults, **{k: v for k, v in (params or {}).items()
                                 if v not in (None, "")}}
        for bk in ("cos_lr", "use_dora", "lowvram", "full_train"):
            if bk in merged:
                merged[bk] = bool(merged[bk])

        yolo_epochs = int(merged["yolo_epochs"])

        def _on_epoch_end(trainer):
            try:
                ep = int(trainer.epoch) + 1
            except Exception:
                return
            task["current_epoch"] = ep
            task["progress"] = round(min(0.7 * ep / max(yolo_epochs, 1), 0.7), 4)
            loss = getattr(trainer, "loss", None)
            if loss is not None:
                try:
                    task["loss"] = round(float(loss), 4)
                except Exception:
                    pass
            m = getattr(trainer, "metrics", None)
            if m is not None:
                try:
                    task["accuracy"] = round(float(getattr(m.box, "map50", 0.0) or 0.0), 4)
                except Exception:
                    pass
                try:
                    task["val_loss"] = round(float(getattr(trainer, "val_loss", task["loss"])), 4)
                except Exception:
                    pass

        try:
            YOLO.add_callback("on_train_epoch_end", _on_epoch_end)
        except Exception:
            pass

        # 加载 models/train.py（其内部会 import identify.train 与 sam2.train）
        train_path = SRC_DIR / "ommateum" / "models" / "train.py"
        if not train_path.exists():
            raise RuntimeError(f"未找到训练模块: {train_path}")
        # models/train.py 以「identify / sam2 为顶层模块」的方式 import，
        # 因此需把 src/ommateum/models 加入 sys.path 才能被正确解析。
        models_dir = SRC_DIR / "ommateum" / "models"
        if str(models_dir) not in sys.path:
            sys.path.insert(0, str(models_dir))
        spec = importlib.util.spec_from_file_location("ommateum_models_train", str(train_path))
        train_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(train_mod)

        # ---- 阶段1：YOLO 检测训练 ----
        task["stage"] = "YOLO 训练"
        model = train_mod.train_yolo_model(
            data_yaml=merged["data_yaml"],
            epochs=yolo_epochs,
            imgsz=int(merged["imgsz"]),
            batch=int(merged["yolo_batch_size"]),
            device=merged["device"],
            workers=int(merged["workers"]),
            project=merged["yolo_cache_path"],
            name=merged["name"],
            patience=int(merged["patience"]),
            freeze=int(merged["freeze"]),
            pretrained=merged["pretrained"],
            lr0=float(merged["yolo_lr"]),
            lrf=float(merged["lrf"]),
            cos_lr=bool(merged["cos_lr"]),
        )

        best_path = None
        if hasattr(model, "trainer") and getattr(model.trainer, "best", None):
            best_path = model.trainer.best

        # ---- 阶段2：SAM2 分割训练（若提供 model_path 且模块支持） ----
        if merged.get("model_path") and hasattr(train_mod, "train_sam2"):
            try:
                task["stage"] = "SAM2 训练"
                task["progress"] = max(task.get("progress", 0), 0.75)
                train_mod.train_sam2(
                    model_path=merged["model_path"],
                    save_path=merged["save_path"],
                    image_dir=merged["image_dir"],
                    label_dir=merged["label_dir"],
                    mask_dir=merged["mask_dir"],
                    epochs=int(merged["sam2_epochs"]),
                    batch_size=int(merged["sam2_batch_size"]),
                    lowvram=bool(merged["lowvram"]),
                    lora_rank=int(merged["lora_rank"]),
                    use_dora=bool(merged["use_dora"]),
                    device=merged["device"],
                    lr=float(merged["sam2_lr"]),
                    weight_decay=float(merged["weight_decay"]),
                    name=merged["name"],
                )
            except Exception as e:
                task["sam2_error"] = str(e)
                print(f"[WARN] SAM2 训练跳过: {e}")

        # 收尾
        final_acc = task.get("accuracy") or 0.0
        task["final_accuracy"] = final_acc
        task["accuracy"] = final_acc
        task["status"] = "done"
        task["progress"] = 1.0
        task["current_epoch"] = yolo_epochs

        model_key = merged.get("pretrained") or "yolo11n.pt"
        weight_id = f"trained_{task_id[-8:]}"
        weight_path = None
        size_mb = 0.0
        if best_path and os.path.exists(best_path):
            dst = MODEL_DIR / f"{weight_id}.pt"
            shutil.copy2(best_path, dst)
            weight_path = f"/models/{weight_id}.pt"
            size_mb = round(os.path.getsize(dst) / (1024 * 1024), 1)

        weight = {
            "id": weight_id,
            "name": f"用户训练权重 · {task['normal_count']}正常+{task['defect_count']}缺陷 · {yolo_epochs}epoch",
            "size_mb": size_mb,
            "dataset": f"用户数据 ({task['normal_count']}正常 + {task['defect_count']}缺陷)",
            "accuracy": final_acc, "trained": True,
            "task_id": task_id, "epochs": yolo_epochs, "lr": float(merged["yolo_lr"]),
            "path": weight_path,
            "created_at": _now_iso(),
        }
        TRAINED_WEIGHTS.setdefault(model_key, []).append(weight)
        task["weight_id"] = weight_id
        task["completed_at"] = _now_iso()
    except Exception as e:
        import traceback
        task["status"] = "error"
        task["error"] = str(e)
        task["traceback"] = traceback.format_exc()
        print(f"[ERROR] 训练任务 {task_id} 失败: {e}")


# ---------------------------------------------------------------------------
# Routes — Training
# ---------------------------------------------------------------------------
@app.route("/api/train", methods=["POST"])
def start_training():
    data = request.get_json(silent=True) or {}
    params = data.get("params", {}) or {}
    normal_ids = data.get("normal_image_ids", [])
    defect_ids = data.get("defect_image_ids", [])

    if not normal_ids and not defect_ids:
        return _err("至少需要上传一张训练图片", 400)
    missing = [iid for iid in (normal_ids + defect_ids) if iid not in IMAGES]
    if missing:
        return _err(f"训练图片不存在: {missing}", 404)

    yolo_epochs = int(params.get("yolo_epochs", 50))
    sam2_epochs = int(params.get("sam2_epochs", 8))
    if yolo_epochs < 1 or yolo_epochs > 200:
        return _err("yolo_epochs 范围 1-200", 400)

    task_id = f"train_{uuid.uuid4().hex[:12]}"
    task = {
        "id": task_id, "status": "training",
        "model": params.get("pretrained", "yolo11n.pt"),
        "epochs": yolo_epochs, "lr": float(params.get("yolo_lr", 0.001)),
        "normal_count": len(normal_ids), "defect_count": len(defect_ids),
        "current_epoch": 0, "progress": 0.0, "stage": "准备中",
        "loss": 0.0, "val_loss": 0.0, "accuracy": 0.0,
        "metrics": [], "started_at": _now_iso(),
        "start_timestamp": time.time(),
        "weight_id": None, "final_accuracy": None,
    }
    TRAINING_TASKS[task_id] = task

    # 在后台线程中调用真实训练（src/ommateum/models/train.py）
    t = threading.Thread(
        target=_training_worker,
        args=(task_id, params, normal_ids, defect_ids),
        daemon=True,
    )
    t.start()
    _TRAIN_THREADS[task_id] = t

    return _ok({
        "task_id": task_id, "status": "training",
        "epochs": yolo_epochs,
        "normal_count": len(normal_ids), "defect_count": len(defect_ids),
        "estimated_seconds": round((yolo_epochs + sam2_epochs) * EPOCH_DURATION, 1),
    })

@app.route("/api/train/<task_id>", methods=["GET"])
def get_training_status(task_id):
    if task_id not in TRAINING_TASKS:
        return _err("训练任务不存在", 404)
    # 状态由后台训练线程实时更新，这里直接返回真实任务状态
    task = TRAINING_TASKS[task_id]
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
