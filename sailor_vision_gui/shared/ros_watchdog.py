import logging
import time
from PyQt5.QtCore import QObject, QThread, pyqtSignal, QTimer
import rclpy
from rclpy.node import Node
from database import get_session
from src.services.camera_service import CameraService

logger = logging.getLogger(__name__)

class ROSWatchdogWorker(QObject):
    ros_status_changed = pyqtSignal(bool)  # True: Connected, False: Disconnected
    cameras_status_changed = pyqtSignal(list)  # Liste des IDs de caméras avec nouvel état

    def __init__(self, node):
        super().__init__()
        self.node = node
        self.last_check_time = 0
        self.check_interval = 1  # Vérifier toutes les 5 secondes
        self.ros_connected = True  # Présumer que ROS est initialement connecté
        self.camera_topics = {}  # Topic -> timestamp de dernière activité
        self.camera_active_status = {}  # ID de caméra -> statut actif
        self.topic_to_camera_id = {}  # Mappage topic -> ID de caméra
        
        # Obtenir une session de base de données
        self.db_session = get_session()
        self.camera_service = CameraService(self.db_session)
        
        # Initialiser les mappages depuis la BD
        self.initialize_camera_mappings()
    
    def initialize_camera_mappings(self):
        """Initialiser les mappages entre topics et caméras depuis la base de données"""
        try:
            cameras = self.camera_service.get_all_cameras()
            for camera in cameras:
                camera_id = camera.id
                # Créer le nom de topic standard pour cette caméra
                if camera.ip_address:
                    device_name = camera.ip_address.split('/')[-1]
                    topic = f"/camera/{device_name}/image_raw"
                    yolo_topic = f"/yolo/{device_name}/image_raw"
                    
                    self.topic_to_camera_id[topic] = camera_id
                    self.topic_to_camera_id[yolo_topic] = camera_id
                    self.camera_active_status[camera_id] = camera.is_active
                    
                    # Initialiser les timestamps à 0 (inactive)
                    self.camera_topics[topic] = 0
                    self.camera_topics[yolo_topic] = 0
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation des mappages de caméras: {e}")

    def check_ros_health(self):
        """Vérifier si les nœuds ROS essentiels sont en cours d'exécution"""
        try:
            # Liste des nœuds essentiels
            essential_nodes = ['camera_publisher', 'camera_manager', 'yolo_node']
            
            # Obtenir la liste des nœuds ROS actuellement en cours d'exécution
            node_names_and_namespaces = self.node.get_node_names_and_namespaces()
            running_nodes = [name for name, namespace in node_names_and_namespaces]
            
            # Vérifier si les nœuds essentiels sont en cours d'exécution
            essential_running = any(node in running_nodes for node in essential_nodes)
            
            # Si l'état a changé, émettre le signal
            if essential_running != self.ros_connected:
                logger.warning(f"État ROS changé: {'connecté' if essential_running else 'déconnecté'}")
                self.ros_connected = essential_running
                self.ros_status_changed.emit(essential_running)
                
                # Si ROS s'est déconnecté, mettre toutes les caméras comme inactives
                if not essential_running:
                    self.update_all_cameras_inactive()
                
            return essential_running
        except Exception as e:
            logger.error(f"Erreur lors de la vérification de la santé de ROS: {e}")
            # En cas d'erreur, présumer que ROS est déconnecté
            if self.ros_connected:
                self.ros_connected = False
                self.ros_status_changed.emit(False)
                self.update_all_cameras_inactive()
            return False

    def update_all_cameras_inactive(self):
        """Marquer toutes les caméras comme inactives"""
        try:
            camera_ids = list(self.camera_active_status.keys())
            changed_cameras = []
            
            for camera_id in camera_ids:
                if self.camera_active_status.get(camera_id, False):
                    self.camera_active_status[camera_id] = False
                    changed_cameras.append((camera_id, False))  # ID, nouveau statut
            
            if changed_cameras:
                # Mise à jour groupée dans la base de données
                self.camera_service.set_cameras_active([id for id, _ in changed_cameras], False)
                # Émettre le signal avec la liste des IDs de caméras modifiées
                self.cameras_status_changed.emit([id for id, _ in changed_cameras])
                
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour des caméras inactives: {e}")

    def update_camera_status(self):
        """Vérifier l'état des topics de caméra et mettre à jour les statuts"""
        current_time = time.time()
        timeout = 5  # Considérer une caméra comme inactive après 5 secondes sans activité
        
        # Si ROS est déconnecté, ne rien faire
        if not self.ros_connected:
            return
            
        try:
            # Vérifier les topics actuels
            topics = self.node.get_topic_names_and_types()
            active_topics = set(topic for topic, _ in topics)
            
            # Caméras avec changement d'état
            changed_cameras = []
            
            # Parcourir les topics de caméra connus
            for topic, last_active in self.camera_topics.items():
                # Vérifier si le topic existe encore
                if topic not in active_topics:
                    continue
                    
                camera_id = self.topic_to_camera_id.get(topic)
                if not camera_id:
                    continue
                
                # Vérifier l'activité (dernière mise à jour)
                is_active = (current_time - last_active) < timeout
                
                # Si l'état a changé
                if is_active != self.camera_active_status.get(camera_id, False):
                    self.camera_active_status[camera_id] = is_active
                    changed_cameras.append((camera_id, is_active))
            
            # Mettre à jour la base de données et émettre le signal si nécessaire
            if changed_cameras:
                # Grouper par état
                active_cameras = [id for id, state in changed_cameras if state]
                inactive_cameras = [id for id, state in changed_cameras if not state]
                
                if active_cameras:
                    self.camera_service.set_cameras_active(active_cameras, True)
                
                if inactive_cameras:
                    self.camera_service.set_cameras_active(inactive_cameras, False)
                
                # Émettre le signal avec la liste des IDs de caméras modifiées
                self.cameras_status_changed.emit([id for id, _ in changed_cameras])
        
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour des statuts de caméra: {e}")
    
    def register_topic_activity(self, topic):
        """Enregistrer l'activité sur un topic"""
        if topic in self.camera_topics:
            self.camera_topics[topic] = time.time()
    
    def run(self):
        """Méthode principale du watchdog"""
        while True:
            try:
                current_time = time.time()
                if current_time - self.last_check_time >= self.check_interval:
                    self.check_ros_health()
                    self.update_camera_status()
                    self.last_check_time = current_time
                
                # Pause courte pour ne pas surcharger le CPU
                time.sleep(0.1)
            except Exception as e:
                logger.error(f"Erreur dans la boucle de surveillance ROS: {e}")
                time.sleep(1)  # Pause plus longue en cas d'erreur

