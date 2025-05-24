import os
import logging
import cv2
import json
from PyQt5.QtCore import QObject, QTimer
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

        # --- Multi-camera buffers ---
        self.last_frame = {}  # topic → last frame
        self.recording = {}   # topic → bool
        self.frame_buffer = {}  # topic → list of frames
        self.frames_since_last_alert = {}  # topic → int
        self.video_start_time = {}  # topic → datetime
        self.detected_class_name = {}  # topic → str
        self.pre_record_buffer = {}  # topic → list of frames

        self.frame_rate = 10  # fps
        self.max_frames_without_alert = 30  # Stop recording 3 seconds after the last alert
        self.pre_record_buffer_size = 20  # Frames to keep before the alert (2 seconds)

        self.storage_service = StorageService()
        self.node = node

        # --- Dynamic subscription to all /yolo/*/image_raw topics ---
        self._subs = {}
        self._timer = QTimer()
        self._timer.timeout.connect(self._subscribe_to_yolo_image_topics)
        self._timer.start(1000)

        # Subscribe to alerts (unique topic)
        node.create_subscription(String, '/yolo/alerts', self._on_alert, 10)

    def _subscribe_to_yolo_image_topics(self):
        topics = self.node.get_topic_names_and_types()
        for topic, types in topics:
            if topic.startswith('/yolo/') and topic.endswith('/image_raw') and 'sensor_msgs/msg/Image' in types:
                if topic not in self._subs:
                    sub = self.node.create_subscription(
                        Image, topic, lambda msg, t=topic: self._on_image(msg, t), 10
                    )
                    self._subs[topic] = sub
                    logger.info(f"DetectionRecorder subscribed to {topic}")

    def _on_image(self, msg, topic):
        """
        Callback for processing incoming image frames for each camera.
        Maintains a pre-record buffer and handles recording logic per topic.
        """
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, "bgr8")
            # Always maintain a pre-record buffer per topic
            if topic not in self.pre_record_buffer:
                self.pre_record_buffer[topic] = []
            self.pre_record_buffer[topic].append(frame)
            if len(self.pre_record_buffer[topic]) > self.pre_record_buffer_size:
                self.pre_record_buffer[topic].pop(0)

            self.last_frame[topic] = frame

            # Recording logic per topic
            if self.recording.get(topic, False):
                self.frame_buffer[topic].append(frame)
                self.frames_since_last_alert[topic] += 1
                if self.frames_since_last_alert[topic] >= self.max_frames_without_alert:
                    self._stop_recording(topic)
        except Exception as e:
            logger.error(f"Error processing image for {topic}: {e}")

    def _on_alert(self, msg):
        """
        Callback for processing incoming alerts.
        Starts or resets recording based on the detected class and source_topic.
        """
        try:
            alert_data = json.loads(msg.data)
            if alert_data.get("detections"):
                for detection in alert_data["detections"]:
                    source_topic = detection.get("source_topic")
                    if not source_topic:
                        continue
                    # Convert /camera/videoX/image_raw → /yolo/videoX/image_raw
                    video_name = source_topic.split('/')[2]
                    yolo_topic = f"/yolo/{video_name}/image_raw"
                    new_detected_class = detection["class"]

                    # If already recording for this topic
                    if self.recording.get(yolo_topic, False):
                        if new_detected_class != self.detected_class_name.get(yolo_topic, "unknown"):
                            logger.info(f"Different class detected on {yolo_topic}, stopping current recording and starting new one")
                            self._stop_recording(yolo_topic)
                            self.detected_class_name[yolo_topic] = new_detected_class
                            self._start_recording(yolo_topic)
                        else:
                            logger.info(f"Same class detected on {yolo_topic}, resetting counter")
                            self.frames_since_last_alert[yolo_topic] = 0
                            self.detected_class_name[yolo_topic] = new_detected_class
                    else:
                        self.detected_class_name[yolo_topic] = new_detected_class
                        self._start_recording(yolo_topic)
            # Optionally, handle the case where there are no detections (not recording)
        except Exception as e:
            logger.error(f"Error processing alert: {e}")

    def _start_recording(self, topic):
        """
        Starts recording by initializing the frame buffer with pre-recorded frames for the topic.
        """
        self.recording[topic] = True
        self.video_start_time[topic] = datetime.now()
        self.frame_buffer[topic] = self.pre_record_buffer.get(topic, []).copy()
        self.frames_since_last_alert[topic] = 0
        logger.info(f"Recording started for class: {self.detected_class_name.get(topic, 'unknown')} on {topic}")

    def _stop_recording(self, topic):
        """
        Stops recording, saves the video, and stores metadata using the storage service for the topic.
        """
        if not self.recording.get(topic, False):
            return

        logger.info(f"Stopping recording for {topic}")
        self.recording[topic] = False
        video_end_time = datetime.now()

        frames = self.frame_buffer.get(topic, [])
        if not frames:
            logger.warning(f"No frames recorded for {topic}")
            return

        class_name = self.detected_class_name.get(topic, "unknown")
        start_time = self.video_start_time.get(topic, datetime.now())
        filename = f"{class_name}_{start_time.strftime('%Y%m%d_%H%M%S')}_{topic.replace('/', '_')}.mp4"
        filepath = os.path.join(self.output_dir, filename)

        height, width, _ = frames[0].shape
        writer = cv2.VideoWriter(filepath, cv2.VideoWriter_fourcc(*'mp4v'), self.frame_rate, (width, height))

        for frame in frames:
            writer.write(frame)
        writer.release()

        duration = (video_end_time - start_time).total_seconds()
        file_size = os.path.getsize(filepath)
        resolution = f"{width}x{height}"

        self.storage_service.store_video_metadata({
            "path": filepath,
            "class_name": class_name,
            "start_time": start_time.isoformat(),
            "duration": duration,
            "frame_count": len(frames),
            "size": file_size,
            "resolution": resolution,
            "storage_type": "LOCAL"
        })

        self.frame_buffer[topic] = []
        logger.info(f"Video saved and metadata stored: {filepath}")