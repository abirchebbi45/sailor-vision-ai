import cv2
from ultralytics import YOLO

def track_objects(video_path, model_path, output_video):
    model = YOLO(model_path)

    cap = cv2.VideoCapture(video_path)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))

    out = cv2.VideoWriter(output_video, cv2.VideoWriter_fourcc(*'mp4v'), fps, (width, height))

    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            break

        results = model.track(frame, persist=True)

        if results[0].boxes is not None:
            for box in results[0].boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                track_id = int(box.id[0]) if box.id is not None else -1
                cv2.putText(frame, f'ID: {track_id}', (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

        out.write(frame)

    cap.release()
    out.release()
    print(f"Tracking terminé et sauvegardé dans {output_video}")

# Exemple d'appel
track_objects('data/test_video.mp4', 'models/yolov8_best.pt', 'outputs/tracked_video.mp4')
