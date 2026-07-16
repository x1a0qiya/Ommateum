from flask import Flask, request, jsonify, send_file, Response
from flask_cors import CORS
import os

import serves

app = Flask(__name__, static_folder='', static_url_path='')
CORS(app)

@app.route('/api', methods=['GET'])
def get_api():
    return jsonify(serves.get_api())

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify(serves.health_check())

@app.route('/api/models', methods=['GET'])
def get_models():
    return jsonify(serves.get_models())

@app.route('/api/weights', methods=['GET'])
def get_weights():
    model_id = request.args.get('model')
    return jsonify(serves.get_weights(model_id))

@app.route('/api/images', methods=['GET'])
def api_images():
    name = request.args.get('name')
    return jsonify(serves.get_images(name))

@app.route('/api/dataset', method=['GET'])
def get_dataset():
    return jsonify(serves.get_dataset())

@app.route('/api/stats', methods=['GET'])
def get_stats():
    return jsonify(serves.get_stats())

@app.route('/api/upload', methods=['POST'])
def upload_zip():
    images_zip = request.files.get('images_zip')
    annotation_json = request.files.get('annotation_json')
    masks_zip = request.files.get('masks_zip')
    return jsonify(serves.upload_zip(images_zip, annotation_json, masks_zip))

@app.route('/api/batches/<batch_id>', methods=['DELETE'])
def delete_batch(batch_id):
    return jsonify(serves.delete_batch(batch_id))

@app.route('/api/predict', methods=['POST'])
def predict():
    data = request.get_data(as_text=True) or None
    return jsonify(serves.predict(data))

@app.route("/api/task-stream/<task_id>", methods=['GET'])
def get_task_stream(task_id):
    return Response(serves.event_generator(task_id), mimetype="text/event-stream")

@app.route("/api/task/<task_id>", methods=['GET'])
def get_task_json(task_id):
    return jsonify(serves.get_task_status(task_id))

@app.route('/api/train', methods=['POST'])
def train():
    data = request.get_data(as_text=True) or None
    return jsonify(serves.train(data))

@app.route('/api/train/<task_id>', methods=['GET'])
def get_train_status(task_id):
    return jsonify(serves.get_train_status(task_id))

@app.route('/api/training-history', methods=['GET'])
def get_training_history():
    return jsonify(serves.get_training_history())

@app.route("/api/export/<task_id>", methods=["GET"])
def export_task(task_id):
    try:
        temp_zip_path = serves.pack_directory_to_temp_zip(task_id)
    except FileNotFoundError as e:
        return jsonify({
            'status': 'error',
            'timestamp': serves.get_datetime(),
            'error': repr(e)
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'timestamp': serves.get_datetime(),
            'error': repr(e)
        })


    def generate_and_cleanup():
        try:
            with open(temp_zip_path, 'rb') as f:
                while chunk := f.read(8192):
                    yield chunk
        finally:
            if os.path.exists(temp_zip_path):
                try:
                    os.remove(temp_zip_path)
                except Exception as e:
                    app.logger.error(f"Cannot delete {temp_zip_path}: {e}")


    return send_file(
        generate_and_cleanup(), #type: ignore
        mimetype="application/zip",
        as_attachment=True,
        download_name=f"task_{task_id}.zip"
    )

@app.route('/')
def index():
    # 因为指定了 static_folder，Flask 会在内部处理路径
    # 使用 send_file 直接发送该目录下的 index.html
    return send_file(os.path.join(app.static_folder, 'index.html')) #type: ignore


# ==================== 启动服务 ====================
if __name__ == '__main__':
    # 默认在 5000 端口启动
    app.run(host='0.0.0.0', port=5000, debug=True)