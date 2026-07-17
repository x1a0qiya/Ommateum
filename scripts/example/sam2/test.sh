#! /bin/bash

cd /Ommateum

python ./src/ommateum/models/sam2/test.py \
    --image_dir YOUR_VALID_IMAGES_DIR \
    --mask_dir YOUR_VALID_MASKS_DIR \
    --label_path YOUR_VALID_LABELS_DIR \
    --model_path facebook/sam2-hiera-tiny \
    --lora_path ./weights/sam2/train01 \
    --save_visualizations \
    --output_dir ./dataset/test01/masks