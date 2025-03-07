import os
import cv2
from ultralytics import YOLO
from utils.log_utils import log_event

def track_objects():
    project_root = os.path.dirname(os.path.dirname(__file__))
    video_path = os.path.join(project_root, "assets", "input_video.mp4")
    model_path = os.path.join(project_root, "outputs", "exports", "yolov8_best.pt")
    output_path = os.path.join(project_root, "outputs", "videos", "tracked_video.mp4")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Modèle introuvable : {model_path}")

    model = YOLO(model_path)
    results = model.track(source=video_path, save=True, project=os.path.dirname(output_path), name="tracked_video")

    log_event(f"Tracking terminé. Vidéo sauvegardée dans {output_path}")
