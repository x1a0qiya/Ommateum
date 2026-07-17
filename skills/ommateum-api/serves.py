import os, uuid, json, threading, tempfile, shutil
import api_utils
from argparse import Namespace
from api_utils import get_datetime
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from ultralytics import YOLO
from src.ommateum.models.test import segment
from src.ommateum.models.train import train_model
from src.ommateum.utils.augment_dataset import sdg
from src.ommateum.utils.coco2yolo import coco2yolo
from src.ommateum.utils.generate_data_yaml import generate_data_yaml

WEIGHTS_DIR = os.path.join(api_utils.get_root_dir(), 'weights')
DATASET_DIR = os.path.join(api_utils.get_root_dir(), 'dataset')
task_events : dict = {} #{ task_id: { "event": threading.Event(), "status": "processing", "error": None, "task": "train" } }


# ═══════════════════════════════════════════════════════════════
#  启动预检：确保预训练权重存在
# ═══════════════════════════════════════════════════════════════

def ensure_pretrained():
    """启动时检测 pretrained/ 目录，不存在则下载预训练模型并生成 config.json。"""
    pretrained_dir = os.path.join(WEIGHTS_DIR, 'pretrained')
    config_path = os.path.join(pretrained_dir, 'config.json')

    if os.path.isfile(config_path):
       
        return

    
    os.makedirs(pretrained_dir, exist_ok=True)

    # ── YOLO 预训练权重 ──
    yolo_dir = os.path.join(pretrained_dir, 'yolo')
    os.makedirs(yolo_dir, exist_ok=True)
    w='yolo11n.pt'
    dst = os.path.join(yolo_dir, w)
    if not os.path.isfile(dst):
        model = YOLO(w)  # ultralytics 自动下载到缓存
        src = str(Path(model.ckpt_path) if hasattr(model, 'ckpt_path') and model.ckpt_path
                    else os.path.join(os.path.expanduser('~'), '.cache', 'ultralytics', w))
        if os.path.isfile(src) and src != dst:
            shutil.copy2(src, dst)
            

    # ── 写入 config.json ──
    config = {
        "id": "pretrained",
    }
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    print(f"[启动] config.json 已创建: {config_path}")

def get_api() -> dict:
    ...

def health_check() -> dict:
    try:
        weights_num = api_utils.count_path_items(WEIGHTS_DIR)
        img_num = api_utils.count_path_items(DATASET_DIR)
        return {
            "status": "ok",
            "timestamp": get_datetime(),
            "data": {
                "service": "Ommateum API",
                "version": "1.0.0",
                "models": 1,
                "images": img_num,
                "trained_weights": weights_num,
                "rag_available": True,
            }
        }
    except Exception as e:
        return {
            'status': 'error',
            'timestamp': get_datetime(),
            'error': repr(e)
        }

def get_models() -> dict:
    try:
        configs = api_utils.get_model_configs(WEIGHTS_DIR)
        return {
            'status': 'ok',
            'timestamp': get_datetime(),
            'data': configs['data']
        }
    except Exception as e:
        return {
            'status': 'error',
            'timestamp': get_datetime(),
            'error': repr(e)
        }

def get_weights(model_id: str | None) -> dict:
    try:
        configs = api_utils.get_model_configs(WEIGHTS_DIR, model_id=model_id)
        return {
            'status': 'ok',
            'timestamp': get_datetime(),
            'data': {
                'models': configs['data']['models'],
                'model_id': model_id
            }
        }
    except Exception as e:
        return {
            'status': 'error',
            'timestamp': get_datetime(),
            'error': repr(e)
        }
    
def get_images(name: str | None) -> dict:
    if name is None:
        return {
            'status': 'error',
            'timestamp': get_datetime(),
            'error': "'Name' must be unempty."
        }
    try:
        dataset_dir = os.path.join(DATASET_DIR, name, 'images')
        imgs = api_utils.scan_images(dataset_dir, name)
        return {
            'status': 'ok',
            'timestamp': get_datetime(),
            'data': {
                'images': imgs,
                'total': len(imgs)
            }
        }
    except Exception as e:
        return {
            'status': 'error',
            'timestamp': get_datetime(),
            'error': repr(e)
        }

