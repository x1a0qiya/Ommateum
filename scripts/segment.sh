#!/bin/bash

cd /Ommateum

python ./src/ommateum/models/identify/generate_result.py \
    --images_dir ./dataset/Tumor-Detection/test/images/ \
    --model_path ./weights/yolo/trained/train01_best.pt \
    --output_dir ./dataset/Tumor-Detection/ts/labels \
    --device cuda \

python ./src/ommateum/models/sam2/test.py \
    --image_dir ./dataset/Tumor-Detection/test/images/ \
    --mask_dir ./dataset/Tumor-Detection/test/masks/ \
    --label_path ./dataset/Tumor-Detection/ts/labels/ \
    --model_path facebook/sam2-hiera-tiny \
    --no_lora \
    --save_visualizations \
    --output_dir ./dataset/Tumor-Detection/ts/masks/
    # --lora_path ./weights/sam2/trained/train01 \