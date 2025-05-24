# camera_manager/camera_manager/camera_publisher.py
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
import json

class CameraPublisher(Node):
    def __init__(self):
        super().__init__('camera_publisher')
        self.bridge = CvBridge()
        self._publisher_map = {}  # topic → Publisher
        self._caps       = {}  # device → VideoCapture
        self.create_subscription(
            String,
            '/camera/list',
            self.cb_camera_list,
            10
        )
        self.get_logger().info('CameraPublisher démarré, attente de /camera/list')

    def cb_camera_list(self, msg):
        data = json.loads(msg.data)
        devices = data.get('cameras', [])
        # Ajouter de nouveaux devices
        for dev in devices:
            if dev not in self._caps:
                cap = cv2.VideoCapture(dev)
                if cap.isOpened():
                    self._caps[dev] = cap
                    topic = f'/camera/{dev.split("/")[-1]}/image_raw'
                    pub   = self.create_publisher(Image, topic, 10)
                    self._publisher_map[dev] = pub
                    # Timer pour publier 30 FPS
                    self.create_timer(1/30.0, lambda d=dev: self.publish_frame(d))
                    self.get_logger().info(f'Publication du flux {dev} → {topic}')
                else:
                    self.get_logger().warning(f"Impossible d'ouvrir {dev}")
        # Supprimer les devices disparus
        to_remove = [d for d in self._caps if d not in devices]
        for d in to_remove:
            self.get_logger().info(f"Arrêt flux {d}")
            self._caps[d].release()
            del self._caps[d]
            del self._publisher_map[d]

    def publish_frame(self, dev):
        cap = self._caps.get(dev)
        if not cap:
            return
        ret, frame = cap.read()
        if not ret:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            return
        msg = self.bridge.cv2_to_imgmsg(frame, encoding='bgr8')
        self._publisher_map[dev].publish(msg)

def main(args=None):
    rclpy.init(args=args)
    node = CameraPublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
