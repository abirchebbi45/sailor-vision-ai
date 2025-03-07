import os
import shutil
from utils.log_utils import log_event

def export_best_model():
    project_root = os.path.dirname(os.path.dirname(__file__))
    training_folder = os.path.join(project_root, "outputs", "train", "train_yolo")
    output_folder = os.path.join(project_root, "outputs", "exports")

    os.makedirs(output_folder, exist_ok=True)

    best_model = os.path.join(training_folder, 'weights', 'best.pt')
    if os.path.exists(best_model):
        shutil.copy(best_model, os.path.join(output_folder, 'yolov8_best.pt'))
        log_event(f"Modèle exporté vers {output_folder}/yolov8_best.pt")
    else:
        log_event("Aucun fichier 'best.pt' trouvé.")
