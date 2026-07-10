#!/bin/bash

cd /Ommateum

python ./src/ommateum/models/test.py \
    --model_path ./weights/yolo/pretrained/yolo11n.pt \
    --source ./dataset/severstal_yolo/images/train \
    --device cuda \
    --project ./dataset/severstal \
