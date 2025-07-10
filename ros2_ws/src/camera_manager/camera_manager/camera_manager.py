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
        
        # Create standard timer for periodic publishing
        self.timer = self.create_timer(2.0, self.publish_camera_list)  # Reduced from 5s to 2s
        
        # Create subscriber for immediate scan requests
        self.scan_request_sub = self.create_subscription(
            String, 
            '/camera/scan_request', 
            self.handle_scan_request, 
            10
        )
        
        self.get_logger().info("CameraManager démarré, publication de /camera/list toutes les 2s et réponse aux demandes de scan")

    def publish_camera_list(self):
        """Publish list of detected camera devices"""
        # Recherche tous les périphériques video*
        devices = sorted(glob.glob('/dev/video*'))
        msg = String()
        msg.data = json.dumps({'cameras': devices})
        self.pub.publish(msg)
        self.get_logger().debug(f"Publié {len(devices)} caméras")
    
    def handle_scan_request(self, msg):
        """Handle immediate scan request"""
        try:
            data = json.loads(msg.data)
            if data.get("command") == "scan_now":
                self.get_logger().info("Demande de scan immédiat reçue")
                # Effectuer un scan immédiat et publier les résultats
                self.publish_camera_list()
        except Exception as e:
            self.get_logger().error(f"Erreur lors du traitement de la demande de scan : {e}")

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
