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
from database import get_session

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
        self.db_session = get_session()  # Initialize database session
        self.camera_service = CameraService(self.db_session)  # CameraService instance
        self.cameras = [camera_to_dict(cam) for cam in self.camera_service.get_all_cameras()]
        self.filtered_cameras = self.cameras  # Ajouté: liste filtrée
        self.camera_widgets = {}
        self.expanded_camera_widget = None
        self.ros_node = ros_node
        self.detected_cameras = set()  # Track detected camera device paths
        self.ros_camera_sub = None
        self.topic_to_camera_id = {}  # Map ROS topic to camera.id
        
        self.init_ui()

        # Use provided ROSImageBridge or create a new one
        self.ros_bridge = ros_bridge or ROSImageBridge(ros_node)
        
        # --- Subscribe to all /yolo/*/image_raw topics dynamically ---
        self.ros_bridge.image_received.connect(self.update_cam_a_feed, Qt.QueuedConnection)
        if ros_node:
            self.ros_bridge.subscribe_to_yolo_topics(self.handle_new_yolo_topic)

        # Subscribe to /camera/list for auto-detection
        if ros_node:
            self.ros_camera_sub = ros_node.create_subscription(
                ROSString, '/camera/list', self.handle_camera_list, 10
            )
    
    def handle_camera_list(self, msg):
        """
        Callback for /camera/list topic. Shows popup for new cameras.
        """
        try:
            data = json.loads(msg.data)
            devices = data.get('cameras', [])
            new_devices = []
            for dev in devices:
                # Check if device is already in DB (by ip_address)
                already_in_db = any(
                    (cam.get("ip_address") or "").strip() == dev.strip()
                    for cam in self.cameras
                )
                if not already_in_db and dev not in self.detected_cameras:
                    new_devices.append(dev)
            if not new_devices:
                return
            for dev in new_devices:
                self.detected_cameras.add(dev)
                self.show_camera_approval_dialog(dev)
        except Exception as e:
            logger.error(f"Error handling camera list: {e}")

    def show_camera_approval_dialog(self, device_path):
        """
        Show a popup to approve a newly detected camera.
        """
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QDialogButtonBox

        dialog = QDialog(self)
        dialog.setWindowTitle("New Camera Detected")
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel(f"Detected camera device: <b>{device_path}</b>"))
        layout.addWidget(QLabel("Approve and add this camera to the system?"))
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        if dialog.exec_() == QDialog.Accepted:
            # Add camera to DB
            try:
                cam_name = f"AutoCam {device_path.split('/')[-1]}"
                new_cam = self.camera_service.add_camera({
                    "name": cam_name,
                    "ip_address": device_path,
                    "port": None,
                    "location": "Auto-detected",
                    "rtsp_url": "",  # Could be filled if needed
                    "is_active": True
                })
                cam_dict = camera_to_dict(new_cam)
                self.cameras.append(cam_dict)
                self.filtered_cameras = self.cameras
                self.load_cameras()
                # Map topic to camera id for feed routing
                topic = f"/camera/{device_path.split('/')[-1]}/image_raw"
                self.topic_to_camera_id[topic] = cam_dict["id"]
                logger.info(f"Camera {cam_name} added and mapped to topic {topic}")
            except Exception as e:
                logger.error(f"Failed to add auto camera: {e}")

    def handle_new_yolo_topic(self, topic):
        """
        Called when a new /yolo/<videoX>/image_raw topic is detected.
        Map it to the correct camera_id.
        """
        try:
            video_name = topic.split('/')[2].lower()  # e.g. video13
            found = False
            for cam in self.cameras:
                # Compare video_name with ip_address (e.g. /dev/video13)
                ip_addr = (cam.get("ip_address") or "").lower()
                cam_name = (cam.get("name") or "").lower()
                # Accept match if video_name in ip_address or in cam_name (ignore spaces)
                if video_name in ip_addr.replace("/dev/", "") or video_name in cam_name.replace(" ", ""):
                    self.topic_to_camera_id[topic] = cam["id"]
                    logger.info(f"Mapped YOLO topic {topic} to camera '{cam.get('name')}' (id={cam['id']})")
                    found = True
                    break
            if not found:
                logger.warning(f"No camera found for YOLO topic {topic} (video_name={video_name})")
        except Exception as e:
            logger.error(f"Error mapping yolo topic {topic}: {e}")

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
        scroll_layout.addLayout(self.cameras_grid)
        scroll_layout.addStretch()
        
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
        for i in reversed(range(self.cameras_grid.count())):
            item = self.cameras_grid.itemAt(i)
            if item.widget():
                item.widget().deleteLater()

        if cameras is None:
            cameras = self.filtered_cameras

        self.camera_widgets = {}  # Réinitialiser les widgets

        for i, camera in enumerate(cameras):
            row = i // 2
            col = i % 2
            camera_feed = CameraFeedWidget(camera)
            camera_feed.expand_clicked.connect(self.expand_camera)
            self.cameras_grid.addWidget(camera_feed, row, col)

            self.camera_widgets[camera["id"]] = camera_feed

    def filter_cameras(self, text):
        """
        Filtre les caméras selon le texte (nom ou localisation).
        """
        text = text.strip().lower()
        if not text:
            self.filtered_cameras = self.cameras
        else:
            self.filtered_cameras = [
                cam for cam in self.cameras
                if text in (cam.get("name") or '').lower() or text in (cam.get("location") or '').lower()
            ]
        self.load_cameras(self.filtered_cameras)

    def expand_camera(self, camera_id):
        try:
            logger.info(f"Attempting to expand camera ID: {camera_id}")
            
            camera_data = next((cam for cam in self.cameras if cam["id"] == camera_id), None)
            if not camera_data:
                logger.warning(f"Camera with ID {camera_id} not found")
                return

            camera_widget = self.camera_widgets.get(camera_id)
            if not camera_widget:
                logger.warning(f"Camera widget for ID {camera_id} not found")
                return

            pixmap = None
            if hasattr(camera_widget, 'feed_label') and hasattr(camera_widget.feed_label, 'pixmap') and camera_widget.feed_label.pixmap():
                original_pixmap = camera_widget.feed_label.pixmap()
                pixmap = QPixmap(original_pixmap)

            self.ensure_camera_streaming(camera_id)
            
            if hasattr(self, 'expanded_camera_widget') and self.expanded_camera_widget:
                self.expanded_camera_widget.close()
                self.expanded_camera_widget.deleteLater()
                self.expanded_camera_widget = None
                
            self.expanded_camera_widget = ExpandedCameraWidget({
                "id": camera_data["id"],
                "name": camera_data["name"],
                "location": camera_data["location"],
                "connected": camera_data.get("is_active", False),
                "image_path": camera_data.get("image_path", "")
            }, pixmap)
            
            self.expanded_camera_widget.camera_id = camera_id
            
            self.expanded_camera_widget.close_clicked.connect(self.close_expanded_camera)

            self.main_layout.addWidget(self.expanded_camera_widget)

            self.content_widget.setVisible(False)
            
            if hasattr(self, 'ros_bridge') and self.ros_bridge:
                try:
                    self.ros_bridge.image_received.disconnect(self.update_expanded_cam_feed)
                except:
                    pass
                
                self.ros_bridge.image_received.connect(self.update_expanded_cam_feed, Qt.QueuedConnection)
                logger.info(f"Connected image_received signal to expanded view for camera {camera_id}")

            logger.info(f"Camera {camera_data['name']} expanded successfully")
        except Exception as e:
            logger.error(f"Error expanding camera: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())

    def close_expanded_camera(self):
        if self.expanded_camera_widget:
            try:
                self.ros_bridge.image_received.disconnect(self.update_expanded_cam_feed)
            except:
                pass
            
            self.expanded_camera_widget.deleteLater()
            self.expanded_camera_widget = None
            
            self.content_widget.setVisible(True)
            
            logger.info("Expanded view closed")

    def update_expanded_cam_feed(self, cv_image):
        if self.expanded_camera_widget is None or not hasattr(self.expanded_camera_widget, 'feed_container'):
            return
            
        try:
            height, width, channel = cv_image.shape
            bytes_per_line = 3 * width
            
            rgb_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
            
            q_image = QImage(rgb_image.data, width, height, bytes_per_line, QImage.Format_RGB888)
            
            pixmap = QPixmap.fromImage(q_image)
            
            QMetaObject.invokeMethod(
                self.expanded_camera_widget,
                "update_feed",
                Qt.QueuedConnection,
                Q_ARG(QPixmap, pixmap)
            )
            
            if hasattr(self.expanded_camera_widget, 'camera_id'):
                camera_id = self.expanded_camera_widget.camera_id
                if camera_id in self.camera_widgets:
                    QMetaObject.invokeMethod(
                        self.camera_widgets[camera_id],
                        "update_feed",
                        Qt.QueuedConnection,
                        Q_ARG(QPixmap, pixmap)
                    )
            
        except Exception as e:
            logger.error(f"Error updating expanded feed: {str(e)}")

    def ensure_camera_streaming(self, camera_id):
        try:
            if hasattr(self, 'ros_bridge') and self.ros_bridge:
                if hasattr(self.ros_bridge, 'restart_camera_feed'):
                    self.ros_bridge.restart_camera_feed(camera_id)
                else:
                    logger.info(f"Ensuring camera {camera_id} is streaming")
                    if hasattr(self.ros_bridge, 'start_camera'):
                        self.ros_bridge.start_camera(camera_id)
            
            logger.info(f"Camera {camera_id} streaming ensured")
        except Exception as e:
            logger.error(f"Error ensuring camera streaming: {str(e)}")

    def set_active_camera(self, camera_id):
        try:
            logger.info(f"Setting active camera to ID: {camera_id}")
            self.active_camera_id = camera_id
            
            camera_data = next((cam for cam in self.cameras if cam["id"] == camera_id), None)
            if not camera_data:
                logger.warning(f"Camera with ID {camera_id} not found")
                return
            
            logger.info(f"Found camera: {camera_data['name']}")
            
            if not camera_data.get("is_active", False):
                try:
                    self.camera_service.set_camera_active(camera_id, True)
                    camera_data["is_active"] = True
                    logger.info(f"Activated camera {camera_id}")
                except Exception as e:
                    logger.error(f"Failed to activate camera: {str(e)}")
            
            self.ensure_camera_streaming(camera_id)
            
            self.highlight_camera(camera_id)
            
        except Exception as e:
            logger.error(f"Error setting active camera: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())

    def highlight_camera(self, camera_id):
        try:
            for cam_widget in self.camera_widgets.values():
                cam_widget.setStyleSheet("""
                    QFrame#liveFeedWidget {
                        background-color: white;
                        border-radius: 8px;
                        margin: 5px;
                    }
                    QFrame#liveFeedWidget:hover {
                        border: 1px solid #2196F3;
                        background-color: #e3f2fd;
                    }
                """)
            
            if camera_id in self.camera_widgets:
                self.camera_widgets[camera_id].setStyleSheet("""
                    QFrame#liveFeedWidget {
                        background-color: #e3f2fd;
                        border: 2px solid #2196F3;
                        border-radius: 8px;
                        margin: 5px;
                    }
                    QFrame#liveFeedWidget:hover {
                        background-color: #bbdefb;
                        border: 2px solid #1976D2;
                    }
                """)
                logger.info(f"Highlighted camera with ID: {camera_id}")
            
            self.update()
            
        except Exception as e:
            logger.error(f"Error highlighting camera: {str(e)}")

    def load_camera_feed(self, camera_id):
        try:
            logger.info(f"Loading feed for camera ID: {camera_id}")
            
            self.active_camera_id = camera_id
            
            self.highlight_camera(camera_id)
            
        except Exception as e:
            logger.error(f"Error loading camera feed: {str(e)}")

    def update_cam_a_feed(self, cv_image, topic=None):
        """
        Update the correct camera widget based on YOLO topic.
        Also update the camera status in the database (is_active=True).
        """
        try:
            camera_id = None
            if topic and topic in self.topic_to_camera_id:
                camera_id = self.topic_to_camera_id[topic]
            else:
                cam_a = next((camera for camera in self.cameras if camera.get("name") == "Cam A"), None)
                if not cam_a:
                    similar_cam = next((camera for camera in self.cameras 
                                      if "cam" in (camera.get("name") or '').lower() and "a" in (camera.get("name") or '').lower()), None)
                    if similar_cam:
                        cam_a = similar_cam
                    else:
                        return
                camera_id = cam_a["id"]

            camera_widget = self.camera_widgets.get(camera_id)
            if not camera_widget:
                return

            # --- Mise à jour du statut dans la base de données ---
            try:
                self.camera_service.set_camera_active(camera_id, True)
                # Mets aussi à jour l'objet local pour cohérence UI
                for cam in self.cameras:
                    if cam["id"] == camera_id:
                        cam["is_active"] = True
            except Exception as e:
                logger.error(f"Failed to set camera active in DB: {e}")

            resized_image = cv2.resize(cv_image, (640, 360))
            height, width, channel = resized_image.shape
            bytes_per_line = 3 * width
            
            rgb_image = cv2.cvtColor(resized_image, cv2.COLOR_BGR2RGB)
            
            q_image = QImage(rgb_image.data, width, height, bytes_per_line, QImage.Format_RGB888)
            
            pixmap = QPixmap.fromImage(q_image)
            
            camera_widget.update_feed(pixmap)
            
            self.frame_updated.emit(camera_id, pixmap)
        except Exception as e:
            logger.error(f"Error updating feed for camera: {str(e)}")

    def feed_timeout_handler(self, camera_id):
        """
        Call this when a camera feed times out (no frame received).
        Update the DB and local state to inactive, and emit feed_stopped.
        """
        try:
            self.camera_service.set_camera_active(camera_id, False)
            for cam in self.cameras:
                if cam["id"] == camera_id:
                    cam["is_active"] = False
            self.feed_stopped.emit(camera_id)
        except Exception as e:
            logger.error(f"Error setting camera inactive on timeout: {str(e)}")

    def closeEvent(self, event):
        self.db_session.close()
        super().closeEvent(event)