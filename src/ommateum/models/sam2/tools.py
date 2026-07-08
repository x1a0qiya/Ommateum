import torch
import torch.nn.functional as F

def collate_fn(batch, target_hw=(512, 512)):
    """
    自定义 Collate Function，用于动态对批次内的掩码进行大小插值
    """
    # 堆叠预处理后的核心字段 (通常由 Sam2Processor 转换完毕，尺寸本就一致)
    pixel_values = torch.stack([item["pixel_values"] for item in batch])
    
    res: dict = {
        "pixel_values": pixel_values,
    }
    
    # 兼容处理其他的可能出现的 tensor 键值
    if "original_sizes" in batch[0]:
        res["original_sizes"] = torch.stack([item["original_sizes"] for item in batch])
    if "reshaped_input_sizes" in batch[0]:
        res["reshaped_input_sizes"] = torch.stack([item["reshaped_input_sizes"] for item in batch])
    if "input_boxes" in batch[0]:
        res["input_boxes"] = torch.stack([item["input_boxes"] for item in batch])
        
    # 对尺寸不一的 ground_truth_mask 统一缩放
    if "ground_truth_mask" in batch[0]:
        ground_truth_masks = []
        for item in batch:
            gt_mask = item["ground_truth_mask"]  # 维度通常为 [H, W]
            if gt_mask.ndim == 2:
                gt_mask = gt_mask.unsqueeze(0)   # 增加通道维度 [1, H, W]
                
            # 扩展到双重 batch 维度 [1, 1, H, W] 以符合 F.interpolate 的要求
            gt_mask_unsqueezed = gt_mask.unsqueeze(0).float()
            
            # 使用 nearest (最近邻) 插值以防数值污染
            gt_mask_resized = F.interpolate(gt_mask_unsqueezed, size=target_hw, mode="nearest")
            
            # 还原形状至 [H, W] 或 [1, H, W] 并保存
            ground_truth_masks.append(gt_mask_resized.squeeze(0).squeeze(0))
            
        res["ground_truth_mask"] = torch.stack(ground_truth_masks)

    # 收集路径、名称等非 tensor 属性（PyTorch default_collate 对 string list 可以自动封装为 list）
    res["image_path"] = [item["image_path"] for item in batch]
    res["image_name"] = [item["image_name"] for item in batch]
    res["bbox"] = torch.stack([item["bbox"] for item in batch])
    
    return res