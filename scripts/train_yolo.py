from ultralytics import YOLO

def train_yolo(data_yaml, model_path, epochs=50, imgsz=640):
    model = YOLO('yolov8n.yaml')  # Utilise le modèle YOLOv8 nano comme base
    results = model.train(
        data=data_yaml,
        epochs=epochs,
        imgsz=imgsz,
        project='outputs',
        name='yolo_training',
        save=True
    )
    print("Entraînement terminé ! Modèle sauvegardé dans outputs/yolo_training/")

# Exemple d'appel
train_yolo('data/dataset.yaml', 'models/yolov8n.pt')
