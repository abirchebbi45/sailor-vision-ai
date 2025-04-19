import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
from ultralytics import YOLO
import cv2

class YoloNode(Node):
    def __init__(self):
        """
        Initializes the YOLO node, sets up the publisher, loads the YOLO model, 
        and connects to the video source.
        """
        super().__init__('yolo_publisher')
        self.publisher_ = self.create_publisher(Image, '/yolo/image_raw', 10)
        self.bridge = CvBridge()
        self.model = YOLO("/home/abirc240/Desktop/sailor-vision-ai/model/yolov8_best.pt")  # Change model if needed
        self.timer = self.create_timer(1/30.0, self.timer_callback)
        self.cap = cv2.VideoCapture('/home/abirc240/Desktop/sailor-vision-ai/testing_video/Swim_video_with_life Jacket.mp4')  # Set your path here
        if not self.cap.isOpened():
            self.get_logger().error('Unable to open video source')
        else:
            self.get_logger().info('Video source connected successfully')

    def timer_callback(self):
        """
        Reads frames from the video source, processes them with the YOLO model, 
        and publishes the annotated frames.
        """
        ret, frame = self.cap.read()
        if not ret:
            # Restart the video if desired
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self.cap.read()
            if not ret:  # If still no frame
                self.get_logger().warn('Unable to read video')
                return
        print("Frame read successfully")

        results = self.model.predict(frame, verbose=False)
        annotated = results[0].plot()
        msg = self.bridge.cv2_to_imgmsg(annotated, encoding='bgr8')
        self.publisher_.publish(msg)
        print("Image published successfully")

def main(args=None):
    """
    Main function to initialize and spin the YOLO node.
    """
    rclpy.init(args=args)
    node = YoloNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
