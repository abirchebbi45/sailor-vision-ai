import cv2
from ultralytics import YOLO
import numpy as np
import os

def load_video(video_path):
    """Load a video file using OpenCV."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Error: Could not open video file at {video_path}")
    return cap

def load_yolo_model(model_path):
    """Load a pre-trained YOLO model."""
    try:
        model = YOLO(model_path)
        return model
    except Exception as e:
        raise ValueError(f"Error: Could not load YOLO model from {model_path}. {str(e)}")


def process_and_display_video(video_path, model_path):
    """Process video frames with YOLO predictions and display them."""
    # Load video and model
    cap = load_video(video_path)
    model = load_yolo_model(model_path)

    # Process each frame
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            print("End of video or error reading frame.")
            break

        # Perform YOLO prediction on the frame
        results = model.predict(source=frame, conf=0.25, iou=0.45)  # Adjust conf and iou as needed

        # Annotate frame with predictions
        annotated_frame = results[0].plot()  # Draw boxes and labels on the frame

        # Display the annotated frame
        cv2.imshow("YOLO Predictions", annotated_frame)

        # Exit on 'q' key press
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Cleanup
    cap.release()
    cv2.destroyAllWindows()

def main():
    # Define paths to your video and model
    video_path = "D:\projects\sailor-vision-ai\data\\test\lifejacket.mp4"
    model_path = "D:\projects\sailor-vision-ai\outputs\exports\yolov8_best.pt"   # Replace with your YOLO model file path (e.g., best.pt)
    print(f"Video path: {video_path}")
    
    try:
        # Process the video and display predictions
        process_and_display_video(video_path, model_path)
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()                         