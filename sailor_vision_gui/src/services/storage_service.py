import os
import logging
from sqlalchemy.orm import Session
from datetime import datetime
from database import get_session
from models import Recording, Camera, StorageType

logger = logging.getLogger(__name__)

class StorageService:
    def __init__(self):
        """Initialize the storage service"""
        self.db_session = get_session()
        logger.info("Storage service initialized")

    def store_video_metadata(self, metadata):
        """
        Store video metadata in database
        
        Args:
            metadata (dict): Video metadata including path, class_name, start_time, duration, frame_count, size, resolution, storage_type
        """
        try:
            # Extract file path and verify its existence
            file_path = metadata.get("path")
            if not os.path.exists(file_path):
                logger.error(f"File does not exist: {file_path}")
                return None
                
            # Retrieve or create the camera (for testing, use the first camera)
            camera = self.db_session.query(Camera).first()
            if not camera:
                logger.warning("No camera found, using default camera ID 1")
                camera_id = 1
            else:
                camera_id = camera.id
            
            # Convert ISO date string to datetime object if necessary
            start_time = metadata.get("start_time")
            if isinstance(start_time, str):
                start_time = datetime.fromisoformat(start_time)
            
            # Create a new recording
            new_recording = Recording(
                camera_id=camera_id,
                file_path=file_path,
                start_time=start_time,
                end_time=datetime.now(),  # End time is now
                duration=metadata.get("duration", 0),
                size=metadata.get("size", 0),
                resolution=metadata.get("resolution", "1920x1080"),
                storage_type=StorageType[metadata.get("storage_type", "LOCAL")]
            )
            
            # Add to the database
            self.db_session.add(new_recording)
            self.db_session.commit()
            
            logger.info(f"Saved recording metadata to database: ID={new_recording.id}, Path={file_path}")
            return new_recording.id
            
        except Exception as e:
            logger.error(f"Error storing video metadata: {str(e)}")
            self.db_session.rollback()
            return None

    def get_recordings(self, limit=10, offset=0, camera_id=None, start_date=None, end_date=None, detection_class=None):
        """
        Récupérer les enregistrements selon les critères de filtrage
        
        Args:
            limit (int): Nombre maximum d'enregistrements à retourner
            offset (int): Décalage pour la pagination
            camera_id (int, optional): Filtrer par ID de caméra
            start_date (datetime, optional): Date de début pour le filtrage
            end_date (datetime, optional): Date de fin pour le filtrage
            detection_class (str, optional): Classe de détection associée
            
        Returns:
            list: Liste des enregistrements
        """
        try:
            query = self.db_session.query(Recording).order_by(Recording.start_time.desc())
            
            # Appliquer les filtres si spécifiés
            if camera_id:
                query = query.filter(Recording.camera_id == camera_id)
                
            if start_date:
                query = query.filter(Recording.start_time >= start_date)
                
            if end_date:
                query = query.filter(Recording.start_time <= end_date)
                
            # Limiter et décaler les résultats
            recordings = query.limit(limit).offset(offset).all()
            
            # Charger les relations (caméras) pour éviter les requêtes N+1
            for recording in recordings:
                _ = recording.camera
                
            return recordings
            
        except Exception as e:
            logger.error(f"Error fetching recordings: {str(e)}")
            return []

    def get_recording(self, recording_id):
        """
        Récupérer un enregistrement spécifique par ID
        
        Args:
            recording_id (int): ID de l'enregistrement
            
        Returns:
            Recording: L'objet d'enregistrement ou None
        """
        try:
            recording = self.db_session.query(Recording).filter(Recording.id == recording_id).first()
            if recording:
                # Charger la relation caméra
                _ = recording.camera
            return recording
        except Exception as e:
            logger.error(f"Error fetching recording {recording_id}: {str(e)}")
            return None

    def delete_recording(self, recording_id):
        """
        Supprimer un enregistrement de la base de données et le fichier associé
        
        Args:
            recording_id (int): ID de l'enregistrement à supprimer
            
        Returns:
            bool: True si supprimé avec succès, False sinon
        """
        try:
            recording = self.get_recording(recording_id)
            if not recording:
                logger.warning(f"Recording not found: {recording_id}")
                return False
                
            # Supprimer le fichier si existant
            if os.path.exists(recording.file_path):
                os.remove(recording.file_path)
                
            # Supprimer l'enregistrement de la base de données
            self.db_session.delete(recording)
            self.db_session.commit()
            
            logger.info(f"Recording deleted: {recording_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting recording {recording_id}: {str(e)}")
            self.db_session.rollback()
            return False

    def get_recordings_by_date(self, date):
        """
        Récupérer les enregistrements pour une date spécifique
        
        Args:
            date (datetime.date): Date pour laquelle récupérer les enregistrements
            
        Returns:
            list: Liste des enregistrements
        """
        try:
            # Convertir la date en datetime pour le début et la fin de la journée
            start_date = datetime.combine(date, datetime.min.time())
            end_date = datetime.combine(date, datetime.max.time())
            
            return self.get_recordings(limit=100, start_date=start_date, end_date=end_date)
            
        except Exception as e:
            logger.error(f"Error fetching recordings by date {date}: {str(e)}")
            return []