import os
import logging
import cv2
import json
from PyQt5.QtCore import QObject
from sensor_msgs.msg import Image
from std_msgs.msg import String
from cv_bridge import CvBridge
from datetime import datetime
from src.services.storage_service import StorageService

logger = logging.getLogger(__name__)

class DetectionRecorder(QObject):
    def __init__(self, node, output_dir="recordings"):
        super().__init__()
        self.bridge = CvBridge()
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

        self.last_frame = None
        self.recording = False
        self.frame_buffer = []
        self.frames_since_last_alert = 0
        self.frame_rate = 10  # fps
        self.video_start_time = None
        self.detected_class_name = "unknown"
        
        # Configuration des paramètres d'enregistrement
        self.max_frames_without_alert = 30  # 3 secondes après la dernière alerte
        self.pre_record_buffer_size = 20  # Frames à conserver avant l'alerte (2 secondes)
        self.pre_record_buffer = []  # Buffer pour les frames avant l'alerte
        
        self.storage_service = StorageService()

        node.create_subscription(Image, '/yolo/image_raw', self._on_image, 10)
        node.create_subscription(String, '/yolo/alerts', self._on_alert, 10)

    def _on_image(self, msg):
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, "bgr8")
            self.last_frame = frame
            
            # Toujours maintenir un buffer de pre-enregistrement
            self.pre_record_buffer.append(frame)
            if len(self.pre_record_buffer) > self.pre_record_buffer_size:
                self.pre_record_buffer.pop(0)  # Garder uniquement les N dernières frames

            if self.recording:
                self.frame_buffer.append(frame)
                self.frames_since_last_alert += 1

                # Arrêter après un certain nombre de frames sans alerte
                if self.frames_since_last_alert >= self.max_frames_without_alert:
                    self._stop_recording()
                    
        except Exception as e:
            logger.error(f"Error processing image: {e}")

    def _on_alert(self, msg):
        try:
            alert_data = json.loads(msg.data)
            if alert_data.get("detections"):
                new_detected_class = alert_data["detections"][0]["class"]
                logger.info(f"Alert detected: {new_detected_class}")
                
                # Si déjà en enregistrement
                if self.recording:
                    # Si c'est une classe différente, arrêter l'enregistrement actuel et en commencer un nouveau
                    if new_detected_class != self.detected_class_name:
                        logger.info(f"Different class detected, stopping current recording and starting new one")
                        self._stop_recording()
                        self.detected_class_name = new_detected_class
                        self._start_recording()
                    else:
                        # Même classe, réinitialiser le compteur
                        logger.info(f"Same class detected, resetting counter")
                        self.frames_since_last_alert = 0
                        self.detected_class_name = new_detected_class
                else:
                    # Pas en enregistrement, commencer un nouveau
                    self.detected_class_name = new_detected_class
                    self._start_recording()
            else:
                if not self.recording:
                    self.detected_class_name = "unknown"
                    self._start_recording()
                
        except Exception as e:
            logger.error(f"Error processing alert: {e}")

    def _start_recording(self):
        self.recording = True
        self.video_start_time = datetime.now()
        
        # Initialiser avec les frames du pre-record buffer
        self.frame_buffer = self.pre_record_buffer.copy()
        self.frames_since_last_alert = 0
        
        logger.info(f"Recording started for class: {self.detected_class_name}")

    def _stop_recording(self):
        if not self.recording:
            return
            
        logger.info("Stopping recording")
        self.recording = False
        video_end_time = datetime.now()

        if not self.frame_buffer:
            logger.warning("No frames recorded")
            return

        filename = f"{self.detected_class_name}_{self.video_start_time.strftime('%Y%m%d_%H%M%S')}.mp4"
        filepath = os.path.join(self.output_dir, filename)

        height, width, _ = self.frame_buffer[0].shape
        writer = cv2.VideoWriter(filepath, cv2.VideoWriter_fourcc(*'mp4v'), self.frame_rate, (width, height))

        for frame in self.frame_buffer:
            writer.write(frame)
        writer.release()

        duration = (video_end_time - self.video_start_time).total_seconds()

        self.storage_service.store_video_metadata({
            "path": filepath,
            "class_name": self.detected_class_name,
            "start_time": self.video_start_time.isoformat(),
            "duration": duration,
            "frame_count": len(self.frame_buffer)
        })

        self.frame_buffer.clear()
        logger.info(f"Video saved and metadata stored: {filepath}")