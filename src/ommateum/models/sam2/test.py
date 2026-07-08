import os
import argparse
import numpy as np
import cv2
import torch
from PIL import Image
from transformers import Sam2Processor, Sam2Model
from peft import PeftModel

# 尝试加载 tqdm 显示进度条，若未安装则提供一个替代的 dummy 进度条
try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, **kwargs):
        return iterable

def parse_args():
    parser = argparse.ArgumentParser(description="SAM 2 Validation Pipeline (Calculating mIoU)")
    
    # 数据路径参数
    parser.add_argument('--image_dir', type=str, required=True, help='Path to the validation images directory')
    parser.add_argument('--mask_dir', type=str, required=True, help='Path to the ground truth masks directory')
    parser.add_argument('--label_path', type=str, required=True, 
                        help='Path to labels. Can be a directory of YOLO .txt files, or a single mapping .txt file.')
    
    # 模型参数
    parser.add_argument('--model_path', type=str, required=True, help='Path or HF repository name of the base SAM2 model')
    parser.add_argument('--lora_path', type=str, default=None, help='Path to the saved LoRA adapter directory')
    parser.add_argument('--no_lora', action='store_true', help='If set, run base model instead of LoRA')
    
    # 结果可视化保存（可选）
    parser.add_argument('--save_visualizations', action='store_true', help='If set, save overlay results to output_dir')
    parser.add_argument('--output_dir', type=str, default='eval_results', help='Directory to save visualization results')
    
    parser.add_argument('--device', type=str, default='cuda' if torch.cuda.is_available() else 'cpu', help='Device')

    return parser.parse_args()

def load_model_and_processor(model_path, lora_path, use_lora, device):
    print(f"正在加载 Processor: {model_path}")
    processor = Sam2Processor.from_pretrained(model_path)
    
    model = Sam2Model.from_pretrained(model_path)
        
    if use_lora and lora_path:
        if os.path.exists(lora_path):
            print(f"正在合并加载 LoRA 权重自: {lora_path}")
            model = PeftModel.from_pretrained(model, lora_path)
        else:
            print(f"警告: 未找到 LoRA 路径 '{lora_path}'，将降级运行 Base 模型。")
    else:
        print("提示: 已禁用 LoRA 权重，将运行 Base 模型。")
            
    model.to(device)
    model.eval()
    return processor, model

def parse_single_label_file(label_file_path):
    """
    解析单个 txt 文件，将文件名与其 box 坐标进行映射。
    支持格式：
    1. YOLO格式 (每行): image_name.jpg class_id x_center y_center width height (6个元素)
    2. 绝对坐标格式 (每行): image_name.jpg xmin ymin xmax ymax (5个元素)
    """
    label_dict = {}
    with open(label_file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) >= 5:
                # 键值使用文件名(无路径的前缀)
                img_key = os.path.basename(parts[0])
                try:
                    coords = [float(x) for x in parts[1:]]
                    label_dict[img_key] = coords
                except ValueError:
                    continue
    return label_dict

