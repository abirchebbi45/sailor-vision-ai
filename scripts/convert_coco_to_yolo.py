import json
import os

def convert_coco_to_yolo(coco_file, output_dir):
    with open(coco_file) as f:
        data = json.load(f)

    images = {img['id']: img for img in data['images']}
    for ann in data['annotations']:
        img = images[ann['image_id']]
        filename = img['file_name'].replace('.jpg', '.txt')

        with open(os.path.join(output_dir, filename), 'a') as f:
            bbox = ann['bbox']
            x_center = (bbox[0] + bbox[2] / 2) / img['width']
            y_center = (bbox[1] + bbox[3] / 2) / img['height']
            width = bbox[2] / img['width']
            height = bbox[3] / img['height']
            f.write(f"{ann['category_id']} {x_center} {y_center} {width} {height}\n")

convert_coco_to_yolo('data/annotations.json', 'data/labels')
