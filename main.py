import yaml
from scripts.convert_coco_to_yolo import convert_coco_to_yolo
from scripts.train_yolo import train_yolo
from scripts.export_model import export_best_model
from scripts.track_objects import track_objects
from scripts.visualize_annotations import visualize_annotations
from scripts.evaluate_model import evaluate_model  # Ajoutez cette ligne
from utils.log_utils import log_event

with open("config.yaml", "r") as file:
    config = yaml.safe_load(file)

def main():
    log_event("Lancement du pipeline complet.")

    # Conversion des annotations COCO vers YOLO
    convert_coco_to_yolo("train")
    convert_coco_to_yolo("val")
    convert_coco_to_yolo("test")

    # Entraînement du modèle YOLO
    train_yolo()

    # Exportation du meilleur modèle
    export_best_model()

    # Visualisation des annotations
    visualize_annotations("train")
    visualize_annotations("val")

    
    # Évaluation du modèle
    evaluate_model(
    images_folder=config['evaluation']['val_images_folder'],
    labels_folder=config['evaluation']['val_labels_folder'],
    model_path=config['evaluation']['best_model_path'],
    metrics_output_file=config['evaluation']['metrics_output_file'],
    confidence_threshold=config['evaluation']['confidence_threshold'],
    iou_threshold=config['evaluation']['iou_threshold']
)

    # Tracking des objets dans une vidéo
    track_objects()

    log_event("Pipeline complet terminé.")

if __name__ == '__main__':
    main()