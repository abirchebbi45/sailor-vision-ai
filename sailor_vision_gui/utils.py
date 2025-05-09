import os
import cv2
import hashlib
import logging
import datetime
from PyQt5.QtCore import QThread, pyqtSignal, QDateTime, Qt
from PyQt5.QtGui import QImage, QPixmap
import jwt
from bcrypt import hashpw, gensalt, checkpw
import enum 

logger = logging.getLogger(__name__)

# JWT Secret Key for token generation/validation
JWT_SECRET = os.getenv("JWT_SECRET", "sailorvision_secret_key")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION = 24 * 60 * 60  # 24 hours in seconds

def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return hashpw(password.encode('utf-8'), gensalt()).decode('utf-8')

def verify_password(provided_password: str, stored_hash: str) -> bool:
    """Verify a password against a stored hash"""
    try:
        return checkpw(provided_password.encode('utf-8'), stored_hash.encode('utf-8'))
    except Exception as e:
        logger.error(f"Error verifying password : {e}")
        return False

def generate_token(user_id, username, role):
    """Generate a JWT token for user authentication"""
    payload = {
        "user_id": user_id,
        "username": username,
        "role": role.value if isinstance(role, enum.Enum) else role,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)  # Token valid for 1 hour
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_token(token):
    """Verify a JWT token and return the payload"""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        logger.warning("Token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        return None

def format_datetime(dt):
    """Format a datetime object for display"""
    if not dt:
        return ""
    return dt.strftime("%d/%m/%Y %H:%M:%S")

def format_relative_time(dt):
    """Format a datetime as a relative time string (e.g., "2 mins ago")"""
    if not dt:
        return ""
    
    now = datetime.datetime.now()
    diff = now - dt
    
    if diff.days > 0:
        return f"{diff.days} days ago"
    elif diff.seconds >= 3600:
        hours = diff.seconds // 3600
        return f"{hours} hours ago"
    elif diff.seconds >= 60:
        minutes = diff.seconds // 60
        return f"{minutes} mins ago"
    else:
        return f"{diff.seconds} secs ago"
""" 
def cv_image_to_qt(cv_img):
    Convert OpenCV image to QPixmap for display in Qt
    if cv_img is None:
        return QPixmap()
    
    # Convert from BGR to RGB
    rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
    h, w, ch = rgb_image.shape
    bytes_per_line = ch * w
    
    # Create QImage from data
    qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
    return QPixmap.fromImage(qt_image) """

""" class VideoThread(QThread):
    Thread for processing video frames
    update_frame = pyqtSignal(QPixmap)
    detection_result = pyqtSignal(list)
    error = pyqtSignal(str)
    
    def __init__(self, camera_url):
        super().__init__()
        self.camera_url = camera_url
        self.running = False
    
    def run(self):
        self.running = True
        cap = cv2.VideoCapture(self.camera_url)
        
        if not cap.isOpened():
            self.error.emit(f"Could not open video stream: {self.camera_url}")
            return
        
        while self.running:
            ret, frame = cap.read()
            if not ret:
                self.error.emit("Error reading frame from video stream")
                break
            
            # Example detection (in reality, this would call your detection service)
            detections = self.detect_objects(frame)
            
            # Draw detection boxes
            for detection in detections:
                x, y, w, h, label, confidence = detection
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.putText(frame, f"{label}: {confidence:.2f}", 
                           (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            # Convert to pixmap and emit
            pixmap = cv_image_to_qt(frame)
            self.update_frame.emit(pixmap)
            
            # Also emit detection results for other components to use
            self.detection_result.emit(detections)
            
            # Sleep a bit to control frame rate
            self.msleep(30)
        
        cap.release()
    
    def detect_objects(self, frame):
        Detect objects in frame (placeholder)
        # This is a placeholder. In a real application, you would:
        # 1. Use a pre-trained model (like YOLO, SSD, etc.) to detect vessels
        # 2. Return the detection results 
        
        # For now, return a dummy detection
        return [
            [100, 100, 200, 100, "boat", 0.92],
            [400, 200, 150, 80, "boat", 0.85]
        ]
    
    def stop(self):
        Stop the video thread
        self.running = False
        self.wait() """
