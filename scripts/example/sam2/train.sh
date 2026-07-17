#!/bin/bash

cd Ommateum

python ./src/ommateum/models/sam2/train.py \
    --model_path facebook/sam2-hiera-tiny \
    --save_path ./weights/train01/sam2 \
    --image_dir YOUR_IMAGES_DIR \
    --label_dir YOUR_LABELS_DIR \
    --mask_dir YOUR_MASKS_DIR \
    --epochs 8 \
    --batch_size 1 \
