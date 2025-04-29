# ros_image_listener.py
from PyQt5.QtCore import QObject, pyqtSignal
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import logging

logger = logging.getLogger(__name__)

class ROSImageBridge(QObject):
    image_received = pyqtSignal(object)

    def __init__(self, node):
        super().__init__()
        self.bridge = CvBridge()
        node.create_subscription(
            Image,
            '/yolo/image_raw',
            self.callback,
            10
        )

    def callback(self, msg):
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
            self.image_received.emit(frame)
        except Exception as e:
            logger.error(f"ROSImageBridge.callback error: {e}")
