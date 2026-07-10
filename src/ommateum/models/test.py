import os, sys
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(parent_dir)
sys.path.append('')

import argparse
import torch
from utils.sahi import predict

def parse_args():
    parser = argparse.ArgumentParser(description='')

    parser.add_argument('--model_path', type=str, required=True)
    parser.add_argument('--source', type=str, required=True)
    parser.add_argument('--model_type', type=str, default='ultralytics')
    parser.add_argument('--model_confidence_threshold', type=float, default=0.5)
    parser.add_argument('--device', type=str, default='cuda' if torch.cuda.is_available() else 'cpu')
    parser.add_argument('--slice_height', type=int, default=256)
    parser.add_argument('--slice_width', type=int, default=256)
    parser.add_argument('--overlap_height_ratio', type=float, default=0.2)
    parser.add_argument('--overlap_width_ratio', type=float, default=0.2)
    parser.add_argument('--project', type=str)
    parser.add_argument('--name', type=str, default='exp')
        
    return parser.parse_args()

def main():
    args = parse_args()

    predict(
        model_path=args.model_path,
        source=args.source,
        model_type=args.model_type,
        model_confidence_threshold=args.model_confidence_threshold,
        model_device=args.device,
        slice_height=args.slice_height,
        slice_width=args.slice_width,
        overlap_height_ratio=args.overlap_height_ratio,
        overlap_width_ratio=args.overlap_width_ratio,
        project=args.name,
        name=args.name
    )

if __name__ == '__main__':
    main()