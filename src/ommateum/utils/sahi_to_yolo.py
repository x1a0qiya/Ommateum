import os
import sys
import json
import subprocess
import argparse

def convert_sahi_to_yolo(coco_json_path, output_dir):
    """
    调用 SAHI CLI 将 COCO JSON 转换为 YOLO TXT 格式
    """
    if not os.path.exists(coco_json_path):
        raise FileNotFoundError(f" 找不到 COCO JSON 文件: {coco_json_path}")
    print(f"正在转换: {coco_json_path} -> {output_dir}")
    cmd = [
        "sahi", "coco", "yolov5",
        "--coco_json_path", coco_json_path,
        "--output_dir", output_dir
    ]
    try:
        subprocess.run(cmd, check=True)
        print("格式转换完成！")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"转换失败: {e}")

def generate_data_yaml(output_dir, coco_json_path):
    """
    自动读取 COCO JSON 中的类别信息，生成 data.yaml
    """
    yaml_path = os.path.join(output_dir, "data.yaml")
    with open(coco_json_path, 'r', encoding='utf-8') as f:
        coco_data = json.load(f)
    categories = coco_data.get("categories", [])
    if not categories:
        raise ValueError("COCO JSON 中未找到 categories 信息")
    names = {cat["id"]: cat["name"] for cat in sorted(categories, key=lambda x: x["id"])}
    with open(yaml_path, 'w', encoding='utf-8') as f:
        f.write(f"path: {os.path.abspath(output_dir)}\n")
        f.write("train: train/images\n")
        f.write("val: val/images\n\n")
        f.write("names:\n")
        for idx, name in names.items():
            f.write(f"  {idx}: {name}\n")
    print(f"已生成配置文件: {yaml_path}")
    return yaml_path

def main():
    parser = argparse.ArgumentParser(description="SAHI 转 YOLO 自动化脚本")
    parser.add_argument("--coco_json", type=str, required=True, help="SAHI 生成的 COCO JSON 文件路径")
    parser.add_argument("--output_dir", type=str, default="yolo_dataset", help="YOLO 数据集输出目录")
    args = parser.parse_args()
    convert_sahi_to_yolo(args.coco_json, args.output_dir)
    yaml_path = generate_data_yaml(args.output_dir, args.coco_json)
    print("\n全部完成")

if __name__ == "__main__":
    main()