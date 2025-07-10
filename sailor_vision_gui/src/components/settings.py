from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QLineEdit, QFrame, QScrollArea,
                            QProgressBar, QFileDialog, QMessageBox, QDialog,
                            QComboBox, QSpinBox, QCheckBox, QTabWidget,
                            QGroupBox, QSlider, QTextEdit)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QPixmap, QIcon, QPainter, QPainterPath, QRegion

from services.user_service import UserService
from services.camera_service import CameraService
from services.storage_service import StorageService
from services.pending_camera_manager import pending_camera_manager
from components.shared import HeaderWidget
from components.camera_dialogs import (CameraConfigDialog, MaintenanceScheduleDialog)
from utils import hash_password
from models import User, Camera, StorageType
from database import create_new_session

class SettingsScreen(QWidget):
    camera_approved_signal = pyqtSignal(dict)  # Signal émis quand une caméra est approuvée
    
    def __init__(self, user, db_session):
        super().__init__()
        self.user = user
        self.db_session = db_session
        
        # Create independent services with their own sessions
        self.user_service = UserService(create_new_session())
        self.camera_service = CameraService(create_new_session())
        self.storage_service = StorageService()
        
        # Connecter aux signaux du gestionnaire de caméras en attente
        self.pending_camera_manager = pending_camera_manager
        try:
            self.setup_pending_camera_connections()
        except Exception as e:
            print(f"[Settings] Erreur lors de la connexion aux signaux: {e}")
        
        self.init_ui()
        
        # Charger les caméras en attente au démarrage
        try:
            self.load_pending_cameras()
        except Exception as e:
            print(f"[Settings] Erreur lors du chargement des caméras en attente: {e}")
        
        # Mettre à jour le badge du nombre de caméras en attente
        try:
            self.update_pending_badge()
        except Exception as e:
            print(f"[Settings] Erreur lors de la mise à jour du badge: {e}")
        
        # Apply styles
        self.setStyleSheet(
            """
            QLabel#sectionHeader {
                font-size: 18px;
                font-weight: bold;
                color: #333;
                margin-bottom: 10px;
            }
            QLabel#subSectionHeader {
                font-size: 14px;
                font-weight: bold;
                color: #555;
                margin-bottom: 8px;
            }
            QLabel#profilePicture {
                border-radius: 40px;
                border: 2px solid #ccc;
            }
            QLabel#pendingBadge {
                background-color: #FF6B6B;
                color: white;
                border-radius: 10px;
                padding: 2px 8px;
                font-size: 12px;
                font-weight: bold;
                min-width: 20px;
            }
            QLabel#pendingName {
                font-size: 14px;
                font-weight: bold;
                color: #2c3e50;
            }
            QLabel#pendingDetails {
                font-size: 12px;
                color: #7f8c8d;
            }
            QPushButton#secondaryButton {
                background-color: #007BFF;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 12px;
                min-width: 80px;
            }
            QPushButton#secondaryButton:hover {
                background-color: #0056b3;
            }
            QPushButton#approveButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton#approveButton:hover {
                background-color: #218838;
            }
            QPushButton#rejectButton {
                background-color: #dc3545;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton#rejectButton:hover {
                background-color: #c82333;
            }
            QPushButton#dangerButton {
                background-color: #DC3545;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
            }
            QPushButton#dangerButton:hover {
                background-color: #a71d2a;
            }
            QProgressBar {
                height: 20px;
                border: 1px solid #ccc;
                border-radius: 4px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #007BFF;
                border-radius: 4px;
            }
            QFrame#contentSection {
                background-color: #f8f9fa;
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 20px;
                margin-bottom: 20px;
            }
            QFrame#pendingSection {
                background-color: #fff3cd;
                border: 1px solid #ffeaa7;
                border-radius: 8px;
                padding: 15px;
                margin-bottom: 15px;
            }
            QFrame#activeSection {
                background-color: #d1ecf1;
                border: 1px solid #a6d9e8;
                border-radius: 8px;
                padding: 15px;
                margin-bottom: 15px;
            }
            QFrame#pendingItem {
                background-color: #ffffff;
                border: 1px solid #ffeaa7;
                border-radius: 6px;
                padding: 10px;
                margin-bottom: 8px;
            }
            QLabel.inputLabel {
                font-size: 14px;
                font-weight: bold;
                color: #333;
                margin-bottom: 5px;
            }
            QLineEdit.inputField {
                height: 40px;
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 0 10px;
                font-size: 14px;
            }
            """
        )
        
        # Load initial data with error handling
        try:
            self.load_profile_settings()
        except Exception as e:
            print(f"[Settings] Erreur lors du chargement du profil: {e}")
        
        try:
            self.load_camera_settings()
        except Exception as e:
            print(f"[Settings] Erreur lors du chargement des caméras: {e}")
        
        try:
            self.load_storage_settings()
        except Exception as e:
            print(f"[Settings] Erreur lors du chargement du stockage: {e}")
        # Note: load_pending_cameras() est appelée dans __init__ après l'initialisation UI
    
    def init_ui(self):
        """Initialize the UI components"""
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Create scroll area for settings content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setFrameShape(QFrame.NoFrame)

        # Settings content widget
        settings_widget = QWidget()
        settings_layout = QVBoxLayout(settings_widget)
        settings_layout.setContentsMargins(20, 20, 20, 20)
        settings_layout.setSpacing(20)

        # Profile Settings section
        profile_section = QFrame()
        profile_section.setObjectName("contentSection")
        profile_layout = QVBoxLayout(profile_section)

        profile_header = QLabel("Profile Settings")
        profile_header.setObjectName("sectionHeader")
        profile_layout.addWidget(profile_header)

        # Profile picture and change button
        profile_pic_layout = QHBoxLayout()

        # Profile picture
        self.profile_pic = QLabel()
        self.profile_pic.setFixedSize(80, 80)
        self.profile_pic.setScaledContents(True)
        self.profile_pic.setObjectName("profilePicture")

        # Set default placeholder image
        default_pic = QPixmap("assets/default_profile.svg")
        if not default_pic.isNull():
            size = self.profile_pic.size()
            rounded_pixmap = QPixmap(size)
            rounded_pixmap.fill(Qt.transparent)

            painter = QPainter(rounded_pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            path = QPainterPath()
            path.addEllipse(0, 0, size.width(), size.height())
            painter.setClipPath(path)
            painter.drawPixmap(0, 0, default_pic.scaled(size.width(), size.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
            painter.end()

            self.profile_pic.setPixmap(rounded_pixmap)

            # Apply circular mask to QLabel
            region = QRegion(0, 0, size.width(), size.height(), QRegion.Ellipse)
            self.profile_pic.setMask(region)

        profile_pic_layout.addWidget(self.profile_pic)

        # Change picture button
        change_pic_btn = QPushButton("Change Picture")
        change_pic_btn.setObjectName("secondaryButton")
        change_pic_btn.clicked.connect(self.change_profile_picture)
        profile_pic_layout.addWidget(change_pic_btn)
        profile_pic_layout.addStretch()

        profile_layout.addLayout(profile_pic_layout)

        # Name field
        name_layout = QVBoxLayout()
        name_label = QLabel("Name")
        name_label.setObjectName("inputLabel")
        self.name_input = QLineEdit()
        self.name_input.setObjectName("inputField")
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_input)
        profile_layout.addLayout(name_layout)

        # Email field
        email_layout = QVBoxLayout()
        email_label = QLabel("Email")
        email_label.setObjectName("inputLabel")
        self.email_input = QLineEdit()
        self.email_input.setObjectName("inputField")
        email_layout.addWidget(email_label)
        email_layout.addWidget(self.email_input)
        profile_layout.addLayout(email_layout)

        # Password field
        password_layout = QVBoxLayout()
        password_label = QLabel("Password")
        password_label.setObjectName("inputLabel")
        self.password_input = QLineEdit()
        self.password_input.setObjectName("inputField")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("••••••••")
        password_layout.addWidget(password_label)
        password_layout.addWidget(self.password_input)

        # Password visibility toggle
        self.password_toggle = QPushButton()
        self.password_toggle.setIcon(QIcon.fromTheme("view-hidden"))
        self.password_toggle.setCheckable(True)
        self.password_toggle.clicked.connect(self.toggle_password_visibility)
        password_layout.addWidget(self.password_toggle)

        profile_layout.addLayout(password_layout)

        settings_layout.addWidget(profile_section)

        # Camera Management section
        camera_section = QFrame()
        camera_section.setObjectName("contentSection")
        camera_layout = QVBoxLayout(camera_section)
        
        # Camera header with pending approvals indicator
        camera_header_layout = QHBoxLayout()
        camera_header = QLabel("Camera Management")
        camera_header.setObjectName("sectionHeader")
        camera_header_layout.addWidget(camera_header)
        
        # Pending approvals badge
        self.pending_badge = QLabel("0")
        self.pending_badge.setObjectName("pendingBadge")
        self.pending_badge.setVisible(False)
        camera_header_layout.addWidget(self.pending_badge)
        camera_header_layout.addStretch()
        
        # Refresh from ROS button
        refresh_btn = QPushButton("Refresh from ROS")
        refresh_btn.setObjectName("secondaryButton")
        refresh_btn.clicked.connect(self.refresh_cameras_from_ros)
        camera_header_layout.addWidget(refresh_btn)
        
        camera_layout.addLayout(camera_header_layout)
        
        # Pending approvals section
        pending_section = QFrame()
        pending_section.setObjectName("pendingSection")
        pending_layout = QVBoxLayout(pending_section)
        
        pending_header = QLabel("Pending Camera Approvals")
        pending_header.setObjectName("subSectionHeader")
        pending_layout.addWidget(pending_header)
        
        self.pending_cameras_list = QVBoxLayout()
        pending_layout.addLayout(self.pending_cameras_list)
        
        camera_layout.addWidget(pending_section)
        
        # Active cameras section
        active_section = QFrame()
        active_section.setObjectName("activeSection")
        active_layout = QVBoxLayout(active_section)
        
        active_header = QLabel("Active Cameras")
        active_header.setObjectName("subSectionHeader")
        active_layout.addWidget(active_header)
        
        # Camera list will be populated dynamically
        self.camera_list = QVBoxLayout()
        active_layout.addLayout(self.camera_list)
        
        camera_layout.addWidget(active_section)
        
        settings_layout.addWidget(camera_section)
        
        # Storage Settings section
        storage_section = QFrame()
        storage_section.setObjectName("contentSection")
        storage_layout = QVBoxLayout(storage_section)
        
        storage_header = QLabel("Storage Settings")
        storage_header.setObjectName("sectionHeader")
        storage_layout.addWidget(storage_header)
        
        # Storage options
        storage_option_layout = QHBoxLayout()
        storage_option_label = QLabel("Storage Option")
        storage_option_layout.addWidget(storage_option_label)
        storage_option_layout.addStretch()
        
        # Cloud button
        self.cloud_btn = QPushButton("Cloud")
        self.cloud_btn.setObjectName("storageButton")
        self.cloud_btn.setCheckable(True)
        self.cloud_btn.clicked.connect(lambda: self.set_storage_type(StorageType.CLOUD))
        
        # Local button
        self.local_btn = QPushButton("Local")
        self.local_btn.setObjectName("storageButton")
        self.local_btn.setCheckable(True)
        self.local_btn.clicked.connect(lambda: self.set_storage_type(StorageType.LOCAL))
        
        storage_option_layout.addWidget(self.cloud_btn)
        storage_option_layout.addWidget(self.local_btn)
        
        storage_layout.addLayout(storage_option_layout)
        
        # Storage status
        storage_status_layout = QHBoxLayout()
        storage_status_label = QLabel("Storage Status")
        storage_status_layout.addWidget(storage_status_label)
        storage_status_layout.addStretch()
        
        # Progress bar
        self.storage_progress = QProgressBar()
        self.storage_progress.setTextVisible(True)
        self.storage_progress.setFormat("%p%")
        storage_status_layout.addWidget(self.storage_progress)
        
        storage_layout.addLayout(storage_status_layout)
        
        settings_layout.addWidget(storage_section)
        
        # Set the settings widget as the scroll area's widget
        scroll_area.setWidget(settings_widget)
        layout.addWidget(scroll_area)
    
    def load_profile_settings(self):
        """Load user profile settings into the UI"""
        full_name = f"{self.user.get('first_name', '')} {self.user.get('last_name', '')}".strip()
        self.name_input.setText(full_name)
        self.email_input.setText(self.user.get('email', ''))
        profile_picture_path = self.user.get('profile_picture', '')
        if profile_picture_path:
            self.profile_pic.setPixmap(QPixmap(profile_picture_path))
    
    def load_camera_settings(self):
        """Load camera settings"""
        # Clear existing camera widgets
        if hasattr(self, 'camera_list'):
            self.clear_camera_list()

        # Get cameras from service
        cameras = self.camera_service.get_all_cameras()

        # Add camera widgets to list
        for camera in cameras:
            camera_item = QFrame()
            camera_item.setObjectName("alertItem")
            camera_item.setFrameShape(QFrame.StyledPanel)
            camera_item.setMaximumHeight(70)

            layout = QHBoxLayout(camera_item)
            layout.setContentsMargins(15, 10, 15, 10)

            # Left part - camera info
            camera_info = QVBoxLayout()
            camera_info.setSpacing(3)

            # Camera name and status
            title = QLabel(camera.name)
            title.setObjectName("alertType")
            type_font = title.font()
            type_font.setBold(True)
            title.setFont(type_font)
            camera_info.addWidget(title)

            status_label = QLabel(f"Status: {'Active' if camera.is_active else 'Inactive'}")
            status_label.setObjectName("alertDescription")
            camera_info.addWidget(status_label)

            layout.addLayout(camera_info)
            layout.addStretch()

            # Action buttons
            actions_layout = QHBoxLayout()
            
            # Primary actions
            edit_btn = QPushButton("⚙️ Configure")
            edit_btn.setObjectName("secondaryButton")
            edit_btn.setToolTip("Configure camera settings")
            edit_btn.clicked.connect(lambda checked, c=camera: self.edit_camera(c))
            
            status_btn = QPushButton("🔴 Disable" if camera.is_active else "🟢 Enable")
            status_btn.setObjectName("secondaryButton")
            status_btn.setToolTip("Toggle camera status")
            status_btn.clicked.connect(lambda checked, c=camera: self.toggle_camera_status(c))
            
            # Monitoring operations
            test_btn = QPushButton("🔍 Test")
            test_btn.setObjectName("secondaryButton")
            test_btn.setToolTip("Test connectivity")
            test_btn.clicked.connect(lambda checked, c=camera: self.test_camera_connectivity(c))
            
            # Maintenance operations
            maintenance_btn = QPushButton("🔧 Maintenance")
            maintenance_btn.setObjectName("secondaryButton")
            maintenance_btn.setToolTip("Schedule maintenance")
            maintenance_btn.clicked.connect(lambda checked, c=camera: self.schedule_camera_maintenance(c))
            
            # Delete operation
            delete_btn = QPushButton("🗑️ Delete")
            delete_btn.setObjectName("dangerButton")
            delete_btn.setToolTip("Delete camera")
            delete_btn.clicked.connect(lambda checked, c=camera: self.delete_camera(c))
            
            # Add buttons to layout
            actions_layout.addWidget(edit_btn)
            actions_layout.addWidget(status_btn)
            actions_layout.addWidget(test_btn)
            actions_layout.addWidget(maintenance_btn)
            actions_layout.addWidget(delete_btn)
            
            layout.addLayout(actions_layout)

            self.camera_list.addWidget(camera_item)

            # Add separator
            if camera != cameras[-1]:
                separator = QFrame()
                separator.setFrameShape(QFrame.HLine)
                separator.setFrameShadow(QFrame.Sunken)
                self.camera_list.addWidget(separator)
    
    def load_storage_settings(self):
        """Load storage settings"""
        # Get current storage type
        storage_type = self.storage_service.get_storage_type()

        # Set button states
        self.cloud_btn.setChecked(storage_type == StorageType.CLOUD)
        self.local_btn.setChecked(storage_type == StorageType.LOCAL)

        # Get storage usage
        usage_percent = int(self.storage_service.get_storage_usage_percent())
        self.storage_progress.setValue(usage_percent)
    
    def change_profile_picture(self):
        """Handle change profile picture button click"""
        # Open file dialog
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Select Profile Picture",
            "",
            "Images (*.png *.jpg *.jpeg)"
        )

        if file_name:
            # Update profile picture
            pixmap = QPixmap(file_name)
            if not pixmap.isNull():
                # Apply circular mask
                size = self.profile_pic.size()
                rounded_pixmap = QPixmap(size)
                rounded_pixmap.fill(Qt.transparent)

                painter = QPainter(rounded_pixmap)
                painter.setRenderHint(QPainter.Antialiasing)
                path = QPainterPath()
                path.addEllipse(0, 0, size.width(), size.height())
                painter.setClipPath(path)
                painter.drawPixmap(0, 0, pixmap.scaled(size.width(), size.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
                painter.end()

                self.profile_pic.setPixmap(rounded_pixmap)

                # Apply circular mask to QLabel
                region = QRegion(0, 0, size.width(), size.height(), QRegion.Ellipse)
                self.profile_pic.setMask(region)

                # Update user in database (in a real app)
                # self.user_service.update_profile_picture(self.user.id, file_name)
    
    def toggle_password_visibility(self, checked):
        """Toggle password field visibility"""
        if checked:
            self.password_input.setEchoMode(QLineEdit.Normal)
            self.password_toggle.setIcon(QIcon.fromTheme("view-visible"))
        else:
            self.password_input.setEchoMode(QLineEdit.Password)
            self.password_toggle.setIcon(QIcon.fromTheme("view-hidden"))
    
    def set_storage_type(self, storage_type):
        """Set storage type"""
        # Update UI
        self.cloud_btn.setChecked(storage_type == StorageType.CLOUD)
        self.local_btn.setChecked(storage_type == StorageType.LOCAL)
        
        # Update storage type in database
        self.storage_service.set_storage_type(storage_type)
    
    def edit_camera(self, camera):
        """Edit camera settings with comprehensive maritime configuration"""
        dialog = CameraConfigDialog(camera, self)
        if dialog.exec_() == QDialog.Accepted:
            updated_data = dialog.get_camera_config()
            
            success = self.camera_service.update_camera(camera.id, updated_data)
            
            if success:
                self.load_camera_settings()
                QMessageBox.information(self, "Success", "Camera configuration updated successfully!")
            else:
                QMessageBox.warning(self, "Error", "Failed to update camera configuration.")
    
    def setup_pending_camera_connections(self):
        """
        Configurer les connexions avec le gestionnaire de caméras en attente
        """
        # Connecter aux signaux du gestionnaire de caméras en attente
        self.pending_camera_manager.new_camera_detected.connect(self.on_new_camera_detected)
        self.pending_camera_manager.pending_cameras_updated.connect(self.on_pending_cameras_updated)
        self.pending_camera_manager.camera_approved.connect(self.on_camera_approved)
        self.pending_camera_manager.camera_rejected.connect(self.on_camera_rejected)
    
    def on_new_camera_detected(self, camera_id: str, camera_name: str, camera_ip: str):
        """
        Appelé quand une nouvelle caméra est détectée
        """
        print(f"[Settings] Nouvelle caméra détectée: {camera_name} ({camera_ip})")
        # Recharger la liste des caméras en attente
        self.load_pending_cameras()
        # Mettre à jour le badge
        self.update_pending_badge()
        # Forcer la mise à jour de l'affichage
        self.update()
        self.repaint()
    
    def on_pending_cameras_updated(self, pending_count: int):
        """
        Appelé quand le nombre de caméras en attente change
        """
        print(f"[Settings] Nombre de caméras en attente: {pending_count}")
        # Recharger la liste des caméras en attente
        self.load_pending_cameras()
        # Mettre à jour le badge
        self.update_pending_badge()
    
    def on_camera_approved(self, camera):
        """
        Appelé quand une caméra est approuvée
        """
        print(f"[Settings] Caméra approuvée: {camera.name}")
        # Recharger les listes
        self.load_pending_cameras()
        self.load_camera_settings()
        self.update_pending_badge()
    
    def on_camera_rejected(self, camera_id: str):
        """
        Appelé quand une caméra est rejetée
        """
        print(f"[Settings] Caméra rejetée: {camera_id}")
        # Recharger la liste des caméras en attente
        self.load_pending_cameras()
        self.update_pending_badge()
    
    def load_pending_cameras(self):
        """
        Charger et afficher les caméras en attente d'approbation
        """
        try:
            print("[Settings] Chargement des caméras en attente...")
            
            # Vérifier que les attributs nécessaires existent
            if not hasattr(self, 'pending_cameras_list'):
                print("[Settings] pending_cameras_list not yet initialized, retrying in 100ms...")
                # Délai pour s'assurer que l'UI est complètement initialisée
                QTimer.singleShot(100, self.load_pending_cameras)
                return
            
            # Force reload from file before getting pending cameras
            self.pending_camera_manager.load_pending_cameras()
            
            # Vider le layout existant
            self.clear_pending_cameras_layout()
            
            # Obtenir les caméras en attente
            pending_cameras = self.pending_camera_manager.get_pending_cameras()
            print(f"[Settings] Found {len(pending_cameras)} pending cameras")
            
            # Debug: print each camera
            for i, cam in enumerate(pending_cameras):
                print(f"[Settings] Pending camera {i+1}: {cam.name} ({cam.ip_address}) - status: {cam.status}")
            
            if not pending_cameras:
                # Afficher un message si aucune caméra en attente
                no_pending_label = QLabel("Aucune caméra en attente d'approbation")
                no_pending_label.setStyleSheet("color: #666; font-style: italic; padding: 10px;")
                self.pending_cameras_list.addWidget(no_pending_label)
                print("[Settings] No pending cameras, showing empty message")
                return
            
            # Afficher chaque caméra en attente
            for pending_camera in pending_cameras:
                print(f"[Settings] Adding pending camera: {pending_camera.name} ({pending_camera.ip_address})")
                self.add_pending_camera_item(pending_camera)
                
        except Exception as e:
            print(f"[Settings] Erreur lors du chargement des caméras en attente: {e}")
            import traceback
            traceback.print_exc()
    
    def add_pending_camera_item(self, pending_camera):
        """
        Ajouter un item de caméra en attente à la liste
        """
        # Créer le conteneur pour la caméra
        camera_frame = QFrame()
        camera_frame.setObjectName("pendingItem")
        camera_layout = QVBoxLayout(camera_frame)
        
        # Informations de la caméra
        info_layout = QHBoxLayout()
        
        # Nom et IP
        name_label = QLabel(f"<b>{pending_camera.name}</b>")
        name_label.setStyleSheet("color: #333; font-size: 14px;")
        info_layout.addWidget(name_label)
        
        ip_label = QLabel(f"IP: {pending_camera.ip_address}")
        ip_label.setStyleSheet("color: #666; font-size: 12px;")
        info_layout.addWidget(ip_label)
        
        # Type de caméra
        type_label = QLabel(f"Type: {pending_camera.camera_type}")
        type_label.setStyleSheet("color: #666; font-size: 12px;")
        info_layout.addWidget(type_label)
        
        # Date de détection
        detection_time = pending_camera.detected_at.strftime("%Y-%m-%d %H:%M:%S")
        time_label = QLabel(f"Détectée: {detection_time}")
        time_label.setStyleSheet("color: #666; font-size: 12px;")
        info_layout.addWidget(time_label)
        
        info_layout.addStretch()
        camera_layout.addLayout(info_layout)
        
        # Boutons d'action
        actions_layout = QHBoxLayout()
        
        # Bouton d'approbation
        approve_btn = QPushButton("Approuver")
        approve_btn.setObjectName("primaryButton")
        approve_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        approve_btn.clicked.connect(lambda: self.approve_pending_camera(pending_camera))
        actions_layout.addWidget(approve_btn)
        
        # Bouton de rejet
        reject_btn = QPushButton("Rejeter")
        reject_btn.setObjectName("dangerButton")
        reject_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        """)
        reject_btn.clicked.connect(lambda: self.reject_pending_camera(pending_camera))
        actions_layout.addWidget(reject_btn)
        
        # Bouton de configuration (optionnel)
        config_btn = QPushButton("Configurer")
        config_btn.setObjectName("secondaryButton")
        config_btn.clicked.connect(lambda: self.configure_pending_camera(pending_camera))
        actions_layout.addWidget(config_btn)
        
        actions_layout.addStretch()
        camera_layout.addLayout(actions_layout)
        
        # Ajouter le widget à la liste
        self.pending_cameras_list.addWidget(camera_frame)
    
    def approve_pending_camera(self, pending_camera):
        """
        Approuver une caméra en attente
        """
        # Confirmer l'approbation
        reply = QMessageBox.question(
            self, 
            "Confirmer l'approbation",
            f"Voulez-vous approuver la caméra '{pending_camera.name}' ({pending_camera.ip_address})?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            try:
                # Approuver via le gestionnaire (marque comme approved dans JSON)
                approved_camera = self.pending_camera_manager.approve_camera(pending_camera.camera_id)
                
                if approved_camera:
                    # Créer la caméra dans la base de données
                    db_camera = self.add_camera_to_database(approved_camera)
                    
                    if db_camera:
                        # Succès : supprimer la caméra du JSON maintenant qu'elle est en DB
                        self.pending_camera_manager.remove_approved_camera(pending_camera.camera_id)
                        
                        QMessageBox.information(self, "Succès", 
                                              f"Caméra '{pending_camera.name}' approuvée avec succès!\n\n"
                                              f"✅ Ajoutée à la base de données (ID: {db_camera.id})\n"
                                              f"✅ Disponible dans le Live Feed\n"
                                              f"✅ Prête pour la surveillance\n"
                                              f"✅ Supprimée de la liste d'attente")
                        
                        # Log détaillé pour debug
                        print(f"[Settings] Processus d'approbation terminé:")
                        print(f"  - Caméra: {pending_camera.name}")
                        print(f"  - IP: {pending_camera.ip_address}")
                        print(f"  - ID BDD: {db_camera.id}")
                        print(f"  - Status DB: is_active=True")
                        print(f"  - Status JSON: supprimée")
                        
                        # Émettre le signal pour notifier les autres composants
                        camera_dict = {
                            "id": db_camera.id,
                            "name": db_camera.name,
                            "ip_address": db_camera.ip_address,
                            "is_active": True
                        }
                        self.camera_approved_signal.emit(camera_dict)
                        print(f"[Settings] Signal émis pour la caméra approuvée: {camera_dict}")
                        
                    else:
                        # Échec DB : revenir l'état pending dans JSON
                        approved_camera.status = "pending"
                        self.pending_camera_manager.save_pending_cameras()
                        QMessageBox.warning(self, "Erreur", 
                                          "Erreur lors de l'ajout de la caméra à la base de données.\n"
                                          "La caméra reste en attente d'approbation.")
                else:
                    QMessageBox.warning(self, "Erreur", 
                                      "Erreur lors de l'approbation de la caméra.")
            except Exception as e:
                import traceback
                print(f"[Settings] Exception lors de l'approbation: {e}")
                traceback.print_exc()
                QMessageBox.warning(self, "Erreur", 
                                   f"Erreur lors de l'approbation: {str(e)}")

    def reject_pending_camera(self, pending_camera):
        """
        Rejeter une caméra en attente
        """
        # Confirmer le rejet
        reply = QMessageBox.question(
            self, 
            "Confirmer le rejet",
            f"Voulez-vous rejeter la caméra '{pending_camera.name}' ({pending_camera.ip_address})?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Rejeter via le gestionnaire
            success = self.pending_camera_manager.reject_camera(pending_camera.camera_id)
            
            if success:
                QMessageBox.information(self, "Succès", 
                                      f"Caméra '{pending_camera.name}' rejetée.")
            else:
                QMessageBox.warning(self, "Erreur", 
                                  "Erreur lors du rejet de la caméra.")
    
    def configure_pending_camera(self, pending_camera):
        """
        Configurer une caméra en attente avant approbation
        """
        # Créer un objet Camera temporaire pour le dialogue
        temp_camera = Camera(
            name=pending_camera.name,
            ip_address=pending_camera.ip_address,
            rtsp_url=pending_camera.rtsp_url,
            port=pending_camera.port,
            location=pending_camera.location,
            camera_type=pending_camera.camera_type,
            is_active=False
        )
        
        # Ouvrir le dialogue de configuration
        dialog = CameraConfigDialog(temp_camera, self)
        if dialog.exec_() == QDialog.Accepted:
            # Obtenir les nouvelles données
            camera_data = dialog.get_camera_data()
            
            # Mettre à jour la caméra en attente
            pending_camera.name = camera_data['name']
            pending_camera.location = camera_data['location']
            pending_camera.rtsp_url = camera_data['rtsp_url']
            pending_camera.port = camera_data['port']
            
            # Sauvegarder les modifications
            self.pending_camera_manager.save_pending_cameras()
            
            # Recharger l'affichage
            self.load_pending_cameras()
            
            QMessageBox.information(self, "Succès", 
                                  f"Configuration de la caméra '{pending_camera.name}' mise à jour.")
    
    def add_camera_to_database(self, pending_camera):
        """
        Ajouter une caméra approuvée à la base de données
        Retourne l'objet caméra créé si succès, None sinon
        """
        try:
            # Créer les données de la caméra - tous les champs compatibles avec le modèle DB
            camera_data = {
                "name": pending_camera.name,
                "ip_address": pending_camera.ip_address,
                "rtsp_url": pending_camera.rtsp_url or f"rtsp://{pending_camera.ip_address}:{pending_camera.port}/stream1",
                "port": pending_camera.port,
                "location": pending_camera.location or "Auto-detected",
                "camera_type": pending_camera.camera_type or "Auto-detected",
                "is_active": True
            }
            
            print(f"[Settings] Données caméra pour DB: {camera_data}")
            
            # Ajouter à la base de données en utilisant camera_service
            new_camera = self.camera_service.add_camera(camera_data)
            
            if new_camera:
                print(f"[Settings] Caméra '{pending_camera.name}' ajoutée à la base de données avec succès (ID: {new_camera.id})")
                
                # Recharger la liste des caméras actives
                try:
                    self.load_camera_settings()
                except Exception as e:
                    print(f"[Settings] Erreur lors du rechargement des paramètres de caméra: {e}")
                
                # Retourner l'objet caméra créé
                return new_camera
            else:
                print(f"[Settings] Échec de l'ajout de la caméra '{pending_camera.name}' à la base de données")
                return None
            
        except Exception as e:
            print(f"[Settings] Erreur lors de l'ajout de la caméra: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def update_pending_badge(self):
        """
        Mettre à jour le badge du nombre de caméras en attente
        """
        try:
            pending_count = self.pending_camera_manager.get_pending_count()
            
            # Vérifier si le badge existe déjà
            if hasattr(self, 'pending_badge'):
                if pending_count > 0:
                    self.pending_badge.setText(str(pending_count))
                    self.pending_badge.setVisible(True)
                else:
                    self.pending_badge.setVisible(False)
            else:
                print("[Settings] pending_badge not yet initialized")
                
        except Exception as e:
            print(f"[Settings] Erreur lors de la mise à jour du badge: {e}")
    
    def refresh_cameras_from_ros(self):
        """
        Rafraîchir les caméras depuis ROS - force la re-détection des caméras
        """
        try:
            # First synchronize with database
            approved_devices = self.camera_service.sync_with_pending_cameras()
            if approved_devices:
                print(f"[Settings] Cleaned up {len(approved_devices)} already-approved cameras")
            
            # Recharger les caméras approuvées depuis la base de données
            self.load_camera_settings()
            
            # Recharger les caméras en attente
            self.load_pending_cameras()
            
            # Mettre à jour le badge
            self.update_pending_badge()
            
            QMessageBox.information(self, "Rafraîchissement", 
                                  "Liste des caméras rafraîchie avec succès!")
        except Exception as e:
            QMessageBox.warning(self, "Erreur", 
                              f"Erreur lors du rafraîchissement: {e}")
    
    def clear_camera_list(self):
        """
        Vider la liste des caméras actives
        """
        if hasattr(self, 'camera_list'):
            while self.camera_list.count():
                item = self.camera_list.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()

    def clear_pending_cameras_layout(self):
        """
        Vider le layout des caméras en attente
        """
        if hasattr(self, 'pending_cameras_list'):
            while self.pending_cameras_list.count():
                item = self.pending_cameras_list.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
    
    def clear_layout(self, layout):
        """
        Vider un layout donné
        """
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()

    def showEvent(self, event):
        """
        Called when the settings screen is shown.
        Refresh pending cameras to ensure the latest state is displayed.
        """
        super().showEvent(event)
        print("[Settings] Settings screen shown, refreshing pending cameras...")
        
        # First, synchronize with database to remove already-approved cameras
        try:
            approved_devices = self.camera_service.sync_with_pending_cameras()
            if approved_devices:
                print(f"[Settings] Removed {len(approved_devices)} already-approved devices from pending list")
        except Exception as e:
            print(f"[Settings] Error synchronizing pending cameras: {e}")
        
        # Force cleanup of duplicates using improved logic
        try:
            self.pending_camera_manager.cleanup_duplicates()
            print("[Settings] Completed duplicate cleanup")
        except Exception as e:
            print(f"[Settings] Error during duplicate cleanup: {e}")
        
        # Force reload from file
        try:
            self.pending_camera_manager.load_pending_cameras()
            self.load_pending_cameras()
            self.update_pending_badge()
            print(f"[Settings] Refreshed - pending count: {self.pending_camera_manager.get_pending_count()}")
        except Exception as e:
            print(f"[Settings] Error refreshing pending cameras on show: {e}")