class ROSWatchdog(QObject):
    ros_status_changed = pyqtSignal(bool)
    cameras_status_changed = pyqtSignal(list)
    
    def __init__(self, ros_node):
        super().__init__()
        self.ros_node = ros_node
        self.worker = None
        self.worker_thread = None
        
        # Démarrer le watchdog dans un thread séparé
        self.start_watchdog()
    
    def start_watchdog(self):
        """Démarrer le watchdog dans un thread séparé"""
        self.worker_thread = QThread()
        self.worker = ROSWatchdogWorker(self.ros_node)
        
        # Déplacer le worker dans le thread
        self.worker.moveToThread(self.worker_thread)
        
        # Connecter les signaux
        self.worker.ros_status_changed.connect(self.ros_status_changed)
        self.worker.cameras_status_changed.connect(self.cameras_status_changed)
        
        # Connecter le signal de démarrage du thread
        self.worker_thread.started.connect(self.worker.run)
        
        # Démarrer le thread
        self.worker_thread.start()
        
        logger.info("Watchdog ROS démarré avec succès")
    
    def register_topic_activity(self, topic):
        """Enregistrer l'activité sur un topic (appelé depuis d'autres composants)"""
        if self.worker:
            self.worker.register_topic_activity(topic)
    
    def get_ros_status(self):
        """Obtenir l'état actuel de ROS"""
        return self.worker.ros_connected if self.worker else False
    
    def cleanup(self):
        """Nettoyer les ressources avant la fermeture"""
        if self.worker_thread and self.worker_thread.isRunning():
            self.worker_thread.quit()
            self.worker_thread.wait()
            logger.info("Watchdog ROS arrêté proprement")
