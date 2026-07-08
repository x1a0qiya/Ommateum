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
    同时兼容推理模式和训练模式
    """
    def __init__(
        self, 
        image_dir: str, 
        label_dir: str, 
        processor: Sam2Processor, 
        mask_dir: str = '', 
        crop_mask_by_bbox: bool = True,
        dtype: torch.dtype = torch.float32
    ):
        """
        Args:
            image_dir: 图像文件夹路径
            label_dir: YOLO 检测结果文件夹路径
            processor: 载入的 SamProcessor, 用于检测等
            mask_dir: Mask 文件夹路径, 若为 None 则为推理模式
            crop_mask_by_bbox: 训练模式下，是否将 bbox 外部的 mask 区域置 0 (适用于多目标混杂的语义掩码)
            dtype: 传给 SAM 模型的张量类型
        """
        self.image_dir = image_dir
        self.label_dir = label_dir
        self.mask_dir = mask_dir
        self.processor = processor
        self.crop_mask_by_bbox = crop_mask_by_bbox
        self.dtype = dtype
        
        self.samples = [] # {"image_path": ..., "bbox": ..., "mask_path": ..., "image_name": ..., "class_id": ...}
        
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
                
            bboxes = self._parse_yolo_txt(txt_path, img_w, img_h)
            if len(bboxes) == 0:
                continue
                
            mask_path = None
            if self.mask_dir is not None:
                for ext in ['.png', '.jpg', '.jpeg']:
                    temp_path = os.path.join(self.mask_dir, f"{base_name}{ext}")
                    if os.path.exists(temp_path):
                        mask_path = temp_path
                        break
                if mask_path is None:
                    continue
            
            for bbox in bboxes:
                self.samples.append({
                    "image_path": img_path,
                    "bbox": bbox,
                    "mask_path": mask_path,
                    "image_name": img_name
                })
                
        print(f"Successfully load {len(image_filenames)} data, with {len(self.samples)} available data")

    def _parse_yolo_txt(self, txt_path : str, img_w : int, img_h : int) -> list:
        """
        解析 YOLO 格式坐标

        Args:
            txt_path (str) : YOLO 粗检结果路径
            img_w (int) : width
            img_h (int) : height

        Returns:
            返回 bbox
        """
        bboxes = []
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
                
                bboxes.append([x1, y1, x2, y2])
        return bboxes

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        sample = self.samples[idx]
        image_path = sample["image_path"]
        bbox = sample["bbox"]
        mask_path = sample["mask_path"]
        
        image = Image.open(image_path).convert('RGB')
        
        processed = self.processor(
            images=image,
            input_boxes=[[bbox]],
            return_tensors="pt"
        )
        
        for key in list(processed.keys()):
            if isinstance(processed[key], torch.Tensor):
                processed[key] = processed[key].squeeze(0)
                if processed[key].dtype in [torch.float32, torch.float64]:
                    processed[key] = processed[key].to(self.dtype)
                    
        if mask_path is not None:
            mask = Image.open(mask_path).convert('L')
            mask_np = np.array(mask)
            binary_mask = (mask_np > 127).astype(np.uint8)
            
            if self.crop_mask_by_bbox:
                h_img, w_img = binary_mask.shape
                x1, y1, x2, y2 = map(int, bbox)
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(w_img, x2), min(h_img, y2)
                
                refined_mask = np.zeros_like(binary_mask)
                refined_mask[y1:y2, x1:x2] = binary_mask[y1:y2, x1:x2]
                processed["ground_truth_mask"] = torch.tensor(refined_mask, dtype=torch.float32)
            else:
                processed["ground_truth_mask"] = torch.tensor(binary_mask, dtype=torch.float32)
                
        processed["image_path"] = image_path
        processed["image_name"] = sample["image_name"]
        processed["bbox"] = torch.tensor(bbox, dtype=torch.float32)
        
        return processed