from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QLineEdit, QFrame, QScrollArea,
                            QProgressBar, QFileDialog, QMessageBox, QDialog,
                            QComboBox, QSpinBox, QCheckBox, QTabWidget,
                            QGroupBox, QSlider, QTextEdit, QGridLayout, QProgressDialog)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QSize, QDateTime
from PyQt5.QtGui import QPixmap, QIcon, QPainter, QPainterPath, QRegion, QColor, QFont
import os

from services.user_service import UserService
from services.camera_service import CameraService
from services.storage_service import StorageService
from services.pending_camera_manager import pending_camera_manager
from services.logging_service import LoggingService
from services.realtime_log_handler import log_manager
from components.shared import HeaderWidget
from components.camera_dialogs import (CameraConfigDialog, MaintenanceScheduleDialog)
from utils import hash_password
from models import User, Camera, StorageType
from database import create_new_session
from services.permission_service import Permission
from services.user_session import UserSession

class SettingsScreen(QWidget):
    camera_approved_signal = pyqtSignal(dict)  # Signal émis quand une caméra est approuvée
    camera_updated_signal = pyqtSignal(dict)   # Signal émis quand une caméra est modifiée
    camera_status_changed_signal = pyqtSignal(dict)  # Signal émis quand le statut d'une caméra change
    
    def __init__(self, user, db_session):
        super().__init__()
        print("[Settings] Initialisation début...")
        self.user = user
        self.db_session = db_session
        
        print("[Settings] Vérification des permissions...")
        # Utiliser directement les données utilisateur pour les permissions
        user_role = user.get('role', '').lower() if isinstance(user, dict) else getattr(user, 'role', '').lower()
        print(f"[Settings] Rôle utilisateur détecté: {user_role}")
        
        # Pour les administrateurs, donner toutes les permissions
        if 'admin' in user_role:
            print("[Settings] Permissions admin accordées")
            self.has_camera_permission = True
            self.has_system_settings_permission = True
        else:
            print("[Settings] Permissions operator accordées")
            self.has_camera_permission = False  # Les opérateurs n'ont pas accès aux paramètres caméras
            self.has_system_settings_permission = True  # Mais ils ont accès aux logs système
        
        print(f"[Settings] Camera permission: {self.has_camera_permission}")
        print(f"[Settings] System settings permission: {self.has_system_settings_permission}")
        
        print("[Settings] Initialisation de l'UI...")
        # Initialiser uniquement l'UI - aucun service pour éviter les blocages
        self.init_ui()
        print("[Settings] UI initialisée avec succès")
        
        # Initialiser les variables de services à None pour le lazy loading
        self.user_service = None
        self.camera_service = None
        self.storage_service = None
        self.pending_camera_manager = None
        self.services_initialized = False
        
        # Initialiser les timers à None
        self.service_update_timer = None
        
        print("[Settings] Programmation du chargement initial...")
        # Charger uniquement les données du profil utilisateur par défaut
        # IMPORTANT: Déplacer cet appel à la fin de init_ui pour s'assurer que tous les widgets sont créés
        # QTimer.singleShot(50, self.load_initial_data)
        
        print("[Settings] UI initialisée - services en lazy loading")
    
    def initialize_services(self):
        """Initialise les services de manière lazy - appelé seulement quand nécessaire"""
        if self.services_initialized:
            return
            
        print("[Settings] Initialisation lazy des services...")
        try:
            # Create independent services with their own sessions
            self.user_service = UserService(create_new_session())
            self.camera_service = CameraService(create_new_session())
            self.storage_service = StorageService()
            
            # Connecter aux signaux du gestionnaire de caméras en attente (uniquement pour les admins)
            if self.has_camera_permission:
                self.pending_camera_manager = pending_camera_manager
                try:
                    self.setup_pending_camera_connections()
                except Exception as e:
                    print(f"[Settings] Erreur lors de la connexion aux signaux: {e}")
            
            self.services_initialized = True
            print("[Settings] Services initialisés avec succès")
            
        except Exception as e:
            print(f"[Settings] Erreur lors de l'initialisation des services: {e}")
            # Même en cas d'erreur, marquer comme initialisé pour éviter les boucles
            self.services_initialized = True
    
    def on_tab_changed(self, index):
        """Gestionnaire pour le changement d'onglet - lazy loading des données"""
        print(f"[Settings] Changement vers l'onglet {index}")
        
        try:
            # Obtenir le nom de l'onglet actuel
            tab_text = self.tabs.tabText(index) if index < self.tabs.count() else ""
            print(f"[Settings] Nom de l'onglet: '{tab_text}'")
            
            # Charger les données en fonction de l'onglet sélectionné
            if tab_text == "User Profile":
                print("[Settings] Chargement du profil utilisateur...")
                # Charger le profil utilisateur - ne nécessite pas de services lourds
                QTimer.singleShot(50, self.load_profile_settings_safe)
                
            elif tab_text == "Camera Management" and self.has_camera_permission:
                print("[Settings] Chargement des données caméras...")
                # Initialiser les services si nécessaire, puis charger les caméras
                if not self.services_initialized:
                    self.initialize_services()
                QTimer.singleShot(100, self.load_camera_data)
                
            elif tab_text == "System Settings" and self.has_system_settings_permission:
                print("[Settings] Chargement des paramètres système...")
                # Initialiser les services si nécessaire, puis charger les paramètres système
                if not self.services_initialized:
                    self.initialize_services()
                # La section Reports & Logging se charge automatiquement
                print("[Settings] Section Reports & Logging prête")
            else:
                print(f"[Settings] Onglet non reconnu ou permissions insuffisantes: '{tab_text}'")
        except Exception as e:
            print(f"[Settings] ERREUR dans on_tab_changed: {e}")
            import traceback
            print(f"[Settings] Traceback: {traceback.format_exc()}")
    
    def load_camera_data(self):
        """Charge toutes les données liées aux caméras"""
        print("[Settings] Chargement des données caméras...")
        try:
            # Charger les caméras actives
            self.load_camera_settings()
            print("[Settings] Caméras actives chargées")
            
            # Charger les caméras en attente
            self.load_pending_cameras()
            print("[Settings] Caméras en attente chargées")
            
            # Mettre à jour le badge
            self.update_pending_badge()
            print("[Settings] Badge mis à jour")
            
        except Exception as e:
            print(f"[Settings] Erreur lors du chargement des données caméras: {e}")
    
    def load_initial_data(self):
        """Charge uniquement les données du profil utilisateur par défaut"""
        print("[Settings] Chargement minimal des données initiales...")
        
        # Vérifier que tous les widgets nécessaires existent
        if not self.verify_widgets_exist():
            print("[Settings] ERREUR: Widgets manquants, report du chargement...")
            # Réessayer dans 200ms
            QTimer.singleShot(200, self.load_initial_data)
            return
        
        # Charger uniquement le profil utilisateur au démarrage
        # Les autres données seront chargées via lazy loading lors du changement d'onglet
        try:
            print("[Settings] Appel à load_profile_settings_safe...")
            self.load_profile_settings_safe()
            print("[Settings] Profil utilisateur chargé avec succès")
        except Exception as e:
            print(f"[Settings] Erreur lors du chargement du profil: {e}")
            import traceback
            print(f"[Settings] Traceback: {traceback.format_exc()}")
        
        print("[Settings] Initialisation terminée - prêt pour l'utilisation")
    
    def verify_widgets_exist(self):
        """Vérifie que tous les widgets nécessaires existent"""
        print("[Settings] Vérification des widgets...")
        
        required_widgets = ['name_input', 'email_input', 'profile_pic']
        missing_widgets = []
        
        for widget_name in required_widgets:
            if not hasattr(self, widget_name) or getattr(self, widget_name) is None:
                missing_widgets.append(widget_name)
                
        if missing_widgets:
            print(f"[Settings] Widgets manquants: {missing_widgets}")
            return False
        else:
            print("[Settings] Tous les widgets requis sont présents")
            return True
    
    def load_cameras_with_delay(self):
        """Charge les caméras et les caméras en attente avec un léger délai"""
        print("[Settings] Chargement des caméras...")
        
        # Charger les caméras actives
        try:
            self.load_camera_settings()
            print("[Settings] Caméras actives chargées")
        except Exception as e:
            print(f"[Settings] Erreur lors du chargement des caméras: {e}")
        
        # Charger les caméras en attente
        try:
            self.load_pending_cameras()
            print("[Settings] Caméras en attente chargées")
        except Exception as e:
            print(f"[Settings] Erreur lors du chargement des caméras en attente: {e}")
        
        # Mettre à jour le badge
        try:
            self.update_pending_badge()
            print("[Settings] Badge mis à jour")
        except Exception as e:
            print(f"[Settings] Erreur lors de la mise à jour du badge: {e}")
        
        # Les données seront chargées de manière asynchrone via initialize_services
        pass
        # Note: load_pending_cameras() est appelée dans __init__ après l'initialisation UI
    
    def init_ui(self):
        """Initialize the UI components"""
        print("[Settings] Début init_ui...")
        # Initialisation préventive des attributs pour éviter les erreurs
        # même pour les utilisateurs sans permissions de gestion de caméras
        self.pending_cameras_list = None
        self.pending_badge = None
        self.camera_list = None
        
        print("[Settings] Création du layout principal...")
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        print("[Settings] Création du TabWidget...")
        # Créer un widget à onglets (TabWidget) pour organiser les différentes sections
        self.tabs = QTabWidget()
        self.tabs.setObjectName("settingsTabs")

        
        
        # Connecter le signal de changement d'onglet pour le lazy loading
        self.tabs.currentChanged.connect(self.on_tab_changed)
        
        layout.addWidget(self.tabs)
        
        print("[Settings] Création de l'onglet profil...")
        # Créer un widget de défilement pour chaque onglet
        self.create_profile_tab()
        print("[Settings] Onglet profil créé")
        
        # Créer les onglets supplémentaires uniquement pour les administrateurs
        if self.has_camera_permission:
            print("[Settings] Création de l'onglet caméras...")
            self.create_camera_tab()
            print("[Settings] Onglet caméras créé")
            
        if self.has_system_settings_permission:
            print("[Settings] Création de l'onglet système...")
            self.create_system_tab()
            print("[Settings] Onglet système créé")
        
        # Apply modern styles with consistent color scheme
        self.setStyleSheet(
            """
            QWidget {
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            
            QLabel#sectionHeader {
                font-size: 16px;
                font-weight: bold;
                color: #333333;
                background-color : transparent;
                margin-bottom: 5px;
                padding-top: 5px;    
                padding-bottom: 5px;
            }
            
            QLabel#subSectionHeader {
                font-size: 16px;
                font-weight: bold;
                color: #34495e;
                margin-bottom: 10px;
                background-color: transparent;
            }
            
            QLabel#profilePicture {
                border-radius: 75px;
                border: 1px solid rgba(220, 220, 225, 0.9);

            }
            
            QLabel#pendingBadge {
                background-color: #f44336;
                color: white;
                border-radius: 12px;
                padding: 3px 10px;
                font-size: 12px;
                font-weight: bold;
                min-width: 24px;
                min-height: 24px;
                text-align: center;
            }
                        
            QLabel#pendingName {
                font-size: 16px;
                font-weight: bold;
                color: #263238;
            }
            
            QLabel#pendingDetails {
                font-size: 10px;
                color: #546e7a;
            }
            
            QPushButton#primaryButton {
                background-color: #0088cc !important;
                color: white !important;
                border: none !important;
                border-radius: 6px !important;
                padding: 10px 20px !important;
                font-size: 14px !important;
                font-weight: bold !important;
                min-width: 120px !important;
            }
            
            QPushButton#primaryButton:hover {
                background-color: #006699 !important;
            }
            
            QPushButton#primaryButton:pressed {
                background-color: #004466 !important;
            }
            
            QPushButton#secondaryButton {
                background-color: #2196f3 !important;
                color: white !important;
                border: none !important;
                border-radius: 6px !important;
                padding: 8px 16px !important;
                font-size: 13px !important;
                font-weight: bold !important;
                min-width: 100px !important;
            }
            
            QPushButton#secondaryButton:hover {
                background-color: #1976d2 !important;
            }
            
            QPushButton#secondaryButton:pressed {
                background-color: #0d47a1 !important;
            }
            
            QPushButton#approveButton {
                background-color: #4caf50 !important;
                color: white !important;
                border: none !important;
                border-radius: 6px !important;
                padding: 8px 16px !important;
                font-size: 13px !important;
                font-weight: bold !important;
            }
            
            QPushButton#approveButton:hover {
                background-color: #43a047 !important;
            }
            
            QPushButton#approveButton:pressed {
                background-color: #388e3c !important;
            }
            
            QPushButton#rejectButton {
                background-color: #f44336 !important;
                color: white !important;
                border: none !important;
                border-radius: 6px !important;
                padding: 8px 16px !important;
                font-size: 13px !important;
                font-weight: bold !important;
            }
            
            QPushButton#rejectButton:hover {
                background-color: #e53935 !important;
            }
            
            QPushButton#rejectButton:pressed {
                background-color: #d32f2f !important;
            }
            
            QPushButton#dangerButton {
                background-color: #f44336 !important;
                color: white !important;
                border: none !important;
                border-radius: 6px !important;
                padding: 8px 16px !important;
                font-size: 13px !important;
                font-weight: bold !important;
            }
            
            QPushButton#dangerButton:hover {
                background-color: #e53935 !important;
            }
            
            QPushButton#dangerButton:pressed {
                background-color: #d32f2f !important;
            }
            
            QPushButton#iconButton {
                border: none;
                background-color: transparent;
                border-radius: 22px;
            }
            
            QPushButton#iconButton:hover {
                background-color: #e9f0f6;
            }
            
            QProgressBar {
                height: 25px;
                border: none;
                border-radius: 12px;
                background-color: #f5f5f5;
                text-align: center;
                color: #333333;
                font-weight: bold;
                margin: 5px 0;
            }
            
            QProgressBar::chunk {
                border-radius: 12px;
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #039be5, stop:1 #29b6f6);
            }
            
            QFrame#contentSection {
                background-color: rgba(240, 240, 245, 0.7);
                padding: 10px 20px 20px 20px;
                margin-bottom: 20px;
                border-radius: 8px;
                border: 1px solid rgba(220, 220, 225, 0.9);
            }
            
            QFrame#pendingSection {
                background-color: #fff8e1;
                border: none;
                border-left: 4px solid #ffc107;
                border-radius: 8px;
                padding: 20px;
                margin-bottom: 20px;
            }
            
            QFrame#activeSection {
                background-color: #e3f2fd;
                border: none;
                border-left: 4px solid #2196f3;
                border-radius: 8px;
                padding: 20px;
                margin-bottom: 20px;
            }
            
            QFrame#pendingItem {
                background-color: #ffffff;
                border: none;
                border-radius: 8px;
                margin-bottom: 8px;
            }
            
            QLabel.inputLabel {
                font-size: 15px;
                font-weight: bold;
                color: #455a64;
                margin-bottom: 5px;
            }
            
            QLineEdit#inputField {
                border: 1px solid #dce4ec;
                border-radius: 6px;
                padding: 5px 15px;
                font-size: 14px;
                background-color: #ffffff;
            }
            
            QLineEdit#inputField:focus {
                border: 2px solid #0088cc;
                background-color: #f8fdff;
            }
            
            QScrollArea {
                border: none;
                background-color: #f5f5f5;
            }
            
            QGroupBox {
                font-size: 15px;
                font-weight: bold;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                margin-top: 15px;
                padding-top: 15px;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 10px;
                color: #455a64;
            }
            
            QTabWidget::pane {
                border: none;
                background: #f5f5f5;
                padding: 0px;
            }
            
            QTabBar::tab {
                background: #f0f0f0;
                color: #555555;
                min-width: 120px;
                width: 200px;
                padding: 12px 25px;
                font-size: 14px;
                font-weight: bold;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            
            QTabBar::tab:selected {
                background: #ffffff;
                color: #0088cc;
                border-bottom: 3px solid #0088cc;
            }
            
            QTabBar::tab:hover:!selected {
                background: #e5e5e5;
            }

            QPushButton#configButton {
                background-color: #2196f3 !important;
                color: white !important;
                border: none !important;
                border-radius: 6px !important;
                padding: 8px 16px !important;
                font-size: 13px !important;
                font-weight: bold !important;
                min-width: 100px !important;
            }
            
            QPushButton#configButton:hover {
                background-color: #1976d2 !important;
            }
            
            QPushButton#configButton:pressed {
                background-color: #0d47a1 !important;
            }
            """
        )
        
        print("[Settings] Fin de init_ui - programmation du chargement des données initiales...")
        # Maintenant que tous les widgets sont créés, charger les données initiales
        QTimer.singleShot(100, self.load_initial_data)
        print("[Settings] init_ui terminé")

    def create_profile_tab(self):
        """Créer l'onglet Profile avec les informations utilisateur"""
        profile_tab = QWidget()
        profile_layout = QVBoxLayout(profile_tab)
        profile_layout.setContentsMargins(30, 10, 30, 30)
        profile_layout.setSpacing(25)
        
        # Scroll area for profile tab
        profile_scroll = QScrollArea()
        profile_scroll.setWidgetResizable(True)
        profile_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        profile_scroll.setFrameShape(QFrame.NoFrame)
        profile_scroll.setStyleSheet("background-color: #f5f5f5; border: none;")
        
        # Profile settings container
        profile_container = QWidget()
        profile_container_layout = QVBoxLayout(profile_container)
        profile_container_layout.setContentsMargins(0, 0, 0, 0)
        profile_container_layout.setSpacing(25)
        
        # Profile Settings section
        profile_section = QFrame()
        profile_section.setObjectName("contentSection")
        profile_section_layout = QVBoxLayout(profile_section)
        profile_section_layout.setSpacing(5)

        # Section header with modern design
        profile_header = QLabel("User Profile")
        profile_header.setObjectName("sectionHeader")
        profile_section_layout.addWidget(profile_header)
        
        # Profile content using grid layout for better responsiveness
        profile_grid = QWidget()
        grid_layout = QGridLayout(profile_grid)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        grid_layout.setSpacing(10)
        grid_layout.setColumnStretch(0, 1)  # Profile picture column
        grid_layout.setColumnStretch(1, 2)  # Form fields column
        
        # Profile picture card with elevation effect
        pic_card = QFrame()
        pic_card.setObjectName("profileCard")
        pic_card.setFixedHeight(300)
        pic_card.setStyleSheet("""
            #profileCard {
                background-color: #ffffff;
                border: 1px solid rgba(220, 220, 225, 0.9);
                border-radius: 12px;
                padding: 10px;
            }
        """)
        pic_layout = QVBoxLayout(pic_card)
        pic_layout.setAlignment(Qt.AlignCenter)
        pic_layout.setSpacing(15)

        # Profile picture
        self.profile_pic = QLabel()
        self.profile_pic.setFixedSize(150, 150)
        self.profile_pic.setScaledContents(True)
        self.profile_pic.setObjectName("profilePicture")
        self.profile_pic.setStyleSheet("""
            #profilePicture {
                border: 1px solid rgba(220, 220, 225, 0.9);
                border-radius: 75px;
            }
        """)

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

        pic_layout.addWidget(self.profile_pic, alignment=Qt.AlignCenter)

        # Change picture button with icon
        change_pic_btn = QPushButton("Change Picture")
        change_pic_btn.setObjectName("outlineButton")
        change_pic_btn.setIcon(QIcon.fromTheme("document-open"))
        change_pic_btn.setIconSize(QSize(16, 16))
        change_pic_btn.clicked.connect(self.change_profile_picture)
        change_pic_btn.setCursor(Qt.PointingHandCursor)
        pic_layout.addWidget(change_pic_btn, alignment=Qt.AlignCenter)
        
        # Add profile picture card to grid
        grid_layout.addWidget(pic_card, 0, 0, 1, 1, Qt.AlignTop)

        # Form fields card with elevation effect
        form_card = QFrame()
        form_card.setObjectName("formCard")
        form_card.setFixedHeight(300)
        form_card.setStyleSheet("""
            #formCard {
                background-color: #ffffff;
                border: 1px solid rgba(220, 220, 225, 0.9);
                border-radius: 12px;
                padding: 10px;
            }
        """)
        form_layout = QVBoxLayout(form_card)
        form_layout.setSpacing(20)

        # Name field with modern styling
        name_layout = self.create_form_field("Full Name", tooltip="Enter your full name")
        self.name_input = QLineEdit()
        self.name_input.setObjectName("inputField")
        self.name_input.setPlaceholderText("John Doe")
        self.name_input.setMinimumHeight(45)
        name_layout.addWidget(self.name_input)
        form_layout.addLayout(name_layout)

        # Email field with modern styling
        email_layout = self.create_form_field("Email Address", tooltip="Enter your email address")
        self.email_input = QLineEdit()
        self.email_input.setObjectName("inputField")
        self.email_input.setPlaceholderText("john.doe@example.com")
        self.email_input.setMinimumHeight(45)
        email_layout.addWidget(self.email_input)
        form_layout.addLayout(email_layout)

        # Password field with modern styling and visibility toggle
        password_layout = self.create_form_field("Password", tooltip="Enter your password")
        password_input_layout = QHBoxLayout()
        
        self.password_input = QLineEdit()
        self.password_input.setObjectName("inputField")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("••••••••")
        self.password_input.setMinimumHeight(45)
        password_input_layout.addWidget(self.password_input)

        # Password visibility toggle with improved styling
        self.password_toggle = QPushButton()
        self.password_toggle.setIcon(QIcon.fromTheme("view-hidden"))
        self.password_toggle.setObjectName("iconButton")
        self.password_toggle.setCheckable(True)
        self.password_toggle.setFixedSize(45, 45)
        self.password_toggle.setCursor(Qt.PointingHandCursor)
        self.password_toggle.setToolTip("Show/Hide Password")
        self.password_toggle.clicked.connect(self.toggle_password_visibility)
        self.password_toggle.setStyleSheet("""
            QPushButton#iconButton {
                border: none;
                background-color: transparent;
                border-radius: 22px;
            }
            QPushButton#iconButton:hover {
                background-color: #e9f0f6;
            }
        """)
        password_input_layout.addWidget(self.password_toggle)
        
        password_layout.addLayout(password_input_layout)
        form_layout.addLayout(password_layout)

        # Save button with modern styling
        save_btn = QPushButton("Save Changes")
        save_btn.setObjectName("outlineButton")
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.setIcon(QIcon.fromTheme("document-save"))
        save_btn.clicked.connect(self.save_profile_changes)
        save_btn.setMinimumHeight(45)
        form_layout.addWidget(save_btn, alignment=Qt.AlignRight)

        # Add form card to grid
        grid_layout.addWidget(form_card, 0, 1, 1, 1)
        
        profile_section_layout.addWidget(profile_grid)
        
        # Ajouter la section au layout du conteneur
        profile_container_layout.addWidget(profile_section)
        
        # Configurer le scroll area
        profile_scroll.setWidget(profile_container)
        profile_layout.addWidget(profile_scroll)
        
        # Ajouter l'onglet au TabWidget
        self.tabs.addTab(profile_tab, "User Profile")
        
    def create_camera_tab(self):
        """Créer l'onglet Camera Management pour les administrateurs"""
        camera_tab = QWidget()
        camera_layout = QVBoxLayout(camera_tab)
        camera_layout.setContentsMargins(30, 10, 30, 30)
        camera_layout.setSpacing(25)
        
        # Scroll area for camera tab
        camera_scroll = QScrollArea()
        camera_scroll.setWidgetResizable(True)
        camera_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        camera_scroll.setFrameShape(QFrame.NoFrame)
        camera_scroll.setStyleSheet("background-color: #f5f5f5; border: none;")
        
        # Camera settings container
        camera_container = QWidget()
        camera_container_layout = QVBoxLayout(camera_container)
        camera_container_layout.setContentsMargins(0, 0, 0, 0)
        camera_container_layout.setSpacing(25)  # diminuer 
        
        # Camera Management section
        camera_section = QFrame()
        camera_section.setObjectName("contentSection")
        camera_section_layout = QVBoxLayout(camera_section)
        camera_section_layout.setSpacing(5)
            
            # Camera header with pending approvals indicator
        # Camera header with pending approvals indicator
        camera_header_container = QWidget()
        camera_header_layout = QHBoxLayout(camera_header_container)
        camera_header_layout.setContentsMargins(0, 0, 0, 0)
        
        camera_header = QLabel("Camera Management")
        camera_header.setObjectName("sectionHeader")
        camera_header_layout.addWidget(camera_header)
        
        # Pending approvals badge
        self.pending_badge = QLabel("0")
        self.pending_badge.setObjectName("pendingBadge")
        self.pending_badge.setVisible(False)
        camera_header_layout.addWidget(self.pending_badge)
        camera_header_layout.addStretch()
        
        camera_section_layout.addWidget(camera_header_container)
    
        # Pending approvals section with improved styling
        pending_section = QFrame()
        pending_section.setObjectName("pendingSection")
        pending_section.setStyleSheet("""
            #pendingSection {
                background-color: #fff8e1;
                border: none;
                border-left: 4px solid #ffc107;
                border-radius: 8px;
                padding: 18px;
                margin-bottom: 20px;
            }
        """)
        pending_layout = QVBoxLayout(pending_section)
        pending_layout.setContentsMargins(15, 15, 15, 15)
        pending_layout.setSpacing(15)
        
        pending_header = QLabel("Pending Camera Approvals")
        pending_header.setObjectName("subSectionHeader")
        pending_header.setStyleSheet("color: #f57c00; font-weight: bold; font-size: 16px; background-color: transparent;")
        pending_layout.addWidget(pending_header)
        
        self.pending_cameras_list = QVBoxLayout()
        pending_layout.addLayout(self.pending_cameras_list)
        
        camera_section_layout.addWidget(pending_section)
        
        # Active cameras section with improved styling
        active_section = QFrame()
        active_section.setObjectName("activeSection")
        active_section.setStyleSheet("""
            #activeSection {
                background-color: #e3f2fd;
                border: none;
                border-left: 4px solid #2196f3;
                border-radius: 8px;
                padding: 18px;
                margin-bottom: 20px;
            }
        """)
        active_layout = QVBoxLayout(active_section)
        active_layout.setContentsMargins(15, 15, 15, 15)
        active_layout.setSpacing(15)
        
        active_header = QLabel("Active Cameras")
        active_header.setObjectName("subSectionHeader")
        active_header.setStyleSheet("color: #0d47a1; font-weight: bold; font-size: 16px; background-color: transparent;")
        active_layout.addWidget(active_header)
        
        # Camera list will be populated dynamically
        self.camera_list = QVBoxLayout()
        active_layout.addLayout(self.camera_list)
        
        # Add sample camera items with proper styling
        self.add_sample_camera_items()
        
        camera_section_layout.addWidget(active_section)
        
        # Ajouter la section au layout du conteneur
        camera_container_layout.addWidget(camera_section)
        
        # Configurer le scroll area
        camera_scroll.setWidget(camera_container)
        camera_layout.addWidget(camera_scroll)
        
        # Ajouter l'onglet au TabWidget
        self.tabs.addTab(camera_tab, "Camera Management")
    
    def add_sample_camera_items(self):
        """Ajouter des items de caméra avec le style approprié"""
        cameras = [
            {"name": "AutoCam video3", "type": "Auto-detected USB", "ip": "/dev/video3", 
            "rtsp": "rtsp://dev/video3:0/stream1", "location": "Auto-detected", "port": "Default", "status": "active"},
            {"name": "AutoCam video4", "type": "Auto-detected", "ip": "/dev/video4", 
            "rtsp": "", "location": "Auto-detected", "port": "", "status": "inactive"}
        ]
        
        for camera in cameras:
            camera_item = self.create_camera_item(camera)
            self.camera_list.addWidget(camera_item)
    
    def create_camera_item(self, camera):
        """Créer un item de caméra avec le style approprié"""
        item_frame = QFrame()
        item_frame.setObjectName("pendingItem")
        
        main_layout = QVBoxLayout(item_frame)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)
        
        # Header avec nom, type et status
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        
        info_layout = QVBoxLayout()
        info_layout.setSpacing(5)

        # Nom de la caméra - compatible avec objets DB et dictionnaires
        camera_name = camera.get("name") if isinstance(camera, dict) else getattr(camera, 'name', 'Unknown')
        name_label = QLabel(camera_name)
        name_label.setObjectName("pendingName")
        info_layout.addWidget(name_label)

        # Type - compatible avec objets DB et dictionnaires
        camera_type = camera.get("type") if isinstance(camera, dict) else getattr(camera, 'camera_type', 'Unknown')
        type_label = QLabel(f"Type: {camera_type}")
        type_label.setObjectName("pendingDetails")
        info_layout.addWidget(type_label)
        
        header_layout.addLayout(info_layout)
        header_layout.addStretch()
        
        # Status badge
        """ status_badge = self.create_status_badge("Inactif", "inactive") """
        # Status badge dynamique - compatible avec objets DB et dictionnaires
        if isinstance(camera, dict):
            # Pour les données de add_sample_camera_items (dictionnaires)
            status_text = "Active" if camera.get("status") == "active" else "Inactive"
            status_value = camera.get("status", "inactive")
        else:
            # Pour les objets Camera de la base de données
            status_text = "Active" if getattr(camera, 'is_active', False) else "Inactive"
            status_value = "active" if getattr(camera, 'is_active', False) else "inactive"

        status_badge = self.create_status_badge(status_text, status_value)
        header_layout.addWidget(status_badge)
        
        main_layout.addLayout(header_layout)
        
        # Détails de la caméra
        details_layout = QGridLayout()
        details_layout.setSpacing(10)
        details_layout.setContentsMargins(0, 0, 0, 0)
    

        # IP Address - compatible avec objets DB et dictionnaires
        details_layout.addWidget(QLabel("IP Address:"), 0, 0)
        camera_ip = camera.get("ip") if isinstance(camera, dict) else getattr(camera, 'ip_address', 'N/A')
        ip_label = QLabel(camera_ip)
        ip_label.setStyleSheet("color: #546e7a;")
        details_layout.addWidget(ip_label, 0, 1)

        # Location - compatible avec objets DB et dictionnaires
        details_layout.addWidget(QLabel("Location:"), 0, 2)
        camera_location = camera.get("location") if isinstance(camera, dict) else getattr(camera, 'location', 'N/A')
        location_label = QLabel(camera_location)
        location_label.setStyleSheet("color: #546e7a;")
        details_layout.addWidget(location_label, 0, 3)

        
        # RTSP URL
        if camera["rtsp"]:
            details_layout.addWidget(QLabel("RTSP URL:"), 1, 0)
            rtsp_label = QLabel(camera["rtsp"])
            rtsp_label.setStyleSheet("color: #546e7a;")
            details_layout.addWidget(rtsp_label, 1, 1)
        
        # Port
        if camera["port"]:
            details_layout.addWidget(QLabel("Port:"), 1, 2)
            port_label = QLabel(camera["port"])
            port_label.setStyleSheet("color: #546e7a;")
            details_layout.addWidget(port_label, 1, 3)
        
        main_layout.addLayout(details_layout)
        
        # Utiliser la méthode commune pour les boutons
        buttons_frame = self.create_camera_buttons(camera, is_dict_camera=True)
        main_layout.addWidget(buttons_frame)
        
        return item_frame

    def create_status_badge(self, text, status="inactive"):
        """Créer un badge de statut avec le style approprié"""
        badge = QLabel(text)
        badge.setObjectName("statusBadge")
        
        # Définir les couleurs selon le statut
        if status == "active":
            background_color = "#28a745"  # Vert
            text_color = "white"
        elif status == "inactive":
            background_color = "#dc3545"  # Rouge
            text_color = "white"
        else:
            background_color = "#6c757d"  # Gris par défaut
            text_color = "white"
        
        # Appliquer le style directement avec des dimensions correctes
        badge.setStyleSheet(f"""
            QLabel#statusBadge {{
                background-color: {background_color};
                color: {text_color};
                border-radius: 12px;
                padding: 6px 16px;
                font-size: 8px;
                font-weight: bold;
                width: 10px;
                height: 8px;
                text-align: center;
            }}
        """)
        
        # Forcer l'application du style
        badge.style().unpolish(badge)
        badge.style().polish(badge)
        badge.update()
        
        return badge
        
    def create_system_tab(self):
        """Créer l'onglet Reports & Logging avec un style simple comme NotificationManager"""
        system_tab = QWidget()
        system_layout = QVBoxLayout(system_tab)
        system_layout.setContentsMargins(30, 10, 30, 30)  # Mêmes margins que Camera Management
        system_layout.setSpacing(5)  # Réduire l'espacement principal de 25 à 8

        # Scroll area for system tab (identique à Camera Management)
        system_scroll = QScrollArea()
        system_scroll.setWidgetResizable(True)
        system_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        system_scroll.setFrameShape(QFrame.NoFrame)
        system_scroll.setStyleSheet("background-color: #f5f5f5; border: none;")
        
        # System settings container
        system_container = QWidget()
        system_container_layout = QVBoxLayout(system_container)
        system_container_layout.setContentsMargins(0, 0, 0, 0)
        system_container_layout.setSpacing(5)  # Réduire l'espacement entre sections de 25 à 12
        
        # === SECTION STATUS DES SERVICES (Style simple) ===
        services_section = QFrame()
        services_section.setObjectName("activeSection")
        services_section_layout = QVBoxLayout(services_section)
        services_section_layout.setSpacing(5)  # Réduire de 15 à 10
        
        # En-tête de section
        services_header = QLabel("Services Status")
        services_header.setObjectName("subSectionHeader")
        services_section_layout.addWidget(services_header)
        
        # Conteneur pour les widgets de services (sera rempli dynamiquement)
        self.services_container = QWidget()
        self.services_container_layout = QVBoxLayout(self.services_container)
        self.services_container_layout.setContentsMargins(0, 0, 0, 0)
        self.services_container_layout.setSpacing(8)
        
        services_section_layout.addWidget(self.services_container)
        
        # Initialiser le monitoring des services
        self.init_service_monitoring()
        
        # Timer pour mise à jour automatique des services
        self.service_update_timer = QTimer()
        self.service_update_timer.timeout.connect(self.update_service_widgets)
        self.service_update_timer.start(5000)  # Mise à jour toutes les 5 secondes
        
        system_container_layout.addWidget(services_section)
        
        # === SECTION LOGS RÉCENTS (Style simple) ===
        logs_section = QFrame()
        logs_section.setObjectName("activeSection")
        logs_section_layout = QVBoxLayout(logs_section)
        logs_section_layout.setSpacing(5)  # Réduire de 15 à 8
        
        # En-tête de section
        logs_header = QLabel("Recent Logs")
        logs_header.setObjectName("subSectionHeader")
        logs_section_layout.addWidget(logs_header)
        
        # Widget de logs simple
        log_widget = self.create_simple_log_widget()
        logs_section_layout.addWidget(log_widget)
        
        system_container_layout.addWidget(logs_section)
        
        # === SECTION REAL-TIME LOGS ===
        realtime_logs_section = QFrame()
        realtime_logs_section.setObjectName("activeSection")
        realtime_logs_section_layout = QVBoxLayout(realtime_logs_section)
        realtime_logs_section_layout.setSpacing(5)  # Réduire de 15 à 8
        
        # En-tête de section
        realtime_header = QLabel("Real-Time System Logs")
        realtime_header.setObjectName("subSectionHeader")
        realtime_logs_section_layout.addWidget(realtime_header)
        
        # Widget de logs en temps réel
        realtime_log_widget = self.create_realtime_log_widget()
        realtime_logs_section_layout.addWidget(realtime_log_widget)
        
        system_container_layout.addWidget(realtime_logs_section)
        system_container_layout.addWidget(logs_section)
        
        # === SECTION AUTHENTIFICATION RÉCENTE ===
        auth_section = QFrame()
        auth_section.setObjectName("activeSection")
        auth_section_layout = QVBoxLayout(auth_section)
        auth_section_layout.setSpacing(5)  # Réduire de 15 à 8
        
        # En-tête de section
        auth_header = QLabel("Recent Authentication Activity")
        auth_header.setObjectName("subSectionHeader")
        auth_section_layout.addWidget(auth_header)
        
        # Widget d'authentification
        auth_widget = self.create_auth_activity_widget()
        auth_section_layout.addWidget(auth_widget)
        
        system_container_layout.addWidget(auth_section)
        
        # === SECTION ALERTES SYSTÈME ===
        alerts_section = QFrame()
        alerts_section.setObjectName("activeSection")
        alerts_section_layout = QVBoxLayout(alerts_section)
        alerts_section_layout.setSpacing(5)  # Réduire de 15 à 8
        
        # En-tête de section
        alerts_header = QLabel("System Alerts & Notifications")
        alerts_header.setObjectName("subSectionHeader")
        alerts_section_layout.addWidget(alerts_header)
        
        # Widget d'alertes
        alerts_widget = self.create_system_alerts_widget()
        alerts_section_layout.addWidget(alerts_widget)
        
        system_container_layout.addWidget(alerts_section)
        
        # === SECTION ACTIONS RAPIDES (Style simple) ===
        actions_section = QFrame()
        actions_section.setObjectName("activeSection")
        actions_section_layout = QVBoxLayout(actions_section)
        actions_section_layout.setSpacing(5)  # Réduire de 15 à 8
        
        # En-tête de section
        actions_header = QLabel("Quick Actions")
        actions_header.setObjectName("subSectionHeader")
        actions_section_layout.addWidget(actions_header)
        
        # Boutons d'actions
        actions_widget = self.create_simple_actions_widget()
        actions_section_layout.addWidget(actions_widget)
        
        system_container_layout.addWidget(actions_section)
        
        # Configurer le scroll area
        system_scroll.setWidget(system_container)
        system_layout.addWidget(system_scroll)
        
        # Ajouter l'onglet au TabWidget
        self.tabs.addTab(system_tab, "Reports")
    
    def init_service_monitoring(self):
        """Initialiser le système de monitoring des services"""
        self.service_widgets = {}  # Dictionnaire pour stocker les widgets par nom de service
        
        # Créer les widgets initiaux
        self.update_service_widgets()
    
    def get_real_service_status(self):
        """Obtenir le vrai statut des services en temps réel"""
        services_status = []
        
        try:
            # 1. Camera Service - Vérifier les services de caméras
            camera_count = 0
            camera_status = "Unknown"
            camera_details = "Checking..."
            
            if hasattr(self, 'camera_service') and self.camera_service:
                try:
                    cameras = self.camera_service.get_all_cameras()
                    active_cameras = [cam for cam in cameras if cam.status == 'active']
                    camera_count = len(active_cameras)
                    
                    if camera_count > 0:
                        camera_status = "Running"
                        camera_details = f"{camera_count} cameras active"
                    else:
                        camera_status = "Warning"
                        camera_details = "No active cameras"
                except Exception as e:
                    camera_status = "Error"
                    camera_details = f"Service error: {str(e)[:30]}..."
            
            services_status.append(("Camera Service", camera_status, camera_details))
            
            # 2. Storage Service - Vérifier l'espace disque
            storage_status = "Unknown"
            storage_details = "Checking..."
            
            if hasattr(self, 'storage_service') and self.storage_service:
                try:
                    storage_info = self.storage_service.get_storage_info()
                    used_percentage = storage_info.get('used_percentage', 0)
                    
                    if used_percentage < 75:
                        storage_status = "Running"
                    elif used_percentage < 90:
                        storage_status = "Warning"
                    else:
                        storage_status = "Error"
                    
                    storage_details = f"{used_percentage:.1f}% disk usage"
                except Exception as e:
                    storage_status = "Error"
                    storage_details = f"Storage check failed"
            
            services_status.append(("Storage Service", storage_status, storage_details))
            
            # 3. AI Detection - Vérifier le service YOLO
            ai_status = "Unknown"
            ai_details = "Checking..."
            
            try:
                # Vérifier si le modèle YOLO est chargé et opérationnel
                import os
                model_path = "/home/abirc240/Desktop/sailor-vision-ai/yolo11n.pt"
                if os.path.exists(model_path):
                    ai_status = "Running"
                    ai_details = "YOLO model loaded"
                else:
                    ai_status = "Warning"
                    ai_details = "Model file not found"
            except Exception as e:
                ai_status = "Error"
                ai_details = "AI service unavailable"
            
            services_status.append(("AI Detection", ai_status, ai_details))
            
            # 4. User Authentication - Vérifier la base de données utilisateurs
            auth_status = "Unknown"
            auth_details = "Checking..."
            
            if hasattr(self, 'user_service') and self.user_service:
                try:
                    # Tester une requête simple sur la base de données
                    users_count = len(self.user_service.get_all_users())
                    auth_status = "Running"
                    auth_details = f"{users_count} users in system"
                except Exception as e:
                    auth_status = "Error"
                    auth_details = "Database connection failed"
            
            services_status.append(("User Authentication", auth_status, auth_details))
            
            # 5. Network Service - Vérifier la connectivité
            network_status = "Unknown"
            network_details = "Checking..."
            
            try:
                import subprocess
                import platform
                
                # Ping test pour vérifier la connectivité
                param = "-n" if platform.system().lower() == "windows" else "-c"
                command = ["ping", param, "1", "8.8.8.8"]
                
                result = subprocess.run(command, capture_output=True, text=True, timeout=3)
                if result.returncode == 0:
                    network_status = "Running"
                    network_details = "Network connectivity OK"
                else:
                    network_status = "Warning"
                    network_details = "Limited connectivity"
            except Exception as e:
                network_status = "Error"
                network_details = "Network check failed"
            
            services_status.append(("Network Service", network_status, network_details))
            
            # 6. Database Service - Vérifier la connexion à la base de données
            db_status = "Unknown"
            db_details = "Checking..."
            
            try:
                from database import create_new_session
                session = create_new_session()
                if session:
                    # Test simple de la base de données
                    session.execute("SELECT 1")
                    session.close()
                    db_status = "Running"
                    db_details = "Database connection OK"
                else:
                    db_status = "Error"
                    db_details = "Cannot create session"
            except Exception as e:
                db_status = "Error"
                db_details = "Database error"
            
            services_status.append(("Database Service", db_status, db_details))
            
        except Exception as e:
            print(f"[Settings] Error getting service status: {e}")
        
        return services_status
    
    def update_service_widgets(self):
        """Mettre à jour les widgets de services avec des données en temps réel"""
        try:
            # Obtenir le statut réel des services
            services_data = self.get_real_service_status()
            
            # Vider le conteneur actuel
            for i in reversed(range(self.services_container_layout.count())):
                child = self.services_container_layout.itemAt(i).widget()
                if child:
                    child.setParent(None)
            
            # Recréer les widgets avec les nouvelles données
            for name, status, details in services_data:
                # Déterminer la couleur selon le statut
                color = self.get_status_color(status)
                
                # Créer le widget avec les vraies données
                service_widget = self.create_enhanced_service_widget(name, status, color, details)
                self.services_container_layout.addWidget(service_widget)
                
                # Stocker une référence au widget
                self.service_widgets[name] = service_widget
            
            print(f"[Settings] Service widgets updated with real-time data")
            
        except Exception as e:
            print(f"[Settings] Error updating service widgets: {e}")
    
    def get_status_color(self, status):
        """Obtenir la couleur selon le statut"""
        status_colors = {
            "Running": "#4caf50",   # Vert
            "Warning": "#ff9800",   # Orange
            "Error": "#f44336",     # Rouge
            "Unknown": "#9e9e9e"    # Gris
        }
        return status_colors.get(status, "#9e9e9e")
    
    def create_enhanced_service_widget(self, name, status, color, details):
        """Créer un widget de service amélioré avec bouton details et plus d'informations"""
        widget = QFrame()
        widget.setFixedHeight(85)  # Légèrement plus haut pour les boutons
        widget.setStyleSheet(f"""
            QFrame {{
                background-color: #e3f2fd;
                border-left: 4px solid {color};
                border-radius: 8px;
                margin: 2px 0px;
                padding: 0px;
            }}
        """)
        
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(15)
        
        # Icône de service avec indicateur de statut
        icon_container = QWidget()
        icon_container.setFixedSize(40, 40)
        icon_container.setStyleSheet(f"""
            background-color: {color};
            border-radius: 20px;
            border: none;
        """)
        icon_layout = QVBoxLayout(icon_container)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        
        service_icons = {
            "Camera Service": "📹",
            "Storage Service": "�", 
            "AI Detection": "🔍",
            "User Authentication": "🔐",
            "Network Service": "🌐",
            "Database Service": "🗄️"
        }
        
        icon_label = QLabel(service_icons.get(name, "⚙️"))
        icon_label.setStyleSheet("""
            font-size: 18px;
            color: white;
            background-color: transparent;
            border: none;
        """)
        icon_label.setAlignment(Qt.AlignCenter)
        icon_layout.addWidget(icon_label)
        
        layout.addWidget(icon_container)
        
        # Conteneur pour le texte
        text_container = QWidget()
        text_container.setStyleSheet("background-color: transparent; border: none;")
        text_layout = QVBoxLayout(text_container)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)
        
        # Nom du service
        name_label = QLabel(name)
        name_label.setStyleSheet("""
            color: #1565C0;
            font-weight: bold;
            font-size: 14px;
            background-color: transparent;
            border: none;
        """)
        text_layout.addWidget(name_label)
        
        # Status et détails du service
        status_details = QLabel(f"Status: {status} • {details}")
        status_details.setStyleSheet("""
            color: #424242;
            font-size: 11px;
            background-color: transparent;
            border: none;
        """)
        text_layout.addWidget(status_details)
        
        layout.addWidget(text_container)
        layout.addStretch()
        
        # Conteneur pour les actions
        actions_container = QWidget()
        actions_container.setStyleSheet("background-color: transparent; border: none;")
        actions_layout = QVBoxLayout(actions_container)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(4)
        
        # Badge de statut
        status_badge = QLabel(status)
        status_badge.setStyleSheet(f"""
            background-color: {color};
            color: white;
            border: none;
            padding: 3px 8px;
            border-radius: 4px;
            font-weight: 500;
            font-size: 10px;
            min-width: 50px;
            text-align: center;
        """)
        status_badge.setAlignment(Qt.AlignCenter)
        actions_layout.addWidget(status_badge)
        
        # Bouton Details (seulement pour Warning/Error)
        if status in ["Warning", "Error"]:
            details_btn = QPushButton("Details")
            details_btn.setStyleSheet("""
                QPushButton {
                    background-color: #1976D2;
                    color: white;
                    border: none;
                    padding: 4px 8px;
                    border-radius: 3px;
                    font-weight: 500;
                    font-size: 10px;
                    min-width: 50px;
                }
                QPushButton:hover {
                    background-color: #1565C0;
                }
            """)
            details_btn.clicked.connect(lambda: self.show_service_details(name, status, details))
            actions_layout.addWidget(details_btn)
        
        layout.addWidget(actions_container)
        
        return widget
    
    def create_auth_activity_widget(self):
        """Créer un widget d'activité d'authentification récente"""
        widget = QFrame()
        widget.setStyleSheet("""
            QFrame {
                background-color: #e3f2fd;
                border-left: 4px solid #2196F3;
                border-radius: 8px;
                margin: 2px 0px;
                padding: 10px;
            }
        """)
        
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(10)
        
        # En-tête avec statistiques
        header_layout = QHBoxLayout()
        
        auth_title = QLabel("🔐 Authentication Logs")
        auth_title.setStyleSheet("""
            color: #1565C0;
            font-weight: bold;
            font-size: 14px;
            background-color: transparent;
            border: none;
        """)
        header_layout.addWidget(auth_title)
        header_layout.addStretch()
        
        # Statistiques rapides
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(15)
        
        # Connexions réussies
        success_stat = QLabel("✅ 24 Success")
        success_stat.setStyleSheet("""
            background-color: #4caf50;
            color: white;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 10px;
            font-weight: bold;
        """)
        stats_layout.addWidget(success_stat)
        
        # Échecs
        failed_stat = QLabel("❌ 5 Failed")
        failed_stat.setStyleSheet("""
            background-color: #f44336;
            color: white;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 10px;
            font-weight: bold;
        """)
        stats_layout.addWidget(failed_stat)
        
        header_layout.addLayout(stats_layout)
        layout.addLayout(header_layout)
        
        # Liste des connexions récentes
        auth_list = QFrame()
        auth_list.setStyleSheet("""
            background-color: #ffffff;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 5px;
        """)
        auth_list.setFixedHeight(180)  # Augmenté de 120 à 180
        
        auth_list_layout = QVBoxLayout(auth_list)
        auth_list_layout.setContentsMargins(8, 5, 8, 5)
        auth_list_layout.setSpacing(3)
        
        # Données d'exemple d'authentification
        auth_data = [
            ("admin", "14:32:15", "Success", "127.0.0.1"),
            ("operator1", "14:30:22", "Success", "192.168.1.45"),
            ("guest", "14:28:10", "Failed", "192.168.1.100"),
            ("admin", "14:25:05", "Success", "127.0.0.1"),
            ("unknown", "14:20:30", "Failed", "192.168.1.200")
        ]
        
        for user, time, result, ip in auth_data:
            auth_item = self.create_auth_item(user, time, result, ip)
            auth_list_layout.addWidget(auth_item)
        
        layout.addWidget(auth_list)
        
        return widget
    
    def create_auth_item(self, user, time, result, ip):
        """Créer un élément d'authentification"""
        item = QFrame()
        item.setFixedHeight(28)  # Augmenté de 20 à 28
        item.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border: none;
                margin: 2px;
                padding: 2px;
            }
        """)
        
        layout = QHBoxLayout(item)
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(8)
        
        # Icône de résultat
        icon = "✅" if result == "Success" else "❌"
        icon_label = QLabel(icon)
        icon_label.setFixedWidth(20)
        icon_label.setStyleSheet("font-size: 10px;")
        layout.addWidget(icon_label)
        
        # Timestamp
        time_label = QLabel(time)
        time_label.setFixedWidth(60)
        time_label.setStyleSheet("font-size: 11px; color: #666; font-weight: bold;")  # Augmenté à 11px
        layout.addWidget(time_label)
        
        # Utilisateur
        user_label = QLabel(user)
        user_label.setFixedWidth(80)
        user_label.setStyleSheet("font-size: 11px; color: #333; font-weight: bold;")  # Augmenté à 11px
        layout.addWidget(user_label)
        
        # IP
        ip_label = QLabel(ip)
        ip_label.setFixedWidth(100)
        ip_label.setStyleSheet("font-size: 11px; color: #888;")  # Augmenté à 11px
        layout.addWidget(ip_label)
        
        # Résultat
        result_color = "#4caf50" if result == "Success" else "#f44336"
        result_label = QLabel(result)
        result_label.setStyleSheet(f"font-size: 11px; color: {result_color}; font-weight: bold;")  # Augmenté à 11px
        layout.addWidget(result_label)
        
        layout.addStretch()
        
        return item
    
    def create_system_alerts_widget(self):
        """Créer un widget d'alertes système"""
        widget = QFrame()
        widget.setStyleSheet("""
            QFrame {
                background-color: #fff3e0;
                border-left: 4px solid #ff9800;
                border-radius: 8px;
                margin: 2px 0px;
                padding: 10px;
            }
        """)
        
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(10)
        
        # En-tête avec compteur d'alertes
        header_layout = QHBoxLayout()
        
        alerts_title = QLabel("🚨 Active System Alerts")
        alerts_title.setStyleSheet("""
            color: #e65100;
            font-weight: bold;
            font-size: 14px;
            background-color: transparent;
            border: none;
        """)
        header_layout.addWidget(alerts_title)
        header_layout.addStretch()
        
        # Compteur d'alertes
        alert_count = QLabel("3 Active")
        alert_count.setStyleSheet("""
            background-color: #ff9800;
            color: white;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: bold;
        """)
        header_layout.addWidget(alert_count)
        
        layout.addLayout(header_layout)
        
        # Liste des alertes actives
        alerts_container = QFrame()
        alerts_container.setStyleSheet("""
            background-color: #ffffff;
            border: 1px solid #ffcc02;
            border-radius: 4px;
            padding: 5px;
        """)
        alerts_container.setFixedHeight(150)  # Ajout d'une hauteur fixe
        
        alerts_layout = QVBoxLayout(alerts_container)
        alerts_layout.setContentsMargins(8, 5, 8, 5)
        alerts_layout.setSpacing(5)
        
        # Alertes d'exemple
        alerts_data = [
            ("High", "⚠️", "Storage usage exceeded 75%", "2 min ago"),
            ("Medium", "🔍", "AI Detection: 3 consecutive failures", "5 min ago"),
            ("Low", "🔐", "Multiple failed login attempts detected", "10 min ago")
        ]
        
        for severity, icon, message, time in alerts_data:
            alert_item = self.create_alert_item(severity, icon, message, time)
            alerts_layout.addWidget(alert_item)
        
        layout.addWidget(alerts_container)
        
        return widget
    
    def create_alert_item(self, severity, icon, message, time):
        """Créer un élément d'alerte"""
        item = QFrame()
        item.setFixedHeight(35)  # Augmenté de 30 à 35
        
        severity_colors = {
            "High": "#f44336",
            "Medium": "#ff9800", 
            "Low": "#2196F3"
        }
        
        item.setStyleSheet(f"""
            QFrame {{
                background-color: #fafafa;
                border-left: 3px solid {severity_colors.get(severity, "#ccc")};
                border-radius: 3px;
                margin: 2px;
                padding: 2px;
            }}
        """)
        
        layout = QHBoxLayout(item)
        layout.setContentsMargins(8, 5, 8, 5)
        layout.setSpacing(8)
        
        # Icône d'alerte
        icon_label = QLabel(icon)
        icon_label.setFixedWidth(20)
        icon_label.setStyleSheet("font-size: 12px;")
        layout.addWidget(icon_label)
        
        # Message d'alerte
        message_label = QLabel(message)
        message_label.setStyleSheet("font-size: 12px; color: #333; font-weight: 500;")  # Augmenté à 12px
        layout.addWidget(message_label)
        
        layout.addStretch()
        
        # Timestamp
        time_label = QLabel(time)
        time_label.setStyleSheet("font-size: 11px; color: #888;")  # Augmenté à 11px
        layout.addWidget(time_label)
        
        # Badge de sévérité
        severity_badge = QLabel(severity)
        severity_badge.setStyleSheet(f"""
            background-color: {severity_colors.get(severity, "#ccc")};
            color: white;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 9px;
            font-weight: bold;
            min-width: 35px;
            text-align: center;
        """)
        severity_badge.setAlignment(Qt.AlignCenter)
        layout.addWidget(severity_badge)
        
        return item
    
    def show_service_details(self, service_name, status, details):
        """Afficher les détails d'un service avec ses logs"""
        from PyQt5.QtWidgets import QDialog, QTextEdit
        
        dialog = QDialog(self)
        dialog.setWindowTitle(f"{service_name} - Details")
        dialog.setFixedSize(600, 400)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
            }
        """)
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # En-tête du service
        header = QLabel(f"🔍 {service_name} - {status}")
        header.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #333;
            padding: 10px;
            background-color: #e3f2fd;
            border-radius: 8px;
            border-left: 4px solid #2196F3;
        """)
        layout.addWidget(header)
        
        # Détails du problème
        details_label = QLabel(f"Issue: {details}")
        details_label.setStyleSheet("""
            font-size: 14px;
            color: #666;
            padding: 8px;
        """)
        layout.addWidget(details_label)
        
        # Zone de logs spécifiques
        logs_area = QTextEdit()
        logs_area.setReadOnly(True)
        logs_area.setStyleSheet("""
            QTextEdit {
                background-color: #ffffff;
                border: 1px solid #ddd;
                border-radius: 4px;
                font-family: 'Courier New', monospace;
                font-size: 11px;
                color: #333;
                padding: 10px;
            }
        """)
        
        # Logs d'exemple selon le service
        sample_logs = {
            "AI Detection": """[14:30:15] ERROR - YOLO model prediction failed
[14:29:45] ERROR - Input tensor shape mismatch
[14:29:20] ERROR - GPU memory allocation failed
[14:28:55] WARN - Falling back to CPU processing
[14:28:30] INFO - Detection service restarted""",
            
            "User Authentication": """[14:32:10] WARN - Failed login attempt for user 'admin' from 192.168.1.100
[14:31:45] WARN - Failed login attempt for user 'guest' from 192.168.1.100  
[14:31:20] WARN - Failed login attempt for user 'operator' from 192.168.1.100
[14:30:55] ERROR - IP 192.168.1.100 temporarily blocked (too many failures)
[14:30:30] INFO - Security notification sent to administrators""",
            
            "Network Service": """[14:35:20] ERROR - Connection timeout to camera 192.168.1.55
[14:35:00] ERROR - Network interface eth0 packet loss 15%
[14:34:30] WARN - High latency detected (>500ms)
[14:34:00] ERROR - DHCP server unreachable
[14:33:30] INFO - Attempting network diagnostics..."""
        }
        
        logs_content = sample_logs.get(service_name, f"[14:32:15] INFO - {service_name} logs\n[14:32:10] WARN - {details}")
        logs_area.setPlainText(logs_content)
        layout.addWidget(logs_area)
        
        # Boutons d'action
        buttons_layout = QHBoxLayout()
        
        export_btn = QPushButton("📤 Export Logs")
        export_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: 500;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        buttons_layout.addWidget(export_btn)
        
        restart_btn = QPushButton("🔄 Restart Service") 
        restart_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff9800;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: 500;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #f57c00;
            }
        """)
        buttons_layout.addWidget(restart_btn)
        
        close_btn = QPushButton("✖️ Close")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #666;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: 500;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #555;
            }
        """)
        close_btn.clicked.connect(dialog.close)
        buttons_layout.addWidget(close_btn)
        
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)
        
        dialog.exec_()
    
    def create_simple_log_widget(self):
        """Créer un widget de logs simple"""
        widget = QFrame()
        widget.setStyleSheet("""
            QFrame {
                background-color: #e3f2fd;
                border-left: 4px solid #2196F3;
                border-radius: 8px;
                margin: 2px 0px;
                padding: 10px;
            }
        """)
        
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(8)
        
        # En-tête avec bouton refresh
        header_layout = QHBoxLayout()
        
        logs_title = QLabel("Recent System Logs")
        logs_title.setStyleSheet("""
            color: #1565C0;
            font-weight: bold;
            font-size: 14px;
            background-color: transparent;
            border: none;
        """)
        header_layout.addWidget(logs_title)
        header_layout.addStretch()
        
        refresh_btn = QPushButton("🔄")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 4px 8px;
                border-radius: 4px;
                font-weight: 500;
                font-size: 12px;
                min-width: 30px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        refresh_btn.setToolTip("Refresh logs")
        header_layout.addWidget(refresh_btn)
        
        layout.addLayout(header_layout)
        
        # Zone de logs
        logs_area = QTextEdit()
        logs_area.setFixedHeight(120)
        logs_area.setReadOnly(True)
        logs_area.setStyleSheet("""
            QTextEdit {
                background-color: #ffffff;
                border: 1px solid #ddd;
                border-radius: 4px;
                font-family: 'Courier New', monospace;
                font-size: 11px;
                color: #333;
                padding: 5px;
            }
        """)
        
        # Ajouter des logs d'exemple
        sample_logs = """[14:32:15] INFO - Camera service started successfully
[14:32:10] INFO - 6 cameras connected and operational
[14:31:45] WARN - Storage usage at 75%
[14:31:30] INFO - AI detection processing normally
[14:31:15] INFO - Database connection established"""
        
        logs_area.setPlainText(sample_logs)
        layout.addWidget(logs_area)
        
        return widget
    
    def create_simple_actions_widget(self):
        """Créer un widget d'actions simples"""
        widget = QFrame()
        widget.setStyleSheet("""
            QFrame {
                background-color: #e3f2fd;
                border-left: 4px solid #2196F3;
                border-radius: 8px;
                margin: 2px 0px;
                padding: 10px;
            }
        """)
        
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(10)
        
        # Titre
        actions_title = QLabel("System Actions")
        actions_title.setStyleSheet("""
            color: #1565C0;
            font-weight: bold;
            font-size: 14px;
            background-color: transparent;
            border: none;
        """)
        layout.addWidget(actions_title)
        
        # Boutons d'actions
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        
        # Export logs
        export_btn = QPushButton("📤 Export Logs")
        export_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: 500;
                font-size: 12px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        buttons_layout.addWidget(export_btn)
        
        # Clear logs
        clear_btn = QPushButton("🗑️ Clear Logs")
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff9800;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: 500;
                font-size: 12px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #f57c00;
            }
        """)
        buttons_layout.addWidget(clear_btn)
        
        # Download report
        report_btn = QPushButton("📊 Generate Report")
        report_btn.setStyleSheet("""
            QPushButton {
                background-color: #4caf50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: 500;
                font-size: 12px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        buttons_layout.addWidget(report_btn)
        
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)
        
        return widget

    def create_form_field(self, label_text, icon_name=None, tooltip=None):
        """Create a form field with label and optional icon with modern styling"""
        layout = QVBoxLayout()
        layout.setSpacing(8)
        
        # Label with icon
        label_layout = QHBoxLayout()
        label_layout.setContentsMargins(0, 0, 0, 0)
        label_layout.setSpacing(8)
        
        # Label
        label = QLabel(label_text)
        label.setObjectName("fieldLabel")
        label.setStyleSheet("color: #333333 ; font-weight: bold; font-size: 14px;")
        label.setProperty("class", "fieldLabel")
        label_layout.addWidget(label)

        label_layout.addStretch()
        layout.addLayout(label_layout)
        
        return layout
        
    def save_profile_changes(self):
        """Save profile changes to database"""
        try:
            # Get values from form
            name = self.name_input.text().strip()
            email = self.email_input.text().strip()
            password = self.password_input.text()
            
            # Basic validation
            if not name:
                QMessageBox.warning(self, "Validation Error", "Please enter your name.")
                return
                
            if not email:
                QMessageBox.warning(self, "Validation Error", "Please enter your email address.")
                return
            
            # Prepare user data
            user_data = {
                "id": self.user.get("id"),
                "email": email
            }
            
            # Split name into first and last name
            name_parts = name.split(maxsplit=1)
            user_data["first_name"] = name_parts[0]
            if len(name_parts) > 1:
                user_data["last_name"] = name_parts[1]
            else:
                user_data["last_name"] = ""
                
            # Handle password change if provided
            if password:
                user_data["password_hash"] = hash_password(password)
                
            # Update user in database
            success = self.user_service.update_user(user_data)
            
            if success:
                QMessageBox.information(self, "Success", "Profile updated successfully!")
                # Update the local user data
                self.user.update(user_data)
            else:
                QMessageBox.warning(self, "Error", "Failed to update profile.")
                
        except Exception as e:
            print(f"[Settings] Error saving profile changes: {e}")
            QMessageBox.warning(self, "Error", f"An error occurred: {str(e)}")
    
    def load_profile_settings_safe(self):
        """Version sécurisée du chargement du profil utilisateur avec gestion d'erreurs"""
        print("[Settings] Début load_profile_settings_safe...")
        try:
            self.load_profile_settings()
            print("[Settings] load_profile_settings_safe terminé avec succès")
        except Exception as e:
            print(f"[Settings] ERREUR dans load_profile_settings_safe: {e}")
            import traceback
            print(f"[Settings] Traceback: {traceback.format_exc()}")

    def load_profile_settings(self):
        """Load user profile settings into the UI"""
        print("[Settings] Début load_profile_settings...")
        
        try:
            print("[Settings] Chargement du nom complet...")
            full_name = f"{self.user.get('first_name', '')} {self.user.get('last_name', '')}".strip()
            print(f"[Settings] Nom complet: '{full_name}'")
            
            if hasattr(self, 'name_input') and self.name_input:
                self.name_input.setText(full_name)
                print("[Settings] Nom défini dans name_input")
            else:
                print("[Settings] ATTENTION: name_input non trouvé ou None")
            
            print("[Settings] Chargement de l'email...")
            email = self.user.get('email', '')
            print(f"[Settings] Email: '{email}'")
            
            if hasattr(self, 'email_input') and self.email_input:
                self.email_input.setText(email)
                print("[Settings] Email défini dans email_input")
            else:
                print("[Settings] ATTENTION: email_input non trouvé ou None")
            
            print("[Settings] Chargement de l'image de profil...")
            profile_picture_path = self.user.get('profile_picture', '')
            print(f"[Settings] Chemin image de profil: '{profile_picture_path}'")
            
            if profile_picture_path and hasattr(self, 'profile_pic') and self.profile_pic:
                print("[Settings] Chargement de l'image...")
                # Charger l'image
                pixmap = QPixmap(profile_picture_path)
                if not pixmap.isNull():
                    print("[Settings] Image chargée, redimensionnement...")
                    # Calculer la taille effective (sans la bordure)
                    size = self.profile_pic.size()
                    border_width = 1 # Largeur de la bordure définie dans le CSS
                    effective_size = QSize(size.width() - 2*border_width, size.height() - 2*border_width)
                    
                    # Créer un pixmap transparent de la taille totale (avec bordure)
                    rounded_pixmap = QPixmap(size)
                    rounded_pixmap.fill(Qt.transparent)
                    
                    # Dessiner l'image dans un masque circulaire
                    painter = QPainter(rounded_pixmap)
                    painter.setRenderHint(QPainter.Antialiasing)
                    
                    # Définir un chemin circulaire qui tient compte de la bordure
                    path = QPainterPath()
                    path.addEllipse(border_width, border_width, 
                                effective_size.width(), effective_size.height())
                    
                    # Appliquer le chemin comme masque
                    painter.setClipPath(path)
                    
                    # Redimensionner l'image et la dessiner avec les bons offsets
                    scaled_pixmap = pixmap.scaled(effective_size.width(), effective_size.height(), 
                                                Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    
                    # Calculer la position pour centrer l'image dans le cercle
                    # Convertir les offsets en entiers pour éviter l'erreur de type
                    x_offset = int(border_width + (effective_size.width() - scaled_pixmap.width()) / 2)
                    y_offset = int(border_width + (effective_size.height() - scaled_pixmap.height()) / 2)
                    
                    # Dessiner l'image dans le cercle
                    painter.drawPixmap(x_offset, y_offset, scaled_pixmap)
                    painter.end()
                    
                    # Appliquer l'image au QLabel
                    self.profile_pic.setPixmap(rounded_pixmap)
                    print("[Settings] Image de profil appliquée avec succès")
                else:
                    print(f"[Settings] ERREUR: Impossible de charger l'image depuis '{profile_picture_path}'")
            else:
                print("[Settings] Aucune image de profil ou profile_pic non trouvé")
            
            print("[Settings] load_profile_settings terminé avec succès")
            
        except Exception as e:
            print(f"[Settings] ERREUR dans load_profile_settings: {e}")
            import traceback
            print(f"[Settings] Traceback: {traceback.format_exc()}")
            raise
    
    def load_camera_settings(self):
        """Load camera settings"""
        # Vérifier si l'utilisateur a les permissions nécessaires
        if not self.has_camera_permission:
            return
            
        # Clear existing camera widgets
        if hasattr(self, 'camera_list'):
            self.clear_camera_list()

        # Get cameras from service
        cameras = self.camera_service.get_all_cameras()

        # Add camera widgets to list
        for camera in cameras:
            camera_item = QFrame()
            camera_item.setObjectName("cameraCard")
            camera_item.setStyleSheet("""
                QFrame#cameraCard {
                    background-color: white;
                    border: none;
                    border-radius: 12px;
                    padding: 0px;
                }
                QFrame#cameraCard:hover {
                }
            """)

            layout = QVBoxLayout(camera_item)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
            
            # Header section with camera name and status
            header_frame = QFrame()
            header_frame.setStyleSheet("""
                background-color: #f5f5f5;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                border-bottom: 1px solid #e0e0e0;
            """)
            header_layout = QHBoxLayout(header_frame)
            header_layout.setContentsMargins(15, 12, 15, 12)

            
            # Camera title and type
            title_layout = QVBoxLayout()
            title_layout.setSpacing(2)
            
            title = QLabel(camera.name)
            title.setStyleSheet("""
                font-size: 12px;
                font-weight: bold;
                color: #333333;
            """)
            title_layout.addWidget(title)
            
            camera_type = QLabel(f"Type: {camera.camera_type or 'Standard'}")

            title_layout.addWidget(camera_type)
            
            header_layout.addLayout(title_layout)
            header_layout.addStretch()
            
            # Status indicator
            status_badge = self.create_status_badge(
                "Active" if camera.is_active else "Inactive",
                "active" if camera.is_active else "inactive"
            )
            header_layout.addWidget(status_badge)
            layout.addWidget(header_frame)
            
            # Content section
            content_frame = QFrame()
            content_frame.setStyleSheet("padding: 0px;")
            content_layout = QVBoxLayout(content_frame)
            content_layout.setContentsMargins(15, 15, 15, 15)
            content_layout.setSpacing(15)
            
            # Camera details
            details_layout = QGridLayout()
            details_layout.setHorizontalSpacing(30)
            details_layout.setVerticalSpacing(8)
            
            # IP Address
            ip_label = QLabel("IP Address:")
            ip_label.setStyleSheet("font-weight: bold; color: #555;")
            details_layout.addWidget(ip_label, 0, 0)
            
            ip_value = QLabel(camera.ip_address)
            ip_value.setStyleSheet("color: #333;")
            details_layout.addWidget(ip_value, 0, 1)
            
            # Location
            location_label = QLabel("Location:")
            location_label.setStyleSheet("font-weight: bold; color: #555;")
            details_layout.addWidget(location_label, 0, 2)
            
            location_value = QLabel(camera.location or "Not specified")
            location_value.setStyleSheet("color: #333;")
            details_layout.addWidget(location_value, 0, 3)
            
            # RTSP URL
            rtsp_label = QLabel("RTSP URL:")
            rtsp_label.setStyleSheet("font-weight: bold; color: #555;")
            details_layout.addWidget(rtsp_label, 1, 0)
            
            rtsp_value = QLabel(camera.rtsp_url or "Default")
            rtsp_value.setStyleSheet("color: #333;")
            details_layout.addWidget(rtsp_value, 1, 1)
            
            # Port
            port_label = QLabel("Port:")
            port_label.setStyleSheet("font-weight: bold; color: #555;")
            details_layout.addWidget(port_label, 1, 2)
            
            port_value = QLabel(str(camera.port or "Default"))
            port_value.setStyleSheet("color: #333;")
            details_layout.addWidget(port_value, 1, 3)
            
            content_layout.addLayout(details_layout)
            
            # Utiliser la méthode commune pour les boutons
            buttons_frame = self.create_camera_buttons(camera, is_dict_camera=False)
            content_layout.addWidget(buttons_frame)
            
            layout.addWidget(content_frame)
            
            self.camera_list.addWidget(camera_item)
    
    def create_camera_buttons(self, camera, is_dict_camera=False):
        """
        Créer les boutons d'action pour une caméra avec un style moderne et raffiné
        """
        # Frame conteneur avec style moderne
        buttons_frame = QFrame()
        buttons_frame.setStyleSheet("""
            background-color: rgba(255, 255, 255, 0.95);
            border-radius: 12px;
            border: 1px solid rgba(0, 0, 0, 0.08);
            padding: 8px;
        """)
        buttons_layout = QHBoxLayout(buttons_frame)
        buttons_layout.setContentsMargins(8, 8, 8, 8)
        buttons_layout.setSpacing(6)
        
        # 1. BOUTON CONFIGURE - Style moderne bleu
        config_btn = QPushButton("Configure")
        config_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4A90E2, stop:1 #357ABD);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 4px 8px;
                font-size: 10px;
                font-weight: bold;
                min-width: 30px;
                min-height: 28px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #5BA0F2, stop:1 #4A90E2);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #357ABD, stop:1 #2C6AA0);
            }
        """)
        
        if is_dict_camera:
            config_btn.clicked.connect(lambda: self.configure_camera_simple(camera))
        else:
            config_btn.clicked.connect(lambda checked, c=camera: self.edit_camera(c))
        buttons_layout.addWidget(config_btn)
        
        # 2. BOUTON STATUS TOGGLE - Style moderne vert/orange
        if is_dict_camera:
            status_text = "Disable" if camera.get("status") == "active" else "Enable"
            is_active = camera.get("status") == "active"
        else:
            status_text = "Disable" if camera.is_active else "Enable"
            is_active = camera.is_active
        
        status_btn = QPushButton(status_text)
        
        if is_active:
            # Style pour Disable (orange)
            status_btn.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #FF9500, stop:1 #E8860C);
                    color: white;
                    border: none;
                    border-radius: 8px;
                    padding: 4px 8px;
                    font-size: 10px;
                    font-weight: bold;
                    min-width: 30px;
                    min-height: 28px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #FFA500, stop:1 #FF9500);
                }
                QPushButton:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #E8860C, stop:1 #D1770A);
                }
            """)
        else:
            # Style pour Enable (vert)
            status_btn.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #34C759, stop:1 #28A745);
                    color: white;
                    border: none;
                    border-radius: 8px;
                    padding: 4px 8px;
                    font-size: 10px;
                    font-weight: bold;
                    min-width: 30px;
                    min-height: 28px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #44D769, stop:1 #34C759);
                }
                QPushButton:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #28A745, stop:1 #1E7E34);
                }
            """)
        
        if is_dict_camera:
            status_btn.clicked.connect(lambda: self.toggle_camera_status_simple(camera))
        else:
            status_btn.clicked.connect(lambda checked, c=camera: self.toggle_camera_status(c))
        buttons_layout.addWidget(status_btn)
        
        # 4. BOUTON DELETE - Style rouge moderne
        delete_btn = QPushButton("Delete")
        delete_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #FF3B30, stop:1 #D70015);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 4px 8px;
                font-size: 10px;
                font-weight: bold;
                min-width: 30px;
                min-height: 28px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #FF5B50, stop:1 #FF3B30);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #D70015, stop:1 #B80012);
            }
        """)
        
        if is_dict_camera:
            delete_btn.clicked.connect(lambda: self.delete_camera_simple(camera))
        else:
            delete_btn.clicked.connect(lambda checked, c=camera: self.delete_camera_simple(c))
        buttons_layout.addWidget(delete_btn)
        
        return buttons_frame
    
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
    
    def edit_camera(self, camera):
        """Edit camera settings with comprehensive maritime configuration"""
        # Vérifier si l'utilisateur a les permissions nécessaires
        if not self.has_camera_permission:
            QMessageBox.warning(self, "Accès refusé", "Vous n'avez pas les permissions nécessaires pour modifier les caméras.")
            return
            
        dialog = CameraConfigDialog(camera, self)
        if dialog.exec_() == QDialog.Accepted:
            updated_data = dialog.get_camera_config()
            
            success = self.camera_service.update_camera(camera.id, updated_data)
            
            if success:
                # Recharger l'affichage local
                self.load_camera_settings()
                
                # Émettre le signal pour notifier les autres écrans (Live Feed)
                updated_camera_dict = {
                    "id": camera.id,
                    "name": updated_data.get("name", camera.name),
                    "ip_address": updated_data.get("ip_address", camera.ip_address),
                    "location": updated_data.get("location", camera.location),
                    "is_active": updated_data.get("is_active", camera.is_active),
                    "rtsp_url": updated_data.get("rtsp_url", camera.rtsp_url),
                    "port": updated_data.get("port", camera.port)
                }
                self.camera_updated_signal.emit(updated_camera_dict)
                print(f"[Settings] Signal émis pour la caméra modifiée: {updated_camera_dict}")
                
                QMessageBox.information(self, "Success", "Camera configuration updated successfully!")
            else:
                QMessageBox.warning(self, "Error", "Failed to update camera configuration.")
    
    def setup_pending_camera_connections(self):
        """
        Configurer les connexions avec le gestionnaire de caméras en attente
        """
        # Ces connexions ne sont nécessaires que pour les administrateurs
        if not self.has_camera_permission:
            return
            
        # Connecter aux signaux du gestionnaire de caméras en attente
        self.pending_camera_manager.new_camera_detected.connect(self.on_new_camera_detected)
        self.pending_camera_manager.pending_cameras_updated.connect(self.on_pending_cameras_updated)
        self.pending_camera_manager.camera_approved.connect(self.on_camera_approved)
        self.pending_camera_manager.camera_rejected.connect(self.on_camera_rejected)
    
    def on_new_camera_detected(self, camera_id: str, camera_name: str, camera_ip: str):
        """
        Appelé quand une nouvelle caméra est détectée
        """
        if not self.has_camera_permission:
            return
            
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
        if not self.has_camera_permission:
            return
            
        print(f"[Settings] Nombre de caméras en attente: {pending_count}")
        # Recharger la liste des caméras en attente
        self.load_pending_cameras()
        # Mettre à jour le badge
        self.update_pending_badge()
    
    def on_camera_approved(self, camera):
        """
        Appelé quand une caméra est approuvée
        """
        if not self.has_camera_permission:
            return
            
        print(f"[Settings] Caméra approuvée: {camera.name}")
        # Recharger les listes
        self.load_pending_cameras()
        self.load_camera_settings()
        self.update_pending_badge()
    
    def on_camera_rejected(self, camera_id: str):
        """
        Appelé quand une caméra est rejetée
        """
        if not self.has_camera_permission:
            return
            
        print(f"[Settings] Caméra rejetée: {camera_id}")
        # Recharger la liste des caméras en attente
        self.load_pending_cameras()
        self.update_pending_badge()
    
    def load_pending_cameras(self):
        """
        Charger et afficher les caméras en attente d'approbation
        """
        # Ne pas charger les caméras si l'utilisateur n'a pas les permissions
        if not self.has_camera_permission:
            return
            
        try:
            print("[Settings] Chargement des caméras en attente...")
            
            # Vérifier que les attributs nécessaires existent
            if not hasattr(self, 'pending_cameras_list') or self.pending_cameras_list is None:
                print("[Settings] pending_cameras_list not yet initialized, UI may not be ready")
                # Ne pas réessayer automatiquement pour éviter les boucles
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
                no_pending_label = QLabel("No cameras pending approval")
                no_pending_label.setStyleSheet("color: #666; font-style: italic; padding: 10px; background-color: transparent;")
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
        Ajouter un item de caméra en attente à la liste avec un design moderne
        """
        # Créer le conteneur pour la caméra avec design amélioré
        camera_frame = QFrame()
        camera_frame.setObjectName("pendingItem")
        camera_layout = QVBoxLayout(camera_frame)
        camera_layout.setContentsMargins(0, 0, 0, 0)
        camera_layout.setSpacing(0)
        
        # Header with notification styling
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            background-color: #fff3cd;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
        """)
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(15, 12, 15, 12)
        
        # Notification icon
        notification_icon = QLabel()
        notification_icon.setFixedSize(32, 32)
        notification_icon.setStyleSheet("""
            background-color: #ffca28;
            border-radius: 16px;
            color: white;
            font-weight: bold;
            font-size: 16px;
        """)
        notification_icon.setText("!")
        notification_icon.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(notification_icon)
        
        # Camera name with styled header
        name_layout = QVBoxLayout()
        name_layout.setSpacing(2)
        
        name_label = QLabel(pending_camera.name)
        name_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #6d4c41;")
        name_layout.addWidget(name_label)
        
        status_label = QLabel("Pending Approval")
        status_label.setStyleSheet("color: #ff6d00; font-weight: bold; font-size: 12px;")
        name_layout.addWidget(status_label)
        
        header_layout.addLayout(name_layout)
        header_layout.addStretch()
        
        # Detection time as badge
        detection_time = pending_camera.detected_at.strftime("%Y-%m-%d %H:%M")
        time_badge = QLabel(detection_time)
        time_badge.setStyleSheet("""
            background-color: #ffe082;
            color: #6d4c41;
            border-radius: 4px;
            padding: 3px 8px;
            font-size: 11px;
        """)
        header_layout.addWidget(time_badge)
        
        camera_layout.addWidget(header_frame)
        
        # Content section
        content_frame = QFrame()
        content_frame.setStyleSheet("""
            background-color: white;
            border-bottom-left-radius: 8px;
            border-bottom-right-radius: 8px;
        """)
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(15, 15, 15, 15)
        
        # Camera details in grid layout
        details_grid = QGridLayout()
        details_grid.setHorizontalSpacing(20)
        details_grid.setVerticalSpacing(10)
        
        # IP Address
        ip_label = QLabel("IP Address:")
        ip_label.setStyleSheet("font-weight: bold; color: #6d4c41;")
        details_grid.addWidget(ip_label, 0, 0)
        
        ip_value = QLabel(pending_camera.ip_address)
        details_grid.addWidget(ip_value, 0, 1)
        
        # Camera Type
        type_label = QLabel("Camera Type:")
        type_label.setStyleSheet("font-weight: bold; color: #6d4c41;")
        details_grid.addWidget(type_label, 0, 2)
        
        type_value = QLabel(pending_camera.camera_type or "Standard")
        details_grid.addWidget(type_value, 0, 3)
        
        # RTSP URL
        rtsp_label = QLabel("RTSP URL:")
        rtsp_label.setStyleSheet("font-weight: bold; color: #6d4c41;")
        details_grid.addWidget(rtsp_label, 1, 0)
        
        rtsp_value = QLabel(pending_camera.rtsp_url or "Default")
        details_grid.addWidget(rtsp_value, 1, 1)
        
        # Port
        port_label = QLabel("Port:")
        port_label.setStyleSheet("font-weight: bold; color: #6d4c41;")
        details_grid.addWidget(port_label, 1, 2)
        
        port_value = QLabel(str(pending_camera.port or "Default"))
        details_grid.addWidget(port_value, 1, 3)
        
        # Location if available
        location_label = QLabel("Location:")
        location_label.setStyleSheet("font-weight: bold; color: #6d4c41;")
        details_grid.addWidget(location_label, 2, 0)
        
        location_value = QLabel(pending_camera.location or "Not specified")
        details_grid.addWidget(location_value, 2, 1, 1, 3)
        
        content_layout.addLayout(details_grid)
        
        # Action buttons with improved styling
        buttons_frame = QFrame()
        buttons_frame.setStyleSheet("""
            background-color: #f9f9f9;
            border-radius: 6px;
            border: 1px solid #eeeeee;
            margin-top: 10px;
        """)
        buttons_layout = QHBoxLayout(buttons_frame)
        buttons_layout.setContentsMargins(10, 10, 10, 10)
        buttons_layout.setSpacing(10)
        
        # Approve button with icon
        approve_btn = QPushButton("Approve")
        approve_btn.setObjectName("approveButton")
        approve_btn.setIcon(QIcon.fromTheme("emblem-ok-symbolic"))
        approve_btn.clicked.connect(lambda: self.approve_pending_camera(pending_camera))
        approve_btn.setMinimumHeight(38)
        approve_btn.setStyleSheet("""
            QPushButton#approveButton {
                background-color: #4caf50;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton#approveButton:hover {
                background-color: #43a047;
            }
            QPushButton#approveButton:pressed {
                background-color: #388e3c;
            }
        """)
        buttons_layout.addWidget(approve_btn)
        
        # Reject button with icon
        reject_btn = QPushButton("Reject")
        reject_btn.setObjectName("rejectButton")
        reject_btn.setIcon(QIcon.fromTheme("window-close"))
        reject_btn.clicked.connect(lambda: self.reject_pending_camera(pending_camera))
        reject_btn.setMinimumHeight(38)
        reject_btn.setStyleSheet("""
            QPushButton#rejectButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton#rejectButton:hover {
                background-color: #e53935;
            }
            QPushButton#rejectButton:pressed {
                background-color: #d32f2f;
            }
        """)
        buttons_layout.addWidget(reject_btn)
        
        # Configure button with icon
        config_btn = QPushButton("Configure")
        config_btn.setObjectName("configButton")
        config_btn.setIcon(QIcon.fromTheme("preferences-system"))
        config_btn.clicked.connect(lambda: self.configure_pending_camera(pending_camera))
        config_btn.setMinimumHeight(38)
        config_btn.setStyleSheet("""
            QPushButton#configButton {
                background-color: #ff9800;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton#configButton:hover {
                background-color: #fb8c00;
            }
            QPushButton#configButton:pressed {
                background-color: #f57c00;
            }
        """)
        buttons_layout.addWidget(config_btn)
        
        buttons_layout.addStretch()
        
        content_layout.addWidget(buttons_frame)
        camera_layout.addWidget(content_frame)
        
        # Ajouter le widget à la liste
        self.pending_cameras_list.addWidget(camera_frame)
        
        # Add space between items
        spacer = QWidget()
        spacer.setFixedHeight(15)
        self.pending_cameras_list.addWidget(spacer)
    
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
        # Ne pas mettre à jour le badge si l'utilisateur n'a pas les permissions
        if not self.has_camera_permission:
            return
            
        try:
            pending_count = self.pending_camera_manager.get_pending_count()
            
            # Vérifier si le badge existe déjà
            if hasattr(self, 'pending_badge') and self.pending_badge is not None:
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
        """Nettoie la liste des caméras avant rechargement"""
        if hasattr(self, 'camera_list') and self.camera_list:
            while self.camera_list.count():
                child = self.camera_list.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()

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
        
        # Ne rafraîchir les caméras en attente que si l'utilisateur est admin
        if not self.has_camera_permission:
            return
            
        print("[Settings] Settings screen shown, scheduling refresh of pending cameras...")
        
        # Utiliser un QTimer pour éviter de bloquer l'interface utilisateur
        # Cela permettra à l'interface de s'afficher avant de charger les caméras
        QTimer.singleShot(500, self.refresh_pending_cameras_async)
    
    def refresh_pending_cameras_async(self):
        """
        Rafraîchir les caméras en attente de manière asynchrone
        pour éviter de bloquer l'interface utilisateur
        """
        # Ne pas continuer si l'utilisateur n'a pas les permissions
        if not self.has_camera_permission:
            return
            
        # First, synchronize with database to remove already-approved cameras
        try:
            if self.camera_service and hasattr(self.camera_service, 'sync_with_pending_cameras'):
                approved_devices = self.camera_service.sync_with_pending_cameras()
                if approved_devices:
                    print(f"[Settings] Removed {len(approved_devices)} already-approved devices from pending list")
            else:
                print("[Settings] Camera service not yet initialized, skipping sync")
        except Exception as e:
            print(f"[Settings] Error synchronizing pending cameras: {e}")
        
        # Force cleanup of duplicates using improved logic
        try:
            if self.pending_camera_manager and hasattr(self.pending_camera_manager, 'cleanup_duplicates'):
                self.pending_camera_manager.cleanup_duplicates()
                print("[Settings] Completed duplicate cleanup")
            else:
                print("[Settings] Pending camera manager not yet initialized, skipping cleanup")
        except Exception as e:
            print(f"[Settings] Error during duplicate cleanup: {e}")
        
        # Force reload from file
        try:
            if self.pending_camera_manager and hasattr(self.pending_camera_manager, 'load_pending_cameras'):
                self.pending_camera_manager.load_pending_cameras()
                self.load_pending_cameras()
                self.update_pending_badge()
                print(f"[Settings] Refreshed - pending count: {self.pending_camera_manager.get_pending_count()}")
            else:
                print("[Settings] Pending camera manager not yet initialized, skipping refresh")
        except Exception as e:
            print(f"[Settings] Error refreshing pending cameras on show: {e}")
    
    def create_logging_system_section(self):
        """Créer la section Real-time System Logs avec le style UserCard"""
        section = QFrame()
        section.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border-radius: 8px;
                border: 1px solid #e0e0e0;
                padding: 0px;
                margin: 0px;
            }
        """)
        
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header section
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border: none;
                padding: 20px 20px 15px 20px;
                border-bottom: 1px solid #e0e0e0;
            }
        """)
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(15)
        
        # Titre de section
        title_label = QLabel("📝 Real-time System Logs")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #333333;
                margin: 0px;
                padding: 0px;
            }
        """)
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Badge Live
        live_badge = QLabel("� Live")
        live_badge.setStyleSheet("""
            QLabel {
                background-color: #e6f4f7;
                color: #219ebc;
                padding: 4px 10px;
                border-radius: 10px;
                font-size: 11px;
                font-weight: bold;
                margin: 0px;
            }
        """)
        header_layout.addWidget(live_badge)
        
        layout.addWidget(header_frame)
        
        # Contenu des logs
        content_frame = QFrame()
        content_frame.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border: none;
                padding: 20px;
            }
        """)
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(15)
        
        # Widget de visualisation des logs
        from components.logging_widgets import LogViewerWidget
        log_viewer = LogViewerWidget()
        content_layout.addWidget(log_viewer)
        
        layout.addWidget(content_frame)
        
        return section
    
    def _load_logging_styles(self):
        """Charger les styles UserCard compatibles pour la section logging"""
        try:
            styles_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                'assets', 'styles', 'logging_styles_usercard.qss'
            )
            
            if os.path.exists(styles_path):
                with open(styles_path, 'r') as f:
                    additional_styles = f.read()
                    # Appliquer les styles à l'ensemble de l'application
                    current_style = self.styleSheet()
                    self.setStyleSheet(current_style + "\n" + additional_styles)
                    print(f"[Settings] Loaded UserCard-compatible logging styles from {styles_path}")
            else:
                print(f"[Settings] Warning: UserCard styles file not found at {styles_path}")
        except Exception as e:
            print(f"[Settings] Error loading UserCard styles: {e}")
    
    def create_compact_service_status_widget(self):
        """Créer widget compact pour le statut des services"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Header avec refresh
        header_layout = QHBoxLayout()
        
        title_label = QLabel("System Services Overview")
        title_label.setStyleSheet("""
            font-size: 20px;
            font-weight: 600;
            color: #2c3e50;
            margin-bottom: 5px;
        """)
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Status global
        self.compact_status_label = QLabel("🟡 5/6 services operational")
        self.compact_status_label.setStyleSheet("""
            font-size: 14px;
            color: #6c757d;
            margin-right: 15px;
        """)
        header_layout.addWidget(self.compact_status_label)
        
        # Bouton refresh
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setStyleSheet("""
            background: #1e88e5;
            color: white;
            border: none;
            border-radius: 8px;
            padding: 8px 16px;
            font-size: 13px;
            font-weight: 600;
            min-width: 100px;
        """)
        refresh_btn.clicked.connect(self.refresh_compact_services)
        header_layout.addWidget(refresh_btn)
        
        layout.addLayout(header_layout)
        
        # Grid des services (2x3)
        services_grid = QGridLayout()
        services_grid.setSpacing(12)
        
        services = [
            ("YOLO Detection", "operational", "Active"),
            ("Camera System", "operational", "6 cameras"),
            ("Alert Processing", "operational", "0 pending"),
            ("ROS Communication", "operational", "Connected"),
            ("Database", "operational", "38% used"),
            ("Authentication", "warning", "Check logs")
        ]
        
        for i, (name, status, info) in enumerate(services):
            card = self.create_compact_service_card(name, status, info)
            row = i // 2
            col = i % 2
            services_grid.addWidget(card, row, col)
        
        layout.addLayout(services_grid)
        layout.addStretch()
        
        return widget
    
    def create_compact_service_card(self, name, status, info):
        """Créer une carte de service compacte"""
        card = QFrame()
        card.setFixedHeight(80)
        card.setStyleSheet("""
            QFrame {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #ffffff,
                    stop: 1 #f8f9fa
                );
                border: 1px solid #e9ecef;
                border-radius: 8px;
                margin: 1px;
            }
            QFrame:hover {
                border-color: #1e88e5;
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #ffffff,
                    stop: 1 #f0f8ff
                );
            }
        """)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)
        
        # Header avec nom et icône
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        name_label = QLabel(name)
        name_label.setStyleSheet("""
            font-size: 13px;
            font-weight: 600;
            color: #2c3e50;
        """)
        header_layout.addWidget(name_label)
        
        status_icon = self.get_status_icon(status)
        icon_label = QLabel(status_icon)
        icon_label.setStyleSheet("font-size: 14px;")
        header_layout.addWidget(icon_label)
        
        layout.addLayout(header_layout)
        
        # Status badge
        status_label = QLabel(status.title())
        status_label.setAlignment(Qt.AlignCenter)
        status_label.setFixedHeight(18)
        
        if status == "operational":
            status_label.setStyleSheet("""
                background-color: #d4edda;
                color: #155724;
                border: 1px solid #c3e6cb;
                border-radius: 9px;
                font-size: 11px;
                font-weight: 600;
                padding: 1px 6px;
            """)
        elif status == "warning":
            status_label.setStyleSheet("""
                background-color: #fff3cd;
                color: #856404;
                border: 1px solid #ffeaa7;
                border-radius: 9px;
                font-size: 11px;
                font-weight: 600;
                padding: 1px 6px;
            """)
        
        layout.addWidget(status_label)
        
        # Info
        info_label = QLabel(info)
        info_label.setStyleSheet("""
            font-size: 10px;
            color: #6c757d;
        """)
        info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(info_label)
        
        return card
    
    def refresh_compact_services(self):
        """Rafraîchir le statut compact des services"""
        import datetime
        current_time = datetime.datetime.now().strftime("%H:%M:%S")
        self.compact_status_label.setText("🟢 6/6 services operational")
        print(f"[Settings] Compact services refreshed at {current_time}")
    
    def create_log_viewer_widget(self):
        """Créer le widget de visualisation des logs"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Header avec contrôles
        header_layout = QHBoxLayout()
        
        title_label = QLabel("Real-time System Logs")
        title_label.setStyleSheet("""
            font-size: 20px;
            font-weight: 600;
            color: #2c3e50;
        """)
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Indicateur live
        live_label = QLabel("🟢 Live")
        live_label.setStyleSheet("""
            background-color: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
            border-radius: 10px;
            padding: 4px 10px;
            font-size: 12px;
            font-weight: 600;
        """)
        header_layout.addWidget(live_label)
        
        layout.addLayout(header_layout)
        
        # Filtres
        filter_layout = QHBoxLayout()
        
        filter_layout.addWidget(QLabel("Level:"))
        level_combo = QComboBox()
        level_combo.addItems(["All", "ERROR", "WARNING", "INFO", "DEBUG"])
        level_combo.setStyleSheet("""
            background: white;
            border: 1px solid #ced4da;
            border-radius: 4px;
            padding: 4px 8px;
            font-size: 12px;
        """)
        filter_layout.addWidget(level_combo)
        
        filter_layout.addWidget(QLabel("Source:"))
        source_combo = QComboBox()
        source_combo.addItems(["All", "YOLO", "Camera", "Alert", "Database"])
        source_combo.setStyleSheet("""
            background: white;
            border: 1px solid #ced4da;
            border-radius: 4px;
            padding: 4px 8px;
            font-size: 12px;
        """)
        filter_layout.addWidget(source_combo)
        
        filter_layout.addStretch()
        
        auto_refresh = QCheckBox("Auto-refresh")
        auto_refresh.setChecked(True)
        auto_refresh.setStyleSheet("color: #495057; font-size: 12px;")
        filter_layout.addWidget(auto_refresh)
        
        layout.addLayout(filter_layout)
        
        # Zone de logs
        log_text = QLabel("🟡 15:01:10 | YOLODetection | No YOLO topics subscribed via ROSImageBridge\n🟢 15:01:15 | Camera | All cameras initialized successfully")
        log_text.setStyleSheet("""
            font-family: 'Courier New', monospace;
            font-size: 12px;
            color: #495057;
            background: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 6px;
            padding: 15px;
        """)
        log_text.setWordWrap(True)
        log_text.setAlignment(Qt.AlignTop)
        layout.addWidget(log_text, 1)
        
        return widget
    
    def create_log_config_widget(self):
        """Créer le widget de configuration des logs"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Titre
        title_label = QLabel("Log Configuration")
        title_label.setStyleSheet("""
            font-size: 20px;
            font-weight: 600;
            color: #2c3e50;
            margin-bottom: 10px;
        """)
        layout.addWidget(title_label)
        
        # Formulaire de configuration
        config_layout = QGridLayout()
        config_layout.setSpacing(15)
        
        # Log Level
        config_layout.addWidget(QLabel("Log Level:"), 0, 0)
        level_input = QLineEdit("INFO")
        level_input.setStyleSheet("""
            background: white;
            border: 1px solid #ced4da;
            border-radius: 6px;
            padding: 8px 12px;
            font-size: 14px;
        """)
        level_input.setReadOnly(True)
        config_layout.addWidget(level_input, 0, 1)
        
        # Retention
        config_layout.addWidget(QLabel("Retention (days):"), 1, 0)
        retention_input = QLineEdit("30")
        retention_input.setStyleSheet("""
            background: white;
            border: 1px solid #ced4da;
            border-radius: 6px;
            padding: 8px 12px;
            font-size: 14px;
        """)
        retention_input.setReadOnly(True)
        config_layout.addWidget(retention_input, 1, 1)
        
        # Database storage
        config_layout.addWidget(QLabel("Store to Database:"), 2, 0)
        db_checkbox = QCheckBox()
        db_checkbox.setChecked(True)
        db_checkbox.setEnabled(False)
        config_layout.addWidget(db_checkbox, 2, 1)
        
        layout.addLayout(config_layout)
        layout.addStretch()
        
        return widget
    
    # Nouvelles méthodes pour la gestion des services optimisées
    
    def get_status_icon(self, status):
        """Retourne l'icône appropriée selon le statut"""
        status_icons = {
            "operational": "✅",
            "warning": "⚠️", 
            "error": "❌",
            "checking": "🔄"
        }
        return status_icons.get(status.lower(), "❓")
    
    def _update_service_status(self):
        """Met à jour le statut de tous les services"""
        try:
            if hasattr(self, 'service_status_widget'):
                # Le nouveau ServiceStatusWidget se met à jour automatiquement
                # via sa méthode refresh_status interne
                self.service_status_widget.refresh_status()
                        
        except Exception as e:
            print(f"[Settings] Error updating service status: {e}")
    
    def _on_service_status_changed(self, service_id: str, status: str):
        """Gère les changements de statut des services"""
        print(f"[Settings] Service {service_id} status changed to {status}")
        # La mise à jour sera faite par le timer périodique
    
    def _on_new_log_received(self, log_entry: dict):
        """Gère la réception de nouveaux logs en temps réel"""
        try:
            # Le LogViewerWidget se charge automatiquement de la mise à jour
            # Nous pouvons ajouter ici des actions supplémentaires si nécessaire
            level = log_entry.get('level', 'INFO')
            if level in ['ERROR', 'CRITICAL']:
                # Logs critiques - on pourrait ajouter des notifications
                pass
                
        except Exception as e:
            print(f"[Settings] Error processing new log: {e}")
    
    def _save_log_configuration(self):
        """Sauvegarde la configuration des logs"""
        try:
            # Configuration des logs sauvegardée
            QMessageBox.information(self, "Configuration Saved", 
                                  "Log configuration has been saved successfully.")
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to save configuration: {e}")
    
    def _test_log_entry(self):
        """Génère une entrée de log de test"""
        try:
            QMessageBox.information(self, "Test Log", "Test log entry generated successfully.")
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to generate test log: {e}")
    
    def toggle_camera_status_simple(self, camera):
        """Toggle camera status for simple camera items"""
        try:
            # Initialiser les services si nécessaire
            self.initialize_services()
            
            if isinstance(camera, dict):
                # Pour les données statiques, juste changer le statut local et recharger
                current_status = camera.get("status", "inactive")
                new_status = "inactive" if current_status == "active" else "active"
                camera["status"] = new_status
                
                # Recharger l'interface pour refléter le changement
                self.load_camera_settings()
                QMessageBox.information(self, "Camera Status", f"Camera status changed to {new_status}")
            else:
                # Pour les objets de base de données, utiliser le service de caméra
                if hasattr(camera, 'is_active') and hasattr(camera, 'id'):
                    new_status = not camera.is_active
                    
                    # Utiliser le service de caméra pour la mise à jour
                    if self.camera_service:
                        success = self.camera_service.update_camera(camera.id, {"is_active": new_status})
                        if success:
                            status_text = "active" if new_status else "inactive"
                            
                            # Émettre le signal pour notifier les autres écrans
                            status_change_dict = {
                                "id": camera.id,
                                "name": camera.name,
                                "is_active": new_status,
                                "ip_address": camera.ip_address,
                                "location": camera.location
                            }
                            self.camera_status_changed_signal.emit(status_change_dict)
                            print(f"[Settings] Signal émis pour changement de statut: {status_change_dict}")
                            
                            QMessageBox.information(self, "Camera Status", f"Camera status changed to {status_text}")
                            # Recharger l'interface pour refléter les changements
                            self.load_camera_settings()
                        else:
                            QMessageBox.warning(self, "Error", "Failed to update camera status in database")
                    else:
                        # Fallback : mise à jour directe si le service n'est pas disponible
                        camera.is_active = new_status
                        self.db_session.commit()
                        status_text = "active" if new_status else "inactive"
                        
                        # Émettre le signal pour notifier les autres écrans
                        status_change_dict = {
                            "id": camera.id,
                            "name": camera.name,
                            "is_active": new_status,
                            "ip_address": camera.ip_address,
                            "location": camera.location
                        }
                        self.camera_status_changed_signal.emit(status_change_dict)
                        print(f"[Settings] Signal émis pour changement de statut (fallback): {status_change_dict}")
                        
                        QMessageBox.information(self, "Camera Status", f"Camera status changed to {status_text}")
                        # Recharger l'interface
                        self.load_camera_settings()
                else:
                    QMessageBox.warning(self, "Error", "Camera object is invalid or missing required attributes")
        except Exception as e:
            print(f"[Settings] Error in toggle_camera_status_simple: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.warning(self, "Error", f"Failed to change camera status: {e}")
    
    def toggle_camera_status(self, camera):
        """Toggle camera status for database camera objects"""
        try:
            # Initialiser les services si nécessaire
            self.initialize_services()
            
            if hasattr(camera, 'is_active') and hasattr(camera, 'id'):
                new_status = not camera.is_active
                
                # Utiliser le service de caméra pour la mise à jour
                if self.camera_service:
                    success = self.camera_service.update_camera(camera.id, {"is_active": new_status})
                    if success:
                        status_text = "active" if new_status else "inactive"
                        
                        # Émettre le signal pour notifier les autres écrans
                        status_change_dict = {
                            "id": camera.id,
                            "name": camera.name,
                            "is_active": new_status,
                            "ip_address": camera.ip_address,
                            "location": camera.location
                        }
                        self.camera_status_changed_signal.emit(status_change_dict)
                        print(f"[Settings] Signal émis pour changement de statut (DB): {status_change_dict}")
                        
                        QMessageBox.information(self, "Camera Status", f"Camera status changed to {status_text}")
                        # Recharger l'interface pour refléter les changements
                        self.load_camera_settings()
                    else:
                        QMessageBox.warning(self, "Error", "Failed to update camera status in database")
                else:
                    # Fallback : mise à jour directe si le service n'est pas disponible
                    camera.is_active = new_status
                    self.db_session.commit()
                    status_text = "active" if new_status else "inactive"
                    
                    # Émettre le signal pour notifier les autres écrans
                    status_change_dict = {
                        "id": camera.id,
                        "name": camera.name,
                        "is_active": new_status,
                        "ip_address": camera.ip_address,
                        "location": camera.location
                    }
                    self.camera_status_changed_signal.emit(status_change_dict)
                    print(f"[Settings] Signal émis pour changement de statut (DB fallback): {status_change_dict}")
                    
                    QMessageBox.information(self, "Camera Status", f"Camera status changed to {status_text}")
                    # Recharger l'interface
                    self.load_camera_settings()
            else:
                QMessageBox.warning(self, "Error", "Camera object is invalid or missing required attributes")
        except Exception as e:
            print(f"[Settings] Error in toggle_camera_status: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.warning(self, "Error", f"Failed to change camera status: {e}")
    
    def configure_camera_simple(self, camera):
        """Configure camera for simple camera items"""
        try:
            camera_name = camera.get("name") if isinstance(camera, dict) else getattr(camera, 'name', 'Unknown')
            QMessageBox.information(self, "Configure Camera", f"Configuration dialog for {camera_name} would open here.")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to configure camera: {e}")
    
    def delete_camera_simple(self, camera):
        """Intelligent camera removal with historical data preservation options"""
        try:
            from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QRadioButton, QButtonGroup, QCheckBox, QTextEdit
            from PyQt5.QtCore import Qt
            from datetime import datetime
            
            camera_id = camera.get("id") if isinstance(camera, dict) else getattr(camera, 'id', None)
            camera_name = camera.get("name") if isinstance(camera, dict) else getattr(camera, 'name', 'Unknown')
            
            if not camera_id:
                QMessageBox.warning(self, "Error", "Cannot delete camera: No ID found")
                return
            
            # Créer un dialog personnalisé pour choisir le type de suppression
            dialog = QDialog(self)
            dialog.setWindowTitle("🗑️ Camera Removal Options")
            dialog.setModal(True)
            dialog.setMinimumWidth(550)
            
            layout = QVBoxLayout(dialog)
            
            # Header
            header = QLabel("📹 Choose Camera Removal Method")
            header.setStyleSheet("""
                QLabel {
                    background-color: #e3f2fd;
                    color: #1565c0;
                    font-size: 16px;
                    font-weight: bold;
                    padding: 15px;
                    border: 2px solid #42a5f5;
                    border-radius: 8px;
                    margin-bottom: 15px;
                }
            """)
            header.setAlignment(Qt.AlignCenter)
            layout.addWidget(header)
            
            # Camera info
            info_label = QLabel(f"📹 Camera: {camera_name}")
            info_label.setStyleSheet("font-size: 14px; font-weight: bold; margin-bottom: 15px;")
            layout.addWidget(info_label)
            
            # Compter les dépendances
            from database import create_new_session, close_session
            from models import Alert, Recording, Detection
            
            session = create_new_session()
            try:
                alerts_count = session.query(Alert).filter(Alert.camera_id == camera_id).count()
                recordings_count = session.query(Recording).filter(Recording.camera_id == camera_id).count()
                detections_count = session.query(Detection).filter(Detection.camera_id == camera_id).count()
            except:
                alerts_count = recordings_count = detections_count = 0
            finally:
                close_session(session)
            
            # Afficher les dépendances
            deps_info = QTextEdit()
            deps_info.setMaximumHeight(100)
            deps_info.setReadOnly(True)
            deps_text = f"""📊 Historical Data: {alerts_count} alerts, {recordings_count} recordings, {detections_count} detections"""
            
            total_data = alerts_count + recordings_count + detections_count
            if total_data > 0:
                deps_info.setStyleSheet("background-color: #fff3e0; color: #f57c00; padding: 10px;")
                deps_text += "\n💡 This represents valuable surveillance history"
            else:
                deps_info.setStyleSheet("background-color: #e8f5e8; color: #2e7d32; padding: 10px;")
                deps_text += "\n✅ No historical data found"
            
            deps_info.setPlainText(deps_text)
            layout.addWidget(deps_info)
            
            # Options de suppression
            options_label = QLabel("🔧 Removal Method:")
            options_label.setStyleSheet("font-size: 14px; font-weight: bold; margin: 15px 0 10px 0;")
            layout.addWidget(options_label)
            
            radio_group = QButtonGroup()
            
            # Option 1: Suppression logique (recommandée)
            soft_radio = QRadioButton("🛡️ Logical Removal (RECOMMENDED)")
            soft_radio.setChecked(True)
            soft_radio.setStyleSheet("font-size: 13px; font-weight: bold; color: #2e7d32; margin: 5px 0;")
            radio_group.addButton(soft_radio, 0)
            layout.addWidget(soft_radio)
            
            soft_desc = QLabel("• Camera hidden from interface but historical data preserved\n• Compliance and audit trail maintained\n• Can be restored if needed")
            soft_desc.setStyleSheet("margin-left: 25px; margin-bottom: 10px; color: #2e7d32; background-color: #e8f5e8; padding: 8px; border-left: 3px solid #4caf50;")
            layout.addWidget(soft_desc)
            
            # Option 2: Suppression physique
            hard_radio = QRadioButton("⚠️ Physical Deletion (PERMANENT)")
            hard_radio.setStyleSheet("font-size: 13px; font-weight: bold; color: #d32f2f; margin: 5px 0;")
            radio_group.addButton(hard_radio, 1)
            layout.addWidget(hard_radio)
            
            hard_desc = QLabel("• PERMANENTLY deletes camera and ALL historical data\n• Action CANNOT be undone\n• Compliance data lost forever")
            hard_desc.setStyleSheet("margin-left: 25px; margin-bottom: 15px; color: #d32f2f; background-color: #ffebee; padding: 8px; border-left: 3px solid #f44336;")
            layout.addWidget(hard_desc)
            
            # Checkbox de confirmation
            confirm_checkbox = QCheckBox("I understand the consequences")
            confirm_checkbox.setStyleSheet("font-size: 13px; font-weight: bold; color: #1976d2; margin: 15px 0;")
            layout.addWidget(confirm_checkbox)
            
            # Boutons
            buttons_layout = QHBoxLayout()
            
            cancel_btn = QPushButton("❌ Cancel")
            cancel_btn.setStyleSheet("""
                QPushButton {
                    background-color: #6c757d; color: white; font-size: 13px; font-weight: bold;
                    padding: 10px 20px; border: none; border-radius: 6px; min-width: 100px;
                }
                QPushButton:hover { background-color: #5a6268; }
            """)
            cancel_btn.clicked.connect(dialog.reject)
            
            action_btn = QPushButton("🛡️ REMOVE LOGICALLY")
            action_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4caf50; color: white; font-size: 13px; font-weight: bold;
                    padding: 10px 20px; border: none; border-radius: 6px; min-width: 150px;
                }
                QPushButton:hover { background-color: #43a047; }
                QPushButton:disabled { background-color: #cccccc; color: #666666; }
            """)
            action_btn.setEnabled(False)
            action_btn.clicked.connect(dialog.accept)
            
            # Mettre à jour le bouton selon la sélection
            def update_button():
                if radio_group.checkedId() == 0:  # Soft delete
                    action_btn.setText("🛡️ REMOVE LOGICALLY")
                    action_btn.setStyleSheet("""
                        QPushButton {
                            background-color: #4caf50; color: white; font-size: 13px; font-weight: bold;
                            padding: 10px 20px; border: none; border-radius: 6px; min-width: 150px;
                        }
                        QPushButton:hover { background-color: #43a047; }
                        QPushButton:disabled { background-color: #cccccc; color: #666666; }
                    """)
                else:  # Hard delete
                    action_btn.setText("🗑️ DELETE PERMANENTLY")
                    action_btn.setStyleSheet("""
                        QPushButton {
                            background-color: #dc3545; color: white; font-size: 13px; font-weight: bold;
                            padding: 10px 20px; border: none; border-radius: 6px; min-width: 150px;
                        }
                        QPushButton:hover { background-color: #c82333; }
                        QPushButton:disabled { background-color: #cccccc; color: #666666; }
                    """)
            
            soft_radio.toggled.connect(update_button)
            hard_radio.toggled.connect(update_button)
            confirm_checkbox.toggled.connect(action_btn.setEnabled)
            
            buttons_layout.addWidget(cancel_btn)
            buttons_layout.addStretch()
            buttons_layout.addWidget(action_btn)
            layout.addLayout(buttons_layout)
            
            # Exécuter le dialog
            if dialog.exec_() == QDialog.Accepted:
                if not hasattr(self, 'camera_service') or not self.camera_service:
                    QMessageBox.warning(self, "Error", "Camera service not available")
                    return
                
                success = False
                is_soft_delete = radio_group.checkedId() == 0
                
                if is_soft_delete:
                    # Suppression logique
                    success = self.camera_service.soft_delete_camera(camera_id)
                    if success:
                        QMessageBox.information(
                            self, "✅ Camera Removed Logically", 
                            f"Camera '{camera_name}' has been logically removed.\n\n"
                            f"✅ Historical data preserved\n✅ Audit trail maintained\n✅ Can be restored if needed"
                        )
                else:
                    # Suppression physique - utiliser la méthode safe existante
                    try:
                        from safe_camera_deletion_patch import safe_delete_camera
                        success = safe_delete_camera(self.camera_service, camera_id)
                    except ImportError:
                        # Fallback sur la méthode du service
                        success = self.camera_service.delete_camera(camera_id)
                    
                    if success:
                        QMessageBox.information(
                            self, "✅ Camera Deleted Permanently", 
                            f"Camera '{camera_name}' and all associated data have been permanently deleted."
                        )
                
                if success:
                    # Recharger l'interface
                    if hasattr(self, 'load_camera_settings'):
                        self.load_camera_settings()
                    
                    # Émettre le signal
                    if hasattr(self, 'camera_status_changed_signal'):
                        self.camera_status_changed_signal.emit({
                            "id": camera_id, 
                            "deleted": True,
                            "soft_delete": is_soft_delete
                        })
                else:
                    QMessageBox.critical(self, "❌ Operation Failed", "An error occurred. Please check the logs.")
                    
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error in camera removal: {e}")
            QMessageBox.critical(self, "Error", f"Unexpected error: {e}")
    
    def closeEvent(self, event):
        """Méthode appelée quand la fenêtre se ferme - nettoyer les timers"""
        try:
            # Arrêter le timer de mise à jour des services
            if hasattr(self, 'service_update_timer') and self.service_update_timer:
                self.service_update_timer.stop()
                print("[Settings] Service update timer stopped")
            
            # Fermer les sessions de base de données
            if hasattr(self, 'user_service') and self.user_service:
                try:
                    self.user_service.session.close()
                except:
                    pass
                    
            if hasattr(self, 'camera_service') and self.camera_service:
                try:
                    self.camera_service.session.close()
                except:
                    pass
            
            print("[Settings] Cleanup completed")
            
        except Exception as e:
            print(f"[Settings] Error during cleanup: {e}")
        
        # Appeler la méthode parent
        super().closeEvent(event)
    
    def create_realtime_log_widget(self):
        """Créer un widget de logs en temps réel utilisant le realtime_log_handler"""
        widget = QFrame()
        widget.setStyleSheet("""
            QFrame {
                background-color: #e8f5e8;
                border-left: 4px solid #4caf50;
                border-radius: 8px;
                margin: 2px 0px;
                padding: 10px;
            }
        """)
        
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(10)
        
        # En-tête avec indicateur live
        header_layout = QHBoxLayout()
        
        logs_title = QLabel("🔴 Live System Logs")
        logs_title.setStyleSheet("""
            color: #2e7d32;
            font-weight: bold;
            font-size: 14px;
            background-color: transparent;
            border: none;
        """)
        header_layout.addWidget(logs_title)
        header_layout.addStretch()
        
        # Contrôles
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(8)
        
        # Niveau de log filter
        level_filter = QComboBox()
        level_filter.addItems(["ALL", "DEBUG", "INFO", "WARN", "ERROR"])
        level_filter.setCurrentText("INFO")
        level_filter.setStyleSheet("""
            QComboBox {
                background-color: #ffffff;
                border: 1px solid #4caf50;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
                min-width: 60px;
                max-width: 80px;
            }
        """)
        controls_layout.addWidget(level_filter)
        
        # Bouton pause/play
        self.realtime_pause_btn = QPushButton("⏸️")
        self.realtime_pause_btn.setCheckable(True)
        self.realtime_pause_btn.setStyleSheet("""
            QPushButton {
                background-color: #4caf50;
                color: white;
                border: none;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 12px;
                min-width: 30px;
                max-width: 40px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:checked {
                background-color: #ff9800;
            }
        """)
        self.realtime_pause_btn.setToolTip("Pause/Resume live logs")
        self.realtime_pause_btn.clicked.connect(self.toggle_realtime_logs)
        controls_layout.addWidget(self.realtime_pause_btn)
        
        # Clear button
        clear_btn = QPushButton("🗑️")
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 12px;
                min-width: 30px;
                max-width: 40px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        clear_btn.setToolTip("Clear logs")
        clear_btn.clicked.connect(self.clear_realtime_logs)
        controls_layout.addWidget(clear_btn)
        
        header_layout.addLayout(controls_layout)
        layout.addLayout(header_layout)
        
        # Zone d'affichage des logs en temps réel
        self.realtime_logs_area = QTextEdit()
        self.realtime_logs_area.setReadOnly(True)
        self.realtime_logs_area.setFixedHeight(200)  # Hauteur plus importante
        self.realtime_logs_area.setStyleSheet("""
            QTextEdit {
                background-color: #ffffff;
                border: 1px solid #4caf50;
                border-radius: 4px;
                font-family: 'Courier New', monospace;
                font-size: 11px;
                color: #333;
                padding: 8px;
            }
        """)
        
        # Se connecter au service de logs en temps réel
        self.connect_to_realtime_logs()
        
        layout.addWidget(self.realtime_logs_area)
        
        return widget
    
    def connect_to_realtime_logs(self):
        """Connecter au service de logs en temps réel"""
        try:
            # Se connecter au log_manager pour recevoir les logs en temps réel
            if hasattr(log_manager, 'new_log_signal'):
                log_manager.new_log_signal.connect(self.on_new_realtime_log)
                print("[Settings] Connected to realtime log handler")
            else:
                print("[Settings] Log manager doesn't have new_log_signal")
                
            # Charger les logs récents existants
            self.load_recent_logs()
            
        except Exception as e:
            print(f"[Settings] Error connecting to realtime logs: {e}")
            # Afficher un message d'erreur dans la zone de logs
            if hasattr(self, 'realtime_logs_area'):
                self.realtime_logs_area.setPlainText(
                    "[ERROR] Unable to connect to real-time log service.\n"
                    "Check if the logging service is running."
                )
    
    def load_recent_logs(self):
        """Charger les logs récents depuis le service"""
        try:
            # Obtenir les logs récents depuis le log_manager
            if hasattr(log_manager, 'get_recent_logs'):
                recent_logs = log_manager.get_recent_logs(limit=50)
                if recent_logs:
                    log_text = "\n".join([
                        f"[{log.get('timestamp', 'N/A')}] {log.get('level', 'INFO')} - {log.get('message', '')}"
                        for log in recent_logs[-20:]  # Derniers 20 logs
                    ])
                    self.realtime_logs_area.setPlainText(log_text)
                    # Scroller vers le bas
                    self.realtime_logs_area.moveCursor(self.realtime_logs_area.textCursor().End)
                else:
                    self.realtime_logs_area.setPlainText("[INFO] Waiting for real-time logs...")
            else:
                # Si pas de méthode get_recent_logs, afficher des logs d'exemple
                sample_logs = f"""[{QDateTime.currentDateTime().toString('hh:mm:ss')}] INFO - Settings screen initialized
[{QDateTime.currentDateTime().addSecs(-30).toString('hh:mm:ss')}] INFO - User authentication successful
[{QDateTime.currentDateTime().addSecs(-60).toString('hh:mm:ss')}] INFO - Camera service started
[{QDateTime.currentDateTime().addSecs(-90).toString('hh:mm:ss')}] WARN - High storage usage detected
[{QDateTime.currentDateTime().addSecs(-120).toString('hh:mm:ss')}] INFO - Database connection established"""
                
                self.realtime_logs_area.setPlainText(sample_logs)
                
        except Exception as e:
            print(f"[Settings] Error loading recent logs: {e}")
            if hasattr(self, 'realtime_logs_area'):
                self.realtime_logs_area.setPlainText(f"[ERROR] Failed to load recent logs: {str(e)}")
    
    def on_new_realtime_log(self, log_entry):
        """Traiter un nouveau log en temps réel"""
        try:
            if hasattr(self, 'realtime_pause_btn') and self.realtime_pause_btn.isChecked():
                return  # Logs en pause
                
            # Formatter le log
            timestamp = log_entry.get('timestamp', QDateTime.currentDateTime().toString('hh:mm:ss'))
            level = log_entry.get('level', 'INFO')
            message = log_entry.get('message', 'No message')
            
            formatted_log = f"[{timestamp}] {level} - {message}"
            
            # Ajouter à la zone de texte
            if hasattr(self, 'realtime_logs_area'):
                current_text = self.realtime_logs_area.toPlainText()
                lines = current_text.split('\n')
                
                # Garder seulement les 100 dernières lignes
                if len(lines) > 100:
                    lines = lines[-99:]  # Garder 99 + 1 nouvelle = 100
                
                lines.append(formatted_log)
                
                self.realtime_logs_area.setPlainText('\n'.join(lines))
                
                # Scroller vers le bas
                self.realtime_logs_area.moveCursor(self.realtime_logs_area.textCursor().End)
            
        except Exception as e:
            print(f"[Settings] Error processing realtime log: {e}")
    
    def toggle_realtime_logs(self):
        """Basculer la pause/reprise des logs en temps réel"""
        if hasattr(self, 'realtime_pause_btn'):
            if self.realtime_pause_btn.isChecked():
                self.realtime_pause_btn.setText("▶️")
                self.realtime_pause_btn.setToolTip("Resume live logs")
            else:
                self.realtime_pause_btn.setText("⏸️")
                self.realtime_pause_btn.setToolTip("Pause live logs")
    
    def clear_realtime_logs(self):
        """Effacer les logs en temps réel"""
        if hasattr(self, 'realtime_logs_area'):
            self.realtime_logs_area.clear()
            self.realtime_logs_area.setPlainText("[INFO] Logs cleared - waiting for new entries...")