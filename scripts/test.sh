#!/bin/bash

cd /Ommateum

python ./src/ommateum/models/test.py \
    --model_path ./weights/yolo/trained/train01_best.pt \
    --source ./dataset/Tumor-Detection/test/images \
    --device cuda \
    --project ./dataset/Tumor-Detection/ts1/ \
