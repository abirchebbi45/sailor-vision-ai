from ultralytics import YOLO
import os
from datetime import datetime
from utils.log_utils import log_event

def train_yolo(data_yaml, model_path='yolov8n.pt', epochs=50, imgsz=640):
    """
    Entraîne un modèle YOLOv8.

    :param data_yaml: Chemin vers le fichier YAML de configuration du dataset.
    :param model_path: Chemin vers le modèle YOLO (pré-entraîné ou vide).
    :param epochs: Nombre d'epochs d'entraînement.
    :param imgsz: Taille des images.
    """
    model = YOLO(model_path)

    results = model.train(
        data=data_yaml,
        epochs=epochs,
        imgsz=imgsz,
        project='outputs',
        name='yolo_training',
        save=True
    )

    print("Entraînement terminé ! Modèle sauvegardé dans outputs/yolo_training/")
    log_event("Entraînement terminé ! Modèle sauvegardé dans outputs/yolo_training/")
