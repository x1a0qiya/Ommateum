from config import add_lora_config
from transformers import Sam2Processor
from torch.optim import AdamW
import torch
from tools import collate_fn
from loss import Sam2Loss
from tqdm import tqdm
from torch.utils.data import DataLoader
from dataset import YOLO2SAM2Dataset
import argparse

def train_sam2(
    model_path : str,
    save_path : str,
    image_dir : str,
    label_dir : str,
    mask_dir : str,
    epochs : int = 8,
    batch_size : int = 8,
    lowvram : bool = False,
    lora_rank : int = 16,
    use_dora : bool = True,
    device : str = 'cpu',
    lr : float = 2e-4,
    weight_decay : float = 1e-2,
) -> None:
    """
    微调模型

    Args:
        model_path (str) : SAM2 在本地或者 Hugging Face 中的地址
        save_path (str) : 参数保存路径
        image_dir (str) : 图像文件夹路径
        label_dir (str) : 标签文件夹路径
        mask_dir (str) : 掩码文件夹路径
        epochs (int) : 训练轮次
        batch_size (int) : 批大小
        lowvram (bool) : 是否启用低显存模式
        lora_rank (int) : LoRA 的秩
        use_dora (bool) : 是否使用 dora
        device (str) : 训练设备, 'cpu' or 'cuda'
        lr (float) : 学习率
        weight_decay (float) : 缩放率
    """
    model = add_lora_config(
        model_path,
        use_quant=lowvram,
        lora_rank=lora_rank,
        use_dora=use_dora,
        train_prompt=False,
    )
    model.to(device)

    processor = Sam2Processor.from_pretrained(model_path)

    trainable_params = [p for p in model.parameters() if p.requires_grad]
    optimizer = AdamW(trainable_params, lr=lr, weight_decay=weight_decay)

    criterion = Sam2Loss().to(device)

    train_dataset = YOLO2SAM2Dataset(image_dir, label_dir, processor, mask_dir)
    train_dataloder = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, collate_fn=collate_fn)

    model.train()
    for epoch in range(epochs):
        epoch_loss = 0.0
        progress_bar = tqdm(train_dataloder, desc=f'Epoch {epoch + 1}/{epochs}')

        for batch in progress_bar:
            optimizer.zero_grad()

            pixel_values = batch["pixel_values"].to(device)
            input_boxes = batch["input_boxes"].to(device)
            input_points = batch["input_points"].to(device) if "input_points" in batch else None
            input_labels = batch["input_labels"].to(device) if "input_labels" in batch else None
            gt_masks = batch["ground_truth_mask"].to(device)            

            outputs = model(
                pixel_values=pixel_values,
                input_boxes=input_boxes,
                input_labels=input_labels,
                input_points=input_points,
                multimask_output=False,
            )

            pred_mask = outputs.pred_masks.squeeze(2)

            pred_mask = torch.nn.functional.interpolate(
                pred_mask,
                size=gt_masks.shape[-2:],  # 动态获取 gt_masks 的高和宽
                mode="bilinear",
                align_corners=False,
            )
            
            pred_iou = outputs.iou_scores.squeeze(2)

            loss, loss_dict = criterion(pred_mask, pred_iou, gt_masks)
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item()
            progress_bar.set_postfix({
                'loss': f'{loss.item():.4f}',
                'f_loss': f'{loss_dict["loss_focal"]:.4f}',
                'd_loss': f'{loss_dict["loss_dice"]:.4f}',
                'i_loss': f'{loss_dict["loss_iou"]:.4f}'
            })

        print(f'Epoch {epoch + 1} finished with loss {epoch_loss:.4f}')

    model.save_pretrained(save_path)

def parse_args():
    parser = argparse.ArgumentParser(description='Sam2 Training Script')

    parser.add_argument('--model_path', type=str, required=True, help='pretrained model params path')
    parser.add_argument('--save_path', type=str, required=True, help='where to save the params')
    parser.add_argument('--image_dir', type=str, required=True, help='where is the image dir')
    parser.add_argument('--label_dir', type=str, required=True, help='where is the label dir')
    parser.add_argument('--mask_dir', type=str, required=True, help='where is the mask dir')
    parser.add_argument('--epochs', type=int, default=8, help='training epoch')
    parser.add_argument('--batch_size', type=int, default=8, help='training batch size')
    parser.add_argument('--lowvram', type=bool, default=False, help='whether to use low vram')
    parser.add_argument('--lora_rank', type=int, default=16, help='lora rank')
    parser.add_argument('--use_dora', type=bool, default=True, help='whether to use dora')
    parser.add_argument('--device', type=str, default='cuda' if torch.cuda.is_available() else 'cpu', help='device to train')
    parser.add_argument('--lr', type=float, default=2e-4, help='learning rate')
    parser.add_argument('--weight_decay', type=float, default=1e-2)

    return parser.parse_args()

if __name__ == '__main__':
    args = parse_args()

    train_sam2(
        model_path=args.model_path,
        save_path=args.save_path,
        image_dir=args.image_dir,
        label_dir=args.label_dir,
        mask_dir=args.mask_dir,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lowvram=args.lowvram,
        lora_rank=args.lora_rank,
        use_dora=args.use_dora,
        device=args.device,
        lr=args.lr,
        weight_decay=args.weight_decay
    )