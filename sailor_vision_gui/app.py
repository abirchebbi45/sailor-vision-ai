import sys
import os
import traceback

# Add the src directory to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from PyQt5.QtWidgets import QApplication, QMainWindow, QStackedWidget, QWidget, QVBoxLayout, QHBoxLayout, QMessageBox, QLabel
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QTimer
from PyQt5.QtGui import QIcon, QFontDatabase, QFont
import logging
import rclpy
from rclpy.node import Node

from src.components.login import LoginScreen
from src.components.dashboard import DashboardScreen
from src.components.live_feed import LiveFeedScreen
from src.components.alerts import AlertsScreen
from src.components.user_management import UserManagementScreen
from src.components.playback import PlaybackScreen
from src.components.shared import Sidebar, HeaderWidget
from src.components.settings import SettingsScreen
from src.components.camera_notification import NotificationManager

# Import the permission service
from src.services.permission_service import PermissionService, Permission
from src.services.user_session import UserSession
from src.utils.permission_helpers import MainWindowPermissionMixin

# Import the watchdog ROS
from shared.ros_watchdog import ROSWatchdog

from database import init_db, get_session, create_new_session
from models import User, Camera, Alert, Recording
from config import load_config
from shared.detection_recorder import DetectionRecorder
from shared.ros_image_listener import ROSImageBridge
from src.services.pending_camera_manager import pending_camera_manager
from src.services.camera_detector import camera_detector  # Import the camera detector

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Ensure no custom handlers are added recursively
if not logger.hasHandlers():
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(console_handler)

