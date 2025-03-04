import os
import cv2

def visualize_annotations(images_folder, labels_folder, output_folder):
    os.makedirs(output_folder, exist_ok=True)

    image_files = [f for f in os.listdir(images_folder) if f.endswith(('.png', '.jpg', '.jpeg'))]

    for idx, image_file in enumerate(image_files):
        print(f"Traitement de l'image {idx + 1}/{len(image_files)} : {image_file}")

        image_path = os.path.join(images_folder, image_file)
        label_path = os.path.join(labels_folder, os.path.splitext(image_file)[0] + '.txt')
        
        if not os.path.exists(label_path):
            print(f"Aucun label trouvé pour {image_file}, passage à l'image suivante.")
            continue

        image = cv2.imread(image_path)

        with open(label_path, 'r') as file:
            for line in file:
                parts = line.strip().split()
                class_id = int(parts[0])
                x_center, y_center, width, height = map(float, parts[1:])

                h, w, _ = image.shape
                x1 = int((x_center - width / 2) * w)
                y1 = int((y_center - height / 2) * h)
                x2 = int((x_center + width / 2) * w)
                y2 = int((y_center + height / 2) * h)

                cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(image, str(class_id), (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        output_path = os.path.join(output_folder, image_file)
        cv2.imwrite(output_path, image)

    print("Visualisation terminée.")

# Exemple d'appel
# visualize_annotations('data/images', 'data/labels', 'data/visualized')
