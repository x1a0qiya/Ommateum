#!/bin/bash

cd Ommateum

python ./src/ommateum/models/identify/train.py \
    --weights_output_path ./weights/train01/yolo \
    --data YOUR_DATAYAML_PATH \
    --epochs 8 \
    --batch 8 \
