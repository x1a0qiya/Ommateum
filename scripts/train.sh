#!/bin/bash

cd /Ommateum

python ./src/ommateum/models/train.py \
    --data_yaml ./dataset/Tumor-Detection/data.yaml \
    --yolo_epochs 100 \
    --yolo_batch_size 4 \
    --yolo_cache_path ./dataset/__cache__/ \
    --name train01 \
    --imgsz 640 \
    --model_path facebook/sam2-hiera-tiny \
    --save_path ./weights/sam2/trained/ \
    --image_dir ./dataset/Detection/train/images \
    --label_dir ./dataset/Detection/train/labels \
    --mask_dir ./dataset/severstal_yolo/masks/train \
    --sam2_batch_size 4 \
    --device cuda \