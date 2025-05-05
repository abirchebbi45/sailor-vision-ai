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
        """
        Initializes the DetectionRecorder with default configurations for recording.
        Sets up ROS subscriptions for image and alert topics.
        """
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
        
        # Configuration for recording parameters
        self.max_frames_without_alert = 30  # Stop recording 3 seconds after the last alert
        self.pre_record_buffer_size = 20  # Frames to keep before the alert (2 seconds)
        self.pre_record_buffer = []  # Buffer for frames before the alert
        
        self.storage_service = StorageService()

        # Subscribe to image and alert topics
        node.create_subscription(Image, '/yolo/image_raw', self._on_image, 10)
        node.create_subscription(String, '/yolo/alerts', self._on_alert, 10)

    def _on_image(self, msg):
        """
        Callback for processing incoming image frames.
        Maintains a pre-record buffer and handles recording logic.
        """
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, "bgr8")
            self.last_frame = frame
            
            # Always maintain a pre-record buffer
            self.pre_record_buffer.append(frame)
            if len(self.pre_record_buffer) > self.pre_record_buffer_size:
                self.pre_record_buffer.pop(0)  # Keep only the last N frames

            if self.recording:
                self.frame_buffer.append(frame)
                self.frames_since_last_alert += 1

                # Stop recording after a certain number of frames without an alert
                if self.frames_since_last_alert >= self.max_frames_without_alert:
                    self._stop_recording()
                    
        except Exception as e:
            logger.error(f"Error processing image: {e}")

    def _on_alert(self, msg):
        """
        Callback for processing incoming alerts.
        Starts or resets recording based on the detected class.
        """
        try:
            alert_data = json.loads(msg.data)
            if alert_data.get("detections"):
                new_detected_class = alert_data["detections"][0]["class"]
                logger.info(f"Alert detected: {new_detected_class}")
                
                # If already recording
                if self.recording:
                    # If a different class is detected, stop the current recording and start a new one
                    if new_detected_class != self.detected_class_name:
                        logger.info(f"Different class detected, stopping current recording and starting new one")
                        self._stop_recording()
                        self.detected_class_name = new_detected_class
                        self._start_recording()
                    else:
                        # Same class detected, reset the counter
                        logger.info(f"Same class detected, resetting counter")
                        self.frames_since_last_alert = 0
                        self.detected_class_name = new_detected_class
                else:
                    # Not recording, start a new recording
                    self.detected_class_name = new_detected_class
                    self._start_recording()
            else:
                if not self.recording:
                    self.detected_class_name = "unknown"
                    self._start_recording()
                
        except Exception as e:
            logger.error(f"Error processing alert: {e}")

    def _start_recording(self):
        """
        Starts recording by initializing the frame buffer with pre-recorded frames.
        """
        self.recording = True
        self.video_start_time = datetime.now()
        
        # Initialize with frames from the pre-record buffer
        self.frame_buffer = self.pre_record_buffer.copy()
        self.frames_since_last_alert = 0
        
        logger.info(f"Recording started for class: {self.detected_class_name}")

    def _stop_recording(self):
        """
        Stops recording, saves the video, and stores metadata using the storage service.
        """
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
        file_size = os.path.getsize(filepath)  # File size in bytes
        resolution = f"{width}x{height}"  # Resolution in "WxH" format

        # Ensure metadata aligns with the Recording model
        self.storage_service.store_video_metadata({
            "path": filepath,
            "class_name": self.detected_class_name,
            "start_time": self.video_start_time.isoformat(),
            "duration": duration,
            "frame_count": len(self.frame_buffer),
            "size": file_size,
            "resolution": resolution,
            "storage_type": "LOCAL"  # Default to LOCAL storage
        })

        self.frame_buffer.clear()
        logger.info(f"Video saved and metadata stored: {filepath}")