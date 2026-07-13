from flask import Flask, request, jsonify
from flask_cors import CORS

import serves

app = Flask(__name__)
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
    image_type = request.args.get('type')
    return jsonify(serves.get_images(image_type))

@app.route('/api/images', methods=['POST'])
def upload_image():
    file = request.files['file']
    type = request.form.get('type')
    return jsonify(serves.upload_image(file, type))


# 7. DELETE /api/images/{img_id} - 删除图片
@app.route('/api/images/<img_id>', methods=['DELETE'])
def delete_image(img_id):
    return jsonify(serves.delete_image(img_id))


# 8. POST /api/predict - 执行缺陷检测
@app.route('/api/predict', methods=['POST'])
def predict():
    return jsonify(serves.predict())


# 9. GET /api/tasks/{task_id} - 查询检测任务结果
@app.route('/api/tasks/<task_id>', methods=['GET'])
def get_task(task_id):
    return jsonify(serves.get_task(task_id))


# 10. POST /api/train - 启动训练
@app.route('/api/train', methods=['POST'])
def train():
    return jsonify(serves.train())


# 11. GET /api/train/{task_id} - 查询训练进度
@app.route('/api/train/<task_id>', methods=['GET'])
def get_train(task_id):
    return jsonify(serves.get_train(task_id))


# 12. GET /api/training-history - 获取训练历史
@app.route('/api/training-history', methods=['GET'])
def training_history():
    return jsonify(serves.training_history())


# 13. GET /api/export/{task_id} - 导出训练模型文件
@app.route('/api/export/<task_id>', methods=['GET'])
def export(task_id):
    return jsonify(serves.export(task_id))


# 14. GET /api/stats - 数据统计
@app.route('/api/stats', methods=['GET'])
def stats():
    return jsonify(serves.stats())


# 15. GET /api/files/{filename} - 获取静态文件
@app.route('/api/files/<path:filename>', methods=['GET'])
def get_file(filename):
    return jsonify(serves.get_file(filename))


# ==================== 启动服务 ====================
if __name__ == '__main__':
    # 默认在 5000 端口启动
    app.run(host='0.0.0.0', port=5000, debug=True)