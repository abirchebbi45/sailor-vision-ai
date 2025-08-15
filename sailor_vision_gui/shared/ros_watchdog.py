import logging
import time
from PyQt5.QtCore import QObject, QThread, pyqtSignal, QTimer
import rclpy
from rclpy.node import Node
from database import get_session, create_new_session, close_session
from src.services.camera_service import CameraService
from models import Camera

logger = logging.getLogger(__name__)

class ROSWatchdogWorker(QObject):
    ros_status_changed = pyqtSignal(bool)  # True: Connected, False: Disconnected
    cameras_status_changed = pyqtSignal(list)  # Liste des IDs de caméras avec nouvel état

    def __init__(self, node):
        super().__init__()
        self.node = node
        self.check_interval = 2  # Check every 2 seconds for faster detection
        self.ros_connected = True  # Initially assume ROS is connected
        self.camera_topics = {}  # Topic -> timestamp de dernière activité
        self.camera_active_status = {}  # ID de caméra -> statut actif
        self.topic_to_camera_id = {}  # Mappage topic -> ID de caméra
        self.topic_timeout = 5  # Topic considered inactive after 5 seconds without frames
        self.ros_health_failures = 0  # Count consecutive health check failures
        self.max_failures = 3  # Max failures before considering ROS disconnected
        
        # Initialize mappings from database
        self.initialize_camera_mappings()
    
    def initialize_camera_mappings(self):
        """Initialize mappings between topics and cameras from database"""
        try:
            session = create_new_session()
            camera_service = CameraService(session)
            cameras = camera_service.get_all_cameras()
            
            for camera in cameras:
                camera_id = camera.id
                
                # Create standard topic names for this camera based on ip_address
                if camera.ip_address and "/dev/video" in camera.ip_address:
                    # Extract device number from /dev/video2 -> video2
                    device_name = camera.ip_address.split('/')[-1]  # video2
                    
                    # ROS topics that we need to monitor
                    camera_topic = f"/camera/{device_name}/image_raw"
                    yolo_topic = f"/yolo/{device_name}/image_raw"
                    
                    # Map both topics to this camera
                    self.topic_to_camera_id[camera_topic] = camera_id
                    self.topic_to_camera_id[yolo_topic] = camera_id
                    
                    # Initialize camera status from database
                    self.camera_active_status[camera_id] = camera.is_active
                    
                    # Initialize topic activity timestamps (0 = no activity)
                    self.camera_topics[camera_topic] = 0
                    self.camera_topics[yolo_topic] = 0
                    
                    logger.info(f"Initialized watchdog for camera {camera.name} (ID: {camera_id})")
                    logger.debug(f"  - Camera topic: {camera_topic}")
                    logger.debug(f"  - YOLO topic: {yolo_topic}")
            
            close_session(session)
                    
        except Exception as e:
            logger.error(f"Error initializing camera mappings: {e}")

    def check_ros_health(self):
        """Check if ROS system is healthy by checking nodes and topics"""
        try:
            # Check if the node is still valid and can make ROS calls
            if not rclpy.ok():
                logger.warning("ROS context is not OK")
                self.ros_health_failures += 1
            else:
                # Try to get node names - this will fail if ROS is disconnected
                try:
                    node_names_and_namespaces = self.node.get_node_names_and_namespaces()
                    topics = self.node.get_topic_names_and_types()
                    
                    # If we get here, ROS is responding
                    self.ros_health_failures = 0
                    
                    # Check for camera-related topics
                    topic_names = [topic for topic, _ in topics]
                    has_camera_topics = any(
                        ('/camera/' in topic and '/image_raw' in topic) or 
                        ('/yolo/' in topic and '/image_raw' in topic)
                        for topic in topic_names
                    )
                    
                    # ROS is healthy if it's responding and we have relevant topics
                    ros_healthy = has_camera_topics
                    
                    # If no camera topics, consider it a "partial" disconnect
                    if not has_camera_topics:
                        logger.debug("ROS responding but no camera/YOLO topics found")
                        self.ros_health_failures += 1
                    
                except Exception as e:
                    logger.warning(f"ROS call failed: {e}")
                    self.ros_health_failures += 1
                    ros_healthy = False
            
            # Determine if ROS should be considered disconnected
            ros_disconnected = self.ros_health_failures >= self.max_failures
            
            # If ROS status changed
            if ros_disconnected and self.ros_connected:
                logger.warning("ROS system detected as disconnected")
                self.ros_connected = False
                self.ros_status_changed.emit(False)
                self.update_all_cameras_inactive()
                
            elif not ros_disconnected and not self.ros_connected:
                logger.info("ROS system detected as reconnected")
                self.ros_connected = True
                self.ros_status_changed.emit(True)
                # Don't automatically activate cameras on reconnect - wait for actual feeds
                
            return self.ros_connected
            
        except Exception as e:
            logger.error(f"Critical error checking ROS health: {e}")
            self.ros_health_failures = self.max_failures  # Force disconnect state
            if self.ros_connected:
                self.ros_connected = False
                self.ros_status_changed.emit(False)
                self.update_all_cameras_inactive()
            return False

    def update_all_cameras_inactive(self):
        """Mark all cameras as inactive when ROS disconnects"""
        try:
            changed_cameras = []
            
            for camera_id in self.camera_active_status.keys():
                if self.camera_active_status.get(camera_id, False):
                    self.camera_active_status[camera_id] = False
                    changed_cameras.append(camera_id)
                    logger.info(f"Camera {camera_id} marked as inactive (ROS disconnected)")
            
            if changed_cameras:
                # Update database
                session = create_new_session()
                camera_service = CameraService(session)
                camera_service.set_cameras_active(changed_cameras, False)
                close_session(session)
                
                # Emit signal
                self.cameras_status_changed.emit(changed_cameras)
                logger.info(f"Updated {len(changed_cameras)} cameras to inactive in database")
                
        except Exception as e:
            logger.error(f"Error updating cameras to inactive: {e}")

    def update_camera_status(self):
        """
        Check topic activity and update camera status based on video feed availability
        Implements maritime-aware logic that respects manual activations
        """
        if not self.ros_connected:
            return
            
        current_time = time.time()
        changed_cameras = []
        
        try:
            # Get fresh camera data from database to check for recent manual changes
            session = create_new_session()
            camera_service = CameraService(session)
            
            # Check each camera's topic activity
            for camera_id in self.camera_active_status.keys():
                try:
                    # Get current database status
                    camera = session.query(Camera).filter(Camera.id == camera_id).first()
                    if not camera:
                        continue
                    
                    # Find topics for this camera
                    camera_topics = [topic for topic, cam_id in self.topic_to_camera_id.items() if cam_id == camera_id]
                    
                    # Check if any topic for this camera has recent activity
                    has_recent_activity = False
                    last_activity_time = 0
                    
                    for topic in camera_topics:
                        topic_last_activity = self.camera_topics.get(topic, 0)
                        if topic_last_activity > 0:  # Has had activity at some point
                            time_since_activity = current_time - topic_last_activity
                            if time_since_activity < self.topic_timeout:
                                has_recent_activity = True
                                last_activity_time = max(last_activity_time, topic_last_activity)
                    
                    # Maritime Logic: Be more conservative about deactivating cameras
                    current_watchdog_status = self.camera_active_status.get(camera_id, False)
                    database_status = camera.is_active
                    
                    # If camera was manually activated recently, be more tolerant of feed loss
                    extended_timeout = self.topic_timeout * 2  # 10 seconds instead of 5
                    
                    should_be_active = current_watchdog_status  # Default to current status
                    
                    if database_status and not current_watchdog_status:
                        # Camera was activated outside of watchdog - respect manual activation
                        logger.info(f"[Watchdog] Camera {camera_id} manually activated - updating watchdog status")
                        should_be_active = True
                    elif has_recent_activity and not current_watchdog_status:
                        # Camera has feed activity - activate it
                        should_be_active = True
                        logger.info(f"[Watchdog] Camera {camera_id} feed detected - activating")
                    elif not has_recent_activity and database_status and current_watchdog_status:
                        # Camera is active but no recent feed - check if should deactivate
                        time_since_last = current_time - last_activity_time if last_activity_time > 0 else 0
                        
                        # If camera never had activity (last_activity_time = 0), it might be manually activated
                        if last_activity_time == 0:
                            # For manually activated cameras without feed, be very tolerant
                            should_be_active = True  # Keep manually activated cameras active
                            logger.debug(f"[Watchdog] Camera {camera_id} manually activated without ROS feed - keeping active")
                        else:
                            # Camera had feed before, use extended timeout
                            should_deactivate = time_since_last > extended_timeout
                            if should_deactivate:
                                should_be_active = False
                                logger.info(f"[Watchdog] 🚢 Maritime Timeout: Camera {camera_id} feed lost for {time_since_last:.1f}s - deactivating")
                            else:
                                should_be_active = True  # Keep active during grace period
                                logger.debug(f"[Watchdog] Camera {camera_id} in grace period ({time_since_last:.1f}s/{extended_timeout}s)")
                    
                    # Update status if changed
                    if should_be_active != current_watchdog_status:
                        self.camera_active_status[camera_id] = should_be_active
                        changed_cameras.append(camera_id)
                        
                        if should_be_active:
                            logger.info(f"[Watchdog] Camera {camera_id} activated (video feed detected)")
                        else:
                            time_since = current_time - last_activity_time if last_activity_time > 0 else 999
                            logger.info(f"[Watchdog] Camera {camera_id} deactivated (no feed for {time_since:.1f}s)")
                
                except Exception as e:
                    logger.error(f"[Watchdog] Error processing camera {camera_id}: {e}")
            
            # Update database and emit signals if there are changes
            if changed_cameras:
                # Group by new status
                active_cameras = [cam_id for cam_id in changed_cameras if self.camera_active_status[cam_id]]
                inactive_cameras = [cam_id for cam_id in changed_cameras if not self.camera_active_status[cam_id]]
                
                if active_cameras:
                    camera_service.set_cameras_active(active_cameras, True)
                    logger.info(f"[Watchdog] Set {len(active_cameras)} cameras as active: {active_cameras}")
                
                if inactive_cameras:
                    camera_service.set_cameras_active(inactive_cameras, False)
                    logger.info(f"[Watchdog] Set {len(inactive_cameras)} cameras as inactive: {inactive_cameras}")
                
                # Emit signal with all changed camera IDs
                self.cameras_status_changed.emit(changed_cameras)
            
            close_session(session)
        
        except Exception as e:
            logger.error(f"Error updating camera status: {e}")
    
    def register_topic_activity(self, topic):
        """Register activity on a topic (called when frames are received)"""
        current_time = time.time()
        
        if topic in self.camera_topics:
            self.camera_topics[topic] = current_time
            
            # Reset ROS health failures since we're receiving data
            if self.ros_health_failures > 0:
                self.ros_health_failures = 0
                if not self.ros_connected:
                    logger.info("ROS reconnected (topic activity detected)")
                    self.ros_connected = True
                    self.ros_status_changed.emit(True)
            
        else:
            # New topic detected
            self.camera_topics[topic] = current_time
            logger.info(f"New topic activity detected: {topic}")
            
            # Try to map to a camera if it follows our naming convention
            if ("/camera/" in topic or "/yolo/" in topic) and "/image_raw" in topic:
                parts = topic.split('/')
                if len(parts) >= 3:
                    device_name = parts[2]  # Extract device name like 'video2'
                    
                    # Find camera with matching device
                    session = create_new_session()
                    camera_service = CameraService(session)
                    cameras = camera_service.get_all_cameras()
                    
                    for camera in cameras:
                        if camera.ip_address and device_name in camera.ip_address:
                            self.topic_to_camera_id[topic] = camera.id
                            if camera.id not in self.camera_active_status:
                                self.camera_active_status[camera.id] = False
                            logger.info(f"Mapped new topic {topic} to camera {camera.id}")
                            break
                    
                    close_session(session)

    def run(self):
        """Main watchdog loop - runs in separate thread"""
        logger.info("ROS Watchdog started")
        last_check_time = 0
        
        try:
            while True:
                current_time = time.time()
                
                # Check ROS health and camera status at regular intervals
                if current_time - last_check_time >= self.check_interval:
                    self.check_ros_health()
                    self.update_camera_status()
                    last_check_time = current_time
                
                # Short pause to avoid excessive CPU usage
                time.sleep(0.1)
                
        except Exception as e:
            logger.error(f"Error in ROS watchdog loop: {e}")
            # Mark ROS as disconnected on critical error
            if self.ros_connected:
                self.ros_connected = False
                self.ros_status_changed.emit(False)
                self.update_all_cameras_inactive()

