from pathlib import Path
from sahi.predict import predict as sahi_predict

def predict(
    model_type: str,
    model_path: str,
    model_confidence_threshold: float,
    model_device: str,
    source: str,
    slice_height: int,
    slice_width: int,
    overlap_height_ratio: float,
    overlap_width_ratio: float,
    export_dir: str = "./runs/predict/exp"
) -> None:
    """
    使用 SAHI 进行切片推理

    Args:
        model_type: 模型类型标识（如 "yolov8", "mmdet" 等）
        model_path: 模型权重文件路径
        model_confidence_threshold: 置信度阈值，值越大准确率越高但召回率越低,导出结果仅保留置信度大于该值的数据
        model_device: 模型部署设备（如 "cpu", "cuda:0"）
        source: 图像文件夹路径
        slice_height: 切片高度（像素）
        slice_width: 切片宽度（像素）
        overlap_height_ratio: 高度方向重叠比例（0~1）
        overlap_width_ratio: 宽度方向重叠比例（0~1）
        export_dir: 结果导出目录，默认为 "./runs/predict/exp"

    Raises:
        FileNotFoundError: 模型权重或数据源路径不存在
        ValueError: 预测参数配置错误
        RuntimeError: 切片推理执行失败
    """
    model_path = Path(model_path)
    source = Path(source)

    if not model_path.exists():
        raise FileNotFoundError(f"模型权重文件未找到: {model_path}")
    if not source.exists():
        raise FileNotFoundError(f"图像数据源路径未找到: {source}")

    try:
        sahi_predict(
            model_type=model_type,
            model_path=str(model_path),
            model_device=model_device,
            model_confidence_threshold=model_confidence_threshold,
            source=str(source),
            slice_height=slice_height,
            slice_width=slice_width,
            overlap_height_ratio=overlap_height_ratio,
            overlap_width_ratio=overlap_width_ratio,
            export_dir=export_dir
        )
    except ValueError as e:
        raise ValueError(f"预测参数配置错误: {e}") from e
    except Exception as e:
        raise RuntimeError(f"批量切片推理执行失败: {e}") from e




