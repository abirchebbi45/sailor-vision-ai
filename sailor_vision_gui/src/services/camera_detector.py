"""
Camera Detector Service
Handles automatic camera detection from ROS and notifies the system about new cameras.
This separates the detection logic from the UI components.
"""

from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from std_msgs.msg import String as ROSString

from src.services.pending_camera_manager import pending_camera_manager
from database import create_new_session, close_session, init_db
from models import Camera
import json
import time
import logging

logger = logging.getLogger(__name__)

class CameraDetector(QObject):
    """
    Service responsible for detecting cameras and handling their registration
    with the pending_camera_manager.
    """
    
    # Signals
    new_camera_detected = pyqtSignal(str, str, str)  # camera_id, camera_name, camera_ip
    camera_disconnected = pyqtSignal(str)  # camera_id
    
    def __init__(self, ros_node=None):
        super().__init__()
        init_db()  # Ensure the database is initialized
        
        self.ros_node = ros_node
        self.detected_cameras = set()  # Track detected camera device paths
        self.approved_cameras = {}  # Maps IP address to camera objects
        self.refresh_timer = None  # Timer for refreshing approved cameras
        
        # Load approved cameras from the database
        self.refresh_approved_cameras()
        
        # Setup ROS subscription if a node is provided
        if ros_node:
            self.setup_ros_subscription()
        
        logger.info("CameraDetector service initialized")
    
    def setup_ros_subscription(self):
        """Set up ROS subscription for camera list detection."""
        if not self.ros_node:
            logger.warning("No ROS node provided, cannot subscribe to camera list")
            return
        
        try:
            self.ros_camera_sub = self.ros_node.create_subscription(
                ROSString, '/camera/list', self.handle_camera_list, 10
            )
            logger.info("Subscribed to /camera/list for camera detection")
        except Exception as e:
            logger.error(f"Failed to set up ROS subscription: {e}")
    
    def setup_timer(self):
        """Setup a timer for refreshing approved cameras."""
        if self.refresh_timer is None:
            self.refresh_timer = QTimer(self)
            self.refresh_timer.timeout.connect(self.refresh_approved_cameras)
            self.refresh_timer.start(60000)  # Refresh every minute
            logger.info("Camera detector refresh timer started")
    
    def refresh_approved_cameras(self):
        """Refresh the list of approved cameras from the database (excluding soft deleted)."""
        session = None
        try:
            session = create_new_session()
            # Query only cameras that are NOT soft deleted (deleted_at is NULL)
            cameras = session.query(Camera).filter(
                Camera.deleted_at.is_(None)
            ).all()
            
            # Store old approved cameras for comparison
            old_approved = set(self.approved_cameras.keys())
            self.approved_cameras = {}
            
            # Store current approved device paths
            approved_device_paths = set()
            
            for camera in cameras:
                if camera.ip_address:
                    self.approved_cameras[camera.ip_address] = camera
                    # Extract device path from camera name if it follows the pattern "AutoCam videoX"
                    if "AutoCam video" in camera.name:
                        video_num = camera.name.replace("AutoCam video", "").strip()
                        device_path = f"/dev/video{video_num}"
                        approved_device_paths.add(device_path)
            
            # Get all cameras (including soft deleted) to check what was removed
            all_cameras = session.query(Camera).all()
            soft_deleted_device_paths = set()
            
            for camera in all_cameras:
                if camera.deleted_at is not None and "AutoCam video" in camera.name:
                    # Handle names like "[DELETED] AutoCam video10"
                    name = camera.name
                    if name.startswith("[DELETED] "):
                        name = name.replace("[DELETED] ", "")
                    
                    if "AutoCam video" in name:
                        video_num = name.replace("AutoCam video", "").strip()
                        device_path = f"/dev/video{video_num}"
                        soft_deleted_device_paths.add(device_path)
            
            # Clean up detected_cameras: remove soft deleted and not approved devices
            # that are also not in pending list
            devices_to_remove = set()
            
            for device_path in self.detected_cameras:
                is_approved = device_path in approved_device_paths
                is_soft_deleted = device_path in soft_deleted_device_paths
                is_pending = self.is_device_in_pending_list(device_path)
                
                if is_soft_deleted or (not is_approved and not is_pending):
                    devices_to_remove.add(device_path)
                    logger.info(f"[CameraDetector] Will remove device from detected set: {device_path} (approved={is_approved}, soft_deleted={is_soft_deleted}, pending={is_pending})")
            
            # Remove the devices
            for device_path in devices_to_remove:
                self.detected_cameras.remove(device_path)
                logger.info(f"[CameraDetector] Removed device from detected set: {device_path}")
            
            logger.debug(f"Refreshed approved cameras: {len(cameras)} found (excluding soft deleted)")
        except Exception as e:
            logger.error(f"Error refreshing approved cameras: {e}")
        finally:
            if session:
                close_session(session)
    
    def is_device_in_pending_list(self, device_path):
        """Check if a device is in the pending cameras list."""
        try:
            pending_cameras = pending_camera_manager.get_pending_cameras()
            for pending_cam in pending_cameras:
                if pending_cam.get('device_path') == device_path:
                    return True
            return False
        except Exception as e:
            logger.error(f"Error checking pending list: {e}")
            return False
    
    def handle_camera_list(self, msg):
        """Handle the /camera/list ROS topic message."""
        try:
            data = json.loads(msg.data)
            devices = data.get('cameras', [])
            new_devices = []
            
            logger.info(f"[CameraDetector] Received camera list with {len(devices)} devices: {devices}")
            
            self.refresh_approved_cameras()  # Refresh approved cameras
            
            for dev in devices:
                dev = dev.strip()
                already_approved = self.is_device_approved(dev)
                already_detected = dev in self.detected_cameras
                
                logger.info(f"[CameraDetector] Checking device: {dev}")
                logger.info(f"[CameraDetector] Already approved: {already_approved}")
                logger.info(f"[CameraDetector] Already detected: {already_detected}")
                
                if not already_approved and not already_detected:
                    logger.info(f"[CameraDetector] ✅ New device to add: {dev}")
                    new_devices.append(dev)
                    # Add to detected devices set to avoid duplicates
                    self.detected_cameras.add(dev)
                else:
                    logger.info(f"[CameraDetector] ❌ Device {dev} skipped (approved={already_approved}, detected={already_detected})")
            
            if not new_devices:
                logger.info(f"[CameraDetector] No new devices to process")
                return
            
            for dev in new_devices:
                self.add_camera_to_pending_list(dev)
                logger.info(f"[CameraDetector] ✅ New camera detected and added: {dev}")
            
        except Exception as e:
            logger.error(f"Error handling camera list: {e}")
    
    def is_device_approved(self, device_path):
        """Check if a device is already approved."""
        device_path = device_path.strip()
        if device_path in self.approved_cameras:
            return True
        if "/dev/video" in device_path:
            device_num = device_path.replace("/dev/video", "")
            if f"video{device_num}" in self.approved_cameras or device_num in self.approved_cameras:
                return True
        return False
    
    def is_device_pending(self, device_path):
        """Check if a device is already in the pending camera list."""
        try:
            pending_cameras = pending_camera_manager.get_pending_cameras()
            for pending_camera in pending_cameras:
                if pending_camera.ip_address == device_path:
                    return True
            return False
        except Exception as e:
            logger.error(f"Error checking pending devices: {e}")
            return False
    
    def add_camera_to_pending_list(self, device_path):
        """
        Add a newly detected camera to the pending list.
        """
        try:
            # Generate a unique ID for the camera
            camera_id = f"autocam_{device_path.split('/')[-1]}_{int(time.time())}"
            
            # Create an automatic name for the camera
            camera_name = f"AutoCam {device_path.split('/')[-1]}"
            
            logger.info(f"[CameraDetector] Adding camera to pending list:")
            logger.info(f"  - ID: {camera_id}")
            logger.info(f"  - Name: {camera_name}")
            logger.info(f"  - Device: {device_path}")
            
            # Add to pending camera manager
            pending_camera_manager.add_detected_camera(
                camera_id=camera_id,
                name=camera_name,
                device_path=device_path
            )
            logger.info(f"[CameraDetector] ✅ Successfully added camera to pending list: {camera_name} ({device_path})")
        except Exception as e:
            logger.error(f"Error adding camera to pending list: {e}")
    
    def force_refresh(self):
        """Force a refresh of approved cameras and trigger an immediate camera scan."""
        logger.info("[CameraDetector] Force refresh triggered")
        self.refresh_approved_cameras()
        self.force_camera_scan()
        if self.refresh_timer is None:
            self.setup_timer()
    
    def force_camera_scan(self):
        """Force an immediate camera scan by requesting the ROS camera list."""
        try:
            if self.ros_node:
                # Create a ROS message to request an immediate camera scan
                from std_msgs.msg import String
                pub = self.ros_node.create_publisher(String, '/camera/scan_request', 10)
                msg = String()
                msg.data = json.dumps({"command": "scan_now"})
                pub.publish(msg)
                logger.info("[CameraDetector] Sent scan_now command to ROS camera_manager")
        except Exception as e:
            logger.error(f"Error during forced camera scan: {e}")

# Create singleton instance
camera_detector = CameraDetector()

# Set the camera detector in pending_camera_manager to avoid circular import
pending_camera_manager.set_camera_detector(camera_detector)