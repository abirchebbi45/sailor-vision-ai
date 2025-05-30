from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QGridLayout, QFrame, QScrollArea,
                            QSpacerItem, QSizePolicy, QCheckBox, QGraphicsOpacityEffect)
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QTimer, QEvent, QDateTime
from PyQt5.QtGui import QPixmap, QIcon, QColor, QFont, QPainter, QPen

from src.services.camera_service import CameraService
from models import Camera, Alert, SystemLog
from src.components.shared import HeaderWidget, Sidebar
from database import get_session, close_session
from datetime import datetime
from PyQt5.QtWidgets import QMessageBox
import logging

logger = logging.getLogger(__name__)


class EnhancedCameraWidget(QFrame):
    clicked = pyqtSignal(int)  # Signal to emit when the widget is clicked

    def __init__(self, camera):
        super().__init__()
        # Store only primitive fields, not the ORM object
        self.camera_id = camera.id
        self.name = getattr(camera, "name", "Unknown")
        self.location = getattr(camera, "location", "Unknown Location")
        self.is_active = getattr(camera, "is_active", False)
        self.placeholder_image = getattr(camera, "placeholder_image", None)
        self.has_live_feed = False
        self.click_enabled = True  # Flag to prevent multiple clicks
        self.init_ui()
        self.setCursor(Qt.PointingHandCursor)  # Change cursor to hand on hover
        self.installEventFilter(self)  # Install event filter for hover effects

    def init_ui(self):
        self.setObjectName("cameraWidget")
        self.setFixedSize(240, 160)  # Further reduced size for smaller widgets
        self.setFrameShape(QFrame.StyledPanel)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)  # Remove spacing
        
        # Camera feed container
        feed_container = QWidget()
        feed_container.setObjectName("cameraFeed")
        feed_container.setFixedHeight(100)  # Reduced height for the feed container
        
        feed_layout = QVBoxLayout(feed_container)
        feed_layout.setContentsMargins(0, 0, 0, 0)
        
        # Feed placeholder (in real app, this would be a video feed)
        self.feed_label = QLabel()
        self.feed_label.setAlignment(Qt.AlignCenter)
        self.feed_label.setStyleSheet("color: white; background-color: #313131;")
        
        # Set placeholder image or text
        if self.placeholder_image:
            pixmap = QPixmap(self.placeholder_image)
            self.feed_label.setPixmap(pixmap.scaled(
                240, 100,  # Adjusted to match the smaller widget size
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            ))
        else:
            self.feed_label.setText("Camera Feed")
        
        feed_layout.addWidget(self.feed_label)
        layout.addWidget(feed_container)
        
        # --- Fix: Add a large stretch to push info text to the bottom ---
        layout.addStretch(1)
        layout.addSpacing(4)  # Small gap between black screen and text

        # Camera info panel
        info_container = QWidget()
        info_container.setObjectName("cameraInfo")
        info_layout = QVBoxLayout(info_container)
        info_layout.setContentsMargins(5, 4, 5, 4)
        info_layout.setSpacing(1)

        # Camera name and location on the same line, separated by a dot
        name = self.name or "Unknown"
        location = self.location or "Unknown Location"
        name_location_label = QLabel(f"{name} · {location}")
        name_location_label.setObjectName("cameraNameLocationLabel")
        name_font = name_location_label.font()
        name_font.setBold(True)
        name_font.setPointSize(10)
        name_location_label.setFont(name_font)
        info_layout.addWidget(name_location_label)

        # Status with colored indicator (unchanged)
        status_container = QWidget()
        status_layout = QHBoxLayout(status_container)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(5)
        status_indicator = QLabel()
        status_indicator.setFixedSize(5, 5)
        if self.is_active:
            status_indicator.setStyleSheet("background-color: #4CAF50; border-radius: 2.5px;")
        else:
            status_indicator.setStyleSheet("background-color: #F44336; border-radius: 2.5px;")
        status_text = QLabel(f"Status: {'Active' if self.is_active else 'Inactive'}")
        status_text.setStyleSheet("color: #757575; font-size: 9px;")
        status_layout.addWidget(status_indicator)
        status_layout.addWidget(status_text)
        status_layout.addStretch()
        info_layout.addWidget(status_container)
        layout.addWidget(info_container)

        self.setStyleSheet("""
            QFrame#cameraWidget {
                border: 1px solid #ccc;
                border-radius: 8px;
                background-color: #f9f9f9;
            }
            QFrame#cameraWidget:hover {
                border: 1px solid #2196F3;
                background-color: #e3f2fd;
            }
            QLabel#cameraNameLocationLabel {
                font-weight: bold;
                font-size: 10px;
                color: #333;
            }
        """)

    def update_frame(self, pixmap):
        """Update the feed with a new video frame"""
        if pixmap and not pixmap.isNull():
            self.has_live_feed = True
            self.feed_label.setPixmap(pixmap.scaled(
                240, 100,  # Match widget dimensions
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            ))
        else:
            self.reset_to_default()
    
    def reset_to_default(self):
        """Reset to default placeholder when feed stops"""
        self.has_live_feed = False
        if self.placeholder_image:
            pixmap = QPixmap(self.placeholder_image)
            self.feed_label.setPixmap(pixmap.scaled(
                240, 100,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            ))
        else:
            self.feed_label.setText("Camera Feed")
            self.feed_label.setStyleSheet("color: white; background-color: #313131;")

    def mousePressEvent(self, event):
        """Emit the clicked signal with the camera ID when the widget is clicked."""
        if event.button() == Qt.LeftButton and self.click_enabled:
            logger.info(f"Camera widget clicked: {self.camera_id}")
            self.click_enabled = False  # Disable clicking temporarily
            self.clicked.emit(self.camera_id)
            
            # Re-enable clicking after a short delay
            QTimer.singleShot(500, self.enable_click)
    
    def enable_click(self):
        """Re-enable clicking after a timeout."""
        self.click_enabled = True

    def eventFilter(self, source, event):
        """Handle hover events to add visual feedback."""
        if event.type() == QEvent.Enter:
            self.setGraphicsEffect(QGraphicsOpacityEffect(opacity=0.9))
        elif event.type() == QEvent.Leave:
            self.setGraphicsEffect(None)
        return super().eventFilter(source, event)