def get_dataset() -> dict:
    try:
        info = api_utils.get_all_dataset(DATASET_DIR)
        return {
            'status': 'ok',
            'timestamp': get_datetime(),
            'data': info
        }
    except Exception as e:
        return {
            'status': 'error',
            'timestamp': get_datetime(),
            'error': repr(e)
        }
    
def upload_zip(images_zip, annotation_json, masks_zip) -> dict:
    try:
        if images_zip is None or not images_zip.filename:
            return {
                'status': 'error',
                'timestamp': get_datetime(),
                'error': 'images_zip is required and must not be empty.'
            }

        js = {
            'status': 'ok',
            'timestamp': get_datetime(),
            'data': {

            }
        }

        id = str(uuid.uuid4()).replace('-', '')
        dir = os.path.join(DATASET_DIR, id)
        img_name = images_zip.filename
        img_info = api_utils.handle_zip_upload(
            file_stream=images_zip,
            original_filename=img_name,
            base_save_dir=dir,
            name='images'
        )

        js['data']['batch_id'] = id
        js['data']['uploaded_at'] = img_info['uploaded_at']
        js['data']['images_file'] = {
            'name': img_name,
            'size_kb': img_info['size_kb'],
            'image_count': img_info['saved_files_count']
        }

        if annotation_json is not None and annotation_json.filename:
            json_content = json.loads(annotation_json.read())
            ann_info = api_utils.save_json_file(
                json_data=json_content,
                base_save_dir=dir,
                name='',
            )
            
            js['data']['annotation_file'] = {
                'name': 'annotation.json',
                'size_kb': ann_info['size_kb'] 
            }

        if masks_zip is not None and masks_zip.filename:
            msk_name = masks_zip.filename
            msk_info = api_utils.handle_zip_upload(
                file_stream=masks_zip,
                original_filename=msk_name,
                base_save_dir=dir,
                name='masks'
            )

            js['data']['masks_file'] = {
                'name': msk_name,
                'size_kb': msk_info['size_kb'],
                'mask_count': msk_info['saved_files_count']
            }

        return js
    except Exception as e:
        return {
            'status': 'error',
            'timestamp': get_datetime(),
            'error': repr(e)
        }
    
def delete_batch(name: str) -> dict:
    try:
        api_utils.handle_batch_delete(DATASET_DIR, name)
        return {
            'status': 'ok',
            'timestamp': get_datetime(),
            'data': {
                'id': name
            }
        }
    except Exception as e:
        return {
            'status': 'error',
            'timestamp': get_datetime(),
            'error': repr(e)
        }

def _run_segment_async(task_id, custom_args):
    try:
        segment(custom_args)
        
        task_events[task_id]["status"] = "completed"
    except Exception as e:
        task_events[task_id]["status"] = "failed"
        task_events[task_id]["error"] = repr(e)
    finally:
        task_events[task_id]["event"].set()

