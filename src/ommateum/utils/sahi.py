from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sahi.predict import get_sliced_prediction
    from sahi import AutoDetectionModel

try:
    from sahi.predict import get_sliced_prediction as sahi_get_sliced
    from sahi import AutoDetectionModel
except ImportError:
    sahi_get_sliced = None  # type: ignore[assignment]
    AutoDetectionModel = None  # type: ignore[assignment]


def _build_coco_json(
    results_with_paths: list[tuple[str, Any]],
    export_dir: str,
) -> None:
    """将 SAHI 检测结果导出为 COCO JSON 格式。

    Args:
        results_with_paths: [(image_path, SliceDetectionResult), ...]
        export_dir: 导出目录。
    """
    export_path = Path(export_dir)
    export_path.mkdir(parents=True, exist_ok=True)

    images: list[dict[str, Any]] = []
    annotations: list[dict[str, Any]] = []
    categories: dict[str, int] = {}
    ann_id = 1

    for img_idx, (img_path, result) in enumerate(results_with_paths, start=1):
        img_name = Path(img_path).name
        # 从图片文件读取尺寸（SAHI 对象属性名各版本不一致）
        try:
            from PIL import Image
            with Image.open(img_path) as _img:
                w, h = _img.size
        except Exception:
            w, h = 0, 0
        images.append({
            "id": img_idx,
            "file_name": img_name,
            "width": w,
            "height": h,
        })

        for pred in result.object_prediction_list:
            cat_name = pred.category.name
            cat_id = pred.category.id
            if cat_name not in categories:
                categories[cat_name] = cat_id

            bbox = [
                float(round(pred.bbox.minx, 2)),
                float(round(pred.bbox.miny, 2)),
                float(round(pred.bbox.maxx - pred.bbox.minx, 2)),
                float(round(pred.bbox.maxy - pred.bbox.miny, 2)),
            ]

            segmentation: list[list[float]] | None = None
            if pred.mask is not None:
                mask = pred.mask.bool_mask
                import cv2
                contours, _ = cv2.findContours(
                    mask.astype("uint8"), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
                )
                if contours:
                    segmentation = [
                        contour.flatten().tolist()
                        for contour in contours
                        if len(contour) >= 6
                    ]

            annotations.append({
                "id": ann_id,
                "image_id": img_idx,
                "category_id": cat_id,
                "bbox": bbox,
                "area": float(round(bbox[2] * bbox[3], 2)),
                "score": float(round(pred.score.value, 4)),
                "segmentation": segmentation or [],
                "iscrowd": 0,
            })
            ann_id += 1

    categories_list = [
        {"id": cid, "name": cname, "supercategory": "defect"}
        for cname, cid in sorted(categories.items(), key=lambda x: x[1])
    ]

    coco_data = {
        "images": images,
        "annotations": annotations,
        "categories": categories_list,
    }

    import json
    out_path = export_path / "annotations.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(coco_data, f, ensure_ascii=False, indent=2)
    print(f"  COCO JSON 已导出: {out_path}")


def predict(
    model_type: str,
    model_path: str,
    model_confidence_threshold: float,
    model_device: str,
    source: str,
    slice_height: int,
    slice_width: int,
    overlap_height_ratio: float,
    overlap_width_ratio: float,
    project: str,
    name: str,
    export_coco: bool = True,
) -> list[dict[str, Any]]:
    """
    使用 SAHI 逐图切片推理，可靠获取检测结果并可选导出 COCO JSON。

    Args:
        model_type: 模型类型标识（如 "yolov8", "mmdet" 等）
        model_path: 模型权重文件路径
        model_confidence_threshold: 置信度阈值
        model_device: 模型部署设备（如 "cpu", "cuda:0"）
        source: 图像文件夹路径
        slice_height: 切片高度（像素）
        slice_width: 切片宽度（像素）
        overlap_height_ratio: 高度方向重叠比例（0~1）
        overlap_width_ratio: 宽度方向重叠比例（0~1）
        project: 结果输出目录（如 "./result"）
        name:     实验名称（如 "exp"）
        export_coco: 是否导出 COCO JSON

    Returns:
        检测结果列表。
    """
    if sahi_get_sliced is None:
        raise ImportError("SAHI 库未安装，请执行: pip install sahi")

    model_path_obj = Path(model_path)
    source_path = Path(source)

    if not model_path_obj.exists():
        raise FileNotFoundError(f"模型权重文件未找到: {model_path}")
    if not source_path.exists():
        raise FileNotFoundError(f"图像数据源路径未找到: {source}")

    # 收集图片路径
    image_paths = sorted([
        p for p in source_path.iterdir()
        if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    ])
    if not image_paths:
        print("  [警告] 未找到任何图片文件")
        return []

    # 加载模型（复用）
    try:
        model = AutoDetectionModel.from_pretrained(
            model_type=model_type,
            model_path=str(model_path_obj),
            confidence_threshold=model_confidence_threshold,
            device=model_device,
        )
    except Exception as e:
        raise RuntimeError(f"模型加载失败: {e}") from e

    export_dir = Path(project) / name
    export_dir.mkdir(parents=True, exist_ok=True)

    results_with_paths: list[tuple[str, Any]] = []
    summary: list[dict[str, Any]] = []

    for img_path in image_paths:
        try:
            result = sahi_get_sliced(
                image=str(img_path),
                detection_model=model,
                slice_height=slice_height,
                slice_width=slice_width,
                overlap_height_ratio=overlap_height_ratio,
                overlap_width_ratio=overlap_width_ratio,
                postprocess_type="NMS",
            )
            results_with_paths.append((str(img_path), result))

            # 保存可视化图片（原图 + 检测框）
            result.export_visuals(export_dir=str(export_dir), file_name=img_path.stem)

            for pred in result.object_prediction_list:
                summary.append({
                    "image_path": str(img_path),
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
        except Exception as e:
            print(f"  [跳过] {img_path.name}: {e}")

    # 导出 COCO JSON
    if export_coco:
        _build_coco_json(results_with_paths, str(export_dir))

    print(f"  处理完成: {len(image_paths)} 张图片, {len(summary)} 个检测框")
    return summary
