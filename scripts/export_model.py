import shutil
import os

def export_best_model(training_folder, output_folder):
    os.makedirs(output_folder, exist_ok=True)
    best_model = os.path.join(training_folder, 'weights', 'best.pt')
    if os.path.exists(best_model):
        shutil.copy(best_model, os.path.join(output_folder, 'yolov8_best.pt'))
        print(f"Modèle exporté dans {output_folder}/yolov8_best.pt")
    else:
        print("Aucun modèle 'best.pt' trouvé.")

# Exemple d'appel
export_best_model('outputs/yolo_training', 'models')
