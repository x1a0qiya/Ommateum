import os, sys
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(parent_dir)
sys.path.append('')

import argparse
import torch
from utils.sahi import predict
from identify.generate_result import generate_result
from sam2.test import predict_and_save_mask_from_yolo

def parse_args():
    parser = argparse.ArgumentParser(description='')

    parser.add_argument("--images_dir", required=True, help="输入图片目录（或单张图片路径）")
    parser.add_argument("--yolo_model_path", default="weights/yolo/pretrained/yolo11n.pt",
                        help="模型权重路径 (.pt)，默认为 weights/yolo/pretrained/yolo11n.pt（未训练模型）")
    parser.add_argument("--yolo_output_dir", default=None,
                        help="输出 labels 目录，默认在 images_dir 同级目录下创建 labels/")
    parser.add_argument("--conf", type=float, default=0.25, help="置信度阈值")
    parser.add_argument("--iou", type=float, default=0.7, help="NMS IoU 阈值")
    parser.add_argument("--imgsz", type=int, default=640, help="推理图像尺寸")

    parser.add_argument('--sam2_model_path', type=str, default='facebook/sam2-hiera-tiny', help='sam2 model')
    parser.add_argument('--lora_path', type=str, default=None, help='Path to the saved LoRA adapter directory')
    parser.add_argument('--output_mask_path', type=str, required=True)

    parser.add_argument('--model_type', type=str, default='ultralytics')
    parser.add_argument('--model_confidence_threshold', type=float, default=0.5)
    parser.add_argument('--device', type=str, default='cuda' if torch.cuda.is_available() else 'cpu')
    parser.add_argument('--slice_height', type=int, default=256)
    parser.add_argument('--slice_width', type=int, default=256)
    parser.add_argument('--overlap_height_ratio', type=float, default=0.2)
    parser.add_argument('--overlap_width_ratio', type=float, default=0.2)
    parser.add_argument('--project', type=str)
    parser.add_argument('--name', type=str, default='exp')
        
    return parser.parse_args()

def segment(args=None):
    if args is None:
        args = parse_args()

    generate_result(
        images_dir=args.images_dir,
        model_path=args.yolo_model_path,
        output_dir=args.yolo_output_dir,
        conf=args.conf,
        iou=args.iou,
        device=args.device,
        imgsz=args.imgsz,
    )

    predict_and_save_mask_from_yolo(
        image_path=args.images_dir,
        yolo_txt_path=args.yolo_output_dir,
        model_path=args.sam2_model_path,
        lora_path=args.lora_path,
        output_mask_path=args.output_mask_path,
        device=args.device
    )

    predict(
        model_path=args.yolo_model_path,
        source=args.images_dir,
        model_type=args.model_type,
        model_confidence_threshold=args.model_confidence_threshold,
        model_device=args.device,
        slice_height=args.slice_height,
        slice_width=args.slice_width,
        overlap_height_ratio=args.overlap_height_ratio,
        overlap_width_ratio=args.overlap_width_ratio,
        project=args.project,
        name=args.name
    )

if __name__ == '__main__':
    segment()