class MainWindow(QMainWindow, MainWindowPermissionMixin):
    def __init__(self, ros_node):
        """Initialize the main application window"""
        super().__init__()
        self.ros_node = ros_node
        
        # Initialize database
        init_db()
        
        # Create one shared ROSImageBridge instance for both LiveFeed and DetectionRecorder
        self.ros_bridge = ROSImageBridge(ros_node)
        
        # Initialize the ROS Watchdog BEFORE DetectionRecorder
        self.ros_watchdog = ROSWatchdog(ros_node)
        logger.info("ROS Watchdog initialized")
        
        # Initialize the camera detector with the ROS node
        camera_detector.ros_node = ros_node
        camera_detector.setup_ros_subscription()
        
        # Initialize the DetectionRecorder with reference to ros_watchdog
        self.detection_recorder = DetectionRecorder(self.ros_node, ros_bridge=self.ros_bridge)
        # Add the missing reference to ros_watchdog
        self.detection_recorder.ros_watchdog = self.ros_watchdog
        logger.info("Detection recorder initialized with ros_watchdog reference")
        
        # Connect the ros_bridge to watchdog for topic activity monitoring
        self.ros_bridge.image_received.connect(self.on_image_activity)

        # Main window configuration
        self.setWindowTitle("Sailor Vision AI - Maritime Surveillance")
        self.setMinimumSize(960, 680)  # Set minimum window size
        
        # Central widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # Main layout
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Login screen
        self.login_screen = LoginScreen()
        self.login_screen.login_successful.connect(self.handle_login_success)
        self.main_layout.addWidget(self.login_screen)
        
        # State variables
        self.current_content = None
        self.stacked_widget = None
        self.sidebar = None
    
    def on_image_activity(self, _, topic):
        """Called when an image is received on a ROS topic"""
        # Inform the watchdog of activity on this topic
        if hasattr(self, 'ros_watchdog'):
            self.ros_watchdog.register_topic_activity(topic)

    def handle_login_success(self, user_data):
        """Handle successful login and transition to the main interface"""
        logger.debug("Login successful, loading main interface")
        
        # Store current user for permission checks
        self.current_user = user_data
        
        # IMPORTANT: Configurer UserSession avec les données utilisateur
        user_session = UserSession.get_instance()
        user_session.set_user(user_data)
        
        # Clean up login screen
        self.login_screen.setParent(None)
        self.main_layout.removeWidget(self.login_screen)
        
        # Create new interface
        self.initialize_main_interface(user_data)

    def initialize_main_interface(self, user_data):
        """Initialize the main interface after login"""
        # Clean up previous content
        if self.current_content:
            self.current_content.deleteLater()
        
        # IMPORTANT: S'assurer que UserSession est configuré avant d'initialiser les écrans
        user_session = UserSession.get_instance()
        if not user_session.is_authenticated:
            user_session.set_user(user_data)
        
        # Debug: Vérifier que UserSession est correctement configuré
        logger.info(f"UserSession before screens init: ID={id(user_session)}, authenticated={user_session.is_authenticated}, permissions={len(getattr(user_session, 'permissions', []))}")
        
        # Debug: Forcer la vérification que c'est la même instance
        test_session = UserSession.get_instance()
        logger.info(f"UserSession test instance: ID={id(test_session)}, same_instance={id(user_session) == id(test_session)}")
        
        # Create main container
        self.current_content = QWidget()
        self.main_layout.addWidget(self.current_content)
        
        # Main layout
        main_layout = QHBoxLayout(self.current_content)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Sidebar
        self.sidebar = Sidebar(user_data=user_data)
        main_layout.addWidget(self.sidebar)

        # Container for header and content
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Header
        self.header = HeaderWidget(
            title="Dashboard",
            action_button_text="", 
            parent=None
        )
        content_layout.addWidget(self.header)

        # Notification manager for camera notifications
        self.notification_manager = NotificationManager()
        self.notification_manager.view_pending_cameras.connect(self.show_settings_pending_cameras)
        content_layout.addWidget(self.notification_manager)

        # Force load pending cameras to ensure we have the latest data
        pending_camera_manager.load_pending_cameras()
        
        # Connect to pending camera manager signals - IMPORTANT: Do this BEFORE initializing screens
        pending_camera_manager.new_camera_detected.connect(self.on_new_camera_detected)
        pending_camera_manager.camera_approved.connect(self.on_camera_approved)
        pending_camera_manager.camera_rejected.connect(self.on_camera_rejected)
        
        # Connect camera detector signals
        camera_detector.new_camera_detected.connect(self.handle_camera_detector_signal)
        
        # Stacked Widget for screens
        self.stacked_widget = QStackedWidget()
        self.initialize_screens(user_data)
        
        # Sidebar connections - configure based on permissions
        # Dashboard - toujours visible
        if hasattr(self, 'dashboard_screen') and self.dashboard_screen:
            self.sidebar.dashboard_clicked.connect(
                lambda: self.switch_view("Dashboard", self.dashboard_screen)
            )
        else:
            self.sidebar.hide_dashboard_button()
            
        # Live Feed - toujours visible
        if hasattr(self, 'live_feed_screen') and self.live_feed_screen:
            self.sidebar.live_feed_clicked.connect(
                lambda: self.switch_view("Live Feed", self.live_feed_screen)
            )
        else:
            self.sidebar.hide_live_feed_button()
            
        # Playback - admin et opérateur
        if hasattr(self, 'playback_screen') and self.playback_screen:
            self.sidebar.playback_clicked.connect(
                lambda: self.switch_view("Playback", self.playback_screen)
            )
        else:
            self.sidebar.hide_playback_button()
            
        # Alerts - admin et opérateur
        if hasattr(self, 'alerts_screen') and self.alerts_screen:
            self.sidebar.alerts_clicked.connect(
                lambda: self.switch_view("Alerts", self.alerts_screen)  
            )
        else:
            self.sidebar.hide_alerts_button()
            
        # User Management - admin uniquement
        if hasattr(self, 'user_management_screen') and self.user_management_screen:
            self.sidebar.user_management_clicked.connect(
                lambda: self.switch_view("User Management", self.user_management_screen)  
            )
        else:
            self.sidebar.hide_user_management_button()
            
        # Settings - toujours visible mais contenu différent selon le rôle
        if hasattr(self, 'settings_screen') and self.settings_screen:
            self.sidebar.settings_clicked.connect(
                lambda: self.switch_view("Settings", self.settings_screen)
            )
            # Connecter le bouton "View Profile" du menu popup pour naviguer vers les paramètres
            self.sidebar.view_profile_clicked.connect(
                lambda: self.switch_view("Settings", self.settings_screen)
            )
        else:
            self.sidebar.hide_settings_button()
            
        # Logout - toujours disponible
        self.sidebar.logout_clicked.connect(self.handle_logout)

        content_layout.addWidget(self.stacked_widget)
        main_layout.addWidget(content_widget, 1)  # Give content area stretch factor of 1

        # Initial view
        self.switch_view("Dashboard", self.dashboard_screen)

    def handle_camera_detector_signal(self, camera_id: str, camera_name: str):
        """Handle camera detector signal and trigger notification"""
        logger.info(f"Camera detector signal received: {camera_name} (ID: {camera_id})")
        
        try:
            # Extract device path from camera_id
            device_path = "/dev/video4"  # Default
            if "video" in camera_id:
                parts = camera_id.split("_")
                if len(parts) > 1 and "video" in parts[1]:
                    device_num = parts[1].replace("video", "")
                    device_path = f"/dev/video{device_num}"
        
            # Get pending count
            pending_count = pending_camera_manager.get_pending_count()
            logger.info(f"Showing notification for {camera_name}, device: {device_path}, pending count: {pending_count}")
            
            # Show notification - IMPORTANT: Use QTimer to ensure notification displays after UI is ready
            QTimer.singleShot(100, lambda: self.notification_manager.show_camera_notification(
                camera_name, device_path, pending_count))
            
            logger.info(f"✅ Notification queued for {camera_name}")
        except Exception as e:
            logger.error(f"Error showing camera notification: {e}")
            traceback.print_exc()

    def on_new_camera_detected(self, camera_id, camera_name, camera_ip):
        """Handle a new camera detection from pending camera manager"""
        logger.info(f"New camera detected: {camera_name} ({camera_ip})")
        if hasattr(self, 'notification_manager'):
            pending_count = len(pending_camera_manager.pending_cameras)
            self.notification_manager.show_camera_notification(camera_name, camera_ip, pending_count)

    def check_screen_access(self, screen_title, permission):
        """Vérifier l'accès à un écran en utilisant UserSession optimisé"""
        user_session = UserSession.get_instance()
        
        # Vérifier si l'utilisateur est authentifié
        if not user_session.is_authenticated:
            logger.warning(f"User not authenticated for screen: {screen_title}")
            return False
            
        # Vérifier la permission spécifique
        has_permission = user_session.has_permission(permission)
        if not has_permission:
            logger.warning(f"User {user_session.get_username()} lacks permission {permission.value} for screen: {screen_title}")
        
        return has_permission

    def switch_view(self, title, widget):
        """Change the active view in the application"""
        if not widget:
            logger.warning(f"Screen '{title}' not implemented or failed to initialize")
            return
        
        # Verify that the widget is in the stack
        if widget not in [self.stacked_widget.widget(i) for i in range(self.stacked_widget.count())]:
            logger.error(f"Widget for '{title}' not found in stacked widget")
            return
            
        # Check permission based on screen title
        permission = None
        if title == "Dashboard":
            permission = Permission.VIEW_DASHBOARD
        elif title == "Live Feed":
            permission = Permission.VIEW_LIVE_FEED
        elif title == "Playback":
            permission = Permission.VIEW_RECORDINGS
        elif title == "Alerts":
            permission = Permission.VIEW_ALERTS
        elif title == "User Management":
            permission = Permission.VIEW_USERS
        elif title == "Settings":
            permission = Permission.VIEW_SETTINGS
            
        # Check permission if applicable
        if permission and not self.check_screen_access(title, permission):
            logger.warning(f"Access denied to screen: {title}")
            return
            
        try:
            # Temporarily disable all signals to avoid crashes during screen changes
            previous_widget = self.stacked_widget.currentWidget()
            if previous_widget:
                previous_widget.blockSignals(True)
                
            # Display the new page
            self.header.set_title(title)
            self.stacked_widget.setCurrentWidget(widget)
            
            # Re-enable signals for the previous widget
            if previous_widget:
                previous_widget.blockSignals(False)

            # Update the sidebar active button
            if title == "Dashboard":
                self.sidebar.set_active_button(self.sidebar.dashboard_btn)
            elif title == "Live Feed":
                self.sidebar.set_active_button(self.sidebar.live_feed_btn)
            elif title == "Playback":
                self.sidebar.set_active_button(self.sidebar.playback_btn)
            elif title == "Alerts":
                self.sidebar.set_active_button(self.sidebar.alerts_btn)
            elif title == "User Management":
                self.sidebar.set_active_button(self.sidebar.user_mgmt_btn)
            elif title == "Settings":
                self.sidebar.set_active_button(self.sidebar.settings_btn)

            # Disconnect and hide the previous action button
            try:
                self.header.action_button_clicked.disconnect()
            except (TypeError, RuntimeError):
                pass
                
            self.header.set_action_button("", visible=False)
            
            # Disconnect the previous search handler (if used)
            try:
                self.header.search_text_changed.disconnect()
            except (TypeError, RuntimeError):
                pass

            # Specific configuration for each screen
            if title == "Dashboard":
                self.header.set_search_box_visibility(True)
                self.header.set_search_placeholder("Search cameras, alerts...")
                
            elif title == "Live Feed":
                self.header.set_search_box_visibility(True)
                self.header.set_search_placeholder("Search cameras...")
                # Connect search to camera filter only if method exists
                if hasattr(self.live_feed_screen, 'filter_cameras'):
                    self.header.search_text_changed.connect(self.live_feed_screen.filter_cameras)

            elif title == "Alerts":
                self.header.set_search_box_visibility(True)
                self.header.set_search_placeholder("Search alerts…")
                # Connect to alerts filter if it exists
                if hasattr(self.alerts_screen, 'filter_alerts'):
                    self.header.search_text_changed.connect(self.alerts_screen.filter_alerts)
                self.header.set_action_button("", False)

            elif title == "User Management":
                self.header.set_search_box_visibility(True)
                self.header.set_search_placeholder("Search users...")
                self.header.set_action_button("Add User", visible=True)
                if hasattr(self.user_management_screen, 'on_add_user_clicked'):
                    self.header.action_button_clicked.connect(self.user_management_screen.on_add_user_clicked)
                if hasattr(self.user_management_screen, 'filter_users'):
                    self.header.search_text_changed.connect(self.user_management_screen.filter_users)

            elif title == "Settings":
                self.header.set_search_box_visibility(False)
                self.header.set_action_button("", visible=False)

            else:
                self.header.set_search_box_visibility(True)
                self.header.set_search_placeholder(f"Search {title.lower()}…")
                
        except Exception as e:
            logger.error(f"Error during screen switch: {str(e)}")
            logger.error(traceback.format_exc())

    def initialize_screens(self, user_data):
        """Initialize different screens for the application based on user permissions"""
        try:
            # Utiliser UserSession optimisé pour les vérifications de permissions
            user_session = UserSession.get_instance()
            
            # Configurer les écrans selon les permissions
            self.dashboard_screen = None
            self.live_feed_screen = None
            self.alerts_screen = None
            self.user_management_screen = None
            self.playback_screen = None
            self.settings_screen = None
            
            # Dashboard - accessible à tous les utilisateurs
            if user_session.has_permission(Permission.VIEW_DASHBOARD):
                try:
                    self.dashboard_screen = DashboardScreen(user_data=user_data)
                    logger.info("Dashboard screen initialized")
                    self.stacked_widget.addWidget(self.dashboard_screen)
                except Exception as e:
                    logger.error(f"Error initializing dashboard: {e}")
                    self.dashboard_screen = None
            else:
                logger.warning(f"User {user_data.get('username')} does not have permission to access Dashboard")
            
            # Live Feed - accessible à tous les utilisateurs
            if user_session.has_permission(Permission.VIEW_LIVE_FEED):
                try:
                    self.live_feed_screen = LiveFeedScreen(user_data=user_data, ros_node=self.ros_node, ros_bridge=self.ros_bridge)
                    logger.info("Live feed screen initialized")
                    self.stacked_widget.addWidget(self.live_feed_screen)
                except Exception as e:
                    logger.error(f"Error initializing live feed: {e}")
                    self.live_feed_screen = None
            else:
                logger.warning(f"User {user_data.get('username')} does not have permission to access Live Feed")
            
            # Alerts - accessible aux admins et opérateurs
            if user_session.has_permission(Permission.VIEW_ALERTS):
                try:
                    self.alerts_screen = AlertsScreen(user_data=user_data, ros_node=self.ros_node)
                    logger.info("Alerts screen initialized")
                    self.stacked_widget.addWidget(self.alerts_screen)
                except Exception as e:
                    logger.error(f"Error initializing alerts: {e}")
                    self.alerts_screen = None
            else:
                logger.warning(f"User {user_data.get('username')} does not have permission to access Alerts")
            
            # User Management - accessible uniquement aux admins
            if user_session.has_permission(Permission.VIEW_USERS):
                try:
                    # Create a new session for user management
                    user_mgmt_session = create_new_session()
                    self.user_management_screen = UserManagementScreen(user_data=user_data, db_session=user_mgmt_session)
                    logger.info("User management screen initialized")
                    self.stacked_widget.addWidget(self.user_management_screen)
                except Exception as e:
                    logger.error(f"Error initializing user management: {e}")
                    self.user_management_screen = None
            else:
                logger.warning(f"User {user_data.get('username')} does not have permission to access User Management")
            
            # Playback - accessible aux admins et opérateurs
            if user_session.has_permission(Permission.VIEW_RECORDINGS):
                try:
                    self.playback_screen = PlaybackScreen(user_data=user_data, ros_node=self.ros_node)
                    logger.info("Playback screen initialized")
                    self.stacked_widget.addWidget(self.playback_screen)
                except Exception as e:
                    logger.error(f"Error initializing playback: {e}")
                    self.playback_screen = None
            else:
                logger.warning(f"User {user_data.get('username')} does not have permission to access Playback")
            
            # Settings - accessible à tous les utilisateurs mais avec différentes capacités
            if user_session.has_permission(Permission.VIEW_SETTINGS):
                try:
                    # Create a new session for settings
                    settings_session = create_new_session()
                    self.settings_screen = SettingsScreen(user=user_data, db_session=settings_session)
                    logger.info("Settings screen initialized")
                    self.stacked_widget.addWidget(self.settings_screen)
                except Exception as e:
                    logger.error(f"Error initializing settings: {e}")
                    logger.error(traceback.format_exc())
                    # Fallback en cas d'erreur avec une meilleure approche
                    # Créer une classe simple qui hérite de QWidget et a le signal requis
                    class FallbackSettingsWidget(QWidget):
                        camera_approved_signal = pyqtSignal(dict)
                    
                    self.settings_screen = FallbackSettingsWidget()
                    layout = QVBoxLayout(self.settings_screen)
                    layout.addWidget(QLabel("Settings - Profile Only Mode"))
                    self.stacked_widget.addWidget(self.settings_screen)
                    logger.info("Fallback settings screen initialized")
            else:
                logger.warning(f"User {user_data.get('username')} does not have permission to access Settings")

            # Connect signals only if screens are initialized
            if self.live_feed_screen and self.dashboard_screen:
                self.live_feed_screen.frame_updated.connect(self.dashboard_screen.update_camera_feed)
                self.live_feed_screen.feed_stopped.connect(self.dashboard_screen.camera_feed_stopped)
            
            if self.dashboard_screen and self.live_feed_screen:
                self.dashboard_screen.navigate_to_live_feed.connect(self.handle_live_feed_navigation)
                
            # Connect signals between settings and live feed
            if self.settings_screen and self.live_feed_screen:
                self.settings_screen.camera_approved_signal.connect(self.live_feed_screen.refresh_cameras_from_database)
                self.settings_screen.camera_updated_signal.connect(self.live_feed_screen.on_camera_updated)
                self.settings_screen.camera_status_changed_signal.connect(self.live_feed_screen.on_camera_status_changed)
                logger.info("Connected camera signals from settings to live feed (approved, updated, status changed)")
            
            # Connect watchdog signals to screens
            if hasattr(self, 'ros_watchdog'):
                self.ros_watchdog.cameras_status_changed.connect(self.on_cameras_status_changed)
                self.ros_watchdog.ros_status_changed.connect(self.on_ros_status_changed)
                
            # Add screens to the stacked widget only if they exist
            if self.dashboard_screen:
                self.stacked_widget.addWidget(self.dashboard_screen)
            if self.live_feed_screen:
                self.stacked_widget.addWidget(self.live_feed_screen)
            if self.alerts_screen:
                self.stacked_widget.addWidget(self.alerts_screen)
            if self.user_management_screen:
                self.stacked_widget.addWidget(self.user_management_screen)
            if self.playback_screen:
                self.stacked_widget.addWidget(self.playback_screen)
            if self.settings_screen:
                self.stacked_widget.addWidget(self.settings_screen)
                
            # Add mechanism for preparing and cleaning screens
            self.stacked_widget.currentChanged.connect(self.on_screen_changed)
            logger.info(f"Screens initialized: {self.stacked_widget.count()} screens added to stack")
            
        except Exception as e:
            logger.error(f"Error initializing screens: {e}")
            logger.error(traceback.format_exc())

    def on_screen_changed(self, index):
        """
        Called when the active screen changes to prepare the new screen
        and clean up the old one
        """
        try:
            current_widget = self.stacked_widget.widget(index)
            # Prepare the new screen if needed
            if hasattr(current_widget, 'prepare_screen'):
                current_widget.prepare_screen()
                
            # For all other screens, call cleanup if available
            for i in range(self.stacked_widget.count()):
                if i != index:
                    widget = self.stacked_widget.widget(i)
                    if widget and hasattr(widget, 'cleanup'):
                        widget.cleanup()
        except Exception as e:
            logger.error(f"Error in screen transition: {e}")
            
    def on_cameras_status_changed(self, camera_ids):
        """Handle camera status changes reported by the watchdog"""
        logger.info(f"Camera status changed for IDs: {camera_ids}")
        
        # Update Dashboard and LiveFeed screens
        if hasattr(self, 'dashboard_screen') and hasattr(self.dashboard_screen, 'refresh_cameras'):
            self.dashboard_screen.refresh_cameras()
        
        if hasattr(self, 'live_feed_screen') and hasattr(self.live_feed_screen, 'refresh_cameras'):
            self.live_feed_screen.refresh_cameras()
            
    def on_ros_status_changed(self, connected):
        """Handle global ROS status changes"""
        status_msg = "connected" if connected else "disconnected"
        logger.warning(f"ROS system is now {status_msg}")
        
        # Show message to user if ROS is disconnected
        if not connected:
            QMessageBox.warning(
                self, 
                "ROS System Disconnected", 
                "Connection to ROS system has been lost. Video feeds and detections are no longer available."
            )
        else:
            # ROS reconnected - show a simple info message
            QMessageBox.information(
                self,
                "ROS System Reconnected", 
                "ROS system is now reconnected. Video feeds and detections are available again."
            )
            
    def handle_live_feed_navigation(self, camera_id):
        """Handle navigation to the live feed screen for a specific camera."""
        logger.info(f"Switching to Live Feed screen for camera ID: {camera_id}")
        
        # Make sure live_feed_screen is initialized
        if not hasattr(self, 'live_feed_screen') or not self.live_feed_screen:
            logger.error("Live feed screen is not initialized")
            return
        
        # Check if the set_active_camera method exists
        if not hasattr(self.live_feed_screen, 'set_active_camera'):
            logger.error("set_active_camera method not found in LiveFeedScreen")
            return
        
        try:
            # Set active camera before switching view
            self.live_feed_screen.set_active_camera(camera_id)
            
            # Switch view to Live Feed
            self.switch_view("Live Feed", self.live_feed_screen)
            logger.info(f"Successfully navigated to Live Feed for camera ID: {camera_id}")
        except Exception as e:
            logger.error(f"Error navigating to Live Feed: {str(e)}")
            logger.error(traceback.format_exc())

    def handle_logout(self):
        """Handle user logout."""
        logger.info("User logged out")
        QMessageBox.information(self, "Logout", "You have been logged out.")
        self.reset_to_login_screen()
        
    def on_new_camera_detected(self, camera_id, camera_name, camera_ip):
        """Handle a new camera detection"""
        logger.info(f"New camera detected: {camera_name} ({camera_ip})")
        # Show notification
        try:
            if hasattr(self, 'notification_manager'):
                # Get pending count
                pending_count = pending_camera_manager.get_pending_count()
                self.notification_manager.show_camera_notification(camera_name, camera_ip, pending_count)
        except Exception as e:
            logger.error(f"Error showing camera notification: {e}")

    def show_settings_pending_cameras(self):
        """Navigate to settings screen and show pending cameras section"""
        try:
            # Switch to settings screen
            self.switch_view("Settings", self.settings_screen)
            logger.info("Navigated to settings screen for pending camera approval")
        except Exception as e:
            logger.error(f"Error navigating to settings: {e}")

    def on_camera_approved(self, approved_camera):
        """
        Handle camera approval
        Automatically reload the Live Feed to include the new camera
        """
        print(f"[MainWindow] Caméra approuvée: {approved_camera.name}")
        
        # Reload the Live Feed to include the new camera
        if hasattr(self, 'live_feed_screen') and self.live_feed_screen:
            try:
                # Reload cameras from the database
                self.live_feed_screen.refresh_cameras_from_database()
                print(f"[MainWindow] Live Feed rechargé avec la nouvelle caméra: {approved_camera.name}")
            except Exception as e:
                print(f"[MainWindow] Erreur lors du rechargement du Live Feed: {e}")
                traceback.print_exc()
        
        # Reload the Dashboard if needed
        if hasattr(self, 'dashboard_screen') and self.dashboard_screen:
            try:
                # The Dashboard may also display cameras
                # Add reload method if needed
                print(f"[MainWindow] Dashboard notifié de la nouvelle caméra: {approved_camera.name}")
            except Exception as e:
                print(f"[MainWindow] Erreur lors de la notification du Dashboard: {e}")
        
        # Show a success notification
        if hasattr(self, 'notification_manager'):
            # Show a specific notification for approval
            self.notification_manager.show_approval_notification(approved_camera.name)
            print(f"[MainWindow] 🎉 Caméra {approved_camera.name} ajoutée au système avec succès!")
            print(f"[MainWindow] 📹 La caméra est maintenant disponible dans le Live Feed")
            print(f"[MainWindow] 🔧 Vous pouvez la voir dans l'écran de surveillance en temps réel")
    
    def on_camera_rejected(self, camera_id: str):
        """
        Handle camera rejection
        """
        print(f"[MainWindow] Caméra rejetée: {camera_id}")
        # You could add additional logic here
        # such as notification or logging
        
    def reset_to_login_screen(self):
        """Reset the application to the login screen."""
        # Clean up main interface
        self.main_layout.removeWidget(self.current_content)
        self.current_content.deleteLater()
        self.current_content = None

        # Show login screen
        self.login_screen = LoginScreen()
        self.main_layout.addWidget(self.login_screen)
        self.login_screen.login_successful.connect(self.handle_login_success)

    def clear_layout(self, layout):
        """Recursively clear all widgets and layouts"""
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
            else:
                self.clear_layout(item.layout())

