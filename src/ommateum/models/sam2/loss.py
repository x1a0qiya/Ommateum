import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, Tuple, Optional

class Sam2Loss(nn.Module):
    """
    SAM 2 组合损失函数 (Sam2Loss)
    它融合了:
    1. Sigmoid Focal Loss (像素级不平衡监督)
    2. Dice Loss (轮廓尺度不敏感监督，支持软标签)
    3. IoU Prediction Loss (L1/MSE 监督 IoU 预测头)
    """
    def __init__(
        self,
        weight_dict : Optional[Dict[str, float]] = None,
        focal_alpha : float = 0.25,
        focal_gamma : float = 2.0,
        iou_use_l1 : bool = True,
        multimask_mode : str = "best_only",  # "best_only" or "all"
        use_soft_label_dice : bool = False,
        eps : float = 1e-8
    ):
        super().__init__()

        if weight_dict is None:
            self.weight_dict = {
                "focal": 20.0,
                "dice": 1.0,
                "iou": 1.0
            }
        else:
            self.weight_dict = weight_dict
            
        self.focal_alpha = focal_alpha
        self.focal_gamma = focal_gamma
        self.iou_use_l1 = iou_use_l1
        
        assert multimask_mode in ['best_only', 'all'], "multimask_mode must in 'best_only' or 'all'"
        self.multimask_mode = multimask_mode
        self.use_soft_label_dice = use_soft_label_dice
        self.eps = eps

    def forward(
        self, 
        pred_masks: torch.Tensor, 
        pred_ious: torch.Tensor, 
        gt_masks: torch.Tensor
    ) -> Tuple[torch.Tensor, Dict[str, float]]:
        """
        Args:
            pred_masks (torch.Tensor) : 预测的掩码, 形状为 [B, M, H, W] (M=3 为多掩码, M=1 为单掩码)
            pred_ious (torch.Tensor) : 预测的 IoU 分数, 形状为 [B, M]
            gt_masks (torch.Tensor) : 真实二值掩码, 形状为 [B, 1, H, W] 或 [B, H, W]
            
        Returns:
            total_loss (torch.Tensor): 标量 Loss
            loss_dict (Dict[str, float]): 详细的 Loss 记录
        """
        pred_masks = pred_masks.float()
        pred_ious = pred_ious.float()
        gt_masks = gt_masks.float()
        
        if gt_masks.dim() == 3:
            gt_masks = gt_masks.unsqueeze(1) # [B, 1, H, W]
            
        B, M, H, W = pred_masks.shape
        
        actual_ious = self._compute_actual_iou(pred_masks, gt_masks) # [B, M]

        if self.multimask_mode == "best_only" and M > 1:
            best_idx = torch.argmax(actual_ious, dim=1)  # [B]
            
            selected_pred_masks = pred_masks[torch.arange(B, device=pred_masks.device), best_idx].unsqueeze(1) # [B, 1, H, W]
            selected_gt_masks = gt_masks # [B, 1, H, W]
            
            loss_focal = self._sigmoid_focal_loss(selected_pred_masks, selected_gt_masks)
            loss_dice = self._dice_loss(selected_pred_masks, selected_gt_masks)
        else:
            selected_gt_masks = gt_masks.expand(-1, M, -1, -1) # [B, M, H, W]
            
            loss_focal = self._sigmoid_focal_loss(pred_masks, selected_gt_masks)
            loss_dice = self._dice_loss(pred_masks, selected_gt_masks)

        if self.iou_use_l1:
            loss_iou = F.l1_loss(pred_ious, actual_ious, reduction="mean")
        else:
            loss_iou = F.mse_loss(pred_ious, actual_ious, reduction="mean")

        weighted_focal = self.weight_dict.get("focal", 1.0) * loss_focal
        weighted_dice = self.weight_dict.get("dice", 1.0) * loss_dice
        weighted_iou = self.weight_dict.get("iou", 1.0) * loss_iou
        
        total_loss = weighted_focal + weighted_dice + weighted_iou
        
        loss_dict = {
            "loss_total": total_loss.item(),
            "loss_focal": loss_focal.item(),
            "loss_dice": loss_dice.item(),
            "loss_iou": loss_iou.item(),
            "weighted_focal": weighted_focal.item(),
            "weighted_dice": weighted_dice.item(),
            "weighted_iou": weighted_iou.item()
        }
        
        return total_loss, loss_dict

    def _sigmoid_focal_loss(self, inputs: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        """
        稳定的 Sigmoid Focal Loss
        """
        prob = torch.sigmoid(inputs)
        ce_loss = F.binary_cross_entropy_with_logits(inputs, targets, reduction="none")
        p_t = prob * targets + (1 - prob) * (1 - targets)
        loss = ce_loss * ((1 - p_t) ** self.focal_gamma)
        
        if self.focal_alpha >= 0:
            alpha_t = self.focal_alpha * targets + (1 - self.focal_alpha) * (1 - targets)
            loss = alpha_t * loss
            
        return loss.mean()

    def _dice_loss(self, inputs: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        """
        Dice 损失函数
        """
        inputs_sig = torch.sigmoid(inputs)
        
       
        inputs_flat = inputs_sig.flatten(2) # [B, C, H*W]
        targets_flat = targets.flatten(2)   # [B, C, H*W]
        
        if self.use_soft_label_dice:
            # cardinality = |x|_1 + |y|_1
            # intersection = (cardinality - |x - y|_1) / 2
            cardinality = inputs_flat.sum(-1) + targets_flat.sum(-1)
            difference = torch.linalg.vector_norm(inputs_flat - targets_flat, ord=1, dim=-1)
            intersection = (cardinality - difference) / 2.0
        else:
            intersection = (inputs_flat * targets_flat).sum(-1)
            cardinality = inputs_flat.sum(-1) + targets_flat.sum(-1)
            
        dice = (2.0 * intersection + 1.0) / (cardinality + 1.0 + self.eps)
        loss = 1.0 - dice
        return loss.mean()

    def _compute_actual_iou(self, pred_masks: torch.Tensor, gt_masks: torch.Tensor) -> torch.Tensor:
        """
        计算 IoU
        pred_masks : [B, M, H, W], gt_masks : [B, 1, H, W]。
        """
        pred_bin = (pred_masks > 0.0).float()
        gt_bin = (gt_masks > 0.5).float()
        
        pred_flat = pred_bin.flatten(2)  # [B, M, H*W]
        gt_flat = gt_bin.flatten(2)      # [B, 1, H*W]
        
        intersection = (pred_flat * gt_flat).sum(dim=-1)  # [B, M]
        union = pred_flat.sum(dim=-1) + gt_flat.sum(dim=-1) - intersection  # [B, M]
        
        actual_iou = intersection / torch.clamp(union, min=1.0)
        
        pred_is_empty = (pred_flat.sum(dim=-1) == 0)
        gt_is_empty = (gt_flat.sum(dim=-1) == 0)  # [B, 1]
        both_empty = pred_is_empty & gt_is_empty  # [B, M]
        
        actual_iou = torch.where(both_empty, torch.ones_like(actual_iou), actual_iou)
        return actual_iou