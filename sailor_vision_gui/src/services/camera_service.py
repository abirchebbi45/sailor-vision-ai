import logging
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from datetime import datetime

from database import get_session, close_session
from models import Camera
from utils import hash_password

logger = logging.getLogger(__name__)

class CameraService:
    def __init__(self, db_session):
        self.db_session = db_session

    def get_all_cameras(self):
        """Fetch all cameras from the database, including inactive ones."""
        return self.db_session.query(Camera).all()

    def get_active_cameras(self):
        """Fetch only active cameras from the database."""
        return self.db_session.query(Camera).filter(Camera.is_active == True).all()

    def add_camera(self, camera_data):
        """Add a new camera to the database."""
        camera_data.pop("username", None)  # Remove username if present
        camera_data.pop("password", None)  # Remove password if present
        new_camera = Camera(**camera_data)
        self.db_session.add(new_camera)
        self.db_session.commit()
        return new_camera

    def update_camera(self, camera_id, updated_data):
        """Update an existing camera."""
        camera = self.db_session.query(Camera).filter(Camera.id == camera_id).first()
        if camera:
            for key, value in updated_data.items():
                setattr(camera, key, value)
            self.db_session.commit()
        return camera

    def delete_camera(self, camera_id):
        """Delete a camera (soft delete by setting is_active to False)."""
        camera = self.db_session.query(Camera).filter(Camera.id == camera_id).first()
        if camera:
            camera.is_active = False
            self.db_session.commit()
        return camera

    def set_camera_active(self, camera_id, active=True):
        """Set camera is_active status."""
        camera = self.db_session.query(Camera).filter(Camera.id == camera_id).first()
        if camera:
            camera.is_active = active
            self.db_session.commit()
            self.db_session.flush()  # Ajouté pour forcer la synchro immédiate
        return camera
    
    def set_cameras_active(self, camera_ids, active=True):
        """Set is_active status for multiple cameras at once."""
        try:
            if not camera_ids:
                return 0  # Rien à mettre à jour
                
            # Mise à jour groupée pour de meilleures performances
            result = self.db_session.query(Camera).filter(Camera.id.in_(camera_ids)).update(
                {"is_active": active}, synchronize_session=False
            )
            self.db_session.commit()
            self.db_session.flush()  # Forcer la synchro immédiate
            
            logger.info(f"Mise à jour groupée de {result} caméras avec statut active={active}")
            return result
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour groupée des caméras: {e}")
            self.db_session.rollback()
            return 0
