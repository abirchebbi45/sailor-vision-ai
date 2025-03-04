from ultralytics import YOLO
import cv2
import os

def track_objects(video_path, model_path, output_path):
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"❌ Le modèle {model_path} est introuvable.")
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"❌ La vidéo {video_path} est introuvable.")

    print(f"🚀 Démarrage du tracking sur {video_path} avec le modèle {model_path}")

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

        print(f"✅ Tracking terminé, vidéo sauvegardée dans {output_path}")

    except Exception as e:
        print(f"⚠️ Erreur lors du traitement : {e}")
    
    finally:
        cap.release()
        out.release()
        cv2.destroyAllWindows()

# Exemple d'appel
# track_objects('input.mp4', 'yolov8n.pt', 'output.mp4')