class AlertWidget(QFrame):
    def __init__(self, alert_data):
        super().__init__()
        self.alert_data = alert_data
        self.init_ui()
        
    def init_ui(self):
        self.setObjectName("alertItem")
        self.setFrameShape(QFrame.StyledPanel)
        self.setMaximumHeight(70)  # Make alert items smaller to match design
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        
        # Left part - alert info
        alert_info = QVBoxLayout()
        alert_info.setSpacing(3)
        
        # Alert type with formatting
        alert_type = QLabel(self.alert_data["type"])
        alert_type.setObjectName("alertType")
        type_font = alert_type.font()
        type_font.setBold(True)
        alert_type.setFont(type_font)
        alert_info.addWidget(alert_type)
        
        # Alert description with location
        desc_label = QLabel(f"{self.alert_data.get('description', '')} • {self.alert_data.get('location', '')}")
        desc_label.setObjectName("alertDescription")
        alert_info.addWidget(desc_label)
        
        # Timestamp
        if "timestamp" in self.alert_data:
            timestamp = QLabel(self.alert_data["timestamp"])
        else:
            timestamp = QLabel(f"{self.alert_data.get('time_ago', '2 mins')} ago")
        timestamp.setObjectName("alertTimestamp")
        timestamp.setStyleSheet("color: #757575; font-size: 11px;")
        alert_info.addWidget(timestamp)
        
        layout.addLayout(alert_info)
        layout.addStretch()
        
        # Button styled to match design
        acknowledge_btn = QPushButton("Acknowledge Alert")
        acknowledge_btn.setObjectName("acknowledgeButton")
        acknowledge_btn.setCursor(Qt.PointingHandCursor)
        acknowledge_btn.setFixedWidth(130)
        acknowledge_btn.setStyleSheet("""
            #acknowledgeButton {
                background-color: #2196F3;
                color: white;
                border-radius: 4px;
                padding: 6px 15px;
                border: none;
            }
            #acknowledgeButton:hover {
                background-color: #1976D2;
            }
        """)
        acknowledge_btn.clicked.connect(lambda: self.acknowledge_alert(self.alert_data.get("id")))
        layout.addWidget(acknowledge_btn)

