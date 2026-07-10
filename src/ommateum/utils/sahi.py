from pathlib import Path
from typing import TYPE_CHECKING, Any, Any

if TYPE_CHECKING:
    from sahi.predict import predict as sahi_predict

try:
    from sahi.predict import predict as sahi_predict
except ImportError:
    sahi_predict = None  # type: ignore[assignment]


def _build_coco_json(results: list[Any], export_dir: str) -> None:
    """将 SAHI 检测结果导出为 COCO JSON 格式。"""
    export_path = Path(export_dir)
    export_path.mkdir(parents=True, exist_ok=True)

    images: list[dict[str, Any]] = []
    annotations: list[dict[str, Any]] = []
    categories: dict[str, int] = {}
    ann_id = 1

    for img_idx, result in enumerate(results, start=1):
        img_name = Path(result.image_path).name
        h, w = result.original_image_height, result.original_image_width
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
                round(pred.bbox.minx, 2),
                round(pred.bbox.miny, 2),
                round(pred.bbox.maxx - pred.bbox.minx, 2),
                round(pred.bbox.maxy - pred.bbox.miny, 2),
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
                "area": round(bbox[2] * bbox[3], 2),
                "score": round(pred.score.value, 4),
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
    使用 SAHI 进行切片推理，可选导出 COCO JSON 格式标注文件。

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
        project: SAHI 项目目录（如 "./runs/predict"）
        name:     SAHI 实验名称（如 "exp"）
        export_coco: 是否额外导出 COCO JSON 标注文件到 {project}/{name}/

    Returns:
        检测结果列表，每条含 image_path, bbox, category, score 等字段。
    """
    if sahi_predict is None:
        raise ImportError("SAHI 库未安装，请执行: pip install sahi")

    model_path_obj = Path(model_path)
    source_path = Path(source)

    if not model_path_obj.exists():
        raise FileNotFoundError(f"模型权重文件未找到: {model_path}")
    if not source_path.exists():
        raise FileNotFoundError(f"图像数据源路径未找到: {source}")

    try:
        results: Any = sahi_predict(
            model_type=model_type,
            model_path=str(model_path_obj),
            model_device=model_device,
            model_confidence_threshold=model_confidence_threshold,
            source=str(source_path),
            slice_height=slice_height,
            slice_width=slice_width,
            overlap_height_ratio=overlap_height_ratio,
            overlap_width_ratio=overlap_width_ratio,
            project=project,
            name=name,
        )

        # 收集精简结果
        summary: list[dict[str, Any]] = []
        for det_result in results:
            for pred in det_result.object_prediction_list:
                summary.append({
                    "image_path": det_result.image_path,
                    "category": pred.category.name,
                    "category_id": pred.category.id,
                    "score": round(pred.score.value, 4),
                    "bbox": [
                        round(pred.bbox.minx, 2),
                        round(pred.bbox.miny, 2),
                        round(pred.bbox.maxx, 2),
                        round(pred.bbox.maxy, 2),
                    ],
                })

        # 可选导出 COCO JSON
        if export_coco:
            export_dir = str(Path(project) / name)
            _build_coco_json(results, export_dir)

        return summary

    except ValueError as e:
        raise ValueError(f"预测参数配置错误: {e}") from e
    except Exception as e:
        raise RuntimeError(f"批量切片推理执行失败: {e}") from e
