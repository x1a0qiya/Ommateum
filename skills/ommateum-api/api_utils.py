import os, json, hashlib, uuid, tempfile, zipfile, shutil
from datetime import datetime, timezone
from pathlib import Path
from PIL import Image
from models import SaveableFileStream
from argparse import Namespace

ALLOWED_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.bmp', '.webp')

def get_root_dir() -> str:
    """
    返回根目录.
    """
    curr_path = Path(__file__).resolve()
    root = curr_path.parent.parent
    return str(root)

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

def get_img_data(path: str, name: str) -> dict:
    """
    返回指定图片的数据.

    Args:
        path (str): 图片路径.
        name (str): 批次名称.
    Returns:
        dict: 数据 json.
    """
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
        'batch_name': name,
        'size_kb': sz_kb,
        'url': f'/api/files/{file_name}',
        'width': w,
        'height': h,
        'uploaded_at': uploaded_at
    }

def scan_images(path: str, name: str) -> list:
    """
    扫描指定文件夹并返回图片数据列表.

    Args:
        path (str): 图片文件夹路径.
        name (str): 批次名称.
    Returns:
        list: 数据 json 列表.
    """
    imgs = []

    for file_name in os.listdir(path):
        if file_name.lower().endswith(ALLOWED_EXTENSIONS):
            full_path = os.path.join(path, file_name)
            meta = get_img_data(full_path, name)
            if meta:
                imgs.append(meta)
                    
    return imgs

def scan_images_max_size(path: str, name: str) -> tuple:
    """
    扫描指定文件夹并返回图片最大大小.

    Args:
        path (str): 图片文件夹路径.
        name (str): 批次名称.
    Returns:
        tuple: 图片最大大小.
    """
    mx = (0, 0)

    for file_name in os.listdir(path):
        if file_name.lower().endswith(ALLOWED_EXTENSIONS):
            full_path = os.path.join(path, file_name)
            meta = get_img_data(full_path, name)
            if meta:
                mx = max(mx, (meta['width'], meta['height']))
    return mx

def handle_zip_upload(
    file_stream: SaveableFileStream,
    original_filename: str,
    base_save_dir: str,
    name: str
) -> dict:
    """
    处理简单的 ZIP 上传, 仅解压并保存其内部文件, 返回基本批次信息.

    Args:
        file_stream (SaveableFileStream): 文件流.
        original_filename (str): 原始文件名.
        base_save_dir (str): 基础存储路径.
        name (str): 作为保存文件的子目录.
    Returns:
        dict: 返回保存成功的批次与基本文件信息.
    """
    _, zip_ext = os.path.splitext(original_filename.lower())
    if zip_ext != '.zip':
        raise ValueError("Unsupported file format. Only .zip files are allowed.")

    target_dir = os.path.join(base_save_dir, name)
    os.makedirs(target_dir, exist_ok=True)

    saved_files = []

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_zip_path = os.path.join(temp_dir, "uploaded.zip")
        file_stream.save(temp_zip_path)

        if not zipfile.is_zipfile(temp_zip_path):
            raise ValueError("The uploaded file is not a valid ZIP archive.")

        with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
            for file_info in zip_ref.infolist():
                if file_info.is_dir():
                    continue
                
                filename_lower = file_info.filename.lower()
                if '__macosx' in filename_lower or os.path.basename(filename_lower).startswith('.'):
                    continue

                base_name = os.path.basename(file_info.filename)
                save_path = os.path.join(target_dir, base_name)

                with open(save_path, 'wb') as f:
                    f.write(zip_ref.read(file_info.filename))
                
                saved_files.append(base_name)

    mtime = os.path.getmtime(target_dir)
    uploaded_at = datetime.fromtimestamp(mtime).isoformat() + 'Z'

    sz_kb = round(os.path.getsize(target_dir) / 1024, 1)

    return {
        "uploaded_at": uploaded_at,
        "saved_files_count": len(saved_files),
        "size_kb": sz_kb
    }

def save_json_file(
    json_data: dict,
    base_save_dir: str,
    name: str,
    filename: str = "annotation.json"
) -> dict:
    """
    保存传入的 dict 数据为 JSON 文件, 并返回批次及文件信息.

    Args:
        json_data (dict): 需要保存的字典/JSON 数据.
        base_save_dir (str): 基础存储路径.
        name (str): 批次名称, 作为子文件夹名称.
        filename (str): 保存的文件名, 默认为 "annotation.json"
        
    Returns:
        dict: 包含 batch_id、保存路径和上传时间等信息。
    """
    if not isinstance(json_data, dict):
        raise ValueError("json_data must be a dictionary.")

    target_dir = os.path.join(base_save_dir, name)
    os.makedirs(target_dir, exist_ok=True)

    save_path = os.path.join(target_dir, filename)

    with open(save_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=4)

    mtime = os.path.getmtime(target_dir)
    uploaded_at = datetime.fromtimestamp(mtime).isoformat() + 'Z'

    sz_kb = round(os.path.getsize(target_dir) / 1024, 1)

    return {
        "size_kb": sz_kb,
        "uploaded_at": uploaded_at
    }

def handle_batch_delete(base_path: str, name: str) -> None:
    """
    删除指定名称的批次文件夹及其内部的所有文件.

    Args:
        base_path (str): 基础存储路径.
        name (str): 批次文件夹名称.
    Returns:
        None:
    """
    target_dir = os.path.join(base_path, name)

    if os.path.exists(target_dir):
        if os.path.isdir(target_dir):
            shutil.rmtree(target_dir)
        else:
            os.remove(target_dir)
    else:
        raise FileNotFoundError(f"Batch folder '{name}' not found at {base_path}")
    
def update_namespace_from_dict(
        args_obj: Namespace,
        data_dict: dict | None,
        keys_to_update: list[str]
    ) -> None:
    """
    如果字典中存在指定的键, 则将其动态同步到 Namespace 对象的属性中.
    
    Args:
        args_obj (argparse.Namespace): 需要赋值的目标对象
        data_dict (dict): 包含新数值的字典
        keys_to_update: 需要检查并更新的键名列表
    """
    if data_dict is None:
        return
    for key in keys_to_update:
        if key in data_dict:
            setattr(args_obj, key, data_dict[key])
