# ros_image_listener.py
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
import rclpy
from sensor_msgs.msg import Image
import cv2
from cv_bridge import CvBridge
import logging
from std_msgs.msg import String
import json
import traceback

logger = logging.getLogger(__name__)

class ROSImageBridge(QObject):
    image_received = pyqtSignal(object, str)  # cv_image, topic

    def __init__(self, ros_node):
        super().__init__()
        self.ros_node = ros_node
        self.bridge = CvBridge()
        self._subs = {}
        self._known_topics = set()
        self._error_count = {}  # Track errors per topic
        self._max_consecutive_errors = 5  # Max consecutive errors before unsubscribing

    def subscribe_to_yolo_topics(self, on_new_topic_cb=None):
        # Call this once to start dynamic subscription
        self._timer = QTimer()
        self._timer.timeout.connect(lambda: self._check_yolo_topics(on_new_topic_cb))
        self._timer.start(500)  # Reduced from 1000ms to 500ms for faster topic discovery
        
        # Force immediate check
        QTimer.singleShot(100, lambda: self._check_yolo_topics(on_new_topic_cb))

    def _check_yolo_topics(self, on_new_topic_cb):
        try:
            topics = self.ros_node.get_topic_names_and_types()
            for topic, types in topics:
                if topic.startswith('/yolo/') and topic.endswith('/image_raw') and 'sensor_msgs/msg/Image' in types:
                    if topic not in self._subs:
                        logger.info(f"Found new YOLO topic: {topic}, subscribing immediately")
                        sub = self.ros_node.create_subscription(
                            Image, topic, lambda msg, t=topic: self._on_image(msg, t), 10
                        )
                        self._subs[topic] = sub
                        self._error_count[topic] = 0  # Initialize error count
                        if on_new_topic_cb:
                            on_new_topic_cb(topic)
        except Exception as e:
            logger.error(f"Error checking YOLO topics: {e}")
            logger.error(traceback.format_exc())

    def _on_image(self, msg, topic):
        try:
            cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
            self.image_received.emit(cv_image, topic)
            self._error_count[topic] = 0  # Reset error count on success
        except Exception as e:
            self._error_count[topic] = self._error_count.get(topic, 0) + 1
            if self._error_count[topic] <= self._max_consecutive_errors:
                logger.error(f"Error processing image from {topic} ({self._error_count[topic]}/{self._max_consecutive_errors}): {e}")
            
            # If too many consecutive errors, unsubscribe to avoid flooding logs
            if self._error_count[topic] == self._max_consecutive_errors:
                logger.warning(f"Too many consecutive errors for {topic}, will stop logging errors")

    def get_active_topics(self):
        """
        Retourne la liste des topics YOLO actuellement actifs
        """
        return list(self._subs.keys())
    
    def get_subscription_count(self):
        """
        Retourne le nombre de topics YOLO actuellement abonnés
        """
        return len(self._subs)
    
    def is_topic_subscribed(self, topic):
        """
        Vérifie si un topic spécifique est abonné
        """
        return topic in self._subs
    
    def force_topic_check(self, on_new_topic_cb=None):
        """
        Force an immediate check of available YOLO topics
        Useful after a new camera is approved
        """
        logger.info("Force checking YOLO topics...")
        try:
            self._check_yolo_topics(on_new_topic_cb)
            
            # Also force a scan on the camera_manager to discover new devices
            try:
                if hasattr(self.ros_node, 'create_publisher'):
                    request_pub = self.ros_node.create_publisher(
                        String, '/camera/scan_request', 10
                    )
                    msg = String()
                    msg.data = json.dumps({"command": "scan_now"})
                    request_pub.publish(msg)
                    logger.info("Camera scan request sent from ROSImageBridge")
            except Exception as e:
                logger.error(f"Error requesting camera scan: {e}")
        
            logger.info(f"Current YOLO subscriptions: {len(self._subs)} topics: {list(self._subs.keys())}")
        except Exception as e:
            logger.error(f"Error during force topic check: {e}")
            logger.error(traceback.format_exc())
    
    def subscribe_to_specific_topic(self, topic, on_new_topic_cb=None):
        """
        S'abonne à un topic YOLO spécifique s'il n'est pas déjà abonné
        """
        try:
            if topic not in self._subs:
                logger.info(f"Attempting to subscribe to specific topic: {topic}")
                topics = self.ros_node.get_topic_names_and_types()
                for available_topic, types in topics:
                    if available_topic == topic and 'sensor_msgs/msg/Image' in types:
                        sub = self.ros_node.create_subscription(
                            Image, topic, lambda msg, t=topic: self._on_image(msg, t), 10
                        )
                        self._subs[topic] = sub
                        self._error_count[topic] = 0  # Initialize error count
                        logger.info(f"✅ Successfully subscribed to topic: {topic}")
                        if on_new_topic_cb:
                            on_new_topic_cb(topic)
                        return True
                logger.warning(f"Topic {topic} not found in available topics")
                return False
            else:
                logger.info(f"Topic {topic} already subscribed")
                return True
        except Exception as e:
            logger.error(f"Error subscribing to specific topic: {e}")
            logger.error(traceback.format_exc())
            return False
