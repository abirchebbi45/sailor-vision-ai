from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, 
                            QScrollArea, QFrame, QLabel, QPushButton, QDialog, 
                            QLineEdit, QFormLayout, QDialogButtonBox, QMessageBox, 
                            QCheckBox, QSizePolicy)
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QMetaObject, Q_ARG, QTimer
from PyQt5.QtGui import QIcon, QPixmap, QColor, QPainter, QImage, QPainterPath

from src.components.shared import HeaderWidget, Sidebar
from shared.ros_image_listener import ROSImageBridge
import cv2
from time import time

from src.services.camera_service import CameraService
from src.services.pending_camera_manager import pending_camera_manager
from src.services.camera_detector import camera_detector  # Import the new camera detector service
from database import get_session, create_new_session

import logging
import json
from std_msgs.msg import String as ROSString

logger = logging.getLogger(__name__)

class CameraFeedWidget(QFrame):
    expand_clicked = pyqtSignal(int)  # Signal for expand button click with camera id
    FEED_TIMEOUT_MS = 3000  # 3 seconds

    def __init__(self, camera):
        super().__init__()
        self.camera = camera
        self.current_pixmap = None  # Stockez le pixmap actuel pour le redimensionnement
        self.last_update_time = 0  # Timestamp of the last frame update
        self.update_interval = 0.033  # Minimum interval between updates (30 FPS)
        self.feed_timer = QTimer(self)
        self.feed_timer.setInterval(self.FEED_TIMEOUT_MS)
        self.feed_timer.setSingleShot(True)
        self.feed_timer.timeout.connect(self.handle_feed_timeout)
        self.feed_active = False
        self.init_ui()

    def init_ui(self):
        self.setObjectName("liveFeedWidget")
        self.setFrameShape(QFrame.StyledPanel)
        
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(240, 300)  # Augmenter la hauteur minimale à 300px
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        feed_container = QFrame(self)
        feed_container.setObjectName("feedContainer")
        feed_container.setStyleSheet("background-color: #1a1a1a; border-radius: 8px;")
        feed_container_layout = QVBoxLayout(feed_container)
        feed_container_layout.setContentsMargins(0, 0, 0, 0)
        feed_container_layout.setSpacing(0)
        feed_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.feed_label = QLabel(feed_container)
        self.feed_label.setObjectName("cameraFeed")
        self.feed_label.setAlignment(Qt.AlignCenter)
        self.feed_label.setMinimumHeight(220)  # Augmenter la hauteur minimale du flux
        self.feed_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.feed_label.setStyleSheet("background-color: #1a1a1a; border-radius: 8px;")
        feed_container_layout.addWidget(self.feed_label)

        overlay_container = QWidget(feed_container)
        overlay_container.setObjectName("overlayContainer")
        overlay_container.setAttribute(Qt.WA_TranslucentBackground)
        overlay_container.setStyleSheet("background-color: transparent;")
        
        overlay_layout = QHBoxLayout(overlay_container)
        overlay_layout.setContentsMargins(10, 10, 10, 10)
        overlay_layout.setSpacing(10)

        self.status_indicator = QLabel(overlay_container)
        self.status_indicator.setObjectName("statusIndicator")
        self.status_indicator.setAttribute(Qt.WA_TranslucentBackground)
        self.update_status_indicator()
        overlay_layout.addWidget(self.status_indicator, 0, Qt.AlignLeft)
        
        overlay_layout.addStretch(1)

        expand_btn = QPushButton("Expand", overlay_container)
        expand_btn.setObjectName("expandButton")
        expand_btn.setCursor(Qt.PointingHandCursor)
        expand_btn.setStyleSheet("""
            #expandButton {
                background-color: rgba(33, 150, 243, 180);
                color: white;
                border: none;
                border-radius: 15px;
                padding: 6px 12px;
                font-size: 12px;
            }
            #expandButton:hover {
                background-color: rgba(25, 118, 210, 200);
            }
        """)
        expand_btn.clicked.connect(lambda: self.expand_clicked.emit(self.camera.get("id", 0)))
        overlay_layout.addWidget(expand_btn, 0, Qt.AlignRight)

        feed_container_layout.addWidget(overlay_container, 0, Qt.AlignTop)

        layout.addWidget(feed_container)

        camera_name = QLabel(self.camera.get("name", "Camera").upper())
        camera_name.setObjectName("cameraName")
        camera_name.setAlignment(Qt.AlignCenter)
        camera_name.setStyleSheet("""
            font-weight: bold; 
            padding: 8px; 
            color: #333333; 
            background-color: #f5f5f5;
        """)
        layout.addWidget(camera_name)

        self.setStyleSheet("""
            #liveFeedWidget {
                background-color: white;
                border-radius: 8px;
                margin: 5px;
            }
            #feedContainer {
                position: relative;
                border-radius: 8px;
            }
            #cameraFeed {
                border-radius: 8px;
            }
        """)

        if self.camera.get("image_path"):
            pixmap = QPixmap(self.camera.get("image_path"))
            if not pixmap.isNull():
                self.current_pixmap = pixmap
                self.feed_label.setPixmap(pixmap.scaled(
                    self.feed_label.width(),
                    self.feed_label.height(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                ))
                self.set_feed_active(True)
            else:
                self.set_feed_active(False)
        else:
            self.set_feed_active(False)

    def set_feed_active(self, active: bool):
        self.feed_active = active
        self.camera["is_active"] = active
        self.update_status_indicator()
        if not active:
            self.feed_label.setText("No available live feed")
            self.feed_label.setStyleSheet("color: white; font-size: 14px; background-color: #1a1a1a; border-radius: 8px;")
            self.current_pixmap = None

    def update_status_indicator(self):
        """
        Updates the status indicator based on the camera's is_active field.
        """
        is_active = self.camera.get("is_active", False)
        status_color = "#4CAF50" if is_active else "#FF5252"
        status_text = "Active" if is_active else "Inactive"
        self.status_indicator.setText(
            f'<span style="color: {status_color}; font-size: 14px;">●</span> '
            f'<span style="color: white; font-size: 12px; text-shadow: 1px 1px 3px rgba(0,0,0,1);">{status_text}</span>'
        )

    def update_feed(self, pixmap):
        """
        Updates the displayed image in the camera feed.

        Args:
            pixmap: QPixmap to display.
        """
        current_time = time()
        if current_time - self.last_update_time < self.update_interval:
            return

        self.last_update_time = current_time

        if not pixmap.isNull():
            self.set_feed_active(True)
            self.feed_timer.start()  # Reset the timeout timer
            self.current_pixmap = pixmap
            if self.feed_label.pixmap() is None or self.feed_label.pixmap().size() != pixmap.size():
                scaled_pixmap = pixmap.scaled(
                    self.feed_label.width(),
                    self.feed_label.height(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                self.feed_label.setPixmap(scaled_pixmap)
            else:
                self.feed_label.setPixmap(pixmap)

    def handle_feed_timeout(self):
        """
        Called when no frame has been received for FEED_TIMEOUT_MS.
        """
        self.set_feed_active(False)

    def resizeEvent(self, event):
        """Redimensionner l'image quand le widget change de taille"""
        super().resizeEvent(event)
        
        if self.current_pixmap and not self.current_pixmap.isNull():
            self.update_feed(self.current_pixmap)

class ExpandedCameraWidget(QWidget):
    close_clicked = pyqtSignal()
    
    def __init__(self, camera_data=None, pixmap=None):
        super().__init__()
        self.camera_data = camera_data
        self.pixmap = pixmap
        self.last_update_time = 0  # Timestamp of the last frame update
        self.update_interval = 0.016  # ~60 FPS (16ms between frames)
        self.frame_queue = []  # Queue to store frames if they come in too fast
        self.max_queue_size = 5  # Maximum number of frames to queue
        self.init_ui()
        
        self.playback_timer = QTimer(self)
        self.playback_timer.timeout.connect(self.process_frame_queue)
        self.playback_timer.start(16)  # ~60 FPS for smooth playback
    
    def init_ui(self):
        self.setObjectName("expandedCameraWidget")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        header_layout = QHBoxLayout()
        
        camera_title = QLabel(self.camera_data.get("name", "Camera").upper())
        camera_title.setObjectName("expandedCameraTitle")
        camera_title.setStyleSheet("font-size: 18px; font-weight: bold;")
        
        close_btn = QPushButton("Cancel")
        close_btn.setObjectName("cancelExpandButton")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.close_clicked.emit)
        
        header_layout.addWidget(camera_title)
        header_layout.addStretch()
        header_layout.addWidget(close_btn)
        
        layout.addLayout(header_layout)
        
        self.feed_container = QLabel()
        self.feed_container.setObjectName("expandedFeedContainer")
        self.feed_container.setAlignment(Qt.AlignCenter)
        self.feed_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        if self.pixmap and not self.pixmap.isNull():
            self.update_feed(self.pixmap)
        else:
            self.feed_container.setText("No feed available")
            self.feed_container.setStyleSheet("background-color: #313131; color: white;")
        
        layout.addWidget(self.feed_container)
        
        self.setStyleSheet("""
            #expandedCameraWidget {
                background-color: #f5f5f5;
            }
            #expandedFeedContainer {
                background-color: #313131;
                border-radius: 8px;
                min-height: 500px;
            }
            #cancelExpandButton {
                background-color: #E53935;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
            }
            #cancelExpandButton:hover {
                background-color: #D32F2F;
            }
        """)
    
    def update_feed(self, pixmap):
        """
        Updates the displayed image in the expanded camera feed.
        """
        if pixmap.isNull():
            return
            
        if len(self.frame_queue) < self.max_queue_size:
            self.frame_queue.append(pixmap)
    
    def process_frame_queue(self):
        """Process queued frames for smooth playback"""
        if not self.frame_queue:
            return
            
        pixmap = self.frame_queue.pop(0)
        
        current_time = time()
        if current_time - self.last_update_time < self.update_interval:
            self.frame_queue.insert(0, pixmap)
            return

        self.last_update_time = current_time
        
        if self.feed_container and not pixmap.isNull():
            container_size = self.feed_container.size()
            
            if container_size.width() <= 0 or container_size.height() <= 0:
                return
                
            scaled_pixmap = pixmap.scaled(
                container_size.width(), 
                container_size.height(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            
            self.feed_container.setPixmap(scaled_pixmap)
            
            self.pixmap = pixmap
    
    def closeEvent(self, event):
        if hasattr(self, 'playback_timer') and self.playback_timer.isActive():
            self.playback_timer.stop()
        
        if hasattr(self, 'frame_queue'):
            self.frame_queue.clear()
            
        event.accept()
    
    def resizeEvent(self, event):
        """
        Resizes the image when the widget size changes.
        """
        super().resizeEvent(event)
        if hasattr(self, 'feed_container') and self.pixmap and not self.pixmap.isNull():
            self.update_feed(self.pixmap)

def camera_to_dict(camera):
    """Convert a Camera ORM object to a plain dict for UI use."""
    return {
        "id": camera.id,
        "name": camera.name,
        "location": camera.location,
        "is_active": camera.is_active,
        "image_path": getattr(camera, "rtsp_url", ""),
        "ip_address": getattr(camera, "ip_address", None),
        "port": getattr(camera, "port", None),
    }

class LiveFeedScreen(QWidget):
    frame_updated = pyqtSignal(int, QPixmap)  # camera_id, frame
    feed_stopped = pyqtSignal(int)            # camera_id

    def __init__(self, user_data=None, ros_node=None, ros_bridge=None):
        super().__init__()
        self.user_data = user_data
        
        # Initialize database session with error handling
        try:
            self.db_session = create_new_session()
            self.camera_service = CameraService(self.db_session)
        except Exception as e:
            logger.error(f"Failed to initialize database session: {e}")
            self.db_session = None
            self.camera_service = None
            
        # Initialize cameras list with validation - LOAD ALL APPROVED CAMERAS
        try:
            if self.camera_service:
                all_cameras = self.camera_service.get_all_cameras()
                # Changed: Load ALL cameras, not just active ones for Live Feed display
                self.cameras = [camera_to_dict(cam) for cam in all_cameras if cam and hasattr(cam, 'id')]
            else:
                self.cameras = []
        except Exception as e:
            logger.error(f"Failed to load cameras: {e}")
            self.cameras = []
            
        self.filtered_cameras = self.cameras
        self.camera_widgets = {}
        self.expanded_camera_widget = None
        self.ros_node = ros_node
        self.topic_to_camera_id = {}  # Map ROS topic to camera.id
        
        self.init_ui()

        # Use provided ROSImageBridge or create a new one
        try:
            self.ros_bridge = ros_bridge or ROSImageBridge(ros_node)
            
            # Connect to the ROS bridge for image updates - FIXED SIGNAL NAME
            self.ros_bridge.image_received.connect(self.on_ros_image_received, Qt.QueuedConnection)
            
            # Subscribe to YOLO topics for camera feeds
            if ros_node:
                self.ros_bridge.subscribe_to_yolo_topics(self.handle_new_yolo_topic)
                
            # Initialize the camera detector with our ROS node
            if ros_node and camera_detector:
                # Ensure the camera detector has our ROS node
                camera_detector.ros_node = ros_node
                camera_detector.setup_ros_subscription()
                
        except Exception as e:
            logger.error(f"Failed to initialize ROS bridge: {e}")
            self.ros_bridge = None

    def on_ros_image_received(self, cv_image, topic):
        """
        Handle image received from ROS bridge
        Convert to pixmap and update corresponding camera feed
        """
        try:
            # Convert CV image to QPixmap
            height, width, channel = cv_image.shape
            bytes_per_line = 3 * width
            
            from PyQt5.QtGui import QImage, QPixmap
            q_image = QImage(cv_image.data, width, height, bytes_per_line, QImage.Format_RGB888).rgbSwapped()
            pixmap = QPixmap.fromImage(q_image)
            
            # Find camera ID for this topic
            camera_id = self.topic_to_camera_id.get(topic)
            if camera_id:
                # Update camera feed
                success = self.update_camera_feed(camera_id, pixmap)
                if success:
                    logger.debug(f"[LiveFeed] Updated camera {camera_id} from topic {topic}")
                else:
                    logger.warning(f"[LiveFeed] Failed to update camera {camera_id} from topic {topic}")
            else:
                logger.debug(f"[LiveFeed] No camera mapping found for topic {topic}")
                
        except Exception as e:
            logger.error(f"[LiveFeed] Error processing ROS image from {topic}: {e}")

    def filter_cameras(self, search_text):
        """Filter cameras based on search text"""
        try:
            if not search_text:
                self.filtered_cameras = self.cameras
            else:
                search_text = search_text.lower()
                self.filtered_cameras = [
                    camera for camera in self.cameras
                    if search_text in camera.get('name', '').lower() or
                       search_text in camera.get('location', '').lower() or
                       search_text in camera.get('ip_address', '').lower()
                ]
            
            # Reload the display with filtered cameras
            self.load_cameras(self.filtered_cameras)
            logger.info(f"[LiveFeed] Filtered cameras: {len(self.filtered_cameras)}/{len(self.cameras)}")
            
        except Exception as e:
            logger.error(f"[LiveFeed] Error filtering cameras: {e}")

    def refresh_cameras(self):
        """Refresh cameras from database (for external calls)"""
        try:
            logger.info("[LiveFeed] External refresh_cameras called")
            self.reload_cameras_from_database()
        except Exception as e:
            logger.error(f"[LiveFeed] Error in refresh_cameras: {e}")

    def set_active_camera(self, camera_id):
        """Set a specific camera as active/highlighted"""
        try:
            logger.info(f"[LiveFeed] Setting active camera: {camera_id}")
            # Find the camera and highlight it
            for cam in self.cameras:
                if cam.get('id') == camera_id:
                    logger.info(f"[LiveFeed] Found camera to highlight: {cam.get('name')}")
                    # You could add highlighting logic here
                    break
        except Exception as e:
            logger.error(f"[LiveFeed] Error setting active camera: {e}")

    def highlight_approved_camera(self, camera_id):
        """Highlight a newly approved camera"""
        try:
            logger.info(f"[LiveFeed] Highlighting approved camera: {camera_id}")
            if camera_id in self.camera_widgets:
                widget = self.camera_widgets[camera_id]
                # Add visual highlight effect
                widget.setStyleSheet(widget.styleSheet() + """
                    #liveFeedWidget {
                        border: 3px solid #4CAF50;
                        animation: pulse 2s;
                    }
                """)
                
                # Remove highlight after 3 seconds
                QTimer.singleShot(3000, lambda: self.remove_highlight(camera_id))
                
        except Exception as e:
            logger.error(f"[LiveFeed] Error highlighting camera: {e}")

    def remove_highlight(self, camera_id):
        """Remove highlight from camera"""
        try:
            if camera_id in self.camera_widgets:
                widget = self.camera_widgets[camera_id]
                # Reset stylesheet to original
                widget.setStyleSheet("""
                    #liveFeedWidget {
                        background-color: white;
                        border-radius: 8px;
                        margin: 5px;
                    }
                    #feedContainer {
                        position: relative;
                        border-radius: 8px;
                    }
                    #cameraFeed {
                        border-radius: 8px;
                    }
                """)
        except Exception as e:
            logger.error(f"[LiveFeed] Error removing highlight: {e}")

    def handle_new_yolo_topic(self, topic):
        """
        Called when a new /yolo/<videoX>/image_raw topic is detected.
        Map it to the correct camera_id based on exact device match.
        """
        try:
            logger.info(f"[LiveFeed] Handling new YOLO topic: {topic}")
            
            # Extract video device number from topic: /yolo/video1/image_raw -> "1"
            topic_parts = topic.split('/')
            if len(topic_parts) < 3:
                logger.error(f"Invalid topic format: {topic}")
                return
                
            video_name = topic_parts[2].lower()  # e.g. video1, video10, video13
            if not video_name.startswith("video"):
                logger.error(f"Invalid video topic format: {topic}")
                return
                
            topic_num = video_name.replace("video", "")  # Extract number part
            logger.info(f"[LiveFeed] Extracted device number from topic: {topic_num}")
            
            # Map to ALL cameras (not just active ones) that match device
            for cam in self.cameras:
                ip_addr = (cam.get("ip_address") or "").lower()
                cam_name = (cam.get("name") or "").lower()
                
                logger.debug(f"[LiveFeed] Checking camera: {cam_name} with IP: {ip_addr}")
                
                # Extract video device number from ip_address for exact matching
                if "/dev/video" in ip_addr:
                    device_num = ip_addr.replace("/dev/video", "")
                    logger.debug(f"[LiveFeed] Camera device number: {device_num}, topic number: {topic_num}")
                    
                    # Exact match only - ensure topic_num matches device_num exactly
                    if device_num == topic_num:
                        # Check if this topic is already mapped
                        if topic in self.topic_to_camera_id:
                            logger.debug(f"Topic {topic} already mapped to camera {self.topic_to_camera_id[topic]}")
                            return
                        
                        self.topic_to_camera_id[topic] = cam["id"]
                        logger.info(f"✅ Mapped YOLO topic {topic} to camera '{cam.get('name')}' (id={cam['id']}, device=/dev/video{device_num})")
                        return
                
                # Fallback: check AutoCam names with exact video number match
                elif "autocam" in cam_name and f"video{topic_num}" in cam_name:
                    # Check if this topic is already mapped
                    if topic in self.topic_to_camera_id:
                        logger.debug(f"Topic {topic} already mapped to camera {self.topic_to_camera_id[topic]}")
                        return
                    
                    self.topic_to_camera_id[topic] = cam["id"]
                    logger.info(f"✅ Mapped YOLO topic {topic} to camera '{cam.get('name')}' (id={cam['id']}) via name matching")
                    return
            
            # If no mapping found, log warning
            logger.warning(f"❌ No camera found for YOLO topic {topic} (device number: {topic_num})")
            
        except Exception as e:
            logger.error(f"Error handling YOLO topic {topic}: {e}")
            import traceback
            traceback.print_exc()

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        self.content_widget = QWidget()
        self.content_widget.setObjectName("contentWidget")
        
        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(0)
        
        header_container = QWidget()
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        header_layout.addStretch()
        
        content_layout.addWidget(header_container)
        
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        
        self.cameras_grid = QGridLayout()
        self.cameras_grid.setSpacing(20)
        self.load_cameras()
        scroll_layout.addLayout(self.cameras_grid, 0)
        scroll_layout.addStretch(1)
        
        scroll_area = QScrollArea()
        scroll_area.setObjectName("feedScrollArea")
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(scroll_content)
        scroll_area.setFrameShape(QFrame.NoFrame)
        content_layout.addWidget(scroll_area)
        
        self.main_layout.addWidget(self.content_widget)
        
        self.setStyleSheet("""
            #contentWidget {
                background-color: #f5f5f5;
            }
            #liveFeedWidget {
                background-color: white;
                border-radius: 8px;
            }
            #cameraFeed {
                background-color: #313131;
                color: white;
                border-radius: 4px;
            }
            #statusIndicator {
                min-width: 12px;
                min-height: 12px;
                border-radius: 6px;
            }
            #statusText {
                color: #555;
                font-size: 13px;
            }
            #expandButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px 10px;
            }
            #expandButton:hover {
                background-color: #1976D2;
            }
            #searchBox {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 8px;
            }
            #cameraName {
                font-weight: bold;
                color: #333;
            }
        """)
    
    def load_cameras(self, cameras=None):
        """
        Charge et affiche les caméras dans la grille.
        Si cameras est None, utilise self.filtered_cameras.
        """
        try:
            # Clear existing widgets safely
            for i in reversed(range(self.cameras_grid.count())):
                item = self.cameras_grid.itemAt(i)
                if item and item.widget():
                    widget = item.widget()
                    widget.deleteLater()
                    self.cameras_grid.removeItem(item)

            if cameras is None:
                cameras = self.filtered_cameras

            self.camera_widgets = {}  # Clear widgets dict

            # Only add cameras that have valid data
            valid_cameras = []
            for camera in cameras:
                if isinstance(camera, dict) and camera.get("id") and camera.get("name"):
                    valid_cameras.append(camera)
                else:
                    logger.warning(f"Invalid camera data: {camera}")

            for i, camera in enumerate(valid_cameras):
                row = i // 2
                col = i % 2
                try:
                    camera_feed = CameraFeedWidget(camera)
                    camera_feed.expand_clicked.connect(self.expand_camera)
                    self.cameras_grid.addWidget(camera_feed, row, col)
                    self.camera_widgets[camera["id"]] = camera_feed
                except Exception as e:
                    logger.error(f"Error creating camera widget for {camera.get('name')}: {e}")
                    
        except Exception as e:
            logger.error(f"Error loading cameras: {e}")
            import traceback
            traceback.print_exc()

    def reload_cameras_from_database(self):
        """
        Reload cameras from database and update internal camera list
        """
        try:
            logger.info("[LiveFeed] Reloading cameras from database...")
            
            # Reload cameras from database
            if self.camera_service:
                all_cameras = self.camera_service.get_all_cameras()
                # FIXED: Load ALL approved cameras, not just active ones
                self.cameras = [camera_to_dict(cam) for cam in all_cameras if cam and hasattr(cam, 'id')]
                self.filtered_cameras = self.cameras
                logger.info(f"[LiveFeed] Loaded {len(self.cameras)} cameras from database (all approved)")
                
                # Force refresh the approved cameras list in camera detector
                if camera_detector:
                    camera_detector.refresh_approved_cameras()
                    logger.info("[LiveFeed] Refreshed camera detector's approved cameras list")
                
                # Clean up invalid topic mappings
                self.clean_topic_mappings()
                
                # Force remapping of YOLO topics for newly approved cameras
                self.force_topic_remapping()
                
                # Reload the camera widgets
                self.load_cameras()
                
                logger.info("[LiveFeed] Camera reload completed successfully")
            else:
                logger.error("[LiveFeed] Camera service not available")
                
        except Exception as e:
            logger.error(f"[LiveFeed] Error reloading cameras from database: {e}")
            import traceback
            traceback.print_exc()

    def on_camera_updated(self, updated_camera_dict):
        """
        Gestionnaire appelé quand une caméra est modifiée depuis Settings
        """
        try:
            camera_id = updated_camera_dict.get("id")
            logger.info(f"[LiveFeed] Camera updated signal received for camera {camera_id}: {updated_camera_dict}")
            
            # Mettre à jour la caméra dans la liste locale
            for i, camera in enumerate(self.cameras):
                if camera.get("id") == camera_id:
                    # Mettre à jour les données de la caméra
                    self.cameras[i].update(updated_camera_dict)
                    logger.info(f"[LiveFeed] Updated camera data in local list: {self.cameras[i]}")
                    break
            
            # Aussi mettre à jour la liste filtrée si elle existe
            for i, camera in enumerate(self.filtered_cameras):
                if camera.get("id") == camera_id:
                    self.filtered_cameras[i].update(updated_camera_dict)
                    break
            
            # Recharger l'affichage pour refléter les changements
            self.load_cameras(self.filtered_cameras)
            logger.info(f"[LiveFeed] UI refreshed after camera update")
            
        except Exception as e:
            logger.error(f"[LiveFeed] Error handling camera update: {e}")
            import traceback
            traceback.print_exc()

    def on_camera_status_changed(self, status_change_dict):
        """
        Gestionnaire appelé quand le statut d'une caméra change depuis Settings
        """
        try:
            camera_id = status_change_dict.get("id")
            new_status = status_change_dict.get("is_active")
            logger.info(f"[LiveFeed] Camera status changed signal received for camera {camera_id}: active={new_status}")
            
            # Mettre à jour le statut dans la liste locale
            for i, camera in enumerate(self.cameras):
                if camera.get("id") == camera_id:
                    self.cameras[i]["is_active"] = new_status
                    logger.info(f"[LiveFeed] Updated camera status in local list: {self.cameras[i]}")
                    break
            
            # Aussi mettre à jour la liste filtrée
            for i, camera in enumerate(self.filtered_cameras):
                if camera.get("id") == camera_id:
                    self.filtered_cameras[i]["is_active"] = new_status
                    break
            
            # Mettre à jour le widget spécifique si il existe
            if camera_id in self.camera_widgets:
                widget = self.camera_widgets[camera_id]
                if hasattr(widget, 'camera'):
                    widget.camera["is_active"] = new_status
                    widget.update_status_indicator()
                    logger.info(f"[LiveFeed] Updated status indicator for camera widget {camera_id}")
                    
        except Exception as e:
            logger.error(f"[LiveFeed] Error handling camera status change: {e}")
            import traceback
            traceback.print_exc()

    def refresh_cameras_from_database(self, approved_camera_dict=None):
        """
        Rafraîchir les caméras depuis la base de données après l'approbation d'une nouvelle caméra.
        Cette méthode est appelée via le signal camera_approved_signal.
        """
        try:
            if approved_camera_dict:
                logger.info(f"[LiveFeed] Nouvelle caméra approuvée: {approved_camera_dict}")
            else:
                logger.info("[LiveFeed] Rafraîchissement des caméras depuis la base de données")
            
            # Use the new reload method
            self.reload_cameras_from_database()
            
            # Si une caméra spécifique a été approuvée, la mettre en évidence
            if approved_camera_dict and approved_camera_dict.get("id"):
                camera_id = approved_camera_dict["id"]
                logger.info(f"[LiveFeed] Mise en évidence de la caméra approuvée: {camera_id}")
                
                # Attendre un peu pour que l'UI se mette à jour
                QTimer.singleShot(500, lambda: self.highlight_approved_camera(camera_id))
            
        except Exception as e:
            logger.error(f"[LiveFeed] Erreur lors du rafraîchissement après approbation: {e}")
            import traceback
            traceback.print_exc()

    def clean_topic_mappings(self):
        """
        Nettoie les mappings de topics pour les caméras qui ne sont plus approuvées
        """
        try:
            valid_camera_ids = {cam["id"] for cam in self.cameras}
            invalid_topics = []
            
            for topic, camera_id in self.topic_to_camera_id.items():
                if camera_id not in valid_camera_ids:
                    invalid_topics.append(topic)
            
            for topic in invalid_topics:
                camera_id = self.topic_to_camera_id[topic]
                del self.topic_to_camera_id[topic]
                logger.info(f"Removed invalid topic mapping: {topic} -> camera_id {camera_id}")
            
            logger.debug(f"Cleaned {len(invalid_topics)} invalid topic mappings")
            
        except Exception as e:
            logger.error(f"Error cleaning topic mappings: {e}")

    def force_yolo_topic_check(self):
        """
        Force une vérification immédiate des topics YOLO disponibles
        Utilisé après l'approbation d'une nouvelle caméra
        """
        try:
            if hasattr(self, 'ros_bridge') and self.ros_bridge:
                logger.info("[LiveFeed] Forcing YOLO topic check after camera approval")
                if hasattr(self.ros_bridge, 'force_topic_check'):
                    self.ros_bridge.force_topic_check(self.handle_new_yolo_topic)
                else:
                    logger.warning("[LiveFeed] ROSImageBridge doesn't have force_topic_check method")
            else:
                logger.warning("[LiveFeed] No ROS bridge available for topic check")
        except Exception as e:
            logger.error(f"[LiveFeed] Error forcing YOLO topic check: {e}")
    
    def force_topic_remapping(self):
        """
        Force le remapping des topics YOLO avec les caméras approuvées
        """
        try:
            logger.info("[LiveFeed] Forçage du remapping des topics YOLO...")
            
            # Clear old mappings for non-existent cameras
            self.clean_topic_mappings()
            
            # Check each camera and try to map its expected YOLO topic
            for camera in self.cameras:
                ip_address = camera.get('ip_address', '')
                camera_id = camera.get('id')
                camera_name = camera.get('name', 'Unknown')
                
                logger.info(f"[LiveFeed] Processing camera {camera_name} (ID: {camera_id}, IP: {ip_address})")
                
                if '/dev/video' in ip_address:
                    device_num = ip_address.replace('/dev/video', '')
                    expected_topic = f'/yolo/video{device_num}/image_raw'
                    
                    logger.info(f"[LiveFeed] Expected YOLO topic for camera {camera_id}: {expected_topic}")
                    
                    # Update the mapping regardless of current active status
                    self.topic_to_camera_id[expected_topic] = camera_id
                    logger.info(f"[LiveFeed] ✅ Mapped {expected_topic} to camera {camera_id} ({camera_name})")
                        
                elif 'autocam' in camera_name.lower() and 'video' in camera_name.lower():
                    # Try to extract video number from camera name
                    import re
                    match = re.search(r'video(\d+)', camera_name.lower())
                    if match:
                        device_num = match.group(1)
                        expected_topic = f'/yolo/video{device_num}/image_raw'
                        
                        # Update the mapping
                        self.topic_to_camera_id[expected_topic] = camera_id
                        logger.info(f"[LiveFeed] ✅ Mapped {expected_topic} to camera {camera_id} ({camera_name}) via name matching")
            
            # Force ROS bridge to check for these topics
            if hasattr(self, 'ros_bridge') and self.ros_bridge:
                self.ros_bridge.force_topic_check(self.handle_new_yolo_topic)
                logger.info("[LiveFeed] Forced ROS bridge topic check")
            
            logger.info(f"[LiveFeed] Topic remapping completed. Current mappings: {self.topic_to_camera_id}")
                            
        except Exception as e:
            logger.error(f"[LiveFeed] Error forcing topic remapping: {e}")
            import traceback
            traceback.print_exc()

    def update_camera_feed(self, camera_id, pixmap):
        """
        Update a specific camera feed with new frame from ROS topic
        """
        try:
            logger.debug(f"[LiveFeed] Updating camera {camera_id} with new frame")
            
            if camera_id in self.camera_widgets:
                widget = self.camera_widgets[camera_id]
                widget.update_feed(pixmap)
                # Emit the frame_updated signal for dashboard
                self.frame_updated.emit(camera_id, pixmap)
                
                # Also update expanded view if this camera is expanded
                if (hasattr(self, 'expanded_camera_widget') and 
                    self.expanded_camera_widget and 
                    hasattr(self.expanded_camera_widget, 'camera_data') and
                    self.expanded_camera_widget.camera_data.get('id') == camera_id):
                    self.expanded_camera_widget.update_feed(pixmap)
                    
                logger.debug(f"[LiveFeed] ✅ Updated feed for camera {camera_id}")
                return True
            else:
                logger.warning(f"[LiveFeed] Camera widget not found for ID {camera_id}")
                return False
                
        except Exception as e:
            logger.error(f"[LiveFeed] Error updating camera feed for {camera_id}: {e}")
            return False

    def expand_camera(self, camera_id):
        """Expand the selected camera feed."""
        try:
            # Find camera data by ID instead of using index
            camera_data = None
            for cam in self.cameras:
                if cam.get('id') == camera_id:
                    camera_data = cam
                    break
            
            if not camera_data:
                logger.error(f"Camera data not found for ID {camera_id}")
                return
                
            # Get current pixmap from widget
            pixmap = None
            if camera_id in self.camera_widgets:
                widget = self.camera_widgets[camera_id]
                if hasattr(widget, 'current_pixmap'):
                    pixmap = widget.current_pixmap
                    
            self.expanded_camera_widget = ExpandedCameraWidget(camera_data=camera_data, pixmap=pixmap)
            self.expanded_camera_widget.close_clicked.connect(self.close_expanded_camera)
            self.expanded_camera_widget.show()
            
            logger.info(f"[LiveFeed] Expanded camera {camera_id} ({camera_data.get('name', 'Unknown')})")
            
        except Exception as e:
            logger.error(f"[LiveFeed] Error expanding camera {camera_id}: {e}")
            import traceback
            traceback.print_exc()

    def close_expanded_camera(self):
        """Close the expanded camera view"""
        try:
            if hasattr(self, 'expanded_camera_widget') and self.expanded_camera_widget:
                self.expanded_camera_widget.close()
                self.expanded_camera_widget = None
                logger.info("[LiveFeed] Closed expanded camera view")
        except Exception as e:
            logger.error(f"[LiveFeed] Error closing expanded camera: {e}")