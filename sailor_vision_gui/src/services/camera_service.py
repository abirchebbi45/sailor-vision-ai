from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from datetime import datetime
import logging

from database import get_session, close_session
from models import Camera
from src.services.pending_camera_manager import pending_camera_manager

logger = logging.getLogger(__name__)

class CameraService:
    def __init__(self, db_session):
        self.db_session = db_session

    def get_all_cameras(self):
        """Get all active cameras (excludes soft deleted)."""
        try:
            cameras = self.db_session.query(Camera).filter(
                Camera.deleted_at.is_(None)
            ).all()
            return cameras
        except Exception as e:
            logger.error(f"Error fetching active cameras: {e}")
            return []
    
    def get_all_cameras_including_deleted(self):
        """Get all cameras including soft deleted ones."""
        try:
            cameras = self.db_session.query(Camera).all()
            return cameras
        except Exception as e:
            logger.error(f"Error fetching all cameras: {e}")
            return []
    
    def get_deleted_cameras(self):
        """Get only soft deleted cameras."""
        try:
            cameras = self.db_session.query(Camera).filter(
                Camera.deleted_at.isnot(None)
            ).all()
            return cameras
        except Exception as e:
            logger.error(f"Error fetching deleted cameras: {e}")
            return []

    def get_active_cameras(self):
        """Fetch only active cameras from the database."""
        return self.db_session.query(Camera).filter(Camera.is_active == True).all()

    def add_camera(self, camera_data):
        """Add a new camera to the database."""
        try:
            camera_data.pop("username", None)  # Remove username if present
            camera_data.pop("password", None)  # Remove password if present
            new_camera = Camera(**camera_data)
            self.db_session.add(new_camera)
            self.db_session.commit()
            logger.info(f"Added new camera: {new_camera.name} (ID: {new_camera.id})")
            return new_camera
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error adding camera: {e}")
            return None

    def update_camera(self, camera_id, updated_data):
        """Update an existing camera."""
        try:
            camera = self.db_session.query(Camera).filter(Camera.id == camera_id).first()
            if not camera:
                logger.warning(f"Camera not found for update: ID {camera_id}")
                return False
                
            # Update camera fields
            for key, value in updated_data.items():
                if hasattr(camera, key):
                    setattr(camera, key, value)
            
            self.db_session.commit()
            logger.info(f"Updated camera: {camera.name} (ID: {camera.id})")
            return True
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error updating camera: {e}")
            return False

    def delete_camera(self, camera_id):
        """Delete a camera from the database (HARD DELETE - not recommended)."""
        try:
            camera = self.db_session.query(Camera).filter(Camera.id == camera_id).first()
            if camera:
                self.db_session.delete(camera)
                self.db_session.commit()
                logger.info(f"Hard deleted camera ID: {camera_id}")
                return True
            return False
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error deleting camera: {e}")
            return False
    
    def soft_delete_camera(self, camera_id):
        """Soft delete a camera (preserves historical data)."""
        try:
            camera = self.db_session.query(Camera).filter(Camera.id == camera_id).first()
            if camera:
                camera.soft_delete()
                self.db_session.commit()
                logger.info(f"Soft deleted camera ID: {camera_id} ({camera.name})")
                return True
            return False
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error soft deleting camera: {e}")
            return False
    
    def restore_camera(self, camera_id):
        """Restore a soft deleted camera."""
        try:
            camera = self.db_session.query(Camera).filter(
                Camera.id == camera_id,
                Camera.deleted_at.isnot(None)
            ).first()
            if camera:
                camera.restore()
                self.db_session.commit()
                logger.info(f"Restored camera ID: {camera_id} ({camera.name})")
                return True
            return False
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error restoring camera: {e}")
            return False

    def set_camera_active(self, camera_id, active=True):
        """Set a camera's active status."""
        try:
            camera = self.db_session.query(Camera).filter(Camera.id == camera_id).first()
            if camera:
                camera.is_active = active
                self.db_session.commit()
                logger.info(f"Set camera {camera_id} active status to {active}")
                return True
            return False
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error setting camera active status: {e}")
            return False
    
    def set_cameras_active(self, camera_ids, active=True):
        """Set multiple cameras' active status at once."""
        if not camera_ids:
            return False
            
        try:
            cameras = self.db_session.query(Camera).filter(Camera.id.in_(camera_ids)).all()
            for camera in cameras:
                camera.is_active = active
            
            self.db_session.commit()
            logger.info(f"Set {len(cameras)} cameras to active={active}")
            return True
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error setting multiple cameras active status: {e}")
            return False

    def get_camera_by_device_path(self, device_path):
        """Get a camera by its device path."""
        try:
            camera = self.db_session.query(Camera).filter(Camera.ip_address == device_path).first()
            return camera
        except Exception as e:
            logger.error(f"Error getting camera by device path: {e}")
            return None
    
    def sync_with_pending_cameras(self):
        """
        Synchronize the database with pending cameras.
        Returns list of already-approved devices that were removed from pending list.
        """
        approved_devices = []
        try:
            # Get all device paths from approved cameras
            approved_paths = [cam.ip_address for cam in self.get_all_cameras() if cam.ip_address]
            
            # Get pending cameras
            pending_cameras = pending_camera_manager.get_pending_cameras()
            
            # Check for already approved devices in pending list
            for pending_camera in pending_cameras:
                if pending_camera.ip_address in approved_paths:
                    logger.info(f"Found already approved device in pending list: {pending_camera.ip_address}")
                    # Remove from pending list
                    pending_camera_manager.reject_camera(pending_camera.camera_id)
                    approved_devices.append(pending_camera.ip_address)
            
            logger.info(f"Synchronized {len(approved_devices)} already-approved devices from pending list")
            return approved_devices
        except Exception as e:
            logger.error(f"Error synchronizing with pending cameras: {e}")
            return []
            all_cameras = self.get_all_cameras()
            
            # Create comprehensive mapping of approved devices
            approved_device_paths = set()
            approved_name_patterns = set()
            
            for camera in all_cameras:
                if camera.ip_address:
                    approved_device_paths.add(camera.ip_address.strip())
                    
                    # Add variations for USB cameras
                    if "/dev/video" in camera.ip_address:
                        device_num = camera.ip_address.replace("/dev/video", "")
                        approved_device_paths.add(f"video{device_num}")
                        approved_device_paths.add(device_num)
                
                if camera.name:
                    approved_name_patterns.add(camera.name.strip())
                    
                    # Extract device patterns from names
                    import re
                    match = re.search(r'video(\d+)', camera.name)
                    if match:
                        device_num = match.group(1)
                        approved_name_patterns.add(f"video{device_num}")
                        approved_name_patterns.add(f"AutoCam video{device_num}")
            
            # Check pending cameras against approved list
            pending_cameras = pending_camera_manager.get_pending_cameras()
            for pending_camera in pending_cameras:
                device_approved = False
                
                # Check by ip_address
                if pending_camera.ip_address.strip() in approved_device_paths:
                    device_approved = True
                
                # Check by name patterns
                if not device_approved:
                    for pattern in approved_name_patterns:
                        if (pending_camera.name in pattern or 
                            pattern in pending_camera.name or
                            pending_camera.ip_address in pattern):
                            device_approved = True
                            break
                
                # Check by device number extraction
                if not device_approved and "/dev/video" in pending_camera.ip_address:
                    device_num = pending_camera.ip_address.replace("/dev/video", "")
                    for approved_path in approved_device_paths:
                        if device_num in approved_path:
                            device_approved = True
                            break
                
                if device_approved:
                    approved_devices.append(pending_camera.ip_address)
                    # Remove from pending list
                    try:
                        pending_camera_manager.remove_approved_camera(pending_camera.camera_id)
                    except Exception as e:
                        logger.error(f"Error removing approved camera: {e}")
            
            logger.info(f"Synchronized {len(approved_devices)} already-approved devices from pending list")
            return approved_devices
            
        except Exception as e:
            logger.error(f"Error synchronizing pending cameras: {e}")
            return []
