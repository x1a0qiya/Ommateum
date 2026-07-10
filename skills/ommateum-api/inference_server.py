"""YOLO 推理服务 - 供后端 API 调用。

在 GPU 容器中运行，接收图片路径或 ID，返回检测结果。
"""

from pathlib import Path

from flask import Flask, jsonify, request

app = Flask(__name__)

# 全局加载模型（容器启动时加载一次）
try:
    from sahi import AutoDetectionModel
    MODEL = AutoDetectionModel.from_pretrained(
        model_type="yolov8",
        model_path="/Ommateum/yolo11n.pt",
        confidence_threshold=0.25,
        device="cuda:0",
    )
    print("  ✓ YOLO 模型已加载")
except Exception as e:
    MODEL = None
    print(f"  ⚠ 模型加载失败: {e}")


@app.route("/inference/predict", methods=["POST"])
def predict():
    """接收后端传来的图片路径，返回检测结果。"""
    data = request.get_json(silent=True) or {}
    image_path = data.get("image_path")
    if not image_path:
        return jsonify({"status": "error", "message": "缺少 image_path"}), 400

    conf = data.get("conf", 0.25)
    slice_h = data.get("slice_height", 256)
    slice_w = data.get("slice_width", 640)
    overlap_h = data.get("overlap_h", 0.2)
    overlap_w = data.get("overlap_w", 0.2)

    if not Path(image_path).exists():
        return jsonify({"status": "error", "message": f"文件不存在: {image_path}"}), 404

    from sahi.predict import get_sliced_prediction as sahi_get_sliced

    result = sahi_get_sliced(
        image=image_path,
        detection_model=MODEL,
        slice_height=slice_h,
        slice_width=slice_w,
        overlap_height_ratio=overlap_h,
        overlap_width_ratio=overlap_w,
        postprocess_type="NMS",
    )

    detections = []
    for pred in result.object_prediction_list:
        detections.append({
            "category": pred.category.name,
            "category_id": pred.category.id,
            "score": float(round(pred.score.value, 4)),
            "bbox": [
                float(round(pred.bbox.minx, 2)),
                float(round(pred.bbox.miny, 2)),
                float(round(pred.bbox.maxx, 2)),
                float(round(pred.bbox.maxy, 2)),
            ],
        })

    return jsonify({"status": "ok", "detections": detections})


@app.route("/inference/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "model_loaded": MODEL is not None})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
