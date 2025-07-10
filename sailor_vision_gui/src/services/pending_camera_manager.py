"""
Gestionnaire pour les caméras en attente d'approbation
Ce module gère les caméras détectées automatiquement qui sont en attente d'approbation par l'admin
"""

from PyQt5.QtCore import QObject, pyqtSignal
from dataclasses import dataclass
import json
import os
import time
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Path to the pending cameras JSON file
PENDING_CAMERAS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                   'shared', 'pending_cameras.json')

@dataclass
class PendingCamera:
    """Class to represent a pending camera"""
    camera_id: str
    name: str
    ip_address: str
    status: str = "pending"
    rtsp_url: str = None
    port: int = 554
    location: str = None
    camera_type: str = "Auto-detected"
    detected_at: datetime = None  # Fix: Add detected_at field
    
    def __post_init__(self):
        if self.detected_at is None:
            self.detected_at = datetime.now()  # Default to current time if not provided
    
    def to_dict(self):
        """Convert PendingCamera object to dictionary for JSON serialization"""
        return {
            'id': self.camera_id,
            'name': self.name,
            'device_path': self.ip_address,
            'status': self.status,
            'rtsp_url': self.rtsp_url,
            'port': self.port,
            'location': self.location,
            'camera_type': self.camera_type,
            'timestamp': self.detected_at.timestamp() if self.detected_at else None  # Serialize detected_at
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create PendingCamera object from dictionary"""
        detected_at = datetime.fromtimestamp(data['timestamp']) if 'timestamp' in data else None
        return cls(
            camera_id=data.get('id', ''),
            name=data.get('name', ''),
            ip_address=data.get('device_path', ''),
            status=data.get('status', 'pending'),
            rtsp_url=data.get('rtsp_url'),
            port=data.get('port', 554),
            location=data.get('location'),
            camera_type=data.get('camera_type', 'Auto-detected'),
            detected_at=detected_at  # Deserialize detected_at
        )

class PendingCameraManager(QObject):
    """
    Manager for pending cameras that handles the detection, approval, and rejection workflow.
    """
    # Signals
    new_camera_detected = pyqtSignal(str, str, str)  # camera_id, camera_name, camera_ip
    camera_approved = pyqtSignal(object)  # PendingCamera object
    camera_rejected = pyqtSignal(str)  # camera_id
    pending_cameras_updated = pyqtSignal(int)  # pending_count
    
    def __init__(self):
        super().__init__()
        # Initialize as empty list
        self.pending_cameras = []
        self.camera_detector = None
        self.data_file = PENDING_CAMERAS_PATH
        # Load any existing pending cameras
        self.load_pending_cameras()
    
    def set_camera_detector(self, camera_detector):
        """
        Set the camera detector reference for this manager.
        """
        self.camera_detector = camera_detector
    
    def load_pending_cameras(self):
        """
        Load pending cameras from the JSON file.
        """
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                
                # Ensure data is a list
                if not isinstance(data, list):
                    logger.error(f"Invalid pending cameras data format: {type(data)}. Resetting to empty list.")
                    self.pending_cameras = []
                    self.save_pending_cameras()  # Reset the file
                    return
                
                # Reset the list
                self.pending_cameras = []
                
                # Log the loaded data for debugging
                logger.debug(f"Loaded pending cameras data: {data}")
                
                # Load each camera as a PendingCamera object
                for item in data:
                    try:
                        camera = PendingCamera.from_dict(item)
                        self.pending_cameras.append(camera)
                        logger.debug(f"Successfully loaded pending camera: {camera.name} (ID: {camera.camera_id})")
                    except Exception as e:
                        logger.error(f"Error loading pending camera: {e}")
                
                logger.info(f"Loaded {len(self.pending_cameras)} pending cameras from {self.data_file}")
            else:
                logger.info(f"No pending cameras file found at {self.data_file}, starting with empty list")
                self.pending_cameras = []
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
                # Create empty file
                self.save_pending_cameras()
        except Exception as e:
            logger.error(f"Error loading pending cameras: {e}")
            self.pending_cameras = []
    
    def save_pending_cameras(self):
        """
        Save pending cameras to the JSON file.
        """
        try:
            # Make sure pending_cameras is a list
            if not isinstance(self.pending_cameras, list):
                logger.error("pending_cameras is not a list. Resetting to an empty list.")
                self.pending_cameras = []
            
            # Convert PendingCamera objects to dictionaries
            data = [camera.to_dict() for camera in self.pending_cameras]
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
            
            # Save to file
            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            # Emit signal with current count
            pending_count = len(self.pending_cameras)
            self.pending_cameras_updated.emit(pending_count)
            logger.info(f"Saved {pending_count} cameras to {self.data_file}")
            logger.debug(f"Saved data: {data}")
            
        except Exception as e:
            logger.error(f"Error saving pending cameras: {e}")
    
    def add_detected_camera(self, camera_id, name, device_path):
        """
        Add a newly detected camera to the pending list.
        
        Args:
            camera_id (str): Unique identifier for the camera.
            name (str): Name of the camera.
            device_path (str): Device path or IP address of the camera.
        """
        try:
            # Check if camera already exists in pending list
            for camera in self.pending_cameras:
                if camera.camera_id == camera_id or camera.ip_address == device_path:
                    logger.info(f"Camera already in pending list: {name} ({device_path})")
                    return
            
            # Create new PendingCamera object
            camera = PendingCamera(
                camera_id=camera_id,
                name=name,
                ip_address=device_path,
                detected_at=datetime.now()
            )
            
            # Add to list (ensure it's a list first)
            if not isinstance(self.pending_cameras, list):
                logger.error("pending_cameras is not a list. Resetting to an empty list.")
                self.pending_cameras = []
            
            self.pending_cameras.append(camera)
            
            # Save to file
            self.save_pending_cameras()
            
            # Emit signal with name and IP instead of object
            logger.info(f"Emitting new_camera_detected signal: {camera_id}, {name}, {device_path}")
            self.new_camera_detected.emit(camera_id, name, device_path)
            
            logger.info(f"Added new camera to pending list: {camera.name} ({camera.ip_address})")
            
        except Exception as e:
            logger.error(f"Error adding camera to pending list: {e}")
    
    def get_pending_cameras(self):
        """
        Get the list of pending cameras.
        """
        # Ensure it's a list
        if not isinstance(self.pending_cameras, list):
            logger.error("pending_cameras is not a list. Resetting to an empty list.")
            self.pending_cameras = []
            self.save_pending_cameras()
        
        logger.debug(f"Returning {len(self.pending_cameras)} pending cameras")
        for camera in self.pending_cameras:
            logger.debug(f"Pending camera: {camera.name} (ID: {camera.camera_id})")
        
        return self.pending_cameras
    
    def get_pending_count(self):
        """
        Get the number of pending cameras.
        """
        count = len(self.pending_cameras) if isinstance(self.pending_cameras, list) else 0
        logger.debug(f"Pending camera count: {count}")
        return count
    
    def approve_camera(self, camera_id):
        """
        Approve a pending camera.
        
        Returns the approved PendingCamera object or None if not found.
        """
        for camera in self.pending_cameras:
            if camera.camera_id == camera_id:
                camera.status = "approved"
                self.save_pending_cameras()
                self.camera_approved.emit(camera)
                return camera
        
        logger.warning(f"Camera not found for approval: {camera_id}")
        return None
    
    def reject_camera(self, camera_id):
        """
        Reject a pending camera.
        
        Returns True if camera was found and rejected, False otherwise.
        """
        for i, camera in enumerate(self.pending_cameras):
            if camera.camera_id == camera_id:
                del self.pending_cameras[i]
                self.save_pending_cameras()
                self.camera_rejected.emit(camera_id)
                return True
        
        logger.warning(f"Camera not found for rejection: {camera_id}")
        return False
    
    def remove_approved_camera(self, camera_id):
        """
        Remove an approved camera from the pending list.
        """
        for i, camera in enumerate(self.pending_cameras):
            if camera.camera_id == camera_id:
                del self.pending_cameras[i]
                self.save_pending_cameras()
                return True
        
        return False
    
    def cleanup_duplicates(self):
        """
        Clean up duplicates in the pending list.
        """
        if not isinstance(self.pending_cameras, list):
            self.pending_cameras = []
            return
        
        seen_ids = set()
        seen_devices = set()
        unique_cameras = []
        
        for camera in self.pending_cameras:
            # Skip if already seen this camera ID or device path
            if camera.camera_id in seen_ids or camera.ip_address in seen_devices:
                continue
            
            seen_ids.add(camera.camera_id)
            seen_devices.add(camera.ip_address)
            unique_cameras.append(camera)
            
            # Special handling for AutoCam pattern duplicates
            if "AutoCam" in camera.name:
                import re
                cam_match = re.search(r'video(\d+)', camera.name)
                if cam_match:
                    device_num = cam_match.group(1)
                    for other_camera in self.pending_cameras:
                        if other_camera != camera and "AutoCam" in other_camera.name:
                            other_match = re.search(r'video(\d+)', other_camera.name)
                            if other_match and other_match.group(1) == device_num:
                                # Mark this other camera to be skipped
                                seen_ids.add(other_camera.camera_id)
                                seen_devices.add(other_camera.ip_address)
        
        if len(unique_cameras) != len(self.pending_cameras):
            logger.info(f"Removed {len(self.pending_cameras) - len(unique_cameras)} duplicate cameras")
            self.pending_cameras = unique_cameras
            self.save_pending_cameras()
    
    def clear_old_cameras(self, days_old: int = 7):
        """Nettoyer les anciennes caméras rejetées (plus de X jours)"""
        from datetime import timedelta
        cutoff_date = datetime.now() - timedelta(days=days_old)
        
        to_remove = []
        for i, camera in enumerate(self.pending_cameras):
            if camera.status == "rejected" and camera.detected_at < cutoff_date:
                to_remove.append(i)
        
        # Remove in reverse order to avoid index shifting
        for i in reversed(to_remove):
            del self.pending_cameras[i]
        
        if to_remove:
            self.save_pending_cameras()
            logger.info(f"{len(to_remove)} old cameras removed")

# Create singleton instance
pending_camera_manager = PendingCameraManager()

