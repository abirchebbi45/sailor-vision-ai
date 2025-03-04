from ultralytics import YOLO
import cv2
import os
from utils.log_utils import log_event

def track_objects(video_path, model_path, output_path):
    if not os.path.exists(model_path):
        log_event(f"Modèle introuvable : {model_path}")
        raise FileNotFoundError(f"Le modèle {model_path} est introuvable.")

    if not os.path.exists(video_path):
        log_event(f"Vidéo introuvable : {video_path}")
        raise FileNotFoundError(f"La vidéo {video_path} est introuvable.")

    log_event(f"Début du tracking pour la vidéo : {video_path} avec le modèle : {model_path}")

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

        log_event(f"Tracking terminé. Vidéo sauvegardée : {output_path}")
    except Exception as e:
        log_event(f"Erreur lors du tracking : {e}")
    finally:
        cap.release()
        out.release()
        cv2.destroyAllWindows()
