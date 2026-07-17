#!/bin/bash

cd /Ommateum

python ./src/ommateum/models/train.py \
    --data_yaml YOUR_DATAYAML_PATH \
    --yolo_epochs 8 \
    --yolo_batch_size 8 \
    --name train01 \
    --model_path facebook/sam2-hiera-tiny \
    --save_path ./weights/sam2/trained/ \
    --image_dir YOUR_IMAGES_DIR \
    --label_dir YOUR_LABELS_DIR \
    --mask_dir YOUR_MASKS_DIR \
    --sam2_batch_size 1 \
    --sam2_epochs 8 \