def predict(data: str | None, file = None) -> dict:
    if data is None:
        return {
            'status': 'error',
            'timestamp': get_datetime(),
            'error': 'Json Error.'
        }
    try:
        data: dict = json.loads(data)
        if file is None or file == '':
            batch_dir =  os.path.join(DATASET_DIR, data['batch_name'])
            images_dir = os.path.join(batch_dir, 'images')
            masks_dir = os.path.join(batch_dir, 'masks')
            saved_path = None
        else:
            batch_dir = os.path.join(DATASET_DIR, 'temp')
            info = api_utils.save_image_file(
                file_stream=file,
                original_filename='temp',
                base_save_dir=batch_dir,
                name='images'
            )
            images_dir = os.path.join(batch_dir, 'images')
            masks_dir = os.path.join(batch_dir, 'masks')
            saved_path = info['saved_path']

        weights_dir = os.path.join(WEIGHTS_DIR, data['weight'])
        yolo_path = os.path.join(weights_dir, 'yolo', data['weight']+'_best.pt')
        sam2_lora_dir = os.path.join(weights_dir, 'sam2')
        mx_sz = max(api_utils.scan_images_max_size(images_dir, ''))
        
        custom_args = Namespace(
            images_dir=images_dir,
            yolo_model_path=yolo_path,
            imgsz=mx_sz,
            lora_path=sam2_lora_dir,
            output_mask_path=masks_dir,
            project=batch_dir,
            # 以下为 segment() 需要的其余参数默认值
            yolo_output_dir=os.path.join(batch_dir, 'labels'),
            conf=0.25,
            iou=0.7,
            device='cpu',
            sam2_model_path='facebook/sam2-hiera-tiny',
            model_type='ultralytics',
            model_confidence_threshold=0.5,
            slice_height=256,
            slice_width=256,
            overlap_height_ratio=0.2,
            overlap_width_ratio=0.2,
            name='exp'
        )

        api_utils.update_namespace_from_dict(
            args_obj=custom_args,
            data_dict=data,
            keys_to_update=[
                'conf',
                'iou',
                'imgsz',
                'device',
                'yolo_output_dir',
                'sam2_model_path',
                'model_type',
                'model_confidence_threshold',
                'slice_height',
                'slice_width',
                'overlap_height_ratio',
                'overlap_width_ratio',
            ]
        )   

        task_id = str(uuid.uuid4())[:8]
        
        task_events[task_id] = {
            "event": threading.Event(),
            "status": "processing",
            "error": None,
            "task": "test",
            "batch_name": data['batch_name']
        }
        
        thread = threading.Thread(
            target=_run_segment_async,
            args=(task_id, custom_args),
            daemon=True
        )
        thread.start()

        return {
            'status': 'ok',
            'timestamp': get_datetime(),
            'data': {
                'task_id': task_id,
                'image_path': saved_path
            }
        }
    except Exception as e:
        return {
            'status': 'error',
            'timestamp': get_datetime(),
            'error': repr(e)
        }
    
def event_generator(task_id: str):
    if task_id not in task_events:
        yield f"data: {json.dumps({'status': 'error', 'timestamp': get_datetime(), 'error': 'No task id'})}\n\n"
        return
        
    event_info = task_events[task_id]
    yield f"data: {json.dumps({'status': 'ok', 'timestamp': get_datetime(), 'message': 'Progressing...'})}\n\n"
    
    finished = event_info["event"].wait(timeout=3600)
    
    if not finished:
        yield f"data: {json.dumps({'status': 'error', 'timestamp': get_datetime(), 'error': 'Time out.'})}\n\n"
    else:
        result = {
            "task_id": task_id,
            "status": event_info["status"],
            "error": event_info["error"]
        }
        yield f"data: {json.dumps(result)}\n\n"
def _run_train_async(task_id, custom_args):
    try:
        train_model(custom_args)
        
        task_events[task_id]["status"] = "completed"
    except Exception as e:
        task_events[task_id]["status"] = "failed"
        task_events[task_id]["error"] = repr(e)
    finally:
        task_events[task_id]["event"].set()

