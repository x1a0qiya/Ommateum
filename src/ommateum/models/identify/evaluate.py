"""
YOLO 模型评估脚本（仅验证，不训练）。
供 test.sh 或外部服务调用。
"""

import argparse
import json
import os
from typing import Optional, Union

from ultralytics import YOLO


def evaluate_yolo_model(
    weights : str,
    data_yaml : str,
    imgsz : int = 640,
    batch : int = 16,
    device : Union[str, int] = "0",
    workers : int = 4,
    project : str = "runs/eval",
    name : str = "eval",
    save_json : bool = True,
    conf : Optional[float] = None,
    iou : float = 0.7,
) -> dict:
    """
    评估 YOLO 模型在指定数据集上的性能，输出指标 JSON 文件。

    Args:
        weights (str): 模型权重路径 (.pt)。
        data_yaml (str): 数据集 data.yaml 配置文件路径。
        imgsz (int): 输入图像尺寸（像素）。
        batch (int): 批大小，根据显存调整。
        device (str | int): 评估设备，如 "0" 表示第一块 GPU，"cpu" 表示 CPU。
        workers (int): 数据加载线程数。
        project (str): 评估输出根目录。
        name (str): 实验子目录名称。
        save_json (bool): 是否保存 COCO 格式 JSON 预测结果。
        conf (float | None): 置信度阈值，None 使用 Ultralytics 默认值。
        iou (float): NMS IoU 阈值。

    Returns:
        dict: 包含以下键的评估指标字典——
            - mAP50 (float): mAP@0.5
            - mAP50_95 (float): mAP@0.5:0.95
            - precision (float): 精确率
            - recall (float): 召回率
            - f1 (float | None): F1 分数
            - save_dir (str): 结果保存目录
    """
    model = YOLO(weights)

    results = model.val(
        data=data_yaml,
        imgsz=imgsz,
        batch=batch,
        device=device,
        workers=workers,
        project=project,
        name=name,
        exist_ok=True,
        conf=conf,
        iou=iou,
        save_json=save_json,
        plots=True,
        verbose=True,
    )

    # 提取核心指标
    metrics = {
        "mAP50": float(results.box.map50),
        "mAP50_95": float(results.box.map),
        "precision": float(results.box.mp),
        "recall": float(results.box.mr),
        "f1": float(results.box.f1) if results.box.f1 is not None else None,
        "save_dir": str(results.save_dir),
    }

    print("\n" + "=" * 50)
    print("评估结果:")
    print(f"  mAP@0.5:      {metrics['mAP50']:.4f}")
    print(f"  mAP@0.5:0.95: {metrics['mAP50_95']:.4f}")
    print(f"  Precision:    {metrics['precision']:.4f}")
    print(f"  Recall:       {metrics['recall']:.4f}")
    if metrics["f1"] is not None:
        print(f"  F1 Score:     {metrics['f1']:.4f}")
    print(f"  结果目录:      {metrics['save_dir']}")
    print("=" * 50 + "\n")

    # 保存指标为 JSON 便于前端读取
    json_path = os.path.join(results.save_dir, "metrics.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)
    print(f"指标已保存到: {json_path}")

    return metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="评估 YOLO 模型")
    parser.add_argument("--weights", required=True, help="模型权重路径 (.pt)")
    parser.add_argument("--data", required=True, help="数据集 data.yaml 路径")
    parser.add_argument("--imgsz", type=int, default=640, help="输入图像尺寸")
    parser.add_argument("--batch", type=int, default=16, help="批大小")
    parser.add_argument("--device", default="0", help="设备, 如 '0' 或 'cpu'")
    parser.add_argument("--workers", type=int, default=4, help="数据加载线程数")
    parser.add_argument("--project", default="runs/eval", help="输出根目录")
    parser.add_argument("--name", default="eval", help="实验名称")
    parser.add_argument("--conf", type=float, default=None, help="置信度阈值")
    parser.add_argument("--iou", type=float, default=0.7, help="NMS IoU 阈值")
    args = parser.parse_args()

    evaluate_yolo_model(
        weights=args.weights,
        data_yaml=args.data,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        workers=args.workers,
        project=args.project,
        name=args.name,
        conf=args.conf,
        iou=args.iou,
    )
