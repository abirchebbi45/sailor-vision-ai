import json
import cv2
import os

def visualize_annotations(image_dir, annotation_file, output_dir):
    with open(annotation_file) as f:
        annotations = json.load(f)

    images = {img['id']: img['file_name'] for img in annotations['images']}
    
    os.makedirs(output_dir, exist_ok=True)

    for ann in annotations['annotations']:
        image_id = ann['image_id']
        bbox = ann['bbox']

        image_path = os.path.join(image_dir, images[image_id])
        img = cv2.imread(image_path)

        if img is None:
            print(f"Image {image_path} not found.")
            continue

        x, y, w, h = map(int, bbox)
        cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)

        output_path = os.path.join(output_dir, images[image_id])
        cv2.imwrite(output_path, img)

    print("Annotations visualisées et sauvegardées dans", output_dir)

# Exemple d'appel
visualize_annotations('data/images', 'data/annotations.json', 'outputs/visualized')