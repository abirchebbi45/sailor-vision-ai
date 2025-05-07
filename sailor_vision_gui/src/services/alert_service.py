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
        """Retrieve all alerts"""
        session = get_session()
        try:
            alerts = session.query(Alert).order_by(Alert.timestamp.desc()).all()
            return alerts
        except SQLAlchemyError as e:
            logger.error(f"Error while retrieving alerts: {str(e)}")
            return []
        finally:
            close_session(session)
    
    def get_unacknowledged_alerts(self):
        """Retrieve unacknowledged alerts"""
        session = get_session()
        try:
            alerts = session.query(Alert).filter(
                Alert.is_acknowledged == False,
                Alert.is_archived == False
            ).order_by(Alert.timestamp.desc()).all()
            return alerts
        except SQLAlchemyError as e:
            logger.error(f"Error while retrieving unacknowledged alerts: {str(e)}")
            return []
        finally:
            close_session(session)
    
    def get_alert_history(self):
        """Retrieve the history of acknowledged alerts"""
        session = get_session()
        try:
            alerts = (
                session.query(Alert)
                .options(joinedload(Alert.camera))
                .filter(Alert.is_acknowledged == True)
                .order_by(Alert.timestamp.desc())
                # .limit(20)
                .all()
            )
            return alerts
        except SQLAlchemyError as e:
            logger.error(f"Error while retrieving alert history: {str(e)}")
            return []
        finally:
            close_session(session)
    
    def get_alert(self, alert_id):
        """Retrieve a specific alert by ID"""
        session = get_session()
        try:
            alert = (
                session.query(Alert)
                .options(joinedload(Alert.camera))
                .filter(Alert.id == alert_id)
                .first()
            )
            return alert
        except SQLAlchemyError as e:
            logger.error(f"Error while retrieving alert {alert_id}: {str(e)}")
            return None
        finally:
            close_session(session)
    
    def acknowledge_alert(self, alert_id, user_id=None):
        """Acknowledge an alert"""
        session = get_session()
        try:
            alert = session.query(Alert).filter(Alert.id == alert_id).first()
            if not alert:
                logger.warning(f"Alert {alert_id} not found for acknowledgment")
                return False
            
            alert.is_acknowledged = True
            alert.acknowledged_by = user_id
            alert.acknowledged_at = datetime.now()
            
            session.commit()
            logger.info(f"Alert {alert_id} successfully acknowledged")
            return True
        except SQLAlchemyError as e:
            logger.error(f"Error while acknowledging alert {alert_id}: {str(e)}")
            session.rollback()
            return False
        finally:
            close_session(session)
    
    def archive_alert(self, alert_id):
        """Archive an alert"""
        session = get_session()
        try:
            alert = session.query(Alert).filter(Alert.id == alert_id).first()
            if not alert:
                logger.warning(f"Alert {alert_id} not found for archiving")
                return False
            
            alert.is_archived = True
            
            session.commit()
            logger.info(f"Alert {alert_id} successfully archived")
            return True
        except SQLAlchemyError as e:
            logger.error(f"Error while archiving alert {alert_id}: {str(e)}")
            session.rollback()
            return False
        finally:
            close_session(session)
    
    def create_alert(self, alert_data):
        """Create a new alert"""
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
            
            logger.info(f"[ALERT SAVED] ID: {alert.id}, Type: {alert.type}, Message: {alert.message}")

            return alert
        except SQLAlchemyError as e:
            logger.error(f"Error while creating alert: {str(e)}")
            session.rollback()
            return None
        finally:
            close_session(session)

    def save_alert_notes(self, alert_id, notes):
        session = get_session()
        try:
            alert = session.query(Alert).filter_by(id=alert_id).first()
            if alert:
                alert.notes = notes
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to save notes: {e}")
            return False
        finally:
            close_session(session)

    def batch_acknowledge_alerts(self, alert_ids):
        """Acknowledge multiple alerts in a single transaction."""
        session = get_session()
        try:
            session.query(Alert).filter(Alert.id.in_(alert_ids)).update(
                {
                    Alert.is_acknowledged: True,
                    Alert.acknowledged_at: datetime.now()
                },
                synchronize_session=False
            )
            session.commit()
            logger.info(f"Successfully acknowledged {len(alert_ids)} alerts.")
        except Exception as e:
            session.rollback()
            logger.error(f"Error while acknowledging alerts: {e}")
        finally:
            close_session(session)
    
    def process_yolo_detection(self, alert_data):
        """Process YOLO detections and create alerts"""
        try:
            if not alert_data.get('detections'):
                return False

            session = get_session()
            try:
                camera = session.query(Camera).filter(Camera.is_active == True).first()
                if not camera:
                    logger.error("No active camera found!")
                    return False
                
                camera_id = camera.id
                
                for detection in alert_data['detections']:
                    try:
                        class_mapping = {
                            "swimmer": AlertType.UNAUTHORIZED_SWIMMER.value,
                            "swimmer with life jacket": AlertType.SAFETY_COMPLIANT_SWIMMER.value,
                            "boat": AlertType.VESSEL_DETECTED.value,
                            "life jacket": AlertType.LIFE_JACKET_DETECTED.value,
                        }

                        detection_class = detection['class']
                        alert_type = class_mapping.get(detection_class, AlertType.GENERAL_DETECTION.value)

                        alert = Alert(
                            type=alert_type,
                            camera_id=camera_id,
                            message=f"{detection['class']} detected (Confidence: {detection['confidence']:.2f})",
                            timestamp=datetime.fromtimestamp(float(detection['timestamp'])),
                            detection_class=detection['class'],
                            image_data=str(detection.get('bbox', 'No position'))  # Added bbox info
                        )
                        
                        session.add(alert)
                        logger.info(f"Added an alert: {detection['class']}")
                    except Exception as e:
                        logger.error(f"Error while adding a detection: {e}")
                
                session.commit()
                logger.info(f"Successfully committed {len(alert_data['detections'])} detections")
                return True
            except Exception as e:
                session.rollback()
                logger.error(f"Database error: {e}")
                return False
            finally:
                close_session(session)

        except Exception as e:
            logger.error(f"Error processing detections: {str(e)}")
            return False