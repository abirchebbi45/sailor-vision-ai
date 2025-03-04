from ultralytics import YOLO
import cv2
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



def track_objects(video_path, model_path, output_path):
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Le modèle {model_path} est introuvable.")
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"La vidéo {video_path} est introuvable.")

    print(f"Démarrage du tracking sur {video_path} avec le modèle {model_path}")

    model = YOLO(model_path)
    cap = cv2.VideoCapture(video_path)

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_size = (int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))
    out = cv2.VideoWriter(output_path, fourcc, fps, frame_size)

    try:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            results = model.track(frame, persist=True)

            if results[0].boxes:
                for box in results[0].boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

                    if box.id is not None:
                        cv2.putText(frame, f"ID: {int(box.id)}", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

            out.write(frame)

        print(f"Tracking terminé, vidéo sauvegardée dans {output_path}")

    except Exception as e:
        print(f"Erreur lors du traitement : {e}")
    
    finally:
        cap.release()
        out.release()
        cv2.destroyAllWindows()

# Exemple d'appel
# track_objects('input.mp4', 'yolov8n.pt', 'output.mp4')
