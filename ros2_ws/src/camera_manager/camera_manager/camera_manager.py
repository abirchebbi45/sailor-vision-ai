# camera_manager/camera_manager/camera_manager.py
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import glob
import json

class CameraManager(Node):
    def __init__(self):
        super().__init__('camera_manager')
        self.pub = self.create_publisher(String, '/camera/list', 10)
        self.timer = self.create_timer(1.0, self.publish_camera_list)
        self.get_logger().info("CameraManager démarré, publication de /camera/list toutes les 5s")

    def publish_camera_list(self):
        # Recherche tous les périphériques video*
        devices = sorted(glob.glob('/dev/video*'))
        msg = String()
        msg.data = json.dumps({'cameras': devices})
        self.pub.publish(msg)
        self.get_logger().info(f"Published cameras: {devices}")

def main(args=None):
    rclpy.init(args=args)
    node = CameraManager()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
