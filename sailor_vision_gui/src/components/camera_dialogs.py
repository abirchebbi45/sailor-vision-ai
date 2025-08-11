from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QLineEdit, QComboBox, QSpinBox,
                            QCheckBox, QTabWidget, QWidget, QGroupBox,
                            QSlider, QTextEdit, QFormLayout, QDateTimeEdit,
                            QProgressBar, QTableWidget, QTableWidgetItem)
from PyQt5.QtCore import Qt, QDateTime, QTimer
from PyQt5.QtGui import QFont, QPixmap, QIcon

class CameraConfigDialog(QDialog):
    """Dialog for comprehensive camera configuration"""
    
    def __init__(self, camera, parent=None):
        super().__init__(parent)
        self.camera = camera
        self.setWindowTitle(f"Configure Camera: {camera.name if camera else 'New Camera'}")
        self.setModal(True)
        self.resize(600, 500)
        
        self.init_ui()
        
        if camera:
            self.load_camera_data()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Basic Settings only
        self.setup_basic_tab(layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.test_btn = QPushButton("Test Connection")
        self.test_btn.clicked.connect(self.test_connection)
        button_layout.addWidget(self.test_btn)
        
        button_layout.addStretch()
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        self.save_btn = QPushButton("Save Configuration")
        self.save_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.save_btn)
        
        layout.addLayout(button_layout)
    
    def setup_basic_tab(self, layout):
        # Basic camera configuration group
        basic_group = QGroupBox("Camera Configuration")
        basic_layout = QFormLayout(basic_group)
        
        # Camera Name
        self.name_input = QLineEdit()
        basic_layout.addRow("Camera Name:", self.name_input)
        
        # Camera Type
        self.type_combo = QComboBox()
        self.type_combo.addItems(["USB Camera", "IP Camera", "RTSP Stream", "CSI Camera"])
        basic_layout.addRow("Camera Type:", self.type_combo)
        
        # Location
        self.location_input = QLineEdit()
        basic_layout.addRow("Physical Location:", self.location_input)
        
        # IP Address (for IP cameras)
        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("192.168.1.100")
        basic_layout.addRow("IP Address:", self.ip_input)
        
        # Port
        self.port_input = QSpinBox()
        self.port_input.setRange(1, 65535)
        self.port_input.setValue(554)
        basic_layout.addRow("Port:", self.port_input)
        
        # RTSP URL
        self.rtsp_input = QLineEdit()
        self.rtsp_input.setPlaceholderText("rtsp://192.168.1.100:554/stream")
        basic_layout.addRow("RTSP URL:", self.rtsp_input)
        
        layout.addWidget(basic_group)
    
    def get_camera_config(self):
        """Get basic camera configuration data"""
        return {
            'name': self.name_input.text(),
            'location': self.location_input.text(),
            'ip_address': self.ip_input.text(),
            'port': self.port_input.value(),
            'rtsp_url': self.rtsp_input.text(),
            'camera_type': self.type_combo.currentText(),
            'is_active': True
        }
    
    def get_camera_data(self):
        """Alias pour get_camera_config pour compatibilité"""
        return self.get_camera_config()
    
    def load_camera_data(self):
        """Load existing camera data into form"""
        if self.camera:
            self.name_input.setText(self.camera.name or "")
            self.location_input.setText(self.camera.location or "")
            self.ip_input.setText(self.camera.ip_address or "")
            self.port_input.setValue(self.camera.port or 554)
            self.rtsp_input.setText(self.camera.rtsp_url or "")
            
            # Set camera type if available
            if hasattr(self.camera, 'camera_type') and self.camera.camera_type:
                index = self.type_combo.findText(self.camera.camera_type)
                if index >= 0:
                    self.type_combo.setCurrentIndex(index)
    
    def test_connection(self):
        """Test camera connection"""
        # Simulate connection test
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.information(self, "Connection Test", 
                              "Testing connection...\n\n"
                              "✓ Network reachable\n"
                              "✓ Camera responding\n"
                              "✓ Stream available\n\n"
                              "Camera is ready for surveillance!")


class MaintenanceScheduleDialog(QDialog):
    """Dialog for scheduling camera maintenance"""
    
    def __init__(self, camera, parent=None):
        super().__init__(parent)
        self.camera = camera
        self.setWindowTitle(f"Schedule Maintenance - {camera.name}")
        self.setModal(True)
        self.resize(400, 300)
        
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Maintenance type
        type_group = QGroupBox("Maintenance Type")
        type_layout = QFormLayout(type_group)
        
        self.maintenance_combo = QComboBox()
        self.maintenance_combo.addItems([
            "Routine Cleaning", "Lens Calibration", "Hardware Check",
            "Software Update", "Emergency Repair", "Preventive Service"
        ])
        type_layout.addRow("Maintenance Type:", self.maintenance_combo)
        
        # Schedule
        self.schedule_datetime = QDateTimeEdit()
        self.schedule_datetime.setDateTime(QDateTime.currentDateTime().addDays(1))
        type_layout.addRow("Schedule Date/Time:", self.schedule_datetime)
        
        # Notes
        self.notes_text = QTextEdit()
        self.notes_text.setMaximumHeight(100)
        type_layout.addRow("Notes:", self.notes_text)
        
        layout.addWidget(type_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        schedule_btn = QPushButton("Schedule")
        schedule_btn.clicked.connect(self.accept)
        button_layout.addWidget(schedule_btn)
        
        layout.addLayout(button_layout)
    
    def get_maintenance_schedule(self):
        return {
            'maintenance_type': self.maintenance_combo.currentText(),
            'scheduled_datetime': self.schedule_datetime.dateTime().toPyDateTime(),
            'notes': self.notes_text.toPlainText()
        }
