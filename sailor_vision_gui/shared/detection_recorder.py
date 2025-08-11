import os
import logging
import cv2
import json
import numpy as np
import uuid
from PyQt5.QtCore import QObject, QTimer, pyqtSignal
from sensor_msgs.msg import Image
from std_msgs.msg import String
from cv_bridge import CvBridge
from datetime import datetime
from src.services.storage_service import StorageService
from shared.ros_image_listener import ROSImageBridge

logger = logging.getLogger(__name__)

class DetectionRecorder(QObject):
    # Signal émis quand un nouvel enregistrement est créé
    recording_created = pyqtSignal(int)  # recording_id

    def __init__(self, node, output_dir="recordings", ros_bridge=None):
        super().__init__()
        self.node = node
        self.output_dir = output_dir
        self.bridge = CvBridge()
        
        # Stockage des trames
        self.frame_buffer = {}  # topic -> [frames]
        self.frame_count = {}  # topic -> count
        self.alert_count = {}  # topic -> count
        
        # État d'enregistrement
        self.recording = {}  # topic -> bool
        self.video_start_time = {}  # topic -> datetime
        self.detected_class_name = {}  # topic -> str
        self.frames_since_last_alert = {}  # topic -> count
        
        # Paramètres temporels
        self.frame_rate = 10  # fps
        self.max_frames_without_alert = 150  # 15 secondes après la dernière détection
        self.pre_record_buffer_size = 100  # 10 secondes à 10 FPS
        self.post_detection_frames = 50  # 5 secondes après la dernière détection
        self.incident_merge_threshold = 300  # 30 secondes - fusion des incidents proches
        self.max_recording_duration = 900  # 90 secondes maximum pour un enregistrement
        
        # Créer le répertoire de sortie s'il n'existe pas
        os.makedirs(output_dir, exist_ok=True)
        
        # Service de stockage pour les métadonnées
        self.storage_service = StorageService()
        
        # Topics pour les images de caméra et les détections
        self.camera_topics = {}  # camera_topic -> yolo_topic
        self.yolo_topics = {}  # yolo_topic -> camera_topic
        
        # Abonnements ROS
        self.subscribers = {}  # topic -> subscription
        self._subs = {}  # Fix: Initialize _subs dictionary for alert subscriptions
        self.alert_subscriber = None
        
        # Bridge ROS pour récupérer les images depuis le bridge partagé
        self.ros_bridge = ros_bridge
        if ros_bridge:
            self.ros_bridge.image_received.connect(self._on_image)
        
        # Timer pour vérifier l'état des enregistrements périodiquement
        self._timer = QTimer()
        self._timer.timeout.connect(self._check_recordings)
        self._timer.start(5000)  # Check every 5 seconds

        # Timer pour vérifier et terminer les enregistrements inactifs
        self._inactive_timer = QTimer()
        self._inactive_timer.timeout.connect(self.check_inactive_recordings)
        self._inactive_timer.start(10000)  # Check every 10 seconds
        
        # Abonnement aux alertes YOLO
        self.alert_subscriber = self.node.create_subscription(
            String, '/yolo/alerts', self._on_alert, 10
        )
        
        # S'abonner aux topics de caméra existants
        self._discover_camera_topics()
        logger.info("DetectionRecorder initialized and ready for recording")

    def _discover_camera_topics(self):
        """Découvre les topics de caméras disponibles et s'y abonne"""
        topics = self.node.get_topic_names_and_types()
        for topic, types in topics:
            if topic.startswith('/camera/') and topic.endswith('/image_raw') and 'sensor_msgs/msg/Image' in types:
                camera_name = topic.split('/')[-2]  # Extraire le nom de la caméra
                logger.info(f"Found camera topic: {topic}, subscribing for monitoring and fallback recording")
                # Mapper le topic de caméra au topic YOLO correspondant (prévu)
                yolo_topic = f'/yolo/{camera_name}/image_raw'
                self.camera_topics[topic] = yolo_topic
                self.yolo_topics[yolo_topic] = topic
                # S'abonner au topic de caméra pour le pré-enregistrement
                if topic not in self.subscribers:
                    self.subscribers[topic] = self.node.create_subscription(
                        Image, topic, lambda msg, t=topic: self._on_camera_image(msg, t), 10
                    )

    def _on_image(self, cv_image, topic):
        """Callback pour traiter les images provenant du ROSImageBridge"""
        try:
            # Ajouter l'image au buffer du topic correspondant
            if topic not in self.frame_buffer:
                self.frame_buffer[topic] = []
                self.frame_count[topic] = 0
                self.alert_count[topic] = 0
                self.recording[topic] = False
                self.frames_since_last_alert[topic] = 0

            self.frame_buffer[topic].append(cv_image.copy())
            self.frame_count[topic] += 1

            # Limiter la taille du buffer pour éviter la surcharge mémoire
            if not self.recording.get(topic, False):
                # Si pas en cours d'enregistrement, garder uniquement le pre-record buffer
                while len(self.frame_buffer[topic]) > self.pre_record_buffer_size:
                    self.frame_buffer[topic].pop(0)
            else:
                # Si en cours d'enregistrement, vérifier si besoin de terminer
                self.frames_since_last_alert[topic] += 1
                if self.frames_since_last_alert[topic] > self.max_frames_without_alert:
                    logger.info(f"No new alerts for topic {topic} after {self.max_frames_without_alert} frames, stopping recording")
                    self._stop_recording(topic)
                elif len(self.frame_buffer[topic]) % 50 == 0:
                    # Log tous les 50 frames
                    logger.info(f"Recording frames for {topic}: {len(self.frame_buffer[topic])} frames captured, {self.frames_since_last_alert[topic]} since alert")
                elif len(self.frame_buffer[topic]) > self.max_recording_duration * self.frame_rate:
                    # Limiter la durée maximale d'enregistrement
                    logger.info(f"Maximum recording duration reached for {topic}, stopping recording")
                    self._stop_recording(topic)
        except Exception as e:
            logger.error(f"Error processing ROSImageBridge frame for {topic}: {str(e)}")

    def _on_camera_image(self, msg, topic):
        """Callback pour les images de caméra brutes"""
        try:
            # Convertir le message ROS en image CV2
            cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
            
            # Vérifier si nous avons déjà reçu des images du topic YOLO correspondant
            yolo_topic = self.camera_topics.get(topic)
            if yolo_topic and yolo_topic not in self.frame_count:
                # Ajouter l'image au buffer du topic YOLO correspondant
                if yolo_topic not in self.frame_buffer:
                    self.frame_buffer[yolo_topic] = []
                    self.frame_count[yolo_topic] = 0
                    self.alert_count[yolo_topic] = 0
                    self.recording[yolo_topic] = False
                    self.frames_since_last_alert[yolo_topic] = 0
                
                # Limiter la taille du buffer de pré-enregistrement
                self.frame_buffer[yolo_topic].append(cv_image.copy())
                self.frame_count[yolo_topic] += 1
                
                while len(self.frame_buffer[yolo_topic]) > self.pre_record_buffer_size:
                    self.frame_buffer[yolo_topic].pop(0)
            
            # Vérifier périodiquement si nous recevons des frames des topics YOLO
            if topic in self.camera_topics and self.camera_topics[topic] not in self.frame_count and self.frame_count.get(topic, 0) % 100 == 0:
                logger.warning(f"No frames received yet from corresponding YOLO topic {self.camera_topics[topic]}")
                
        except Exception as e:
            logger.error(f"Error processing camera image for {topic}: {str(e)}")

    def _check_recordings(self):
        """Vérifie périodiquement l'état des enregistrements"""
        active_topics = set(self.frame_buffer.keys())
        
        # Vérifier les topics YOLO connus
        yolo_topics = [t for t in active_topics if t.startswith('/yolo/')]
        if not yolo_topics:
            logger.warning("No YOLO topics subscribed via ROSImageBridge")
        
        # Vérifier l'état de tous les topics actifs
        for topic in active_topics:
            frame_count = self.frame_count.get(topic, 0)
            alert_count = self.alert_count.get(topic, 0)
            recording = self.recording.get(topic, False)
            logger.info(f"Topic {topic}: {frame_count} frames, {alert_count} alerts, recording: {recording}")
            
            if recording:
                frames = len(self.frame_buffer.get(topic, []))
                logger.info(f"ACTIVE RECORDING: {topic}, class: {self.detected_class_name.get(topic, 'unknown')}, frames: {frames}")
                
                # Vérifier si le recording a duré trop longtemps
                if self.video_start_time.get(topic) and (datetime.now() - self.video_start_time[topic]).total_seconds() > 120:  # 2 minutes max
                    logger.info(f"Maximum recording time reached for {topic}, stopping recording")
                    self._stop_recording(topic)

    def check_inactive_recordings(self):
        """Vérifier et terminer les enregistrements inactifs ou trop longs"""
        now = datetime.now()
        for topic, is_recording in list(self.recording.items()):
            if is_recording:
                start_time = self.video_start_time.get(topic)
                if start_time:
                    # Vérifier si l'enregistrement dure depuis trop longtemps
                    recording_duration = (now - start_time).total_seconds()
                    if recording_duration > self.max_recording_duration:
                        logger.info(f"Maximum recording duration reached for {topic}: {recording_duration:.2f}s > {self.max_recording_duration}s")
                        self._stop_recording(topic)
                    
                    # Vérifier s'il n'y a pas eu d'alerte depuis trop longtemps
                    frames_since_alert = self.frames_since_last_alert.get(topic, 0)
                    time_since_alert = frames_since_alert / self.frame_rate
                    if time_since_alert > self.max_frames_without_alert / self.frame_rate:
                        logger.info(f"No alerts for {topic} in the last {time_since_alert:.2f}s, stopping recording")
                        self._stop_recording(topic)

    def _on_alert(self, msg):
        """Traite les alertes de détection YOLO"""
        try:
            alert_data = json.loads(msg.data)
            if alert_data.get("detections"):
                for detection in alert_data["detections"]:
                    source_topic = detection.get("source_topic", "")
                    new_detected_class = detection.get("class", "unknown")
                    
                    # Déterminer le topic YOLO correspondant
                    camera_name = source_topic.split('/')[-2]
                    yolo_topic = f'/yolo/{camera_name}/image_raw'
                    
                    logger.info(f"Alert for {source_topic} → {yolo_topic}, class={new_detected_class}")
                    
                    # S'assurer que nous sommes abonnés à ce topic YOLO
                    if yolo_topic not in self.frame_buffer:
                        logger.info(f"New detection on {yolo_topic}, class={new_detected_class}, starting recording")
                        # Créer un buffer pour ce topic s'il n'existe pas encore
                        self.frame_buffer[yolo_topic] = []
                        self.frame_count[yolo_topic] = 0
                        self.alert_count[yolo_topic] = 0
                        self.recording[yolo_topic] = False
                        self.frames_since_last_alert[yolo_topic] = 0
                        
                        # Essayer de s'abonner au topic YOLO
                        try:
                            camera_topic = source_topic
                            if camera_topic not in self.camera_topics:
                                self.camera_topics[camera_topic] = yolo_topic
                            
                            if yolo_topic not in self.yolo_topics:
                                self.yolo_topics[yolo_topic] = camera_topic
                                
                            logger.info(f"Forced subscription to {yolo_topic}")
                        except Exception as e:
                            logger.error(f"Error subscribing to {yolo_topic}: {e}")
                        
                        # Commencer l'enregistrement avec la classe détectée
                        self.detected_class_name[yolo_topic] = new_detected_class
                        self._start_recording(yolo_topic)
                    else:
                        # Si on enregistre déjà ce topic
                        if self.recording.get(yolo_topic, False):
                            # Si c'est une classe différente
                            if new_detected_class != self.detected_class_name.get(yolo_topic, "unknown"):
                                # Si c'est une classe différente mais critique (nageur), on garde la priorité
                                if new_detected_class == "swimmer" or (
                                    self.detected_class_name.get(yolo_topic) != "swimmer" and 
                                    new_detected_class != self.detected_class_name.get(yolo_topic, "unknown")
                                ):
                                    logger.info(f"Different class detected on {yolo_topic}, stopping current recording and starting new one")
                                    self._stop_recording(yolo_topic)
                                    self.detected_class_name[yolo_topic] = new_detected_class
                                    self._start_recording(yolo_topic)
                            else:
                                # Même classe = on étend l'enregistrement actuel
                                logger.info(f"Same class detected on {yolo_topic}, resetting counter")
                                self.frames_since_last_alert[yolo_topic] = 0
                        else:
                            # Vérifier si un enregistrement récent a eu lieu (fusion d'incidents)
                            last_recording_time = self.video_start_time.get(yolo_topic)
                            current_time = datetime.now()
                            
                            if (last_recording_time and 
                                (current_time - last_recording_time).total_seconds() < self.incident_merge_threshold / self.frame_rate):
                                logger.info(f"Recent recording detected, merging incidents for {yolo_topic}")
                                self.detected_class_name[yolo_topic] = new_detected_class
                                self._start_recording(yolo_topic)
                            else:
                                logger.info(f"New detection on {yolo_topic}, class={new_detected_class}, starting recording")
                                self.detected_class_name[yolo_topic] = new_detected_class
                                self._start_recording(yolo_topic)

                    # Incrémenter le compteur d'alertes pour ce topic
                    self.alert_count[yolo_topic] = self.alert_count.get(yolo_topic, 0) + 1
                    
        except Exception as e:
            logger.error(f"Error processing alert: {e}")

    def _start_recording(self, topic):
        """Démarre l'enregistrement pour un topic"""
        self.recording[topic] = True
        self.video_start_time[topic] = datetime.now()
        self.frames_since_last_alert[topic] = 0
        
        # Log du début d'enregistrement
        pre_record_frames = len(self.frame_buffer.get(topic, []))
        logger.info(f"Recording started for class: {self.detected_class_name.get(topic, 'unknown')} on {topic} with {pre_record_frames} pre-recorded frames")

    def _stop_recording(self, topic):
        """Arrête l'enregistrement et sauvegarde la vidéo et les métadonnées"""
        if not self.recording.get(topic, False):
            return

        logger.info(f"Stopping recording for {topic}")
        self.recording[topic] = False
        video_end_time = datetime.now()

        frames = self.frame_buffer.get(topic, [])
        if not frames:
            logger.warning(f"No frames recorded for {topic}, cannot save video")
            return

        class_name = self.detected_class_name.get(topic, "unknown")
        start_time = self.video_start_time.get(topic, datetime.now())
        
        # Création d'un ID d'incident unique
        incident_id = f"INC-{uuid.uuid4().hex[:8].upper()}"
        
        # Structure hiérarchique de stockage
        today = start_time.strftime('%Y-%m-%d')
        camera_name = topic.split('/')[-2]
        
        # Création de la hiérarchie de dossiers
        storage_path = os.path.join(
            self.output_dir,
            today,
            camera_name,
            class_name
        )
        os.makedirs(storage_path, exist_ok=True)
        
        # Ajout de logs pour vérifier le chemin de stockage
        logger.debug(f"Saving video to storage path: {storage_path}")
        
        # Nom de fichier avec ID d'incident
        timestamp = start_time.strftime('%H%M%S')
        filename = f"{incident_id}_{timestamp}_{class_name}.mp4"
        filepath = os.path.join(storage_path, filename)

        try:
            height, width, _ = frames[0].shape
            writer = cv2.VideoWriter(filepath, cv2.VideoWriter_fourcc(*'mp4v'), self.frame_rate, (width, height))

            frame_count = 0
            for frame in frames:
                writer.write(frame)
                frame_count += 1
            writer.release()

            duration = (video_end_time - start_time).total_seconds()
            file_size = os.path.getsize(filepath)
            resolution = f"{width}x{height}"

            logger.info(f"Video saved: {filepath} with {frame_count} frames, duration: {duration:.2f}s")
            
            # Enrichissement des métadonnées
            metadata = {
                "path": filepath,
                "class_name": class_name,
                "incident_id": incident_id,
                "start_time": start_time.isoformat(),
                "end_time": video_end_time.isoformat(),
                "duration": duration,
                "frame_count": len(frames),
                "size": file_size,
                "resolution": resolution,
                "storage_type": "LOCAL",
                "severity": "HIGH" if class_name == "swimmer" else "MEDIUM",
                "camera_name": camera_name
            }
            
            # Stockage des métadonnées et récupération de l'ID d'enregistrement
            recording_id = self.storage_service.store_video_metadata(metadata)
            
            # Notification de l'interface utilisateur
            if recording_id:
                self.recording_created.emit(recording_id)
            
            # Vider le buffer pour libérer la mémoire
            self.frame_buffer[topic] = []
            
            logger.info(f"Video metadata stored successfully: {filepath}")
            
        except Exception as e:
            logger.error(f"Error saving video for {topic}: {e}")