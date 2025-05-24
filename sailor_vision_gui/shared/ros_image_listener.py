# ros_image_listener.py
from PyQt5.QtCore import QObject, pyqtSignal
import rclpy
from sensor_msgs.msg import Image
import cv2
from cv_bridge import CvBridge
import logging

logger = logging.getLogger(__name__)

class ROSImageBridge(QObject):
    image_received = pyqtSignal(object, str)  # cv_image, topic

    def __init__(self, ros_node):
        super().__init__()
        self.ros_node = ros_node
        self.bridge = CvBridge()
        self._subs = {}
        self._known_topics = set()

    def subscribe_to_yolo_topics(self, on_new_topic_cb=None):
        # Call this once to start dynamic subscription
        from PyQt5.QtCore import QTimer
        self._timer = QTimer()
        self._timer.timeout.connect(lambda: self._check_yolo_topics(on_new_topic_cb))
        self._timer.start(1000)

    def _check_yolo_topics(self, on_new_topic_cb):
        topics = self.ros_node.get_topic_names_and_types()
        for topic, types in topics:
            if topic.startswith('/yolo/') and topic.endswith('/image_raw') and 'sensor_msgs/msg/Image' in types:
                if topic not in self._subs:
                    sub = self.ros_node.create_subscription(
                        Image, topic, lambda msg, t=topic: self._on_image(msg, t), 10
                    )
                    self._subs[topic] = sub
                    if on_new_topic_cb:
                        on_new_topic_cb(topic)

    def _on_image(self, msg, topic):
        try:
            cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
            self.image_received.emit(cv_image, topic)
        except Exception as e:
            logger.error(f"ROSImageBridge._on_image error: {e}")
