# yolo_node.py
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
        super().__init__('yolo_node')

        self.bridge = CvBridge()
        self.model = YOLO("/home/abirc240/Desktop/sailor-vision-ai/model/yolov8_best.pt")
        self._yolo_publishers = {}  # topic_name → publisher
        self.alert_publisher = self.create_publisher(String, '/yolo/alerts', 10)
        self.confidence_threshold = 0.5
        
        self._camera_subs  = {}  # topic_name → subscription
        self.create_timer(1.0, self.update_camera_subscriptions)  # check every 1s

        self.get_logger().info('YOLO Node ready. Waiting for image streams on /camera/*/image_raw')
    
    def update_camera_subscriptions(self):
        topics = self.get_topic_names_and_types()
        for topic, types in topics:
            if topic.startswith('/camera/') and topic.endswith('/image_raw') and 'sensor_msgs/msg/Image' in types:
                if topic not in self._camera_subs:
                    self.get_logger().info(f"Subscribing to {topic}")
                    sub = self.create_subscription(
                        Image, topic, lambda msg, t=topic: self.image_callback(msg, t), 10
                    )
                    self._camera_subs[topic] = sub
        # Remove subscriptions for topics that disappeared
        to_remove = [t for t in self._camera_subs if t not in dict(topics)]
        for t in to_remove:
            self.get_logger().info(f"Unsubscribing from {t}")
            self._camera_subs[t].destroy()
            del self._camera_subs[t]

    def image_callback(self, msg, topic):
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        self.process_and_publish(frame, topic)

    def process_and_publish(self, frame, topic):
        results = self.model.predict(frame, verbose=False)
        annotated = results[0].plot()
        # --- Publish on /yolo/<videoX>/image_raw ---
        video_name = topic.split('/')[2]  # e.g. video12
        yolo_topic = f'/yolo/{video_name}/image_raw'
        if yolo_topic not in self._yolo_publishers:
            self._yolo_publishers[yolo_topic] = self.create_publisher(Image, yolo_topic, 10)
        msg = self.bridge.cv2_to_imgmsg(annotated, encoding='bgr8')
        self._yolo_publishers[yolo_topic].publish(msg)
        self.process_detections(results[0], frame, topic)

    def process_detections(self, result, frame, topic):
        detections = []
        current_time = self.get_clock().now().to_msg()
        if result.boxes:
            for box in result.boxes:
                if box.conf.item() > self.confidence_threshold:
                    detections.append({
                        'class': self.model.names[int(box.cls.item())],
                        'confidence': round(float(box.conf.item()), 4),
                        'timestamp': f"{current_time.sec}.{current_time.nanosec}",
                        'bbox': [round(float(x), 2) for x in box.xyxy[0].tolist()],
                        'source_topic': topic
                    })
        if detections:
            alert_msg = String()
            alert_msg.data = json.dumps({
                'detections': detections,
                'frame_width': frame.shape[1],
                'frame_height': frame.shape[0]
            })
            self.alert_publisher.publish(alert_msg)
            self.get_logger().info(f"Published {len(detections)} detections from {topic}")

def main(args=None):
    rclpy.init(args=args)
    node = YoloNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()