class ROSWatchdog(QObject):
    ros_status_changed = pyqtSignal(bool)
    cameras_status_changed = pyqtSignal(list)
    
    def __init__(self, ros_node):
        super().__init__()
        self.ros_node = ros_node
        self.worker = None
        self.worker_thread = None
        
        # Start the watchdog in a separate thread
        self.start_watchdog()
    
    def start_watchdog(self):
        """Start the watchdog in a separate thread"""
        try:
            self.worker_thread = QThread()
            self.worker = ROSWatchdogWorker(self.ros_node)
            
            # Move worker to thread
            self.worker.moveToThread(self.worker_thread)
            
            # Connect signals
            self.worker.ros_status_changed.connect(self.ros_status_changed)
            self.worker.cameras_status_changed.connect(self.cameras_status_changed)
            
            # Connect thread start signal
            self.worker_thread.started.connect(self.worker.run)
            
            # Start thread
            self.worker_thread.start()
            
            logger.info("ROS Watchdog started successfully")
            
        except Exception as e:
            logger.error(f"Error starting ROS Watchdog: {e}")
    
    def register_topic_activity(self, topic):
        """Register topic activity (called from other components when frames are received)"""
        if self.worker:
            self.worker.register_topic_activity(topic)
    
    def get_ros_status(self):
        """Get current ROS status"""
        return self.worker.ros_connected if self.worker else False
    
    def cleanup(self):
        """Clean up resources before shutdown"""
        try:
            if self.worker_thread and self.worker_thread.isRunning():
                self.worker_thread.quit()
                self.worker_thread.wait(5000)  # Wait up to 5 seconds
                if self.worker_thread.isRunning():
                    self.worker_thread.terminate()
                logger.info("ROS Watchdog stopped cleanly")
        except Exception as e:
            logger.error(f"Error cleaning up ROS Watchdog: {e}")
