#!/usr/bin/env python3
"""
YOLO 数据集数据增强脚本。

基于 albumentations 对目标检测数据集进行在线增强，自动同步变换
YOLO 格式标注（归一化 class_id x_center y_center width height）。

功能:
  - 从 images/ 目录读取图片，自动查找同级 labels/ 下的同名 .txt 标注
  - 若存在同级 masks/ 目录，自动同步增强掩码（仅几何变换）
  - 支持指定输出目录 (output/images/ + output/labels/ + output/masks/)，默认在原路径追加
  - 每张原图生成 N 个增强变体，命名格式: basename_aug{N}.jpg / .txt / .png
  - 无标注的图片仅做图像增强，不生成空标签文件
  - 支持多类别、多尺度、多光照条件的增强管道

用法:
  # 在原 images / labels / masks 目录中追加增强数据（自动检测 masks/）
  python src/ommateum/models/identify/augment_dataset.py \
      --images /path/to/dataset/images

  # 指定输出目录，增强 5 个变体
  python src/ommateum/models/identify/augment_dataset.py \
      --images /path/to/dataset/images \
      --output /path/to/augmented \
      --num_aug 5

  # 显式指定 masks 目录
  python src/ommateum/models/identify/augment_dataset.py \
      --images /path/to/dataset/images \
      --masks /path/to/dataset/masks \
      --output /path/to/augmented \
      --num_aug 3

Python API:
  from ommateum.models.identify.augment_dataset import augment_dataset

  augment_dataset(
      images_dir="/path/to/images",
      labels_dir=None,          # 默认取 images 同级的 labels/
      masks_dir=None,           # 默认取 images 同级的 masks/，不存在则跳过
      output_dir="/path/to/out",# 默认 None → 写回原路径
      num_aug=3,
  )
"""

import argparse
import os
from pathlib import Path
from typing import List, Optional, Tuple

import albumentations as A
import cv2

# ── 支持的图像后缀 ──
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"}


# ── 增强管道定义 ──

# 阶段一：几何变换（作用于图像 + bbox + mask，三者严格同步）
_GEOM_TRANSFORMS = [
    A.HorizontalFlip(p=0.5),
    A.VerticalFlip(p=0.1),
    A.Affine(
        scale=(0.85, 1.1),
        translate_percent=(-0.1, 0.1),
        rotate=(-15, 15),
        shear=(-3, 3),
        p=0.5,
        border_mode=cv2.BORDER_CONSTANT,
    ),
]

# 阶段二：像素变换（仅作用于 RGB 图像，不触碰 mask / bbox）
_PIXEL_TRANSFORMS = [
    A.OneOf(
        [
            A.RandomBrightnessContrast(
                brightness_limit=0.2, contrast_limit=0.2, p=1.0,
            ),
            A.HueSaturationValue(
                hue_shift_limit=10, sat_shift_limit=20,
                val_shift_limit=20, p=1.0,
            ),
        ],
        p=0.5,
    ),
    A.OneOf(
        [
            A.GaussNoise(std_range=(0.02, 0.10), p=1.0),
            A.GaussianBlur(blur_limit=(3, 5), p=1.0),
            A.MotionBlur(blur_limit=(3, 5), p=1.0),
        ],
        p=0.3,
    ),
    A.RandomGamma(gamma_limit=(80, 120), p=0.2),
    A.CLAHE(clip_limit=2.0, tile_grid_size=(8, 8), p=0.2),
]


def _build_pipelines(
    with_bbox: bool = False,
    with_mask: bool = False,
) -> Tuple[A.Compose, A.Compose]:
    """根据数据可用性构建两阶段管道。

    阶段 1 — 几何变换管道：通过 additional_targets 保证 image / bbox / mask 严格同步。
    阶段 2 — 像素变换管道：仅作用于 RGB 图像。

    Returns:
        (geom_pipeline, pixel_pipeline)
    """
    geom_kwargs: dict = {}
    if with_bbox:
        geom_kwargs["bbox_params"] = A.BboxParams(
            format="yolo",
            label_fields=["class_labels"],
            min_visibility=0.3,
            min_area=0.0,
        )
    if with_mask:
        geom_kwargs["additional_targets"] = {"mask": "image"}

    return A.Compose(_GEOM_TRANSFORMS, **geom_kwargs), A.Compose(_PIXEL_TRANSFORMS)


