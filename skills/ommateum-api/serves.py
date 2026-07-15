import os, uuid, json, threading, tempfile, shutil
import api_utils
from argparse import Namespace
from api_utils import get_datetime
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.ommateum.models.test import segment
from src.ommateum.models.train import train_model
from src.ommateum.models.identify.generate_data_yaml import coco2yolo

WEIGHTS_DIR = os.path.join(api_utils.get_root_dir(), 'weights')
DATASET_DIR = os.path.join(api_utils.get_root_dir(), 'dataset')
task_events = {} #{ task_id: { "event": threading.Event(), "status": "processing", "error": None, "task": "train" } }


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
                "trained_weights": weights_num
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
            'data': configs
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
        configs['model_id'] = model_id
        return {
            'status': 'ok',
            'timestamp': get_datetime(),
            'data': configs
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
            # annotation_json 是 FileStorage, 需先读取再解析 JSON
            json_content = json.loads(annotation_json.read())
            ann_info = api_utils.save_json_file(
                json_data=json_content,
                base_save_dir=dir,
                name='',
            )
            
            js['data']['annotation_file'] = {
                'name': 'coco_annotations.json',
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

def predict(data: str | None) -> dict:
    if data is None:
        return {
            'status': 'error',
            'timestamp': get_datetime(),
            'error': 'Json Error.'
        }
    try:
        data: dict = json.loads(data)
        batch_dir =  os.path.join(DATASET_DIR, data['batch_name'])
        images_dir = os.path.join(batch_dir, 'images')
        masks_dir = os.path.join(batch_dir, 'masks')
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
        )

        api_utils.update_namespace_from_dict(
            args_obj=custom_args,
            data_dict=data,
            keys_to_update=[
                'conf',
                'iou',
                'imgsz'
            ]
        )   

        task_id = str(uuid.uuid4())[:8]
        
        task_events[task_id] = {
            "event": threading.Event(),
            "status": "processing",
            "error": None,
            "task": "test",
            "batch_name": data.get('batch_name'),
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
            "status": event_info["status"],
            "error": event_info["error"]
        }
        yield f"data: {json.dumps(result)}\n\n"
    
    task_events.pop(task_id, None)

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
        json_name = os.path.join(batch_dir, 'coco_annotations.json')

        coco2yolo_args = Namespace(
            coco_json=json_name,
        )
        coco2yolo(coco2yolo_args)


        train_dir = os.path.join(batch_dir, 'train')
        masks_dir = os.path.join(batch_dir, 'masks')
        labels_dir = os.path.join(train_dir, 'labels')
        train_images_dir = os.path.join(train_dir, 'images')
        weights_dir = os.path.join(WEIGHTS_DIR, task_id)
        yolo_path = os.path.join(weights_dir, 'yolo')
        sam2_lora_dir = os.path.join(weights_dir, 'sam2')
        data_yaml_path = os.path.join(batch_dir, 'data.yaml')

        custom_args = Namespace(
            save_path=sam2_lora_dir,
            image_dir=train_images_dir,
            label_dir=labels_dir,
            mask_dir=masks_dir,
            data_yaml=data_yaml_path,
            weights_output_path=yolo_path,
            id=task_id,
            weights_dir=weights_dir
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
                'yolo_lr'
            ]
        )
        
        task_events[task_id] = {
            "event": threading.Event(),
            "status": "processing",
            "error": None,
            "task": "train",
            "batch_name": data.get('batch_name'),
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
    if not task_id in task_events:
        raise ValueError(f"Task id '{task_id}' is not exist.")

    source_dir = os.path.join(
        WEIGHTS_DIR if task_events[task_id]['task'] == 'train' else DATASET_DIR,
        task_id
    )
    if not os.path.exists(source_dir) or not os.path.isdir(source_dir):
        raise FileNotFoundError(f"Dir '{source_dir}' is not exist or is not a dir.")

    temp_dir = tempfile.gettempdir()
    temp_zip_base = os.path.join(temp_dir, f"export_temp_{os.urandom(8).hex()}")

    temp_zip_path = shutil.make_archive(
        base_name=temp_zip_base,
        format='zip',
        root_dir=source_dir
    )

    return temp_zip_path


# ── 统计数据 ──
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
                anno_path = os.path.join(exp_dir, 'annotations.json')
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
                    'model': 'yolo',
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