class DashboardAlertItem(QFrame):
    """A styled alert item for the dashboard's Security Alerts section"""
    acknowledge_clicked = pyqtSignal(int)
    
    def __init__(self, alert):
        super().__init__()
        self.alert = alert
        self.init_ui()
        
    def init_ui(self):
        """Initialize the UI for the alert item."""
        self.setObjectName("alertItem")
        self.setMaximumHeight(70)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 8, 15, 8)
        layout.setSpacing(12)
        
        # Left: Information
        info = QVBoxLayout()
        info.setSpacing(2)
        
        # 1) Alert type
        alert_type = self.alert.type
        if not isinstance(alert_type, str):
            alert_type = alert_type.value
            
        title = QLabel(alert_type)
        title.setObjectName("alertType")
        f = title.font()
        f.setBold(True)
        title.setFont(f)
        info.addWidget(title)
        
        # 2) Brief message
        message = self.alert.message
        if "\n" in message:
            message = message.split('\n')[0]  # first line only
        # Robust location extraction
        location = "Unknown"
        if self.alert.camera and getattr(self.alert.camera, "location", None):
            loc = getattr(self.alert.camera, "location", None)
            if loc:
                location = loc
        else:
            logger.debug(f"Alert {self.alert.id} has no camera location, displaying 'Unknown'")
        brief = QLabel(f"{message} • {location}")
        brief.setObjectName("alertDescription")
        info.addWidget(brief)
        
        # 3) Relative timestamp
        try:
            current_time = QDateTime.currentDateTime()
            alert_time = QDateTime.fromString(self.alert.timestamp.strftime("%Y-%m-%d %H:%M:%S"), "yyyy-MM-dd HH:mm:ss")
            minutes_ago = (current_time.toSecsSinceEpoch() - alert_time.toSecsSinceEpoch()) // 60
            time_text = f"{minutes_ago} mins ago" if minutes_ago > 0 else "Just now"
        except Exception:
            time_text = "Recent"
        time = QLabel(time_text)
        time.setObjectName("alertTimestamp")
        info.addWidget(time)
        
        layout.addLayout(info)
        layout.addStretch()
        
        # Right: Acknowledge button
        btn_ack = QPushButton("Acknowledge")
        btn_ack.setObjectName("acknowledgeButton")
        btn_ack.setCursor(Qt.PointingHandCursor)
        btn_ack.setFixedWidth(100)
        btn_ack.setStyleSheet("""
            #acknowledgeButton {
                background-color: #2196F3;
                color: white;
                border-radius: 4px;
                padding: 6px 15px;
                border: none;
            }
            #acknowledgeButton:hover {
                background-color: #1976D2;
                color: white;
            }
        """)
        btn_ack.clicked.connect(lambda: self.acknowledge_clicked.emit(self.alert.id))
        layout.addWidget(btn_ack)

