from ultralytics import YOLO
import os
from datetime import datetime

def log_event(event_message):
    """
    Enregistre un événement dans le fichier log.txt à la racine du projet.
    """
    # Chemin du log.txt à la racine du projet
    log_file_path = os.path.join(os.path.dirname(__file__), '..', 'log.txt')

    # S'assure que le dossier parent existe (au cas où le script est exécuté seul)
    if not os.path.exists(os.path.dirname(log_file_path)):
        os.makedirs(os.path.dirname(log_file_path))

    # Ajoute l'événement au fichier log
    with open(log_file_path, "a", encoding="utf-8") as log_file:
        timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        log_file.write(f"{timestamp} {event_message}\n")

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

# Exemple d'appel avec un modèle pré-entraîné
train_yolo('data/dataset.yaml', 'models/yolov8n.pt')
