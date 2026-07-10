#!/bin/bash

cd /Ommateum

python ./src/ommateum/models/train.py \
    --data_yaml ./dataset/severstal_yolo/dataset.yaml \
    --yolo_epochs 10 \
    --yolo_batch_size 4 \
    --yolo_cache_path ./dataset/__cache__/ \
    --name train01 \
    --imgsz 1600 \
    --model_path facebook/sam2-hiera-tiny \
    --save_path ./weights/sam2/trained/ \
    --image_dir ./dataset/severstal_yolo/images/train \
    --label_dir ./dataset/severstal_yolo/labels/train \
    --mask_dir ./dataset/severstal_yolo/masks/train \
    --sam2_batch_size 4 \
    --device cuda \