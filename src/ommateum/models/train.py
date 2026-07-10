from identify.train import train_yolo_model
from sam2.train import train_sam2
import argparse
import torch

def parse_args():
    parser = argparse.ArgumentParser(description='Sam2 Training Script')

    parser.add_argument('--model_path', type=str, required=True, help='pretrained model params path')
    parser.add_argument('--save_path', type=str, default='weights/sam2', help='where to save the params')
    parser.add_argument('--image_dir', type=str, required=True, help='where is the image dir')
    parser.add_argument('--label_dir', type=str, required=True, help='where is the label dir')
    parser.add_argument('--mask_dir', type=str, required=True, help='where is the mask dir')
    parser.add_argument('--sam2_epochs', type=int, default=8, help='training epoch')
    parser.add_argument('--sam2_batch_size', type=int, default=8, help='training batch size')
    parser.add_argument('--lowvram', type=bool, default=False, help='whether to use low vram')
    parser.add_argument('--lora_rank', type=int, default=16, help='lora rank')
    parser.add_argument('--use_dora', type=bool, default=True, help='whether to use dora')
    parser.add_argument('--device', type=str, default='cuda' if torch.cuda.is_available() else 'cpu', help='device to train')
    parser.add_argument('--sam2_lr', type=float, default=2e-4, help='learning rate')
    parser.add_argument('--weight_decay', type=float, default=1e-2)

    parser.add_argument("--data_yaml", default="dataset/data.yaml", help="数据集配置 YAML")
    parser.add_argument("--yolo_epochs", type=int, default=50, help="训练轮数")
    parser.add_argument("--imgsz", type=int, default=640, help="输入图像尺寸")
    parser.add_argument("--yolo_batch_size", type=int, default=16, help="批大小")
    parser.add_argument("--workers", type=int, default=4, help="数据加载线程数")
    parser.add_argument("--yolo_cache_path", default="runs/train", help="输出根目录（图片、csv 等）")    
    parser.add_argument("--name", default="trained", help="实验子目录名")
    parser.add_argument("--patience", type=int, default=10, help="早停耐心值")
    parser.add_argument("--freeze", type=int, default=20,
                        help="冻结主干前 N 层，小样本推荐 20 (0=全量微调)")
    parser.add_argument("--pretrained", default="yolo11n.pt", help="预训练权重路径")
    parser.add_argument("--yolo_lr", type=float, default=0.001,
                        help="初始学习率（全量训练 0.01，微调 0.001 或更低）")
    parser.add_argument("--lrf", type=float, default=0.1,
                        help="最终学习率因子 (final_lr = lr0 * lrf)")
    parser.add_argument("--cos_lr", type=bool, default=True,
                        help="使用 cosine 学习率衰减")
    parser.add_argument("--full_train", action="store_true",
                        help="全量训练模式：不冻结 backbone，使用默认学习率")
    args = parser.parse_args()

    return parser.parse_args()

def main():
    args = parse_args()

    train_yolo_model(
        data_yaml=args.data_yaml,
        epochs=args.yolo_epochs,
        imgsz=args.imgsz,
        batch=args.yolo_batch_size,
        device=args.device,
        workers=args.workers,
        project=args.yolo_cache_path,
        name=args.name,
        patience=args.patience,
        freeze=args.freeze,
        pretrained=args.pretrained,
        lr0=args.yolo_lr,
        lrf=args.lrf,
        cos_lr=args.cos_lr,
    )

    train_sam2(
        model_path=args.model_path,
        save_path=args.save_path,
        image_dir=args.image_dir,
        label_dir=args.label_dir,
        mask_dir=args.mask_dir,
        epochs=args.sam2_epochs,
        batch_size=args.sam2_batch_size,
        lowvram=args.lowvram,
        lora_rank=args.lora_rank,
        use_dora=args.use_dora,
        device=args.device,
        lr=args.sam2_lr,
        weight_decay=args.weight_decay,
        name=args.name
    )

if __name__ == '__main__':
    main()