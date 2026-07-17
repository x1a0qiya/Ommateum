#! /bin/bash

cd Ommateum

python ./src/ommateum/models/identify/generate_result.py \
    --images_dir YOUR_IMAGES_DIR \
    --model_path ./weights/train01/yolo \
