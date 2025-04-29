# Fichier: yolo_node.py

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import String
from cv_bridge import CvBridge
from ultralytics import YOLO
import cv2
import json

class YoloNode(Node):
    def __init__(self):
        super().__init__('yolo_publisher')
        self.publisher_ = self.create_publisher(Image, '/yolo/image_raw', 10)
        self.alert_publisher = self.create_publisher(String, '/yolo/alerts', 10)
        self.bridge = CvBridge()
        self.model = YOLO("/home/abirc240/Desktop/sailor-vision-ai/model/yolov8_best.pt")
        print("CLASSES DU MODÈLE :", self.model.names)

        self.timer = self.create_timer(1 / 30.0, self.timer_callback)
        self.cap = cv2.VideoCapture('/home/abirc240/Desktop/sailor-vision-ai/testing_video/Swim_video_with_life Jacket.mp4')

        self.confidence_threshold = 0.2
        self.alert_classes = self.model.names.values() 

        if not self.cap.isOpened():
            self.get_logger().error('Unable to open video source')
        else:
            self.get_logger().info('Video source connected successfully')
            self.get_logger().info(f"Model classes (manually overridden): {self.model.names}")

    def timer_callback(self):
        ret, frame = self.cap.read()
        if not ret:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self.cap.read()
            if not ret:
                self.get_logger().warn('Unable to read video')
                return
        print("Frame read successfully")

        results = self.model.predict(frame, verbose=False)
        annotated = results[0].plot()
        msg = self.bridge.cv2_to_imgmsg(annotated, encoding='bgr8')
        self.publisher_.publish(msg)
        print("Image published successfully")

        self.process_detections(results[0], frame)

    def process_detections(self, result, frame):
        detections = []
        current_time = self.get_clock().now().to_msg()
        
        if result.boxes:
            for box in result.boxes:
                if box.conf.item() > self.confidence_threshold:
                    detections.append({
                        'class': self.model.names[int(box.cls.item())],
                        'confidence': round(float(box.conf.item()), 4),
                        'timestamp': f"{current_time.sec}.{current_time.nanosec}",
                        'bbox': [round(float(x), 2) for x in box.xyxy[0].tolist()]
                    })

            if detections:
                alert_msg = String()
                alert_msg.data = json.dumps({
                    'detections': detections,
                    'frame_width': frame.shape[1],
                    'frame_height': frame.shape[0]
                })
                self.alert_publisher.publish(alert_msg)
                self.get_logger().info(f"Published {len(detections)} detections")

def main(args=None):
    rclpy.init(args=args)
    node = YoloNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
