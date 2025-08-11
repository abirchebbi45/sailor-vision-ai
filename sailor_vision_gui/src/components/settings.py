from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QLineEdit, QFrame, QScrollArea,
                            QProgressBar, QFileDialog, QMessageBox, QDialog,
                            QComboBox, QSpinBox, QCheckBox, QTabWidget,
                            QGroupBox, QSlider, QTextEdit, QGridLayout)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QSize
from PyQt5.QtGui import QPixmap, QIcon, QPainter, QPainterPath, QRegion, QColor, QFont

from services.user_service import UserService
from services.camera_service import CameraService
from services.storage_service import StorageService
from services.pending_camera_manager import pending_camera_manager
from components.shared import HeaderWidget
from components.camera_dialogs import (CameraConfigDialog, MaintenanceScheduleDialog)
from utils import hash_password
from models import User, Camera, StorageType
from database import create_new_session
from services.permission_service import Permission
from services.user_session import UserSession

class SettingsScreen(QWidget):
    camera_approved_signal = pyqtSignal(dict)  # Signal émis quand une caméra est approuvée
    
    def __init__(self, user, db_session):
        super().__init__()
        print("[Settings] Initialisation début...")
        self.user = user
        self.db_session = db_session
        
        print("[Settings] Vérification des permissions...")
        # Approche optimisée : utiliser UserSession avec une approche plus robuste
        from services.permission_service import Permission
        from services.user_session import UserSession
        
        # S'assurer que nous avons la bonne instance de UserSession
        user_session = UserSession.get_instance()
        print(f"[Settings] UserSession récupérée: authenticated={user_session.is_authenticated}")
        
        # Fallback : si UserSession n'est pas authentifié, utiliser les données utilisateur directement
        if not user_session.is_authenticated or not hasattr(user_session, 'permissions'):
            print("[Settings] Utilisation du fallback pour les permissions...")
            # Approche de performance : déduire les permissions du rôle utilisateur
            user_role = user.get('role', '').lower() if isinstance(user, dict) else getattr(user, 'role', '').lower()
            print(f"[Settings] Rôle utilisateur détecté: {user_role}")
            
            # Pour les administrateurs, donner toutes les permissions
            if 'administrator' in user_role or 'admin' in user_role:
                self.has_manage_cameras_permission = True
                self.has_edit_system_settings_permission = True
                print("[Settings] Permissions admin accordées")
            else:
                # Pour les autres rôles, permissions limitées
                self.has_manage_cameras_permission = False
                self.has_edit_system_settings_permission = False
                print("[Settings] Permissions limitées accordées")
        else:
            print("[Settings] Utilisation des permissions UserSession...")
            # Utiliser le cache UserSession (approche optimisée)
            self.has_manage_cameras_permission = user_session.has_permission(Permission.MANAGE_CAMERAS)
            self.has_edit_system_settings_permission = user_session.has_permission(Permission.EDIT_SYSTEM_SETTINGS)
            print(f"[Settings] Permissions chargées: caméras={self.has_manage_cameras_permission}, système={self.has_edit_system_settings_permission}")
        
        print(f"[Settings] Camera permission: {self.has_manage_cameras_permission}")
        print(f"[Settings] System settings permission: {self.has_edit_system_settings_permission}")
        
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
            if self.has_manage_cameras_permission:
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
                
            elif tab_text == "Camera Management" and self.has_manage_cameras_permission:
                print("[Settings] Chargement des données caméras...")
                # Initialiser les services si nécessaire, puis charger les caméras
                if not self.services_initialized:
                    self.initialize_services()
                QTimer.singleShot(100, self.load_camera_data)
                
            elif tab_text == "System Settings" and self.has_edit_system_settings_permission:
                print("[Settings] Chargement des paramètres système...")
                # Initialiser les services si nécessaire, puis charger les paramètres système
                if not self.services_initialized:
                    self.initialize_services()
                QTimer.singleShot(100, self.load_storage_settings)
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
                font-size: 13px;
                color: #546e7a;
            }
            
            QPushButton#primaryButton {
                background-color: #0088cc;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
                min-width: 120px;
            }
            
            QPushButton#primaryButton:hover {
                background-color: #006699;
            }
            
            QPushButton#primaryButton:pressed {
                background-color: #004466;
            }
            
            QPushButton#secondaryButton {
                background-color: #2196f3;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: bold;
                min-width: 100px;
            }
            
            QPushButton#secondaryButton:hover {
                background-color: #1976d2;
            }
            
            QPushButton#secondaryButton:pressed {
                background-color: #0d47a1;
            }
            
            QPushButton#approveButton {
                background-color: #4caf50;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: bold;
            }
            
            QPushButton#approveButton:hover {
                background-color: #43a047;
            }
            
            QPushButton#approveButton:pressed {
                background-color: #388e3c;
            }
            
            QPushButton#rejectButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: bold;
            }
            
            QPushButton#rejectButton:hover {
                background-color: #e53935;
            }
            
            QPushButton#rejectButton:pressed {
                background-color: #d32f2f;
            }
            
            QPushButton#dangerButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: bold;
            }
            
            QPushButton#dangerButton:hover {
                background-color: #e53935;
            }
            
            QPushButton#dangerButton:pressed {
                background-color: #d32f2f;
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
            """
        )
        
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
        if self.has_manage_cameras_permission:
            print("[Settings] Création de l'onglet caméras...")
            self.create_camera_tab()
            print("[Settings] Onglet caméras créé")
            
        if self.has_edit_system_settings_permission:
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
                font-size: 13px;
                color: #546e7a;
            }
            
            QPushButton#primaryButton {
                background-color: #0088cc;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
                min-width: 120px;
            }
            
            QPushButton#primaryButton:hover {
                background-color: #006699;
            }
            
            QPushButton#primaryButton:pressed {
                background-color: #004466;
            }
            
            QPushButton#secondaryButton {
                background-color: #2196f3;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: bold;
                min-width: 100px;
            }
            
            QPushButton#secondaryButton:hover {
                background-color: #1976d2;
            }
            
            QPushButton#secondaryButton:pressed {
                background-color: #0d47a1;
            }
            
            QPushButton#approveButton {
                background-color: #4caf50;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: bold;
            }
            
            QPushButton#approveButton:hover {
                background-color: #43a047;
            }
            
            QPushButton#approveButton:pressed {
                background-color: #388e3c;
            }
            
            QPushButton#rejectButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: bold;
            }
            
            QPushButton#rejectButton:hover {
                background-color: #e53935;
            }
            
            QPushButton#rejectButton:pressed {
                background-color: #d32f2f;
            }
            
            QPushButton#dangerButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: bold;
            }
            
            QPushButton#dangerButton:hover {
                background-color: #e53935;
            }
            
            QPushButton#dangerButton:pressed {
                background-color: #d32f2f;
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
        camera_container_layout.setSpacing(25)
        
        # Camera Management section
        camera_section = QFrame()
        camera_section.setObjectName("contentSection")
        camera_section_layout = QVBoxLayout(camera_section)
        camera_section_layout.setSpacing(20)
            
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
        pending_header.setStyleSheet("color: #f57c00; font-weight: bold; font-size: 16px;")
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
        active_header.setStyleSheet("color: #0d47a1; font-weight: bold; font-size: 16px;")
        active_layout.addWidget(active_header)
        
        # Camera list will be populated dynamically
        self.camera_list = QVBoxLayout()
        active_layout.addLayout(self.camera_list)
        
        camera_section_layout.addWidget(active_section)
        
        # Ajouter la section au layout du conteneur
        camera_container_layout.addWidget(camera_section)
        
        # Configurer le scroll area
        camera_scroll.setWidget(camera_container)
        camera_layout.addWidget(camera_scroll)
        
        # Ajouter l'onglet au TabWidget
        self.tabs.addTab(camera_tab, "Camera Management")
        
    def create_system_tab(self):
        """Créer l'onglet System Settings pour les administrateurs"""
        system_tab = QWidget()
        system_layout = QVBoxLayout(system_tab)
        system_layout.setContentsMargins(30, 10, 30, 30)
        system_layout.setSpacing(25)
        
        # Scroll area for system tab
        system_scroll = QScrollArea()
        system_scroll.setWidgetResizable(True)
        system_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        system_scroll.setFrameShape(QFrame.NoFrame)
        system_scroll.setStyleSheet("background-color: #f5f5f5; border: none;")
        
        # System settings container
        system_container = QWidget()
        system_container_layout = QVBoxLayout(system_container)
        system_container_layout.setContentsMargins(0, 0, 0, 0)
        system_container_layout.setSpacing(25)
        
        # Storage Settings section with improved styling
        storage_section = QFrame()
        storage_section.setObjectName("contentSection")
        storage_section.setStyleSheet("""
            #contentSection {
                background-color: rgba(240, 240, 245, 0.7);
                border: none;
                border-radius: 12px;
                padding: 25px;
            }
        """)
        storage_section_layout = QVBoxLayout(storage_section)
        storage_section_layout.setSpacing(25)
        
        storage_header = QLabel("Storage Configuration")
        storage_header.setObjectName("sectionHeader")
        storage_section_layout.addWidget(storage_header)
    
    
        # Storage options with improved styling
        options_group = QGroupBox("Storage Location")
        options_group.setStyleSheet("""
            QGroupBox {
                font-size: 15px;
                font-weight: bold;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                margin-top: 15px;
                padding-top: 20px;
                padding-bottom: 10px;
                background-color: #f9f9f9;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 10px;
                color: #455a64;
                font-weight: bold;
            }
        """)
        options_layout = QVBoxLayout(options_group)
    
        storage_option_layout = QHBoxLayout()
        storage_option_label = QLabel("Select where to store surveillance data:")
        storage_option_label.setStyleSheet("font-size: 14px; color: #546e7a;")
        storage_option_layout.addWidget(storage_option_label)
        storage_option_layout.addStretch()
        
        # Button group for storage options
        storage_buttons = QHBoxLayout()
        
        # Cloud button with icon
        self.cloud_btn = QPushButton(" Cloud Storage")
        self.cloud_btn.setObjectName("storageButton")
        self.cloud_btn.setIcon(QIcon.fromTheme("network-server"))
        self.cloud_btn.setIconSize(QSize(20, 20))
        self.cloud_btn.setCheckable(True)
        self.cloud_btn.setMinimumHeight(40)
        self.cloud_btn.clicked.connect(lambda: self.set_storage_type(StorageType.CLOUD))
        self.cloud_btn.setStyleSheet("""
            QPushButton#storageButton {
                background-color: #f5f5f5;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
                color: #546e7a;
            }
            QPushButton#storageButton:checked {
                background-color: #039be5;
                border-color: #0288d1;
                color: white;
            }
            QPushButton#storageButton:hover:!checked {
                background-color: #e0e0e0;
                border-color: #bdbdbd;
            }
        """)
    
        # Local button with icon
        self.local_btn = QPushButton(" Local Storage")
        self.local_btn.setObjectName("storageButton")
        self.local_btn.setIcon(QIcon.fromTheme("drive-harddisk"))
        self.local_btn.setIconSize(QSize(20, 20))
        self.local_btn.setCheckable(True)
        self.local_btn.setMinimumHeight(40)
        self.local_btn.clicked.connect(lambda: self.set_storage_type(StorageType.LOCAL))
        self.local_btn.setStyleSheet("""
            QPushButton#storageButton {
                background-color: #f5f5f5;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
                color: #546e7a;
            }
            QPushButton#storageButton:checked {
                background-color: #039be5;
                border-color: #0288d1;
                color: white;
            }
            QPushButton#storageButton:hover:!checked {
                background-color: #e0e0e0;
                border-color: #bdbdbd;
            }
        """)
        
        storage_buttons.addWidget(self.cloud_btn)
        storage_buttons.addWidget(self.local_btn)
        storage_buttons.addStretch()
        
        options_layout.addLayout(storage_option_layout)
        options_layout.addLayout(storage_buttons)
        storage_section_layout.addWidget(options_group)
        
        # Storage status with improved styling
        status_group = QGroupBox("Storage Status")
        status_group.setStyleSheet("""
            QGroupBox {
                font-size: 15px;
                font-weight: bold;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                margin-top: 15px;
                padding-top: 20px;
                padding-bottom: 10px;
                background-color: #f9f9f9;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 10px;
                color: #455a64;
                font-weight: bold;
            }
        """)
        status_layout = QVBoxLayout(status_group)
        
        status_info_label = QLabel("Current storage usage:")
        status_info_label.setStyleSheet("font-size: 14px; color: #455a64; margin-bottom: 5px; font-weight: bold;")
        status_layout.addWidget(status_info_label)
        
        # Progress bar with improved styling
        self.storage_progress = QProgressBar()
        self.storage_progress.setMinimumHeight(25)
        self.storage_progress.setTextVisible(True)
        self.storage_progress.setFormat("%p% used")
        self.storage_progress.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 12px;
                background-color: #f5f5f5;
                text-align: center;
                color: #333333;
                font-weight: bold;
                margin: 5px 0;
                padding: 1px;
            }
            QProgressBar::chunk {
                border-radius: 12px;
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #039be5, stop:1 #29b6f6);
            }
        """)
        status_layout.addWidget(self.storage_progress)
    
        storage_section_layout.addWidget(status_group)
        
        # Ajouter la section au layout du conteneur
        system_container_layout.addWidget(storage_section)
        
        # Configurer le scroll area
        system_scroll.setWidget(system_container)
        system_layout.addWidget(system_scroll)
        
        # Ajouter l'onglet au TabWidget
        self.tabs.addTab(system_tab, "System Settings")
        
        # Apply consistent styling for the entire settings screen
        
        # Apply additional responsive styling for the entire settings screen
        self.setStyleSheet(self.styleSheet() + """
            QScrollArea {
                border: none;
                background-color: #f5f5f5;
            }
            QLabel.fieldLabel {
                font-size: 15px;
                font-weight: bold;
                color: #333333;
                margin-bottom: 5px;
                background-color: #ffffff;
            }
            QLineEdit#inputField {
                border: 1px solid #dce4ec;
                border-radius: 6px;
                padding: 8px 15px;
                font-size: 14px;
                background-color: #ffffff;
                min-height: 20px;
                selection-background-color: #0088cc;
            }
            QLineEdit#inputField:focus {
                border: 2px solid #0088cc;
                background-color: #f8fdff;
            }
            QLineEdit#inputField:hover:!focus {
                background-color: #f5f9fc;
                border: 1px solid #bcd4e6;
            }
            QPushButton#primaryButton {
                background-color: #0088cc;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 15px;
                font-weight: bold;
                min-width: 160px;
            }
            QPushButton#primaryButton:hover {
                background-color: #006699;
            }
            QPushButton#primaryButton:pressed {
                background-color: #004466;
            }
            QPushButton#secondaryButton {
                background-color: #2196f3;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: bold;
                min-width: 100px;
            }
            QPushButton#secondaryButton:hover {
                background-color: #1976d2;
            }
            QPushButton#secondaryButton:pressed {
                background-color: #0d47a1;
            }
            QLabel#pendingBadge {
                background-color: #f44336;
                color: white;
                border-radius: 12px;
                padding: 3px 10px;
                font-size: 12px;
                font-weight: bold;
                min-width: 24px;
            }
            QFrame#pendingItem {
                background-color: #ffffff;
                border: none;
                border-left: 4px solid #ffca28;
                border-radius: 6px;
                padding: 15px;
                margin-bottom: 10px;
            }
        """)

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
        if not self.has_manage_cameras_permission:
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
                    border-radius: 8px;
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
            
            # Camera icon
            camera_icon = QLabel()
            camera_icon.setFixedSize(32, 32)
            camera_icon.setStyleSheet("""
                background-color: #0088cc;
                border-radius: 16px;
                color: white;
                font-weight: bold;
                font-size: 16px;
            """)
            camera_icon.setText("📹")
            camera_icon.setAlignment(Qt.AlignCenter)
            header_layout.addWidget(camera_icon)
            
            # Camera title and type
            title_layout = QVBoxLayout()
            title_layout.setSpacing(2)
            
            title = QLabel(camera.name)
            title.setStyleSheet("""
                font-size: 16px;
                font-weight: bold;
                color: #333333;
            """)
            title_layout.addWidget(title)
            
            camera_type = QLabel(f"Type: {camera.camera_type or 'Standard'}")
            camera_type.setStyleSheet("font-size: 12px; color: #757575;")
            title_layout.addWidget(camera_type)
            
            header_layout.addLayout(title_layout)
            header_layout.addStretch()
            
            # Status indicator
            status_frame = QFrame()
            status_frame.setFixedSize(85, 25)
            status_frame.setStyleSheet(f"""
                background-color: {('#4caf50' if camera.is_active else '#f44336')};
                border-radius: 12px;
                padding: 0px;
            """)
            status_layout = QHBoxLayout(status_frame)
            status_layout.setContentsMargins(8, 0, 8, 0)
            
            status_icon = QLabel("●")
            status_icon.setStyleSheet("color: white; font-size: 12px;")
            status_layout.addWidget(status_icon)
            
            status_text = QLabel("Active" if camera.is_active else "Inactive")
            status_text.setStyleSheet("color: white; font-weight: bold; font-size: 12px;")
            status_layout.addWidget(status_text)
            
            header_layout.addWidget(status_frame)
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
            
            # Action buttons in a card-like footer
            buttons_frame = QFrame()
            buttons_frame.setStyleSheet("""
                background-color: #f9f9f9;
                border-radius: 6px;
                border: 1px solid #eeeeee;
            """)
            buttons_layout = QHBoxLayout(buttons_frame)
            buttons_layout.setContentsMargins(10, 10, 10, 10)
            buttons_layout.setSpacing(10)
            
            # Primary actions
            edit_btn = QPushButton("Configure")
            edit_btn.setObjectName("secondaryButton")
            edit_btn.setIcon(QIcon.fromTheme("preferences-system"))
            edit_btn.setToolTip("Configure camera settings")
            edit_btn.clicked.connect(lambda checked, c=camera: self.edit_camera(c))
            buttons_layout.addWidget(edit_btn)
            
            status_text = "Disable" if camera.is_active else "Enable"
            status_icon = QIcon.fromTheme("media-playback-pause" if camera.is_active else "media-playback-start")
            status_btn = QPushButton(status_text)
            status_btn.setObjectName("toggleButton")
            status_btn.setIcon(status_icon)
            status_btn.setToolTip("Toggle camera status")
            status_btn.setStyleSheet("""
                QPushButton#toggleButton {
                    background-color: #ff9800;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-weight: bold;
                }
                QPushButton#toggleButton:hover {
                    background-color: #f57c00;
                }
            """)
            status_btn.clicked.connect(lambda checked, c=camera: self.toggle_camera_status(c))
            buttons_layout.addWidget(status_btn)
            
            # Monitoring operations
            test_btn = QPushButton("Test")
            test_btn.setObjectName("secondaryButton")
            test_btn.setIcon(QIcon.fromTheme("network-wireless"))
            test_btn.setToolTip("Test connectivity")
            test_btn.clicked.connect(lambda checked, c=camera: self.test_camera_connectivity(c))
            buttons_layout.addWidget(test_btn)
            
            # Maintenance operations
            maintenance_btn = QPushButton("Maintenance")
            maintenance_btn.setObjectName("secondaryButton")
            maintenance_btn.setIcon(QIcon.fromTheme("applications-system"))
            maintenance_btn.setToolTip("Schedule maintenance")
            maintenance_btn.clicked.connect(lambda checked, c=camera: self.schedule_camera_maintenance(c))
            buttons_layout.addWidget(maintenance_btn)
            
            buttons_layout.addStretch()
            
            # Delete operation
            delete_btn = QPushButton("Delete")
            delete_btn.setObjectName("dangerButton")
            delete_btn.setIcon(QIcon.fromTheme("edit-delete"))
            delete_btn.setToolTip("Delete camera")
            delete_btn.clicked.connect(lambda checked, c=camera: self.delete_camera(c))
            buttons_layout.addWidget(delete_btn)
            
            content_layout.addWidget(buttons_frame)
            layout.addWidget(content_frame)
            
            self.camera_list.addWidget(camera_item)
            
            # Add spacing between camera items
            if camera != cameras[-1]:
                spacer = QWidget()
                spacer.setFixedHeight(15)
                self.camera_list.addWidget(spacer)
    
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
        # Vérifier si l'utilisateur a les permissions nécessaires
        if not self.has_manage_cameras_permission:
            QMessageBox.warning(self, "Accès refusé", "Vous n'avez pas les permissions nécessaires pour modifier les caméras.")
            return
            
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
        # Ces connexions ne sont nécessaires que pour les administrateurs
        if not self.has_manage_cameras_permission:
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
        if not self.has_manage_cameras_permission:
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
        if not self.has_manage_cameras_permission:
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
        if not self.has_manage_cameras_permission:
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
        if not self.has_manage_cameras_permission:
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
        if not self.has_manage_cameras_permission:
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
        if not self.has_manage_cameras_permission:
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
        
        # Ne rafraîchir les caméras en attente que si l'utilisateur est admin
        if not self.has_manage_cameras_permission:
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
        if not self.has_manage_cameras_permission:
            return
            
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