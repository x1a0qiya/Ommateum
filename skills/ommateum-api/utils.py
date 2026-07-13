import os, json, hashlib, uuid
from datetime import datetime, timezone
from pathlib import Path
from PIL import Image
from models import SaveableFileStream

ALLOWED_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.bmp', '.webp')

def get_datetime() -> str:
    """
    返回当前时间戳, ISO 格式.

    Returns:
        str: ISO 格式字符串.
    Examples:
        "2026-07-11T01:23:45+00:00"
    """
    return datetime.now(timezone.utc).isoformat(timespec='seconds')

def count_path_items(path: str) -> int:
    """
    统计目标文件夹下直接存放在该目录的文件和文件夹总数.

    Args:
        path (str) : 目标文件夹地址.
    Returns:
        int : number.
    """
    dir = Path(path)
    items = list(dir.iterdir())
    return len(items)

def get_model_configs(path: str, *, name: str | None = None, model_id: str | None = None) -> dict:
    """
    返回指定名称/类型或所有的预训练模型的 config.

    Args:
        path (str) : 模型 config 路径.
        name (str) : 指定模型名称.
        model_id (str) : 指定模型 id.
    Returns:
        dict: config 字典.
    """
    if name is not None and model_id is not None:
        raise ValueError('name and model_id up to ones.')

    models_dir = Path(path)
    configs = {
        'data': {
            'models': []
        },
        'total': 0
    }
    total = 0

    if name is None:
        for json_file in models_dir.glob('*/config.json'):
            with open(json_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                if model_id is None or config['id'] == model_id:
                    configs['data']['models'].append(config)
                    total += 1
    else:
        with open(models_dir / name / 'config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
            configs['data']['models'].append(config)
            total = 1
    
    configs['total'] = total
    return configs

def get_img_data(path: str, type: str | None) -> dict:
    """
    返回指定图片的数据.

    Args:
        path (str): 图片路径.
        type (str | None): 图片类型.
    Returns:
        dict: 数据 json.
    """
    if type is not None or type is not 'normal' or type is not 'defect':
        raise ValueError('type is illegal.')
    
    sz_kb = round(os.path.getsize(path) / 1024, 1)

    with Image.open(path) as img:
        w, h = img.size

    file_name = os.path.basename(path)
    hash_obj = hashlib.sha256(file_name.encode('utf-8'))
    hash_id = hash_obj.hexdigest()

    mtime = os.path.getmtime(path)
    uploaded_at = datetime.fromtimestamp(mtime).isoformat()+'Z'

    return {
        'id': hash_id,
        'name': file_name,
        'type': type,
        'size_kb': sz_kb,
        'url': f'/api/files/{type}/{file_name}',
        'width': w,
        'height': h,
        'uploaded_at': uploaded_at
    }

def scan_images(path: str, type: str | None = None) -> list:
    """
    扫描指定文件夹并返回图片数据列表.

    Args:
        path (str): 图片文件夹路径.
        type (str | None): 图片类型.
    Returns:
        list: 数据 json 列表.
    """
    imgs = []

    floders = []
    if type == 'normal' or type is None:
        normal_path = os.path.join(path, 'normal', 'images')
        floders.append((normal_path, 'normal'))
    if type == 'defect' or type is None:
        defect_path = os.path.join(path, 'defect', 'images')
        floders.append((defect_path, 'defect'))

    for folder_path, t in floders:
        if not os.path.exists(folder_path):
            continue
        
        for file_name in os.listdir(folder_path):
            if file_name.lower().endswith(ALLOWED_EXTENSIONS):
                full_path = os.path.join(folder_path, file_name)
                meta = get_img_data(full_path, t)
                if meta:
                    imgs.append(meta)
                    
    return imgs

def handle_img_upload(
    file_stream: SaveableFileStream,
    original_filename: str,
    type: str | None,
    base_save_dir: str
) -> dict:
    """
    处理图片上传保存并解析的业务逻辑函数
    
    Args:
        file_stream (SaveableFileStream): 具有 .save() 行为的文件流对象（如 Flask 中的 FileStorage）.
        original_filename (str): 原始文件名.
        type (str): 'normal' 或 'defect'.
        base_save_dir (str): 存放 normal 和 defect 文件夹的根目录.
        
    Returns:
        dict: 包含解析后的图片元数据的字典。
    """
    if type not in ['normal', 'defect']:
        raise ValueError("Invalid type. Must be 'normal' or 'defect'")

    _, ext = os.path.splitext(original_filename.lower())
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported file format: {ext}. Only {ALLOWED_EXTENSIONS} are allowed.")

    target_dir: str = os.path.join(base_save_dir, type, 'images')
    os.makedirs(target_dir, exist_ok=True)

    unique_id: str = str(uuid.uuid4()).split('-')[0]  # 短 UUID (如 'a1b2c3d4')
    new_filename: str = f"img_{unique_id}{ext}"
    save_path: str = os.path.join(target_dir, new_filename)
    file_stream.save(save_path)

    with Image.open(save_path) as img:
        w, h = img.size

    size_kb: float = round(os.path.getsize(save_path) / 1024, 1)

    mtime = os.path.getmtime(save_path)
    uploaded_at = datetime.fromtimestamp(mtime).isoformat()+'Z'

    hash_obj = hashlib.sha256(new_filename.encode('utf-8'))
    hash_id = hash_obj.hexdigest()

    return {
        "id": hash_id,
        "name": new_filename,
        "type": type,
        "size_kb": size_kb,
        "url": f"/api/files/{type}/{new_filename}",
        "width": w,
        "height": h,
        "uploaded_at": uploaded_at
    }

def handle_img_delete(img_id: str) -> None:
    ...