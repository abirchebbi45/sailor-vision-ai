import json
import os

# Mapping des catégories COCO vers les indices YOLO (qui commencent à 0)
coco_to_yolo = {
    1: 0,   # swimmer
    2: 1,   # swimmer with life jacket
    3: 2,   # boat
    6: 3    # life jacket
}

def convert_coco_to_yolo(coco_file, output_dir):
    with open(coco_file) as f:
        data = json.load(f)

    os.makedirs(output_dir, exist_ok=True)

    images = {img['id']: img for img in data['images']}

    for ann in data['annotations']:
        img = images[ann['image_id']]
        filename = img['file_name'].replace('.jpg', '.txt')
        output_file = os.path.join(output_dir, filename)

        yolo_class_id = coco_to_yolo[ann['category_id']]

        # Normalisation des coordonnées bbox
        bbox = ann['bbox']
        x_center = (bbox[0] + bbox[2] / 2) / img['width']
        y_center = (bbox[1] + bbox[3] / 2) / img['height']
        width = bbox[2] / img['width']
        height = bbox[3] / img['height']

        with open(output_file, 'a') as f:
            f.write(f"{yolo_class_id} {x_center} {y_center} {width} {height}\n")

# Exécution
convert_coco_to_yolo('data/annotations.json', 'data/labels')
