#! /bin/bash

cd /Ommateum/src/ommateum/models/sam2

python test.py \
    --image_dir /Ommateum/data/instance_version/images/val/ \
    --mask_dir /Ommateum/data/instance_version/masks/val/ \
    --label_path /Ommateum/data/instance_version/labels/val/ \
    --model_path facebook/sam2-hiera-large \
    --lora_path ./Ommateum/sam2_lora/