# ── 标注读取 / 写入 ──

def _read_yolo_labels(label_path: str) -> Tuple[List[List[float]], List[int]]:
    """
    读取 YOLO 格式的标签文件。

    Args:
        label_path (str): .txt 标注文件路径。

    Returns:
        Tuple[List[List[float]], List[int]]:
            - bboxes: 归一化 bbox 列表 [x_center, y_center, width, height]。
            - class_ids: 对应类别 ID 列表。
    """
    bboxes: List[List[float]] = []
    class_ids: List[int] = []

    with open(label_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) < 5:
                continue
            class_id = int(parts[0])
            x, y, w, h = map(float, parts[1:5])
            class_ids.append(class_id)
            bboxes.append([x, y, w, h])

    return bboxes, class_ids


def _clip_bboxes(
    bboxes: List[List[float]],
    class_ids: List[int],
) -> Tuple[List[List[float]], List[int]]:
    """裁剪 bbox 到 [0,1] 归一化范围，剔除退化框。

    有些标注工具生成的 bbox 可能略微超出边界（如 width > 1），
    在传入 albumentations 之前需要裁剪，否则会触发验证错误。
    """
    clipped_bboxes: List[List[float]] = []
    clipped_ids: List[int] = []
    for bbox, cls_id in zip(bboxes, class_ids):
        cx, cy, w, h = bbox
        x1 = cx - w / 2.0
        y1 = cy - h / 2.0
        x2 = cx + w / 2.0
        y2 = cy + h / 2.0
        x1 = max(0.0, x1)
        y1 = max(0.0, y1)
        x2 = min(1.0, x2)
        y2 = min(1.0, y2)
        new_w = x2 - x1
        new_h = y2 - y1
        if new_w <= 0.0 or new_h <= 0.0:
            continue
        clipped_bboxes.append([x1 + new_w / 2.0, y1 + new_h / 2.0, new_w, new_h])
        clipped_ids.append(cls_id)
    return clipped_bboxes, clipped_ids


def _write_yolo_labels(label_path: str, bboxes: List[List[float]], class_ids: List[int]) -> None:
    """
    将 bbox 和类别 ID 写入 YOLO 格式 .txt 文件。

    Args:
        label_path (str): 输出标注文件路径。
        bboxes (List[List[float]]): 归一化 bbox 列表。
        class_ids (List[int]): 类别 ID 列表。
    """
    os.makedirs(os.path.dirname(label_path), exist_ok=True)
    with open(label_path, "w", encoding="utf-8") as f:
        for cid, bbox in zip(class_ids, bboxes):
            f.write(f"{cid} {bbox[0]:.6f} {bbox[1]:.6f} {bbox[2]:.6f} {bbox[3]:.6f}\n")


# ── 核心增强函数 ──

