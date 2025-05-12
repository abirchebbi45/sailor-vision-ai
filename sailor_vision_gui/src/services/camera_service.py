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