def setup_fonts():
    """Configure application fonts"""
    font_db = QFontDatabase()
    try:
        font_db.addApplicationFont("/home/abirc240/Desktop/sailor-vision-ai/sailor_vision_gui/src/assets/fonts/Inter-Regular.ttf")
        font_db.addApplicationFont("/home/abirc240/Desktop/sailor-vision-ai/sailor_vision_gui/src/assets/fonts/Inter-Bold.ttf")
        font_db.addApplicationFont("/home/abirc240/Desktop/sailor-vision-ai/sailor_vision_gui/src/assets/fonts/Inter-Medium.ttf")
        app_font = QFont("Inter")
        app_font.setPixelSize(14)  # Base font size
    except Exception as e:
        logger.warning(f"Error loading fonts: {str(e)}")
        app_font = QFont("Arial")
        app_font.setPixelSize(14)
    
    QApplication.setFont(app_font)

def main():
    """Main entry point for the application"""
    rclpy.init()
    ros_node = Node('sailor_vision_bridge')
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Setup style
    style_path = os.path.join(os.path.dirname(__file__), "src", "assets", "style.qss")
    logger.info(f"Loading style from {style_path}")
    try:
        with open(style_path, "r") as f:
            app.setStyleSheet(f.read())
    except Exception as e:
        logger.warning(f"Error loading style: {str(e)}")
        # Try to create a default style file
        os.makedirs(os.path.dirname(style_path), exist_ok=True)
        with open(style_path, "w") as f:
            f.write("""
            /* Default styling */
            QMainWindow {
                background-color: #f5f5f5;
            }
            """)
        logger.info(f"Created default style file at {style_path}")
        
    setup_fonts()
    
    window = MainWindow(ros_node)
    window.show()
    
    # ROS ↔ Qt event loop
    timer = QTimer()
    timer.timeout.connect(lambda: rclpy.spin_once(ros_node, timeout_sec=0.0))
    timer.start(10)
    
    exit_code = app.exec_()
    
    # Clean shutdown
    rclpy.shutdown()
    sys.exit(exit_code)

if __name__ == "__main__":
    main()