# Fichier: src/services/alert_service.py

import logging
import json
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError

from database import get_session, close_session
from models import Alert, AlertType, Camera
from sqlalchemy.orm import joinedload


logger = logging.getLogger(__name__)

class AlertService:
    def get_all_alerts(self):
        """Récupérer toutes les alertes"""
        session = get_session()
        try:
            alerts = session.query(Alert).order_by(Alert.timestamp.desc()).all()
            return alerts
        except SQLAlchemyError as e:
            logger.error(f"Erreur lors de la récupération des alertes: {str(e)}")
            return []
        finally:
            close_session(session)
    
    def get_unacknowledged_alerts(self):
        """Récupérer les alertes non confirmées"""
        session = get_session()
        try:
            alerts = session.query(Alert).filter(
                Alert.is_acknowledged == False,
                Alert.is_archived == False
            ).order_by(Alert.timestamp.desc()).all()
            return alerts
        except SQLAlchemyError as e:
            logger.error(f"Erreur lors de la récupération des alertes non confirmées: {str(e)}")
            return []
        finally:
            close_session(session)
    
    def get_alert_history(self):
        """Récupérer l'historique des alertes"""
        session = get_session()
        try:
            alerts = session.query(Alert).filter(
                Alert.is_acknowledged == True
            ).order_by(Alert.timestamp.desc()).limit(20).all()
            return alerts
        except SQLAlchemyError as e:
            logger.error(f"Erreur lors de la récupération de l'historique des alertes: {str(e)}")
            return []
        finally:
            close_session(session)
    
    def get_alert(self, alert_id):
        """Récupérer une alerte spécifique par ID"""
        session = get_session()
        try:
            alert = session.query(Alert).filter(Alert.id == alert_id).first()
            # on force le chargement de la relation camera AVANT de fermer la session
            alert = (
                session.query(Alert)
                        .options(joinedload(Alert.camera))
                        .filter(Alert.id == alert_id)
                        .first()
            )
            return alert
        except SQLAlchemyError as e:
            logger.error(f"Erreur lors de la récupération de l'alerte {alert_id}: {str(e)}")
            return None
        finally:
            close_session(session)
    
    def acknowledge_alert(self, alert_id, user_id=None):
        """Confirmer une alerte"""
        session = get_session()
        try:
            alert = session.query(Alert).filter(Alert.id == alert_id).first()
            if not alert:
                logger.warning(f"Alerte {alert_id} non trouvée pour confirmation")
                return False
            
            alert.is_acknowledged = True
            alert.acknowledged_by = user_id
            alert.acknowledged_at = datetime.now()
            
            session.commit()
            logger.info(f"Alerte {alert_id} confirmée avec succès")
            return True
        except SQLAlchemyError as e:
            logger.error(f"Erreur lors de la confirmation de l'alerte {alert_id}: {str(e)}")
            session.rollback()
            return False
        finally:
            close_session(session)
    
    def archive_alert(self, alert_id):
        """Archiver une alerte"""
        session = get_session()
        try:
            alert = session.query(Alert).filter(Alert.id == alert_id).first()
            if not alert:
                logger.warning(f"Alerte {alert_id} non trouvée pour archivage")
                return False
            
            alert.is_archived = True
            
            session.commit()
            logger.info(f"Alerte {alert_id} archivée avec succès")
            return True
        except SQLAlchemyError as e:
            logger.error(f"Erreur lors de l'archivage de l'alerte {alert_id}: {str(e)}")
            session.rollback()
            return False
        finally:
            close_session(session)
    
    def create_alert(self, alert_data):
        """Créer une nouvelle alerte"""
        session = get_session()
        try:
            alert = Alert(
                type=alert_data.get('type'),
                camera_id=alert_data.get('camera_id'),
                message=alert_data.get('message'),
                timestamp=datetime.now(),
                is_acknowledged=False,
                is_archived=False,
                image_data=alert_data.get('image_data')
            )
            
            session.add(alert)
            session.commit()
            
            logger.info(f"[ALERTE ENREGISTRÉE] ID: {alert.id}, Type: {alert.type}, Message: {alert.message}")

            return alert
        except SQLAlchemyError as e:
            logger.error(f"Erreur lors de la création de l'alerte: {str(e)}")
            session.rollback()
            return None
        finally:
            close_session(session)
    
    def process_yolo_detection(self, alert_data):
        """Traiter toutes les détections sans exception"""
        try:
            if not alert_data.get('detections'):
                return False

            session = get_session()
            try:
                camera = session.query(Camera).filter(Camera.is_active == True).first()
                if not camera:
                    logger.error("Aucune caméra active trouvée !")
                    return False
                
                camera_id = camera.id
                
                for detection in alert_data['detections']:
                    try:
                        alert = Alert(
                            type=AlertType.GENERAL_DETECTION.value,
                            camera_id=camera_id,
                            message=f"{detection['class']} détecté (Confiance: {detection['confidence']:.2f})",
                            timestamp=datetime.fromtimestamp(float(detection['timestamp'])),
                            detection_class=detection['class'],
                            image_data=str(detection.get('bbox', 'Aucune position'))  # Added bbox info
                        )
                        
                        session.add(alert)
                        logger.info(f"Ajout d'une alerte: {detection['class']}")
                    except Exception as e:
                        logger.error(f"Erreur lors de l'ajout d'une détection: {e}")
                
                session.commit()
                logger.info(f"Commit réussi pour {len(alert_data['detections'])} détections")
                return True
            except Exception as e:
                session.rollback()
                logger.error(f"Erreur DB: {e}")
                return False
            finally:
                close_session(session)

        except Exception as e:
            logger.error(f"Erreur traitement détections: {str(e)}")
            return False