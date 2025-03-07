import json
import os
import cv2
from utils.log_utils import log_event

COLORS = {0: (0, 255, 0), 1: (255, 0, 0), 2: (0, 0, 255), 3: (255, 255, 0)}

def visualize_annotations(split):
    """
    Visualize annotations for a given dataset split.

    Args:
        split (str): The dataset split to visualize (e.g., 'train', 'val', 'test').

    Returns:
        None
    """
    project_root = os.path.dirname(os.path.dirname(__file__))
    annotations_path = os.path.join(project_root, "data", "annotations", f"instances_{split}_objects_in_water.json")
    images_folder = os.path.join(project_root, "data", "images", split)
    output_folder = os.path.join(project_root, "outputs", "visualizations", split)

    os.makedirs(output_folder, exist_ok=True)

    with open(annotations_path, 'r', encoding='utf-8') as file:
        coco_data = json.load(file)

    image_metadata = {img['id']: img for img in coco_data['images']}

    for annotation in coco_data['annotations']:
        image_id = annotation['image_id']
        category_id = annotation['category_id']
        image_data = image_metadata.get(image_id)

        if not image_data:
            continue

        image_file = image_data['file_name']
        image_path = os.path.join(images_folder, image_file)
        output_path = os.path.join(output_folder, image_file)

        if not os.path.exists(image_path):
            continue

        image = cv2.imread(image_path)
        if image is None:
            continue

        x, y, width, height = annotation['bbox']
        x2, y2 = x + width, y + height
        color = COLORS.get(category_id, (255, 255, 255))

        cv2.rectangle(image, (int(x), int(y)), (int(x2), int(y2)), color, 2)
        cv2.imwrite(output_path, image)

    log_event(f"Visualisation {split} terminée, sauvegardée dans : {output_folder}")
