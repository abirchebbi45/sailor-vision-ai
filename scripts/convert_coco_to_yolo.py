import json
import os
from utils.log_utils import log_event

coco_to_yolo = {1: 0, 2: 1, 3: 2, 6: 3}

def convert_coco_to_yolo(split):
    """
    Convert COCO annotations to YOLO format.

    Args:
        split (str): The dataset split to convert (e.g., 'train', 'val', 'test').

    Returns:
        None
    """
    project_root = os.path.dirname(os.path.dirname(__file__))
    annotations_path = os.path.join(project_root, "data", "annotations", f"instances_{split}_objects_in_water.json")
    images_folder = os.path.join(project_root, "data", "images", split)
    output_folder = os.path.join(project_root, "data", "yolo_labels", split)
    os.makedirs(output_folder, exist_ok=True)

    with open(annotations_path, 'r', encoding='utf-8') as file:
        coco_data = json.load(file)

    images = {img['id']: img['file_name'] for img in coco_data['images']}
    image_metadata = {img['id']: img for img in coco_data['images']}

    nb_fichiers_convertis = 0

    for annotation in coco_data['annotations']:
        image_id = annotation['image_id']
        category_id = annotation['category_id']
        image_file = images.get(image_id)

        if not image_file:
            continue

        image_path = os.path.join(images_folder, image_file)
        if not os.path.exists(image_path):
            log_event(f"Image manquante : {image_path}")
            continue

        label_file = os.path.splitext(image_file)[0] + ".txt"
        label_path = os.path.join(output_folder, label_file)

        image_data = image_metadata[image_id]
        image_width, image_height = image_data['width'], image_data['height']
        x, y, width, height = annotation['bbox']

        x_center = (x + width / 2) / image_width
        y_center = (y + height / 2) / image_height
        width /= image_width
        height /= image_height

        if category_id in coco_to_yolo:
            with open(label_path, 'a', encoding='utf-8') as label_file:
                label_file.write(f"{coco_to_yolo[category_id]} {x_center} {y_center} {width} {height}\n")

        nb_fichiers_convertis += 1

    log_event(f"Conversion {split} terminée : {nb_fichiers_convertis} annotations converties.")