class SectionFrame(QFrame):
    """Custom frame for dashboard sections with blurred background"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sectionFrame")
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet("""
            #sectionFrame {
                background-color: rgba(240, 240, 245, 0.7);
                border-radius: 8px;
                border: 1px solid rgba(220, 220, 225, 0.9);
            }
        """)

class DashboardScreen(QWidget):
    # Signal to request navigation to the alerts screen
    navigate_to_alerts = pyqtSignal()
    alerts_acknowledged = pyqtSignal()  # New signal for alert acknowledgment
    navigate_to_live_feed = pyqtSignal(int)  # Signal to navigate to the live feed screen

    def __init__(self, user_data=None):
        super().__init__()
        self.user_data = user_data
        self.camera_service = CameraService(get_session())  # Initialize CameraService
        
        # Initialize AlertService for proper alert handling
        from src.services.alert_service import AlertService
        self.alert_service = AlertService()
        
        # Dictionary to store camera widgets by camera ID
        self.camera_widgets = {}
        
        # Latest frames for each camera
        self.camera_frames = {}
        
        self.init_ui()
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_data)
        self.update_timer.start(30000)  # Update every 30 seconds
        self.update_data()
        self.installEventFilter(self)  # Install event filter for responsiveness

    def init_ui(self):
        # Create a scroll area for the dashboard content
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setStyleSheet("background-color: transparent;")
        
        # Container widget for all dashboard content
        self.dashboard_widget = QWidget()
        self.dashboard_layout = QVBoxLayout(self.dashboard_widget)
        self.dashboard_layout.setContentsMargins(10, 10, 10, 10)  # Initial margins
        self.dashboard_layout.setSpacing(10)
        
        # Connected Cameras Section (was Active Cameras)
        self.cameras_section = SectionFrame()
        self.cameras_layout = QVBoxLayout(self.cameras_section)
        self.cameras_layout.setContentsMargins(15, 15, 15, 15)
        self.cameras_layout.setSpacing(10)
        
        cameras_title = QLabel("Connected Cameras")  # <-- Titre changé
        cameras_title.setObjectName("SectionTitle")
        title_font = cameras_title.font()
        title_font.setBold(True)
        title_font.setPointSize(12)
        cameras_title.setFont(title_font)
        self.cameras_layout.addWidget(cameras_title)
        
        # Horizontal container for camera widgets
        self.camera_flow_widget = QWidget()
        self.camera_flow_layout = QHBoxLayout(self.camera_flow_widget)
        self.camera_flow_layout.setContentsMargins(0, 5, 0, 0)  # Small top padding for spacing from title
        self.camera_flow_layout.setSpacing(10)
        self.camera_flow_layout.setAlignment(Qt.AlignLeft)  # Align cameras to the left
        
        # Add the flow layout widget to the cameras layout
        self.cameras_layout.addWidget(self.camera_flow_widget)
        
        # Label for additional cameras indicator
        self.more_cameras_label = QLabel()
        self.more_cameras_label.setObjectName("moreCamerasLabel")
        self.more_cameras_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.more_cameras_label.setStyleSheet("color: #757575; font-style: italic; margin-top: 5px;")
        self.more_cameras_label.setVisible(False)  # Initially hidden
        self.cameras_layout.addWidget(self.more_cameras_label)
        self.dashboard_layout.addWidget(self.cameras_section)
        
        # Security Alerts Section
        alerts_section = SectionFrame()
        alerts_layout = QVBoxLayout(alerts_section)
        alerts_layout.setContentsMargins(15, 15, 15, 15)  # Match margins with the camera section
        alerts_layout.setSpacing(8)  # Reduced spacing to make section more compact
        
        # Header with title and actions
        alerts_header_layout = QHBoxLayout()
        alerts_header_layout.setContentsMargins(0, 0, 0, 0)  # Remove margins to reduce height
        
        alerts_title = QLabel("Security Alerts")
        alerts_title.setObjectName("SectionTitle")
        alerts_title.setFont(title_font)
        alerts_header_layout.addWidget(alerts_title)
        
        # View all alerts button
        view_all_alerts = QPushButton("View All")
        view_all_alerts.setObjectName("outlineButton")
        view_all_alerts.setCursor(Qt.PointingHandCursor)
        view_all_alerts.clicked.connect(self.view_all_alerts)
        alerts_header_layout.addWidget(view_all_alerts, alignment=Qt.AlignRight)
        alerts_layout.addLayout(alerts_header_layout)
        
        # Alerts container with increased height
        self.alerts_container = QScrollArea()
        self.alerts_container.setWidgetResizable(True)
        self.alerts_container.setObjectName("AlertsContainer")
        self.alerts_container.setFrameShape(QFrame.NoFrame)
        self.alerts_container.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.alerts_container.setFixedHeight(280)  # Increased height to show more alerts
        self.alerts_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        alerts_container_widget = QWidget()
        self.alerts_container_layout = QVBoxLayout(alerts_container_widget)
        self.alerts_container_layout.setContentsMargins(0, 0, 0, 0)
        self.alerts_container_layout.setSpacing(8)  # Slightly reduced spacing between alerts
        self.alerts_container_layout.setAlignment(Qt.AlignTop)
        self.alerts_container.setWidget(alerts_container_widget)
        alerts_layout.addWidget(self.alerts_container)
        
        # Acknowledge all alerts button - with reduced height container
        ack_button_container = QWidget()
        ack_button_container.setFixedHeight(40)  # Reduced height for this section
        ack_button_layout = QHBoxLayout(ack_button_container)
        ack_button_layout.setContentsMargins(0, 0, 0, 0)
        ack_button_layout.setAlignment(Qt.AlignRight)
        
        self.acknowledge_all_btn = QPushButton("Acknowledge All Alerts")
        self.acknowledge_all_btn.setObjectName("secondaryButton")
        self.acknowledge_all_btn.setCursor(Qt.PointingHandCursor)
        self.acknowledge_all_btn.clicked.connect(self.acknowledge_all_alerts)
        ack_button_layout.addWidget(self.acknowledge_all_btn)
        alerts_layout.addWidget(ack_button_container)
        self.dashboard_layout.addWidget(alerts_section)
        
        # System Status Section
        status_section = SectionFrame()
        status_layout = QVBoxLayout(status_section)
        status_layout.setContentsMargins(10, 10, 10, 10)  # Adjusted margins for responsiveness
        status_layout.setSpacing(10)
        
        status_title = QLabel("System Status")
        status_title.setObjectName("SectionTitle")
        status_title.setFont(title_font)
        status_layout.addWidget(status_title)
        
        # Status card
        status_card = QWidget()
        status_card.setObjectName("Card")
        status_card_layout = QHBoxLayout(status_card)
        status_card_layout.setContentsMargins(10, 10, 10, 10)  # Adjusted margins for responsiveness
        
        status_indicator = QLabel()
        status_indicator.setFixedSize(16, 16)
        status_indicator.setStyleSheet("background-color: #4CAF50; border-radius: 8px;")
        status_card_layout.addWidget(status_indicator)
        
        self.status_text = QLabel("All systems operational")
        status_card_layout.addWidget(self.status_text)
        status_card_layout.addStretch()
        
        view_details = QPushButton("View Details")
        view_details.setObjectName("ActionButton")
        view_details.setCursor(Qt.PointingHandCursor)
        view_details.setStyleSheet("""
            #ActionButton {
                background-color: #2196F3;
                color: white;
                border-radius: 4px;
                padding: 6px 12px;
                border: none;
            }
            #ActionButton:hover {
                background-color: #1976D2;
            }
        """)
        view_details.clicked.connect(self.view_system_details)
        status_card_layout.addWidget(view_details)
        
        status_layout.addWidget(status_card)
        self.dashboard_layout.addWidget(status_section)
                
        # Set the scroll area widget
        self.scroll_area.setWidget(self.dashboard_widget)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)  # Removed outer margins                
        self.main_layout.addWidget(self.scroll_area)

        # Connect camera widget clicks to navigation
        self.navigate_to_live_feed.connect(self.open_live_feed_screen)

    def eventFilter(self, source, event):
        """Handle resize events to adjust responsiveness."""
        if event.type() == QEvent.Resize and source is self:
            self.adjust_responsiveness()
        return super().eventFilter(source, event)

    def adjust_responsiveness(self):
        """Adjust the layout based on the window size."""
        width = self.width()
        camera_width = 240  # Width of each camera widget
        if width < 600:
            self.camera_flow_layout.setSpacing(5)
            self.cameras_layout.setContentsMargins(10, 10, 10, 10)
            self.dashboard_layout.setContentsMargins(10, 10, 10, 10)
        else:
            self.camera_flow_layout.setSpacing(10)
            self.cameras_layout.setContentsMargins(15, 15, 15, 15)
            self.dashboard_layout.setContentsMargins(15, 15, 15, 15)
        
        available_width = width - 30  # Subtract left and right margins
        self.max_cameras = max(1, int(available_width / (camera_width + self.camera_flow_layout.spacing())))
        self.load_cameras()
        self.update()

    def update_data(self):
        """Update all dashboard data."""
        self.load_cameras()
        self.load_alerts()
        self.check_system_status()
    
    def load_cameras(self):
        """Load and display all cameras from the database (always fresh from DB)."""
        self.clear_layout(self.camera_flow_layout)
        self.camera_widgets = {}
        # Always reload from DB to get the latest status
        cameras = self.camera_service.get_all_cameras()
        if not hasattr(self, 'max_cameras'):
            self.max_cameras = 3
        cameras_to_show = min(len(cameras), self.max_cameras)
        remaining_cameras = len(cameras) - cameras_to_show
        for i in range(cameras_to_show):
            camera = cameras[i]
            # Pass the ORM object, but EnhancedCameraWidget only stores primitives
            camera_widget = EnhancedCameraWidget(camera)
            camera_widget.clicked.connect(self.navigate_to_live_feed)
            self.camera_widgets[camera.id] = camera_widget
            if camera.id in self.camera_frames:
                camera_widget.update_frame(self.camera_frames[camera.id])
            self.camera_flow_layout.addWidget(camera_widget)
        self.camera_flow_layout.addStretch(1)
        if remaining_cameras > 0:
            self.more_cameras_label.setText(f"{remaining_cameras} other connected {'camera' if remaining_cameras == 1 else 'cameras'}")
            self.more_cameras_label.setVisible(True)
        else:
            self.more_cameras_label.setVisible(False)

    def update_camera_feed(self, camera_id, pixmap):
        """Update a specific camera feed with new frame and set status active in DB."""
        logger.info(f"Updating feed for camera ID: {camera_id}")
        self.camera_frames[camera_id] = pixmap
        # Set camera as active in DB
        self.camera_service.set_camera_active(camera_id, True)
        # Reload cameras from DB to ensure status is up-to-date everywhere
        self.load_cameras()

    def camera_feed_stopped(self, camera_id):
        """Handle when a camera feed stops and set status inactive in DB."""
        logger.info(f"Feed stopped for camera ID: {camera_id}")
        if camera_id in self.camera_frames:
            del self.camera_frames[camera_id]
        # Set camera as inactive in DB
        self.camera_service.set_camera_active(camera_id, False)
        # Reload cameras from DB to ensure status is up-to-date everywhere
        self.load_cameras()
    
    def view_all_alerts(self):
        """Navigate to the alerts screen if there are active alerts, otherwise show a dialog"""
        session = get_session()
        active_alerts = session.query(Alert).filter_by(is_acknowledged=False).count()
        if active_alerts > 0:
            self.navigate_to_alerts.emit()
        else:
            QMessageBox.information(self, "No Active Alerts", 
                                   "There are currently no active alerts to display.",
                                   QMessageBox.Ok)
    
    def acknowledge_all_alerts(self):
        """Acknowledge all pending alerts, not just the visible ones"""
        session = get_session()
        try:
            alerts = session.query(Alert).filter_by(is_acknowledged=False).all()
            alert_ids = [alert.id for alert in alerts]
            if not alerts:
                QMessageBox.information(self, "No Alerts", "There are no alerts to acknowledge.")
                return
            alert_count = len(alerts)
            from src.services.alert_service import AlertService
            alert_service = AlertService()
            result = alert_service.batch_acknowledge_alerts(alert_ids, self.user_data['id'] if self.user_data else None)
            QMessageBox.information(self, "Alerts Acknowledged", 
                                  f"{alert_count} alert{'s' if alert_count > 1 else ''} successfully acknowledged.")
            self.alerts_acknowledged.emit()
            self.load_alerts()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred while acknowledging alerts: {str(e)}")
        finally:
            close_session(session)
    
    def acknowledge_alert(self, alert_id):
        """Mark an alert as acknowledged and refresh the UI."""
        try:
            from src.services.alert_service import AlertService
            alert_service = AlertService()
            success = alert_service.acknowledge_alert(alert_id, self.user_data['id'] if self.user_data else None)
            if success:
                self.alerts_acknowledged.emit()
                self.load_alerts()
                from PyQt5.QtWidgets import QToolTip
                QToolTip.showText(self.mapToGlobal(self.rect().center()), "Alert acknowledged", self)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred while acknowledging the alert: {str(e)}")
    
    def reset_acknowledge_button(self):
        """Reset the acknowledge all button to its original state"""
        self.acknowledge_all_btn.setEnabled(True)
        self.acknowledge_all_btn.setText("Acknowledge All Alerts")
    
    def load_alerts(self):
        """Load and display real-time alerts from the alert service."""
        self.clear_layout(self.alerts_container_layout)
        try:
            session = get_session()
            alerts = session.query(Alert).filter(Alert.is_acknowledged == False).order_by(Alert.timestamp.desc()).limit(5).all()
            total_unack_alerts = session.query(Alert).filter_by(is_acknowledged=False).count()
            
            # Ensure the acknowledge button reflects the correct state
            if total_unack_alerts > 0:
                self.acknowledge_all_btn.setText(f"Acknowledge All Alerts ({total_unack_alerts})")
                self.acknowledge_all_btn.setEnabled(True)
                
                # Populate the alerts container
                for alert in alerts:
                    alert_widget = DashboardAlertItem(alert)
                    alert_widget.acknowledge_clicked.connect(self.acknowledge_alert)
                    self.alerts_container_layout.addWidget(alert_widget)
                
                # Show additional alerts label if there are more than 5
                if total_unack_alerts > 5:
                    more_alerts_label = QLabel(f"+ {total_unack_alerts - 5} more pending alerts")
                    more_alerts_label.setObjectName("moreAlertsLabel")
                    more_alerts_label.setAlignment(Qt.AlignCenter)
                    more_alerts_label.setStyleSheet("color: #757575; font-style: italic; padding: 5px;")
                    self.alerts_container_layout.addWidget(more_alerts_label)
                self.alerts_container.setFixedHeight(280)  # Ensure proper height
            else:
                # Show a message if no alerts are available
                no_alerts = QLabel("No active alerts")
                no_alerts.setObjectName("emptyStateMessage")
                no_alerts.setAlignment(Qt.AlignCenter)
                self.alerts_container_layout.addWidget(no_alerts)
                self.alerts_container.setFixedHeight(30)
                self.acknowledge_all_btn.setEnabled(False)
                self.acknowledge_all_btn.setText("No Pending Alerts")
            
            self.alerts_container_layout.addStretch()
        except Exception as e:
            logger.error(f"Error loading alerts: {str(e)}")
            error_label = QLabel("Error loading alerts")
            error_label.setObjectName("errorStateMessage")
            error_label.setAlignment(Qt.AlignCenter)
            self.alerts_container_layout.addWidget(error_label)
            self.alerts_container.setFixedHeight(100)
        finally:
            close_session(session)
    
    def check_system_status(self):
        """Check and update system status."""
        session = get_session()
        recent_logs = session.query(SystemLog).order_by(SystemLog.timestamp.desc()).limit(1).first()
        if recent_logs and recent_logs.level == "ERROR":
            self.status_text.setText("System issues detected")
            self.status_text.setStyleSheet("color: #F44336;")
        else:
            self.status_text.setText("All systems operational")
            self.status_text.setStyleSheet("color: #4CAF50;")
        close_session(session)
    
    def view_system_details(self):
        """Show system details dialog"""
        print("View system details clicked")
    
    def clear_layout(self, layout):
        """Clear all widgets from a layout"""
        if layout is None:
            return
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
            elif item.layout():
                self.clear_layout(item.layout())

    def open_live_feed_screen(self, camera_id):
        """Navigate to the live feed screen for the selected camera."""
        # Prevent recursion or multiple signal emissions
        try:
            self.clicked_camera_id = getattr(self, 'clicked_camera_id', None)
            if self.clicked_camera_id == camera_id:
                # Skip if already processing this camera
                logger.info(f"Already navigating to camera ID: {camera_id}")
                return
                
            self.clicked_camera_id = camera_id
            logger.info(f"Navigating to live feed for camera ID: {camera_id}")
            self.navigate_to_live_feed.emit(camera_id)
            
            # Reset after a delay
            QTimer.singleShot(1000, self.reset_clicked_camera)
        except Exception as e:
            logger.error(f"Error in open_live_feed_screen: {str(e)}")
    
    def reset_clicked_camera(self):
        """Reset the clicked camera ID."""
        self.clicked_camera_id = None