from PyQt5.QtCore import QObject, pyqtSignal
from threading import Thread
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2

class ROSImageBridge(QObject):
    image_received = pyqtSignal(object)  # Signal containing an OpenCV image

    def __init__(self):
        super().__init__()
        self.bridge = CvBridge()

    def start(self):
        """Initialize the ROS node and subscribe to the image topic"""
        try:
            rclpy.init(args=None)
        except RuntimeError:
            # ROS already initialized, continue
            pass
            
        self.node = Node("ros_image_bridge_node")
        # Ensure the topic name matches the one published by YoloNode
        self.subscription = self.node.create_subscription(
            Image, 
            '/yolo/image_raw',  # Ensure this name matches the published topic
            self.callback, 
            10
        )
        print(f"Subscribed to /yolo/image_raw")
        
        self.thread = Thread(target=rclpy.spin, args=(self.node,), daemon=True)
        self.thread.start()

    def stop(self):
        """Clean up ROS resources"""
        if hasattr(self, 'node'):
            self.node.destroy_node()
            if self.thread.is_alive():
                # Properly stop the thread
                rclpy.shutdown()
                self.thread.join(timeout=1.0)

    def callback(self, msg):
        """Callback function to process incoming ROS image messages"""
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
            self.image_received.emit(frame)
        except Exception as e:
            print(f"Error during image conversion: {e}")
