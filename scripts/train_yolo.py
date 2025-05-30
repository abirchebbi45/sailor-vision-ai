import os
import yaml
from ultralytics import YOLO
from utils.log_utils import log_event

def train_yolo():
    # Chemin racine du projet
    project_root = os.path.dirname(os.path.dirname(__file__))

    # Charger la configuration
    config_path = os.path.join(project_root, "config.yaml")
    print(f"The config_path : {config_path}")
    with open(config_path, "r") as file:
        config = yaml.safe_load(file)

    # Dossier de sortie pour les résultats de l'entraînement
    output_dir = os.path.join(project_root, "outputs", "train")
    os.makedirs(output_dir, exist_ok=True)  # Création du dossier s'il n'existe pas

    # Chemin vers le modèle pré-entraîné YOLOv8n
    model_path = config["yolo"]["pretrained_model"]
    
    # Charger le modèle YOLO
    model = YOLO(model_path)

    # Paramètres d'entraînement
    total_epochs = config["yolo"]["epochs"]
    batch_size = config["yolo"]["batch_size"]
    img_size = config["yolo"]["img_size"]
    
    # Dossier pour sauvegarder les modèles intermédiaires
    model_checkpoint_dir = os.path.join(output_dir, "checkpoints")
    os.makedirs(model_checkpoint_dir, exist_ok=True)  # Création du dossier

    log_event("Début de l'entraînement YOLO...")

    # Boucle d'entraînement pour gérer la sauvegarde et le logging
    data_path = os.path.join(project_root, "data.yaml")
    print("total epochs : ",total_epochs)
    #for epoch in range(1, total_epochs + 1):
    results = model.train(
            data=data_path,  # Utiliser le fichier config.yaml comme config YOLO
            epochs=total_epochs,  # Entraîner une epoch à la fois pour capturer les logs
            batch=batch_size,
            imgsz=img_size,
            project=output_dir,
            name="train_yolo",
            exist_ok=True
        )
    # Displaying results
    print(dir(results))
        
    # Get the correct metric from results
    if hasattr(results, 'metrics'):
        best_metric = results.metrics.mAP50 if hasattr(results.metrics, 'mAP50') else "N/A"
    else:
        best_metric = "N/A"

    #log_event(f"Epoch {epoch}/{total_epochs} terminée. Meilleure précision : {best_metric}")

        # Sauvegarde du modèle tous les 5 epochs
    #    if epoch % 5 == 0:
    model_save_path = os.path.join(model_checkpoint_dir, f"yolo_1.pt")
    model.save(model_save_path)
    #        log_event(f"Modèle sauvegardé après {epoch} epochs : {model_save_path}")

    log_event(f"Entraînement YOLO terminé. Modèles sauvegardés dans {model_checkpoint_dir}")
