#!/bin/bash

cd /Ommateum/src/ommateum/models/sam2

python train.py \
    --model_path facebook/sam2-hiera-tiny \
    --save_path ./Ommateum/sam2_lora/ \
    --image_dir /Ommateum/data/instance_version/images/train/ \
    --label_dir /Ommateum/data/instance_version/labels/train/ \
    --mask_dir /Ommateum/data/instance_version/masks/train/ \
    --device "cuda" \
    --epochs 8 \
    --batch_size 4 \
