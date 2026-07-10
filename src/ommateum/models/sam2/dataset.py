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
        mask_dir: str = None, # type: ignore 
        crop_mask_by_bbox: bool = True,
        dtype: torch.dtype = torch.float32
    ):
        """
        Args:
            image_dir: 图像文件夹路径
            label_dir: YOLO 检测结果文件夹路径
            processor: 载入的 SamProcessor / Sam2Processor, 用于前处理
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
                
            # 1. 提取图像对应的所有 bbox 实例及 class_id
            instances = self._parse_yolo_txt(txt_path, img_w, img_h)
            if len(instances) == 0:
                continue
                
            mask_path = None
            if self.mask_dir is not None:
                for ext in ['.png', '.jpg', '.jpeg']:
                    temp_path = os.path.join(self.mask_dir, f"{base_name}{ext}")
                    if os.path.exists(temp_path):
                        mask_path = temp_path
                        break
                if mask_path is None:
                    continue # 训练模式下，若存在标签文件但无对应掩码，则跳过
            
            if len(instances) > 0:
                self.samples.append({
                    "image_path": img_path,
                    "bboxes": [inst["bbox"] for inst in instances],  # 保存所有框的列表
                    "class_ids": [inst["class_id"] for inst in instances],
                    "mask_path": mask_path,
                    "image_name": img_name
                })
                
        print(f"成功加载数据集：总图片数 {len(image_filenames)}，可用于训练的缺陷实例数 {len(self.samples)}")

    def _parse_yolo_txt(self, txt_path: str, img_w: int, img_h: int) -> list:
        """
        解析 YOLO 格式坐标并保留类别

        Args:
            txt_path (str) : YOLO 检测结果路径
            img_w (int) : 宽度
            img_h (int) : 高度

        Returns:
            list: 包含 {"bbox": [x1, y1, x2, y2], "class_id": class_id} 的列表
        """
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
                
                # 边界约束保护
                x1 = max(0.0, min(x1, img_w))
                y1 = max(0.0, min(y1, img_h))
                x2 = max(0.0, min(x2, img_w))
                y2 = max(0.0, min(y2, img_h))
                
                # 安全过滤：忽略长或宽为 0 的异常边界框
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
        bboxes = sample["bboxes"]

        image = Image.open(image_path).convert('RGB')

        # 传入所有的 bboxes 列表
        processed = self.processor(
            images=image,
            input_boxes=[bboxes],  # 注意：这里外层多套一个列表，表示 batch 中的第一张图有多个框
            return_tensors="pt"
        )
        
        # 移除 processor 自动附加的单张图 Batch 维度 (将在 DataLoader 中被重新 Collate)
        for key in list(processed.keys()):
            if isinstance(processed[key], torch.Tensor):
                if processed[key].shape[0] == 1:
                    processed[key] = processed[key].squeeze(0)
                if processed[key].dtype in [torch.float32, torch.float64]:
                    processed[key] = processed[key].to(self.dtype)
                    
        if mask_path is not None:
            mask = Image.open(mask_path).convert('L')
            mask_np = np.array(mask)
            
            # 【修复 1】：自动兼容类别图（1, 2, 3, 4）和常规二值图（0 或 255）
            # 如果 mask 最大值 <= 10，说明这是之前脚本生成的包含缺陷类别类别的掩码。
            # 此时，我们只为 SAM 2 提取和当前 bbox 类别一致的像素，排除其他类别干扰。
            if mask_np.max() > 0 and mask_np.max() <= 10:
                # 对应关系：class_id_yolo = ClassId - 1。因此掩码值应为 class_id + 1
                target_pixel_val = class_id + 1
                binary_mask = (mask_np == target_pixel_val).astype(np.uint8)
            else:
                # 常规 0-255 二值灰度图处理方式
                binary_mask = (mask_np > 127).astype(np.uint8)
            
            # 裁剪框外部的 Mask 区域（将框外的缺陷遮罩置零，实现实例级抠图）
            if self.crop_mask_by_bbox:
                h_img, w_img = binary_mask.shape
                x1, y1, x2, y2 = map(int, bbox)
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(w_img, x2), min(h_img, y2)
                
                refined_mask = np.zeros_like(binary_mask)
                refined_mask[y1:y2, x1:x2] = binary_mask[y1:y2, x1:x2]
                
                # 【修复 3】：添加 Channel 通道维度，形状变为 [1, H, W]
                processed["ground_truth_mask"] = torch.tensor(refined_mask, dtype=torch.float32).unsqueeze(0)
            else:
                processed["ground_truth_mask"] = torch.tensor(binary_mask, dtype=torch.float32).unsqueeze(0)
                
        processed["image_path"] = image_path
        processed["image_name"] = sample["image_name"]
        processed["bbox"] = torch.tensor(bbox, dtype=torch.float32)
        processed["class_id"] = torch.tensor(class_id, dtype=torch.long) # 输出类别标签以备用
        
        return processed