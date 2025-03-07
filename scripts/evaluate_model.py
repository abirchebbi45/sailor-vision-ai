import os
import json
from ultralytics import YOLO
from utils.log_utils import log_event

def evaluate_model(labels_folder, model_path, metrics_output_file, confidence_threshold=0.5, iou_threshold=0.5):
    """
    Evaluate the YOLO model on a validation set and save the metrics.
    
    Args:
        labels_folder (str): Path to the folder containing the validation labels.
        model_path (str): Path to the trained YOLO model.
        metrics_output_file (str): Path to the output file to save the metrics.
        confidence_threshold (float): Confidence threshold for detections.
        iou_threshold (float): IoU threshold for non-maximal suppression (NMS).
    """
    # Charger le modèle
    model = YOLO(model_path)
    
    # Évaluer le modèle
    results = model.val(
        data=os.path.join(labels_folder, "dataset.yaml"),  # Chemin vers le fichier YAML du dataset
        split="val",  # Utiliser l'ensemble de validation
        conf=confidence_threshold,
        iou=iou_threshold,
        save_json=True,  # Sauvegarder les résultats au format JSON
        project=os.path.dirname(metrics_output_file),
        name=os.path.basename(metrics_output_file).split(".")[0]
    )
    
    # Enregistrer les métriques dans un fichier
    metrics = {
        "precision": results.results_dict["metrics/precision"],
        "recall": results.results_dict["metrics/recall"],
        "mAP50": results.results_dict["metrics/mAP50"],
        "mAP50-95": results.results_dict["metrics/mAP50-95"]
    }
    
    with open(metrics_output_file, "w") as f:
        json.dump(metrics, f, indent=4)
    
    log_event(f"Évaluation terminée. Métriques sauvegardées dans {metrics_output_file}")