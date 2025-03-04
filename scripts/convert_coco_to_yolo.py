import json
import os

# Mapping des catégories COCO vers les indices YOLO (qui commencent à 0)
coco_to_yolo = {
    1: 0,   # swimmer
    2: 1,   # swimmer with life jacket
    3: 2,   # boat
    6: 3    # life jacket
}

def convert_coco_to_yolo(coco_json_path, images_folder, output_folder):
    os.makedirs(output_folder, exist_ok=True)

    with open(coco_json_path, 'r', encoding='utf-8') as file:
        coco_data = json.load(file)

    images = {image['id']: image['file_name'] for image in coco_data['images']}
    categories = {category['id']: category['name'] for category in coco_data['categories']}
    nb_fichiers_convertis = 0

    for annotation in coco_data['annotations']:
        image_id = annotation['image_id']
        category_id = annotation['category_id']

        image_file = images.get(image_id)
        if not image_file:
            continue

        image_path = os.path.join(images_folder, image_file)
        if not os.path.exists(image_path):
            print(f"Image manquante : {image_path}")
            continue

        label_file = os.path.splitext(image_file)[0] + ".txt"
        label_path = os.path.join(output_folder, label_file)

        image_width = coco_data['images'][image_id-1]['width']
        image_height = coco_data['images'][image_id-1]['height']

        x, y, width, height = annotation['bbox']
        x_center = (x + width / 2) / image_width
        y_center = (y + height / 2) / image_height
        width /= image_width
        height /= image_height

        with open(label_path, 'a') as label_file:
            label_file.write(f"{category_id} {x_center} {y_center} {width} {height}\n")

        nb_fichiers_convertis += 1

    print(f"Conversion terminée : {nb_fichiers_convertis} annotations traitées.")