def train(data: str | None) -> dict:
    if data is None:
        return {
            'status': 'error',
            'timestamp': get_datetime(),
            'error': 'Json Error.'
        }
    try:
        data: dict = json.loads(data)
        params = data['params'] if 'params' in data else None

        task_id = str(uuid.uuid4())[:8]

        batch_dir = os.path.join(DATASET_DIR, data['batch_name'])
        images_dir = os.path.join(batch_dir, 'images')
        json_name = os.path.join(batch_dir, 'annotation.json')
        if not os.path.exists(json_name):
            return {
                'status': 'error',
                'timestamp': get_datetime(),
                'error': "The dataset don't have any annotation file"
            }

        data_yaml_path = os.path.join(batch_dir, 'data.yaml')

        count = api_utils.count_path_items(batch_dir)
        if count > 1 and count < 4:
            coco2yolo(json_name)

            if 'use_SDG' in data:
                sdg_args = Namespace(
                    images=images_dir,
                    labels=None,
                    masks=None,
                    output=None,
                    num_aug=3
                )

                api_utils.update_namespace_from_dict(
                    args_obj=sdg_args,
                    data_dict=params,
                    keys_to_update=[
                        'num_aug'
                    ]
                )                

                sdg(sdg_args)

            generate_data_yaml(
                images=images_dir,
                output=data_yaml_path
            )

        train_dir = os.path.join(batch_dir, 'train')
        masks_dir = os.path.join(train_dir, 'masks')
        labels_dir = os.path.join(train_dir, 'labels')
        train_images_dir = os.path.join(train_dir, 'images')
        weights_dir = os.path.join(WEIGHTS_DIR, task_id)
        yolo_path = os.path.join(weights_dir, 'yolo')
        sam2_lora_dir = os.path.join(weights_dir, 'sam2')

        custom_args = Namespace(
            save_path=sam2_lora_dir,
            image_dir=train_images_dir,
            label_dir=labels_dir,
            mask_dir=masks_dir,
            data_yaml=data_yaml_path,
            weights_output_path=yolo_path,
            id=task_id,
            name=task_id,
            weights_dir=weights_dir,
            device='cuda' if __import__('torch').cuda.is_available() else 'cpu',
        )

        api_utils.update_namespace_from_dict(
            args_obj=custom_args,
            data_dict=params,
            keys_to_update=[
                'model_path',
                'sam2_epochs',
                'sam2_batch_size',
                'lora_rank',
                'sam2_lr',
                'weight_decay',
                'yolo_epochs',
                'imgsz',
                'yolo_batch_size',
                'patience',
                'freeze',
                'pretrained',
                'yolo_lr',
                'workers',
                'lrf',
                'cos_lr',
                'full_train',
                'use_dora'
            ]
        )
        
        task_events[task_id] = {
            "event": threading.Event(),
            "status": "processing",
            "error": None,
            "task": "train",
            "weight_id": task_id
        }
        
        thread = threading.Thread(
            target=_run_train_async,
            args=(task_id, custom_args),
            daemon=True
        )
        thread.start()

        return {
            'status': 'ok',
            'timestamp': get_datetime(),
            'data': {
                'task_id': task_id,
            }
        }
    except Exception as e:
        return {
            'status': 'error',
            'timestamp': get_datetime(),
            'error': repr(e)
        }
    
def pack_directory_to_temp_zip(task_id: str) -> str:
    # 优先尝试 WEIGHTS_DIR，若不存在则尝试 DATASET_DIR
    info = task_events[task_id]
    if info['task'] == 'train':
        source_dir = os.path.join(WEIGHTS_DIR, info['weight_id'])
    else:
        source_dir = os.path.join(DATASET_DIR, info['batch_name'])

    temp_dir = tempfile.gettempdir()
    temp_zip_base = os.path.join(temp_dir, f"export_temp_{os.urandom(8).hex()}")

    temp_zip_path = shutil.make_archive(
        base_name=temp_zip_base,
        format='zip',
        root_dir=source_dir
    )

    return temp_zip_path


def get_stats() -> dict:
    try:
        weights_num = api_utils.count_path_items(WEIGHTS_DIR)
        batch_names = [d for d in os.listdir(DATASET_DIR)
                       if os.path.isdir(os.path.join(DATASET_DIR, d))]
        recent_accuracy = 0.0
        return {
            'status': 'ok',
            'timestamp': get_datetime(),
            'data': {
                'recent_accuracy': recent_accuracy,
                'trained_weights': weights_num,
                'total_batches': len(batch_names),
            }
        }
    except Exception as e:
        return {
            'status': 'error',
            'timestamp': get_datetime(),
            'error': repr(e)
        }


