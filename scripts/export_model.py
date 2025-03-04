import shutil
import os

def export_best_model(training_folder, output_folder):
    """
    Exporte le meilleur modèle YOLOv8 (best.pt) d'un dossier de formation vers un dossier de destination.

    :param training_folder: Dossier de l'entraînement (ex: outputs/yolo_training).
    :param output_folder: Dossier où exporter le modèle.
    :return: True si export réussi, False sinon.
    """
    os.makedirs(output_folder, exist_ok=True)

    weights_folder = os.path.join(training_folder, 'weights')
    best_model = os.path.join(weights_folder, 'best.pt')

    if not os.path.exists(training_folder):
        print(f"Le dossier d'entraînement '{training_folder}' n'existe pas.")
        return False

    if not os.path.exists(weights_folder):
        print(f"Le dossier 'weights' est introuvable dans '{training_folder}'.")
        return False

    if os.path.exists(best_model):
        shutil.copy(best_model, os.path.join(output_folder, 'yolov8_best.pt'))
        print(f"Modèle exporté dans {output_folder}/yolov8_best.pt")
        return True
    else:
        print("Aucun fichier 'best.pt' trouvé dans le dossier 'weights'.")
        return False

# Exemple d'appel
export_best_model('outputs/yolo_training', 'models')
