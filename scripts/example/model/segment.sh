#!/bin/bash

cd /Ommateum

python ./src/ommateum/models/test.py \
    --images_dir YOUR_VALID_IMAGES_DIR \
    --yolo_model_path YOUR_TRAINED_YOLO_PATH \
    --lora_path YOUR_SAM2_LORA_PATH \
    --output_mask_path ./dataset/test02/masks \
    