def augment_dataset(
    images_dir: str,
    labels_dir: Optional[str] = None,
    masks_dir: Optional[str] = None,
    output_dir: Optional[str] = None,
    num_aug: int = 3,
) -> dict:
    """
    对指定数据集进行数据增强。

    遍历 images_dir 下所有图片，自动查找同级 labels/ 和 masks/，
    每张图片生成 num_aug 个增强变体，同步变换 bbox 和掩码。

    Args:
        images_dir (str): 原始图片目录路径。
        labels_dir (Optional[str]): 原始标注目录路径，默认取 images_dir
            父目录下的 labels/。若目录不存在则不处理标注。
        masks_dir (Optional[str]): 掩码目录路径，默认取 images_dir
            父目录下的 masks/。若目录不存在则不处理掩码。
        output_dir (Optional[str]): 增强数据输出根目录，默认 None
            表示在原路径中追加。
        num_aug (int): 每张原图生成的增强变体数量，默认 3。

    Returns:
        dict: 统计信息 ——
            - total_images (int): 处理的原始图片数。
            - total_augmented (int): 生成的增强图片总数。
            - images_with_labels (int): 带标注的图片数。
            - images_with_masks (int): 带掩码的图片数。
            - output_images_dir (str): 增强图片输出目录。
            - output_labels_dir (str): 增强标注输出目录。
            - output_masks_dir (str): 增强掩码输出目录。
    """
    images_dir = os.path.abspath(images_dir)
    parent_dir = os.path.dirname(images_dir)

    # ── 推断 labels 目录 ──
    if labels_dir is None:
        inferred = os.path.join(parent_dir, "labels")
        labels_dir = inferred if os.path.isdir(inferred) else None
    else:
        labels_dir = os.path.abspath(labels_dir)
        if not os.path.isdir(labels_dir):
            print(f"[WARN] 指定的 labels 目录不存在: {labels_dir}，将仅对图片做增强")
            labels_dir = None

    # ── 推断 masks 目录 ──
    if masks_dir is None:
        inferred = os.path.join(parent_dir, "masks")
        masks_dir = inferred if os.path.isdir(inferred) else None
    else:
        masks_dir = os.path.abspath(masks_dir)
        if not os.path.isdir(masks_dir):
            print(f"[WARN] 指定的 masks 目录不存在: {masks_dir}，将不处理掩码")
            masks_dir = None
    if masks_dir:
        print(f"[INFO] 检测到掩码目录: {masks_dir}，将同步增强掩码")

    # ── 确定输出路径 ──
    if output_dir is None:
        out_images_dir = images_dir
        out_labels_dir = labels_dir
        out_masks_dir = masks_dir
    else:
        output_dir = os.path.abspath(output_dir)
        out_images_dir = os.path.join(output_dir, "images")
        out_labels_dir = os.path.join(output_dir, "labels") if labels_dir else None
        out_masks_dir = os.path.join(output_dir, "masks") if masks_dir else None
        os.makedirs(out_images_dir, exist_ok=True)
        if out_labels_dir:
            os.makedirs(out_labels_dir, exist_ok=True)
        if out_masks_dir:
            os.makedirs(out_masks_dir, exist_ok=True)

    # ── 收集待处理图片 ──
    image_files: List[str] = []
    for fname in sorted(os.listdir(images_dir)):
        if Path(fname).suffix.lower() in IMAGE_EXTS:
            image_files.append(fname)

    if not image_files:
        print("[WARN] 未在 images_dir 中找到图片文件")
        return {
            "total_images": 0,
            "total_augmented": 0,
            "images_with_labels": 0,
            "images_with_masks": 0,
            "output_images_dir": out_images_dir,
            "output_labels_dir": out_labels_dir or "",
            "output_masks_dir": out_masks_dir or "",
        }

    total_images = len(image_files)
    total_augmented = 0
    images_with_labels = 0
    images_with_masks = 0

    # ── 逐张增强 ──
    for fname in image_files:
        img_path = os.path.join(images_dir, fname)
        image = cv2.imread(img_path)
        if image is None:
            print(f"[SKIP] 无法读取图片: {img_path}")
            continue

        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        h, w = image.shape[:2]

        stem = Path(fname).stem

        # 读取对应标注（如果存在）
        has_labels = False
        bboxes: List[List[float]] = []
        class_ids: List[int] = []
        if labels_dir:
            label_path = os.path.join(labels_dir, f"{stem}.txt")
            if os.path.isfile(label_path):
                bboxes, class_ids = _read_yolo_labels(label_path)
                if bboxes:
                    bboxes, class_ids = _clip_bboxes(bboxes, class_ids)
                if bboxes:
                    has_labels = True
                    images_with_labels += 1

        # 读取对应掩码（如果存在）
        has_mask = False
        mask_image = None
        if masks_dir:
            for ext in [".png", ".jpg", ".jpeg", ".bmp"]:
                mask_path = os.path.join(masks_dir, f"{stem}{ext}")
                if os.path.isfile(mask_path):
                    mask_image = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
                    if mask_image is not None and mask_image.shape[:2] == (h, w):
                        has_mask = True
                        images_with_masks += 1
                    else:
                        mask_image = None
                    break

        # 构建两阶段管道
        # 阶段 1 — 几何变换：图 + bbox + mask 在同一 Compose 中严格同步
        # 阶段 2 — 像素变换：仅作用于 RGB 图像
        geom_pipeline, pixel_pipeline = _build_pipelines(
            with_bbox=has_labels, with_mask=has_mask
        )

        base_stem = stem

        for aug_idx in range(num_aug):
            # ── 组装几何变换参数 ──
            geom_kwargs: dict = {"image": image.copy()}
            if has_labels:
                geom_kwargs["bboxes"] = bboxes.copy()
                geom_kwargs["class_labels"] = class_ids.copy()
            if has_mask:
                geom_kwargs["mask"] = mask_image.copy()

            geom_result = geom_pipeline(**geom_kwargs)
            # 图像再经过像素变换
            aug_image = pixel_pipeline(image=geom_result["image"])["image"]

            # ── bbox 后处理 ──
            if has_labels:
                aug_bboxes: List[List[float]] = geom_result["bboxes"]
                aug_class_ids: List[int] = geom_result["class_labels"]

                valid_bboxes = []
                valid_class_ids = []
                for bbox, cls_id in zip(aug_bboxes, aug_class_ids):
                    x, y, bw, bh = bbox
                    x = max(0.0, min(1.0, x))
                    y = max(0.0, min(1.0, y))
                    bw = max(0.0, min(1.0, bw))
                    bh = max(0.0, min(1.0, bh))
                    if bw <= 0.0 or bh <= 0.0:
                        continue
                    x1 = max(0.0, x - bw / 2.0)
                    y1 = max(0.0, y - bh / 2.0)
                    x2 = min(1.0, x + bw / 2.0)
                    y2 = min(1.0, y + bh / 2.0)
                    new_w = x2 - x1
                    new_h = y2 - y1
                    if new_w <= 0.0 or new_h <= 0.0:
                        continue
                    valid_bboxes.append([x1 + new_w / 2.0, y1 + new_h / 2.0, new_w, new_h])
                    valid_class_ids.append(cls_id)

                if out_labels_dir and valid_bboxes:
                    out_label_name = f"{base_stem}_aug{aug_idx}.txt"
                    out_label_path = os.path.join(out_labels_dir, out_label_name)
                    _write_yolo_labels(out_label_path, valid_bboxes, valid_class_ids)

            # ── 掩码保存 ──
            if has_mask and out_masks_dir:
                aug_mask = geom_result["mask"]
                out_mask_name = f"{base_stem}_aug{aug_idx}.png"
                out_mask_path = os.path.join(out_masks_dir, out_mask_name)
                cv2.imwrite(out_mask_path, aug_mask)

            # 保存增强后的图片
            out_img_name = f"{base_stem}_aug{aug_idx}.jpg"
            out_img_path = os.path.join(out_images_dir, out_img_name)
            aug_image_bgr = cv2.cvtColor(aug_image, cv2.COLOR_RGB2BGR)
            cv2.imwrite(out_img_path, aug_image_bgr)
            total_augmented += 1

        print(f"[OK] {fname} → 生成 {num_aug} 个变体")

    # ── 汇总日志 ──
    print(f"\n[完成] 数据增强结束")
    print(f"  原始图片: {total_images}")
    print(f"  增强图片: {total_augmented}")
    print(f"  带标注图片: {images_with_labels}")
    print(f"  带掩码图片: {images_with_masks}")
    print(f"  图片输出: {out_images_dir}")
    if out_labels_dir:
        print(f"  标注输出: {out_labels_dir}")
    if out_masks_dir:
        print(f"  掩码输出: {out_masks_dir}")

    return {
        "total_images": total_images,
        "total_augmented": total_augmented,
        "images_with_labels": images_with_labels,
        "images_with_masks": images_with_masks,
        "output_images_dir": out_images_dir,
        "output_labels_dir": out_labels_dir or "",
        "output_masks_dir": out_masks_dir or "",
    }


# ── CLI 入口 ──

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="YOLO 数据集数据增强（基于 albumentations）",
    )
    parser.add_argument(
        "--images",
        type=str,
        required=True,
        help="原始图片目录路径 (images/)",
    )
    parser.add_argument(
        "--labels",
        type=str,
        default=None,
        help="原始标注目录路径 (labels/)，默认取 images 同级的 labels/",
    )
    parser.add_argument(
        "--masks",
        type=str,
        default=None,
        help="掩码目录路径 (masks/)，默认取 images 同级的 masks/，不存在则跳过掩码增强",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="增强数据输出根目录，默认在原路径追加",
    )
    parser.add_argument(
        "--num_aug",
        type=int,
        default=3,
        help="每张原图生成的增强变体数（默认 3）",
    )
    args = parser.parse_args()

    augment_dataset(
        images_dir=args.images,
        labels_dir=args.labels,
        masks_dir=args.masks,
        output_dir=args.output,
        num_aug=args.num_aug,
    )
