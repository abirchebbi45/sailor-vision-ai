from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QGridLayout, QFrame, QScrollArea,
                            QSpacerItem, QSizePolicy)
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QTimer
from PyQt5.QtGui import QPixmap, QIcon, QColor, QFont, QPainter, QPen

from src.services.camera_service import CameraService
from src.components.shared import HeaderWidget, Sidebar
from models import Camera

class EnhancedCameraWidget(QFrame):
    def __init__(self, camera):
        super().__init__()
        self.camera = camera
        self.init_ui()
        
    def init_ui(self):
        self.setObjectName("cameraWidget")
        self.setFixedSize(360, 270)  # Adjusted size to match design
        self.setFrameShape(QFrame.StyledPanel)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)  # Remove spacing
        
        # Camera feed container
        feed_container = QWidget()
        feed_container.setObjectName("cameraFeed")
        feed_container.setFixedHeight(200)
        
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
                360, 200,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            ))
            
            # Draw detection boxes (in real app these would be dynamically updated)
            self.draw_detection_boxes()
        else:
            self.feed_label.setText("Camera Feed")
        
        feed_layout.addWidget(self.feed_label)
        layout.addWidget(feed_container)
        
        # Camera info panel
        info_container = QWidget()
        info_container.setObjectName("cameraInfo")
        info_layout = QVBoxLayout(info_container)
        info_layout.setContentsMargins(15, 10, 15, 10)
        info_layout.setSpacing(2)
        
        # Location/name - bold and larger
        location_label = QLabel(self.camera.location or "Unknown Location")
        location_label.setObjectName("cameraLocation")
        location_font = location_label.font()
        location_font.setBold(True)
        location_font.setPointSize(10)
        location_label.setFont(location_font)
        info_layout.addWidget(location_label)
        
        # Camera details
        details_label = QLabel(f"Camera {self.camera.name} {self.camera.location}")
        details_font = details_label.font()
        details_font.setPointSize(9)
        details_label.setFont(details_font)
        info_layout.addWidget(details_label)
        
        # Status with colored indicator
        status_container = QWidget()
        status_layout = QHBoxLayout(status_container)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(5)
        
        status_indicator = QLabel()
        status_indicator.setFixedSize(8, 8)
        if self.camera.is_active:
            status_indicator.setStyleSheet("background-color: #4CAF50; border-radius: 4px;")
        else:
            status_indicator.setStyleSheet("background-color: #F44336; border-radius: 4px;")
        
        status_text = QLabel(f"Status: {'Active' if self.camera.is_active else 'Inactive'}")
        status_text.setStyleSheet("color: #757575;")
        
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
        self.camera_service = CameraService()
        self.init_ui()
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_data)
        self.update_timer.start(30000)  # Update every 30 seconds
        self.update_data()
    
    def init_ui(self):
        # Use VBoxLayout for the main container
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)  # Remove margins
        main_layout.setSpacing(0)  # Remove spacing
        
        # Create a scroll area for the dashboard content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setStyleSheet("background-color: transparent;")
        
        # Container widget for all dashboard content
        dashboard_widget = QWidget()
        dashboard_layout = QVBoxLayout(dashboard_widget)
        dashboard_layout.setContentsMargins(20, 20, 20, 20)
        dashboard_layout.setSpacing(20)
        
        # Connected Cameras Section with blurred background
        cameras_section = SectionFrame()
        cameras_layout = QVBoxLayout(cameras_section)
        cameras_layout.setContentsMargins(20, 20, 20, 20)
        cameras_layout.setSpacing(15)
        
        cameras_title = QLabel("Connected Cameras")
        cameras_title.setObjectName("SectionTitle")
        title_font = cameras_title.font()
        title_font.setBold(True)
        title_font.setPointSize(12)
        cameras_title.setFont(title_font)
        cameras_layout.addWidget(cameras_title)
        
        # Camera Grid
        cameras_container = QWidget()
        self.cameras_grid = QGridLayout(cameras_container)
        self.cameras_grid.setHorizontalSpacing(20)
        self.cameras_grid.setVerticalSpacing(20)
        self.cameras_grid.setContentsMargins(0, 0, 0, 0)
        cameras_layout.addWidget(cameras_container)
        
        dashboard_layout.addWidget(cameras_section)
        
        # Security Alerts Section with blurred background
        alerts_section = SectionFrame()
        alerts_layout = QVBoxLayout(alerts_section)
        alerts_layout.setContentsMargins(20, 20, 20, 20)
        alerts_layout.setSpacing(15)
        
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
        
        dashboard_layout.addWidget(alerts_section)
        
        # System Status Section with blurred background
        status_section = SectionFrame()
        status_layout = QVBoxLayout(status_section)
        status_layout.setContentsMargins(20, 20, 20, 20)
        status_layout.setSpacing(15)
        
        status_title = QLabel("System Status")
        status_title.setObjectName("SectionTitle")
        status_title.setFont(title_font)
        status_layout.addWidget(status_title)
        
        # Status card
        status_card = QWidget()
        status_card.setObjectName("Card")
        status_card_layout = QHBoxLayout(status_card)
        status_card_layout.setContentsMargins(15, 15, 15, 15)
        
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
        dashboard_layout.addWidget(status_section)
        
        # Set the scroll area widget
        scroll_area.setWidget(dashboard_widget)
        main_layout.addWidget(scroll_area)
    
    def update_data(self):
        """Update all dashboard data"""
        self.load_cameras()
        self.load_alerts()
        self.check_system_status()
    
    def load_cameras(self):
        """Load and display camera widgets"""
        # Clear existing camera widgets
        self.clear_layout(self.cameras_grid)
        
        # Get cameras from service
        cameras = self.camera_service.get_active_cameras()
        
        # Mock camera data if empty (for development)
        if not cameras:
            # Create some example cameras with maritime locations
            example_cameras = [
                Camera(id=1, name="A", location="Downtown", is_active=True, placeholder_image="assets/camera1.jpg"),
                Camera(id=2, name="B", location="City Park", is_active=True, placeholder_image="assets/camera2.jpg"),
                Camera(id=3, name="C", location="Main Entrance", is_active=True, placeholder_image="assets/camera3.jpg")
            ]
            cameras = example_cameras
        
        # Add camera widgets to grid
        for i, camera in enumerate(cameras):
            row = i // 3  # 3 cameras per row
            col = i % 3
            camera_widget = EnhancedCameraWidget(camera)
            self.cameras_grid.addWidget(camera_widget, row, col)
    
    def load_alerts(self):
        """Load and display security alerts"""
        # Clear existing alerts
        self.clear_layout(self.alerts_container_layout)
        
        # Mock alerts for development - Using maritime specific alerts
        mock_alerts = [
            {
                "id": 1, 
                "type": "Motion Detected", 
                "description": "Living room camera detected motion", 
                "location": "Living Room",
                "time_ago": "2 mins"
            },
            {
                "id": 2, 
                "type": "Motion Detected", 
                "description": "Living room camera detected motion", 
                "location": "Living Room",
                "time_ago": "2 mins"
            },
            {
                "id": 3, 
                "type": "Motion Detected", 
                "description": "Living room camera detected motion", 
                "location": "Living Room",
                "time_ago": "2 mins"
            }
        ]
        
        # Add alert widgets
        for alert in mock_alerts:
            alert_widget = AlertWidget(alert)
            self.alerts_container_layout.addWidget(alert_widget)
    
    def check_system_status(self):
        """Check and update system status"""
        # In a real app, this would check actual system status
        self.status_text.setText("All systems operational")
    
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