# ── 任务状态（JSON 版，供前端 API.task() 调用）──
def get_task_status(task_id: str) -> dict:
    try:
        if task_id not in task_events:
            return {
                'status': 'error',
                'timestamp': get_datetime(),
                'error': f'Task {task_id} not found.'
            }

        info = task_events[task_id]
        status = info["status"]
        error = info.get("error")
        task_type = info.get("task", "test")

        result = {
            'status': 'ok',
            'timestamp': get_datetime(),
            'data': {
                'task_id': task_id,
                'status': status,
                'task_type': task_type,
                'error': error,
                'results': [],
            }
        }

        # 对于已完成的检测任务，尝试从批次目录读取检测结果
        if status == 'completed' and task_type == 'test':
            # 从 task_events 中找 batch_name（存储在 predict 创建的事件中）
            batch_name = info.get('batch_name')
            if batch_name:
                exp_dir = os.path.join(DATASET_DIR, batch_name, 'exp')
                anno_path = os.path.join(exp_dir, 'annotation.json')
                if os.path.exists(anno_path):
                    with open(anno_path, 'r', encoding='utf-8') as f:
                        coco_data = json.load(f)
                    # 转换为前端期望的 results 格式
                    results = []
                    for ann in coco_data.get('annotations', []):
                        img_info = next(
                            (img for img in coco_data.get('images', [])
                             if img['id'] == ann['image_id']),
                            None
                        )
                        results.append({
                            'image_name': img_info['file_name'] if img_info else f'img_{ann["image_id"]}',
                            'verdict': 'defect' if ann.get('score', 0) > 0.3 else 'normal',
                            'confidence': ann.get('score', 0),
                            'defect_type': ann.get('category_id', 'unknown'),
                            'bbox': ann.get('bbox', []),
                        })
                    result['data']['results'] = results

        return result
    except Exception as e:
        return {
            'status': 'error',
            'timestamp': get_datetime(),
            'error': repr(e)
        }


# ── 训练状态（JSON 版）──
def get_train_status(task_id: str) -> dict:
    try:
        if task_id not in task_events:
            return {
                'status': 'error',
                'timestamp': get_datetime(),
                'error': f'Training task {task_id} not found.'
            }

        info = task_events[task_id]
        return {
            'status': 'ok',
            'timestamp': get_datetime(),
            'data': {
                'task_id': task_id,
                'status': 'done' if info['status'] == 'completed' else info['status'],
                'progress': 1.0 if info['status'] == 'completed' else 0.0,
                'current_epoch': 0,
                'stage': 'completed' if info['status'] == 'completed' else info['status'],
                'loss': None,
                'val_loss': None,
                'accuracy': 1.0 if info['status'] == 'completed' else 0.0,
                'final_accuracy': 1.0 if info['status'] == 'completed' else 0.0,
                'error': info.get('error'),
            }
        }
    except Exception as e:
        return {
            'status': 'error',
            'timestamp': get_datetime(),
            'error': repr(e)
        }


# ── 训练历史 ──
def get_training_history() -> dict:
    try:
        tasks = []
        for tid, info in task_events.items():
            if info.get('task') == 'train':
                tasks.append({
                    'id': tid,
                    'status': 'done' if info['status'] == 'completed' else info['status'],
                    'accuracy': 1.0 if info['status'] == 'completed' else 0.0,
                    'epochs': 0,
                    'normal_count': 0,
                    'defect_count': 0,
                    'model': tid,
                    'weight_id': tid,
                    'timestamp': get_datetime(),
                })
        return {
            'status': 'ok',
            'timestamp': get_datetime(),
            'data': {
                'tasks': tasks,
            }
        }
    except Exception as e:
        return {
            'status': 'error',
            'timestamp': get_datetime(),
            'error': repr(e)
        }