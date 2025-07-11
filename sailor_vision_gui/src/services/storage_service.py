import os
import logging
import uuid
from PyQt5.QtCore import QObject, pyqtSignal
from sqlalchemy.orm import Session
from datetime import datetime
from database import get_session, create_new_session, close_session
from models import Recording, Camera, StorageType, Settings

logger = logging.getLogger(__name__)

class StorageService(QObject):
    # Signal émis quand un nouvel enregistrement est ajouté
    recording_added = pyqtSignal(int)  # recording_id
    
    def __init__(self, db_session=None):
        """Initialize the storage service"""
        super().__init__()
        # Don't store a session, create new ones for each operation
        self.db_session = None
        logger.info("Storage service initialized")

    def store_video_metadata(self, metadata):
        """
        Store video metadata in database
        
        Args:
            metadata (dict): Video metadata including path, class_name, etc.
        
        Returns:
            int: ID of the created recording, or None if failed
        """
        session = create_new_session()
        try:
            # Extract file path and verify its existence
            file_path = metadata.get("path")
            if not os.path.exists(file_path):
                logger.error(f"File does not exist: {file_path}")
                return None
            
            # Trouver la caméra correspondante en fonction du nom ou de l'ID fournis
            camera = None
            camera_name = metadata.get("camera_name")
            
            if camera_name:
                camera = session.query(Camera).filter_by(name=f"AutoCam {camera_name}").first()
            
            # Si on n'a pas trouvé de caméra, utiliser la première disponible
            if not camera:
                camera = session.query(Camera).first()
                if not camera:
                    logger.warning("No camera found, using default camera ID 1")
                    camera_id = 1
                else:
                    camera_id = camera.id
            else:
                camera_id = camera.id
            
            # Convert ISO date string to datetime object if necessary
            start_time = metadata.get("start_time")
            if isinstance(start_time, str):
                start_time = datetime.fromisoformat(start_time)
                
            end_time = metadata.get("end_time")
            if isinstance(end_time, str):
                end_time = datetime.fromisoformat(end_time)
            
            # Create a new recording
            new_recording = Recording(
                camera_id=camera_id,
                file_path=file_path,
                name=metadata.get("class_name"),  # Use class_name for the name field
                start_time=start_time,
                end_time=end_time,
                duration=metadata.get("duration", 0),
                size=metadata.get("size", 0),
                resolution=metadata.get("resolution", "1920x1080"),
                storage_type=StorageType[metadata.get("storage_type", "LOCAL")]
            )
            
            # Add to the database
            session.add(new_recording)
            session.commit()
            
            logger.info(f"Saved recording metadata to database: ID={new_recording.id}, Name={new_recording.name}, Path={file_path}")
            
            # Émettre le signal pour notification
            self.recording_added.emit(new_recording.id)
            
            return new_recording.id
            
        except Exception as e:
            logger.error(f"Error storing video metadata: {str(e)}")
            session.rollback()
            return None
        finally:
            close_session(session)

    def get_recordings(self, limit=10, offset=0, camera_id=None, start_date=None, end_date=None, detection_class=None, search_term=None):
        """
        Récupérer les enregistrements selon les critères de filtrage
        
        Args:
            limit (int): Nombre maximum d'enregistrements à retourner
            offset (int): Décalage pour la pagination
            camera_id (int, optional): Filtrer par ID de caméra
            start_date (datetime, optional): Date de début pour le filtrage
            end_date (datetime, optional): Date de fin pour le filtrage
            detection_class (str, optional): Classe de détection associée
            search_term (str, optional): Termes de recherche dans le nom de l'enregistrement
            
        Returns:
            list: Liste des enregistrements
        """
        session = create_new_session()
        try:
            query = session.query(Recording).order_by(Recording.start_time.desc())
            
            # Appliquer les filtres si spécifiés
            if camera_id:
                query = query.filter(Recording.camera_id == camera_id)
                
            if start_date:
                query = query.filter(Recording.start_time >= start_date)
                
            if end_date:
                query = query.filter(Recording.start_time <= end_date)
                
            if search_term:
                # Recherche dans le nom de l'enregistrement
                search_pattern = f"%{search_term}%"
                query = query.filter(Recording.name.like(search_pattern))
                
            # Limiter et décaler les résultats
            recordings = query.limit(limit).offset(offset).all()
            
            # Charger les relations (caméras) pour éviter les requêtes N+1
            for recording in recordings:
                _ = recording.camera
                
            return recordings
            
        except Exception as e:
            logger.error(f"Error fetching recordings: {str(e)}")
            return []
        finally:
            close_session(session)

    def get_recording(self, recording_id):
        """
        Récupérer un enregistrement spécifique par ID
        
        Args:
            recording_id (int): ID de l'enregistrement
            
        Returns:
            Recording: L'objet d'enregistrement ou None
        """
        session = create_new_session()
        try:
            recording = session.query(Recording).filter(Recording.id == recording_id).first()
            if recording:
                # Charger la relation caméra
                _ = recording.camera
            return recording
        except Exception as e:
            logger.error(f"Error fetching recording {recording_id}: {str(e)}")
            return None
        finally:
            close_session(session)

    def delete_recording(self, recording_id):
        """
        Supprimer un enregistrement de la base de données et le fichier associé
        
        Args:
            recording_id (int): ID de l'enregistrement à supprimer
            
        Returns:
            bool: True si supprimé avec succès, False sinon
        """
        session = create_new_session()
        try:
            recording = self.get_recording(recording_id)
            if not recording:
                logger.warning(f"Recording not found: {recording_id}")
                return False
                
            # Supprimer le fichier si existant
            if os.path.exists(recording.file_path):
                os.remove(recording.file_path)
                
            # Supprimer l'enregistrement de la base de données
            session.delete(recording)
            session.commit()
            
            logger.info(f"Recording deleted: {recording_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting recording {recording_id}: {str(e)}")
            session.rollback()
            return False
        finally:
            close_session(session)

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

    def get_storage_type(self):
        """Retrieve the current storage type from the database or configuration"""
        session = create_new_session()
        try:
            # Example logic: Fetch storage type from settings table or configuration
            storage_setting = session.query(Settings).filter_by(key="storage_type").first()
            if storage_setting:
                return storage_setting.value
            return "Local"  # Default storage type
        except Exception as e:
            logger.error(f"Error retrieving storage type: {str(e)}")
            return "Local"  # Fallback to default
        finally:
            close_session(session)

    def get_storage_usage_percent(self):
        """Calculate and return the storage usage percentage"""
        try:
            # Example logic: Fetch total and used storage from the database or configuration
            total_storage = 1000  # Example total storage in GB
            used_storage = 250   # Example used storage in GB
            usage_percent = (used_storage / total_storage) * 100
            return usage_percent
        except Exception as e:
            logger.error(f"Error calculating storage usage percent: {str(e)}")
            return 0  # Fallback to 0% usage