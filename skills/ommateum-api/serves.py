import os
import utils
from utils import get_datetime

WEIGHTS_DIR = '/Ommateum/weights'
DATASET_DIR = '/Ommateum/dataset'

def get_api() -> dict:
    ...

def health_check() -> dict:
    try:
        weights_num = utils.count_path_items(WEIGHTS_DIR)
        dataser_dir = os.path.join(DATASET_DIR, 'train', 'images')
        img_num = utils.count_path_items(dataser_dir)
        return {
            "status": "ok",
            "timestamp": get_datetime(),
            "data": {
                "service": "Ommateum API",
                "version": "1.0.0",
                "models": 1,
                "images": img_num,
                "trained_weights": weights_num,
                "rag_available": True
            }
        }
    except OSError as e:
        return {
            'status': 'error',
            'timestamp': get_datetime(),
            'error': repr(e)
        }

def get_models() -> dict:
    try:
        configs = utils.get_model_configs(WEIGHTS_DIR)
        return {
            'status': 'ok',
            'timestamp': get_datetime(),
            'data': configs
        }
    except OSError as e:
        return {
            'status': 'error',
            'timestamp': get_datetime(),
            'error': repr(e)
        }

def get_weights(model_id: str | None) -> dict:
    try:
        configs = utils.get_model_configs(WEIGHTS_DIR, model_id=model_id)
        configs['model_id'] = model_id
        return {
            'status': 'ok',
            'timestamp': get_datetime(),
            'data': configs
        }
    except OSError as e:
        return {
            'status': 'error',
            'timestamp': get_datetime(),
            'error': repr(e)
        }
    
def get_images(type: str | None) -> dict:
    try:
        dataset_dir = os.path.join(DATASET_DIR, 'train')
        imgs = utils.scan_images(dataset_dir, type)
        return {
            'status': 'ok',
            'timestamp': get_datetime(),
            'data': {
                'images': imgs,
                'total': len(imgs)
            }
        }
    except OSError as e:
        return {
            'status': 'error',
            'timestamp': get_datetime(),
            'error': repr(e)
        }
    
def upload_image(file, type: str | None) -> dict:
    try:
        filename = file.filename
        img_dir = os.path.join(DATASET_DIR, 'train')
        img_info = utils.handle_img_upload(
            file_stream=file,
            original_filename=filename,
            type=type,
            base_save_dir=img_dir
        )
        return {
            'status': 'ok',
            'timestamp': get_datetime(),
            'data':{
                'image': img_info
            }
        }
    except OSError as e:
        return {
            'status': 'error',
            'timestamp': get_datetime(),
            'error': repr(e)
        }
    
def delete_image(img_id: str) -> dict:
    ...

def predict() -> dict:
    ...

def get_task(task_id: str) -> dict:
    ...

def train() -> dict:
    ...

def get_train(task_id: str) -> dict:
    ...

def training_history() -> dict:
    ...

def export(task_id: str) -> dict:
    ...

def stats() -> dict:
    ...

def get_file(filename: str) -> dict:
    ...