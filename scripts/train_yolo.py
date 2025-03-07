import os
from ultralytics import YOLO
from utils.log_utils import log_event

def train_yolo():
    project_root = os.path.dirname(os.path.dirname(__file__))
    data_yaml = os.path.join(project_root, "config.yaml")
    output_dir = os.path.join(project_root, "outputs", "train")
    model_path = "yolov8n.pt"

    os.makedirs(output_dir, exist_ok=True)

    model = YOLO(model_path)
    results = model.train(data=data_yaml, epochs=50, batch=16, project=output_dir, name='train_yolo', exist_ok=True)

    log_event(f"Entraînement YOLO terminé. Résultats sauvegardés dans {output_dir}")
