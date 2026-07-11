import os
import numpy as np
import torch
from torch.utils.data import Dataset
from PIL import Image
from transformers import Sam2Processor

class YOLO2SAM2Dataset(Dataset):
    """
    适用于 YOLO 粗检测后的数据集
    可以将 YOLO 标准的 .txt 格式坐标自动解析, [class_id, x_center, y_center, width, height]
    自动将一张图内的多个检测框“平铺”为多个独立的训练样本
    同时兼容推理模式和训练模式
    """
    def __init__(
        self, 
        image_dir: str, 
        label_dir: str, 
        processor: Sam2Processor, 
        mask_dir: str = None, #type: ignore
        crop_mask_by_bbox: bool = True,
        dtype: torch.dtype = torch.float32
    ):
        self.image_dir = image_dir
        self.label_dir = label_dir
        self.mask_dir = mask_dir
        self.processor = processor
        self.crop_mask_by_bbox = crop_mask_by_bbox
        self.dtype = dtype
        
        # 保存平铺后的实例: {"image_path": ..., "bbox": ..., "class_id": ..., "mask_path": ..., "image_name": ...}
        self.samples = [] 
        
        image_filenames = sorted([
            f for f in os.listdir(image_dir) 
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff'))
        ])
        
        for img_name in image_filenames:
            base_name = os.path.splitext(img_name)[0]
            img_path = os.path.join(image_dir, img_name)
            txt_path = os.path.join(label_dir, f"{base_name}.txt")
            
            if not os.path.exists(txt_path):
                continue
                
            with Image.open(img_path) as img:
                img_w, img_h = img.size
                
            # 提取图像对应的所有 bbox 实例及 class_id
            instances = self._parse_yolo_txt(txt_path, img_w, img_h)
            if len(instances) == 0:
                continue
                
            # 寻找当前图像对应的 mask 路径
            img_mask_path = None
            if self.mask_dir is not None:
                for ext in ['.png', '.jpg', '.jpeg']:
                    temp_path = os.path.join(self.mask_dir, f"{base_name}{ext}")
                    if os.path.exists(temp_path):
                        img_mask_path = temp_path
                        break
                if img_mask_path is None:
                    continue  # 训练模式下，若存在标签文件但无对应掩码，则跳过
            
            # 将多框图片拆分为多个单框样本
            for inst in instances:
                self.samples.append({
                    "image_path": img_path,
                    "bbox": inst["bbox"],            # 保存单个框 [x1, y1, x2, y2]
                    "class_id": inst["class_id"],    # 保存单个类别 ID
                    "mask_path": img_mask_path,      # 保存当前图片对应的 mask 路径
                    "image_name": img_name
                })
                
        print(f"成功加载数据集：总图片数 {len(image_filenames)}，可用于训练的缺陷实例数 {len(self.samples)}")

    def _parse_yolo_txt(self, txt_path: str, img_w: int, img_h: int) -> list:
        instances = []
        with open(txt_path, 'r') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) < 5:
                    continue
                class_id = int(parts[0])
                x_c, y_c, w, h = map(float, parts[1:5])
                
                x1 = (x_c - w / 2) * img_w
                y1 = (y_c - h / 2) * img_h
                x2 = (x_c + w / 2) * img_w
                y2 = (y_c + h / 2) * img_h
                
                x1 = max(0.0, min(x1, img_w))
                y1 = max(0.0, min(y1, img_h))
                x2 = max(0.0, min(x2, img_w))
                y2 = max(0.0, min(y2, img_h))
                
                # 忽略长或宽为 0 的异常边界框
                if x2 > x1 and y2 > y1:
                    instances.append({
                        "bbox": [x1, y1, x2, y2],
                        "class_id": class_id
                    })
        return instances

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        sample = self.samples[idx]
        image_path = sample["image_path"]
        bbox = sample["bbox"]               # 平铺后的单框
        class_id = sample["class_id"]       # 对应单个类别
        mask_path = sample["mask_path"]     # 样本独有的 mask 路径
        image_name = sample["image_name"]

        image = Image.open(image_path).convert('RGB')

        # 传入单个 bbox. Sam2Processor -> [[[x1, y1, x2, y2]]]
        processed = self.processor(
            images=image,
            input_boxes=[[bbox]],  
            return_tensors="pt"
        )
        
        # 移除 processor 自动附加的单张图 Batch 维度
        for key in list(processed.keys()):
            if isinstance(processed[key], torch.Tensor):
                if processed[key].shape[0] == 1:
                    processed[key] = processed[key].squeeze(0)
                if processed[key].dtype in [torch.float32, torch.float64]:
                    processed[key] = processed[key].to(self.dtype)
                    
        if mask_path is not None:
            mask = Image.open(mask_path).convert('L')
            mask_np = np.array(mask)
            
            # 自动兼容类别图（1, 2, 3...）和常规二值图（0 或 255）
            if mask_np.max() > 0 and mask_np.max() <= 10:
                target_pixel_val = class_id + 1
                binary_mask = (mask_np == target_pixel_val).astype(np.uint8)
            else:
                # 常规 0-255 二值灰度图处理方式
                binary_mask = (mask_np > 127).astype(np.uint8)
            
            # 裁剪框外部的 Mask 区域
            if self.crop_mask_by_bbox:
                h_img, w_img = binary_mask.shape
                x1, y1, x2, y2 = map(int, bbox)
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(w_img, x2), min(h_img, y2)
                
                refined_mask = np.zeros_like(binary_mask)
                refined_mask[y1:y2, x1:x2] = binary_mask[y1:y2, x1:x2]
                
                # Channel 通道, [1, H, W]
                processed["ground_truth_mask"] = torch.tensor(refined_mask, dtype=torch.float32).unsqueeze(0)
            else:
                processed["ground_truth_mask"] = torch.tensor(binary_mask, dtype=torch.float32).unsqueeze(0)
                
        processed["image_path"] = image_path
        processed["image_name"] = image_name
        processed["bbox"] = torch.tensor(bbox, dtype=torch.float32)
        processed["class_id"] = torch.tensor(class_id, dtype=torch.long)
        
        return processed