def main():
    args = parse_args()
    
    # 1. 加载模型
    use_lora = not args.no_lora
    processor, model = load_model_and_processor(
        model_path=args.model_path,
        lora_path=args.lora_path,
        use_lora=use_lora,
        device=args.device
    )
    
    # 2. 解析标注数据
    label_dict = {}
    is_label_dir = os.path.isdir(args.label_path)
    if not is_label_dir:
        label_dict = parse_single_label_file(args.label_path)
        print(f"成功读取单个 label 文件，共解析到 {len(label_dict)} 条标注记录。")
    
    # 3. 筛选所有图像
    supported_exts = {'.jpg', '.jpeg', '.png', '.bmp', '.webp', '.JPEG', '.JPG'}
    image_files = [os.path.join(args.image_dir, f) for f in os.listdir(args.image_dir) 
                   if os.path.splitext(f)[1].lower() in supported_exts]
    
    if not image_files:
        print(f"错误: 在目录 {args.image_dir} 中未找到合规格式的图像。")
        return
        
    print(f"在 val 文件夹中找到 {len(image_files)} 张待评估图像。")
    
    ious = []
    
    if args.save_visualizations:
        os.makedirs(args.output_dir, exist_ok=True)
        
    # 4. 循环批处理
    for img_path in tqdm(image_files, desc="Calculating mIoU"):
        img_name = os.path.basename(img_path)
        img_stem, _ = os.path.splitext(img_name)
        
        # 4.1 提取并解析对应 bounding box 坐标
        coords = None
        is_yolo = False
        
        if is_label_dir:
            # 如果是 YOLO 标注文件夹，寻找同名 txt
            label_file = os.path.join(args.label_path, f"{img_stem}.txt")
            if os.path.exists(label_file):
                with open(label_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                if lines:
                    parts = lines[0].strip().split() # 默认读取首个 box
                    try:
                        coords = [float(x) for x in parts]
                        # 文件夹中单个 txt 的 YOLO 格式通常为 5 个元素: class_id x_center y_center w h
                        if len(coords) == 5:
                            is_yolo = True
                        elif len(coords) == 4:
                            is_yolo = False
                        else:
                            coords = None
                    except ValueError:
                        pass
        else:
            # 从单个大 label 文件字典中匹配
            if img_name in label_dict:
                coords = label_dict[img_name]
            elif f"{img_stem}.txt" in label_dict:
                coords = label_dict[f"{img_stem}.txt"]
                
            if coords is not None:
                if len(coords) == 5:
                    is_yolo = True
                elif len(coords) == 4:
                    is_yolo = False
                else:
                    coords = None
                    
        if coords is None:
            # 未找到对应 Box 标签，跳过此图
            continue
            
        # 4.2 寻找对应的 Ground Truth Mask
        mask_file = None
        for ext in ['.png', '.jpg', '.jpeg', '.bmp']:
            possible_path = os.path.join(args.mask_dir, f"{img_stem}{ext}")
            if os.path.exists(possible_path):
                mask_file = possible_path
                break
                
        if mask_file is None:
            # 未找到对应的 mask，跳过此图
            continue
            
        # 4.3 读取图像与 Ground Truth Mask
        try:
            raw_image = Image.open(img_path).convert("RGB")
            img_w, img_h = raw_image.size
        except Exception as e:
            print(f"无法读取图片 {img_path}: {e}")
            continue
            
        gt_img = cv2.imread(mask_file, cv2.IMREAD_GRAYSCALE)
        if gt_img is None:
            continue
            
        # 兼容二值图在 0/255 和 0/1 的范围
        max_val = gt_img.max()
        if max_val == 0:
            gt_mask = gt_img > 0
        elif max_val == 1:
            gt_mask = gt_img == 1
        else:
            gt_mask = gt_img > (max_val / 2)
            
        # 4.4 坐标转换
        if is_yolo:
            class_id, x_center, y_center, norm_w, norm_h = coords
            xmin = max(0, min(img_w - 1, int((x_center - norm_w / 2.0) * img_w)))
            ymin = max(0, min(img_h - 1, int((y_center - norm_h / 2.0) * img_h)))
            xmax = max(0, min(img_w - 1, int((x_center + norm_w / 2.0) * img_w)))
            ymax = max(0, min(img_h - 1, int((y_center + norm_h / 2.0) * img_h)))
        else:
            xmin, ymin, xmax, ymax = map(int, coords)
            xmin = max(0, min(img_w - 1, xmin))
            ymin = max(0, min(img_h - 1, ymin))
            xmax = max(0, min(img_w - 1, xmax))
            ymax = max(0, min(img_h - 1, ymax))
            
        box_coords = [xmin, ymin, xmax, ymax]
        
        # 4.5 SAM 2 预测
        bb = list(map(float, box_coords))
        input_boxes = [[bb]]
        inputs = processor(
            images=raw_image, 
            input_boxes=input_boxes, 
            return_tensors="pt"
        ).to(args.device)
        
        with torch.no_grad():
            outputs = model(**inputs, multimask_output=False)
            
        # 后处理并与原图尺寸进行对齐
        masks = processor.image_processor.post_process_masks(
            outputs.pred_masks.cpu(), 
            inputs["original_sizes"].cpu()
        )
        binary_mask = masks[0][0][0].numpy()
        
        # 转换并确保预测掩码与 Ground Truth 掩码的分辨率完全匹配
        binary_mask_uint8 = (binary_mask > 0.5).astype(np.uint8)
        if binary_mask_uint8.shape != gt_mask.shape:
            binary_mask_uint8 = cv2.resize(
                binary_mask_uint8, 
                (gt_mask.shape[1], gt_mask.shape[0]), 
                interpolation=cv2.INTER_NEAREST
            )
            
        pred_mask = binary_mask_uint8 > 0.5
        
        # 4.6 计算 IoU
        intersection = np.logical_and(pred_mask, gt_mask).sum()
        union = np.logical_or(pred_mask, gt_mask).sum()
        
        if union == 0:
            iou = 1.0  # 如果两张掩码均为空白，IoU 为 1.0
        else:
            iou = intersection / union
            
        ious.append(iou)
        
        # 4.7 可视化部分（可选，在参数里指定 --save_visualizations 才会激活）
        if args.save_visualizations:
            img_cv = cv2.imread(img_path)
            if img_cv is not None:
                # 若需要，将 cv2 读取的原图 resize 到 gt_mask 匹配的大小
                if (img_cv.shape[0], img_cv.shape[1]) != pred_mask.shape:
                    img_cv = cv2.resize(img_cv, (gt_mask.shape[1], gt_mask.shape[0]))
                    
                overlay = img_cv.copy()
                mask_color = [0, 255, 0]  # SAM 2 预测结果 (绿色)
                gt_color = [255, 0, 0]    # Ground Truth 实际掩码 (蓝色)
                opacity = 0.4
                
                # 绘制覆盖物
                overlay[pred_mask] = (img_cv[pred_mask] * (1.0 - opacity) + np.array(mask_color) * opacity).astype(np.uint8)
                overlay[gt_mask] = (overlay[gt_mask] * (1.0 - opacity) + np.array(gt_color) * opacity).astype(np.uint8)
                
                # 重新计算坐标缩放比率以准确绘制矩形框
                scale_x = gt_mask.shape[1] / img_w
                scale_y = gt_mask.shape[0] / img_h
                cv2.rectangle(
                    overlay, 
                    (int(xmin * scale_x), int(ymin * scale_y)), 
                    (int(xmax * scale_x), int(ymax * scale_y)), 
                    (0, 0, 255), 
                    2
                )
                
                cv2.imwrite(os.path.join(args.output_dir, f"res_{img_name}"), overlay)

    # 5. 计算并输出最终的 mIoU
    if ious:
        miou = np.mean(ious)
        print("\n" + "=" * 40)
        print("【 评估流程结束 】")
        print(f"成功运行并匹配的图像总数: {len(ious)}")
        print(f"全局平均 mIoU: {miou:.6f}")
        print("=" * 40)
    else:
        print("\n[错误]: 未找到任何能匹配到标签和 Ground Truth 的图片，评估未启动。")

if __name__ == "__main__":
    main()