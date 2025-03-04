import os
import cv2
from utils.log_utils import log_event

def visualize_annotations(images_folder, labels_folder, output_folder):
    os.makedirs(output_folder, exist_ok=True)

    image_files = [f for f in os.listdir(images_folder) if f.endswith(('.png', '.jpg', '.jpeg'))]

    for idx, image_file in enumerate(image_files):
        log_event(f"Traitement de l'image {idx + 1}/{len(image_files)} : {image_file}")

        image_path = os.path.join(images_folder, image_file)
        label_path = os.path.join(labels_folder, os.path.splitext(image_file)[0] + ".txt")
        output_path = os.path.join(output_folder, image_file)

        if not os.path.exists(label_path):
            log_event(f"Aucune annotation trouvée pour {image_file}")
            continue

        image = cv2.imread(image_path)
        with open(label_path, 'r') as label_file:
            for line in label_file:
                cls, x, y, w, h = map(float, line.strip().split())
                # Convertir YOLO format en coordonnées image
                pass  # (ajouter la visualisation ici)

        cv2.imwrite(output_path, image)
       
