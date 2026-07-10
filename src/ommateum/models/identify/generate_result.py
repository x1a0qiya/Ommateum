"""
YOLO 推理脚本 —— 批量对图片集进行检测，输出 YOLO 格式结果。

供外部服务 / 前端调用，加载指定模型对图片目录进行推理，
将结果以 YOLO 标准格式保存为 .txt 文件（一图一文件，文件名与图片相同）。
"""

import argparse
import os
from pathlib import Path
from typing import Optional, Union

from ultralytics import YOLO


def generate_result(
    images_dir : str,
    model_path : str,
    output_dir : Optional[str] = None,
    conf : float = 0.25,
    iou : float = 0.7,
    device : Union[str, int] = "0",
    imgsz : int = 640,
) -> str:
    """
    对图片集进行批量推理，输出 YOLO 标准格式的检测结果。

    YOLO 标签格式（归一化坐标）::
        class_id x_center y_center width height

    每张图片对应一个同名的 .txt 文件，未检测到目标时生成空文件。

    Args:
        images_dir (str): 输入图片目录路径（或单张图片路径）。
        model_path (str): 模型权重文件路径 (.pt)。
        output_dir (str | None): 输出 labels 目录路径，默认为 images_dir 同级目录下的 labels/。
        conf (float): 置信度阈值 (0.0~1.0)，低于此值的结果将被过滤。
        iou (float): NMS IoU 阈值 (0.0~1.0)。
        device (str | int): 推理设备，如 "0" 表示第一块 GPU，"cpu" 表示 CPU。
        imgsz (int): 推理时图像尺寸（像素）。

    Returns:
        str: 输出 labels 目录的绝对路径。

    Raises:
        FileNotFoundError: 模型权重或图片目录不存在时抛出。
    """
    # ── 路径校验 ──
    model_path = os.path.abspath(model_path)
    images_dir = os.path.abspath(images_dir)

    if not os.path.exists(model_path):
        raise FileNotFoundError(f"模型权重文件不存在: {model_path}")
    if not os.path.exists(images_dir):
        raise FileNotFoundError(f"图片目录不存在: {images_dir}")

    # ── 确定输出目录 ──
    if output_dir is None:
        parent_dir = os.path.dirname(images_dir)
        output_dir = os.path.join(parent_dir, "labels")
    output_dir = os.path.abspath(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    # ── 加载模型并推理 ──
    model = YOLO(model_path)
    results = model(
        source=images_dir,
        conf=conf,
        iou=iou,
        device=device,
        imgsz=imgsz,
        save=False,           # 不保存标注后的图片
        save_txt=False,       # 手动写入，以便控制输出路径
        verbose=False,
    )

    # ── 写入 YOLO 格式标签文件 ──
    written = 0
    for result in results:
        img_path = Path(result.path)
        txt_name = img_path.stem + ".txt"
        txt_path = os.path.join(output_dir, txt_name)

        if result.boxes is not None and len(result.boxes) > 0:
            boxes = result.boxes
            with open(txt_path, "w", encoding="utf-8") as f:
                for idx in range(len(boxes)):
                    cls_id = int(boxes.cls[idx].item())
                    x_center = float(boxes.xywhn[idx][0].item())
                    y_center = float(boxes.xywhn[idx][1].item())
                    width = float(boxes.xywhn[idx][2].item())
                    height = float(boxes.xywhn[idx][3].item())
                    f.write(f"{cls_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}\n")
            written += 1
        else:
            # 无检测结果，写入空文件以保持一一对应
            open(txt_path, "w", encoding="utf-8").close()

    print(f"[完成] 推理结果已输出到: {output_dir}")
    print(f"       共处理 {len(results)} 张图片，{written} 张有检测结果")
    return output_dir


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="YOLO 批量推理，输出标准标签格式")
    parser.add_argument("--images_dir", required=True, help="输入图片目录（或单张图片路径）")
    parser.add_argument("--model_path", required=True, help="模型权重路径 (.pt)")
    parser.add_argument("--output_dir", default=None,
                        help="输出 labels 目录，默认在 images_dir 同级目录下创建 labels/")
    parser.add_argument("--conf", type=float, default=0.25, help="置信度阈值")
    parser.add_argument("--iou", type=float, default=0.7, help="NMS IoU 阈值")
    parser.add_argument("--device", default="0", help="设备，如 '0' 或 'cpu'")
    parser.add_argument("--imgsz", type=int, default=640, help="推理图像尺寸")
    args = parser.parse_args()

    generate_result(
        images_dir=args.images_dir,
        model_path=args.model_path,
        output_dir=args.output_dir,
        conf=args.conf,
        iou=args.iou,
        device=args.device,
        imgsz=args.imgsz,
    )
