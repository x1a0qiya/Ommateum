#!/bin/bash

cd /Ommateum

python ./src/ommateum/models/identify/generate_result.py \
    --images_dir ./dataset/severstal_yolo/images/val \
    --model_path ./weights/yolo/trained/train01_best.pt \
    --output_dir ./dataset/severstal/labels/val \
    --device cuda \

python ./src/ommateum/models/sam2/test.py \
    --image_dir ./dataset/severstal_yolo/images/val\
    --mask_dir ./dataset/severstal_yolo/masks/val \
    --label_path ./dataset/severstal/labels/val \
    --model_path facebook/sam2-hiera-tiny \
    --lora_path ./weights/sam2/trained/train01 \
    --save_visualizations \
    --output_dir ./dataset/severstal/masks/val