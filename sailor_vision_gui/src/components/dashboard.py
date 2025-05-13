from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QGridLayout, QFrame, QScrollArea,
                            QSpacerItem, QSizePolicy)
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QTimer, QEvent
from PyQt5.QtGui import QPixmap, QIcon, QColor, QFont, QPainter, QPen

from src.services.camera_service import CameraService
from models import Camera, Alert, SystemLog
from src.components.shared import HeaderWidget, Sidebar
from database import get_session


class EnhancedCameraWidget(QFrame):
    def __init__(self, camera):
        super().__init__()
        self.camera = camera
        self.init_ui()
        
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
        if hasattr(self.camera, 'placeholder_image') and self.camera.placeholder_image:
            pixmap = QPixmap(self.camera.placeholder_image)
            self.feed_label.setPixmap(pixmap.scaled(
                240, 100,  # Adjusted to match the smaller widget size
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            ))
        else:
            self.feed_label.setText("Camera Feed")
        
        feed_layout.addWidget(self.feed_label)
        layout.addWidget(feed_container)
        
        # Camera info panel
        info_container = QWidget()
        info_container.setObjectName("cameraInfo")
        info_layout = QVBoxLayout(info_container)
        info_layout.setContentsMargins(5, 4, 5, 4)  # Reduced left and right padding
        info_layout.setSpacing(2)
        
        # Location/name - bold and larger
        location_label = QLabel(self.camera.location or "Unknown Location")
        location_label.setObjectName("cameraLocation")
        location_font = location_label.font()
        location_font.setBold(True)
        location_font.setPointSize(8)  # Reduced font size
        location_label.setFont(location_font)
        info_layout.addWidget(location_label)
        
        # Camera details
        details_label = QLabel(f"Camera {self.camera.name} {self.camera.location}")
        details_font = details_label.font()
        details_font.setPointSize(7)  # Reduced font size
        details_label.setFont(details_font)
        info_layout.addWidget(details_label)
        
        # Status with colored indicator
        status_container = QWidget()
        status_layout = QHBoxLayout(status_container)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(5)
        
        status_indicator = QLabel()
        status_indicator.setFixedSize(5, 5)  # Reduced size for the status indicator
        if self.camera.is_active:
            status_indicator.setStyleSheet("background-color: #4CAF50; border-radius: 2.5px;")
        else:
            status_indicator.setStyleSheet("background-color: #F44336; border-radius: 2.5px;")
        
        status_text = QLabel(f"Status: {'Active' if self.camera.is_active else 'Inactive'}")
        status_text.setStyleSheet("color: #757575; font-size: 9px;")  # Reduced font size
        
        status_layout.addWidget(status_indicator)
        status_layout.addWidget(status_text)
        status_layout.addStretch()
        
        info_layout.addWidget(status_container)
        layout.addWidget(info_container)

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
                padding: 6px 12px;
                border: none;
            }
            #acknowledgeButton:hover {
                background-color: #1976D2;
            }
        """)
        acknowledge_btn.clicked.connect(lambda: self.acknowledge_alert(self.alert_data.get("id")))
        layout.addWidget(acknowledge_btn)

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
    def __init__(self, user_data=None):
        super().__init__()
        self.user_data = user_data
        self.camera_service = CameraService(get_session())  # Initialize CameraService
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
        
        # Active Cameras Section
        self.cameras_section = SectionFrame()
        self.cameras_layout = QVBoxLayout(self.cameras_section)
        self.cameras_layout.setContentsMargins(15, 15, 15, 15)  # Match margins with the title
        self.cameras_layout.setSpacing(10)
        
        cameras_title = QLabel("Active Cameras")
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
        alerts_layout.setContentsMargins(10, 10, 10, 10)  # Adjusted margins for responsiveness
        alerts_layout.setSpacing(10)
        
        alerts_title = QLabel("Security Alerts")
        alerts_title.setObjectName("SectionTitle")
        alerts_title.setFont(title_font)
        alerts_layout.addWidget(alerts_title)
        
        # Alerts container
        alerts_container = QWidget()
        alerts_container.setObjectName("AlertsContainer")
        self.alerts_container_layout = QVBoxLayout(alerts_container)
        self.alerts_container_layout.setContentsMargins(0, 0, 0, 0)
        self.alerts_container_layout.setSpacing(10)
        alerts_layout.addWidget(alerts_container)
        
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

    def eventFilter(self, source, event):
        """Handle resize events to adjust responsiveness."""
        if event.type() == QEvent.Resize and source is self:
            self.adjust_responsiveness()
        return super().eventFilter(source, event)

    def adjust_responsiveness(self):
        """Adjust the layout based on the window size."""
        width = self.width()
        
        # Calculate how many camera widgets can fit in the current width
        # Each camera is 240px wide with spacing between them
        camera_width = 240  # Width of each camera widget
        
        if width < 600:
            self.camera_flow_layout.setSpacing(5)
            spacing = 5
            self.cameras_layout.setContentsMargins(10, 10, 10, 10)
            self.dashboard_layout.setContentsMargins(10, 10, 10, 10)
        else:
            self.camera_flow_layout.setSpacing(10)
            spacing = 10
            self.cameras_layout.setContentsMargins(15, 15, 15, 15)
            self.dashboard_layout.setContentsMargins(15, 15, 15, 15)
        
        # Calculate available width for cameras (accounting for margins)
        available_width = width - 30  # Subtract left and right margins
        
        # Calculate how many cameras can fit in the available width
        self.max_cameras = max(1, int(available_width / (camera_width + spacing)))
        
        # Force an update to the camera layout
        self.load_cameras()
        
        # Force layout update
        self.update()

    def update_data(self):
        """Update all dashboard data."""
        self.load_cameras()
        self.load_alerts()
        self.check_system_status()
    
    def load_cameras(self):
        """Load and display active camera widgets."""
        # Clear existing widgets
        self.clear_layout(self.camera_flow_layout)
        
        # Get active cameras
        cameras = self.camera_service.get_active_cameras()
        
        # Calculate how many cameras to show and how many are remaining
        if not hasattr(self, 'max_cameras'):
            self.max_cameras = 3  # Default max cameras to display
        
        cameras_to_show = min(len(cameras), self.max_cameras)
        remaining_cameras = len(cameras) - cameras_to_show
        
        # Add camera widgets
        for i in range(cameras_to_show):
            camera_widget = EnhancedCameraWidget(cameras[i])
            self.camera_flow_layout.addWidget(camera_widget)
        
        # Add stretch to keep cameras aligned left
        self.camera_flow_layout.addStretch(1)
        
        # Update the more cameras label
        if remaining_cameras > 0:
            self.more_cameras_label.setText(f"{remaining_cameras} other active {'camera' if remaining_cameras == 1 else 'cameras'}")
            self.more_cameras_label.setVisible(True)
        else:
            self.more_cameras_label.setVisible(False)
    
    def load_alerts(self):
        """Load and display security alerts."""
        self.clear_layout(self.alerts_container_layout)  # Clear existing alerts
        session = get_session()
        alerts = session.query(Alert).filter_by(is_acknowledged=False).order_by(Alert.timestamp.desc()).limit(10).all()

        for alert in alerts:
            alert_data = {
                "id": alert.id,
                "type": alert.type,
                "description": alert.message,
                "location": alert.camera.location if alert.camera else "Unknown",
                "timestamp": alert.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            }
            alert_widget = AlertWidget(alert_data)
            self.alerts_container_layout.addWidget(alert_widget)
    
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
    
    def view_system_details(self):
        """Show system details dialog"""
        # This would open a system details dialog in a real app
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