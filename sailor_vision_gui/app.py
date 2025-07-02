import sys
import os

# Add the src directory to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from PyQt5.QtWidgets import QApplication, QMainWindow, QStackedWidget, QWidget, QVBoxLayout, QHBoxLayout, QMessageBox
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

# Import le watchdog ROS
from shared.ros_watchdog import ROSWatchdog

from database import init_db, get_session
from models import User, Camera, Alert, Recording
from config import load_config
from shared.detection_recorder import DetectionRecorder
from shared.ros_image_listener import ROSImageBridge

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

class MainWindow(QMainWindow):
    def __init__(self, ros_node):
        """Initialize the main application window"""
        super().__init__()
        self.ros_node = ros_node
        
        # Initialize database
        init_db()
        
        # Create one shared ROSImageBridge instance for both LiveFeed and DetectionRecorder
        self.ros_bridge = ROSImageBridge(ros_node)
        
        # Initialize the DetectionRecorder
        self.detection_recorder = DetectionRecorder(self.ros_node, ros_bridge=self.ros_bridge)
        logger.info("Detection recorder initialized")
        
        # Initialize the ROS Watchdog
        self.ros_watchdog = ROSWatchdog(ros_node)
        logger.info("ROS Watchdog initialized")
        
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
        # Informer le watchdog de l'activité sur ce topic
        if hasattr(self, 'ros_watchdog'):
            self.ros_watchdog.register_topic_activity(topic)

    def handle_login_success(self, user_data):
        """Handle successful login and transition to the main interface"""
        logger.debug("Login successful, loading main interface")
        
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

        # Stacked Widget for screens
        self.stacked_widget = QStackedWidget()
        self.initialize_screens(user_data)
        
        # Sidebar connections
        self.sidebar.dashboard_clicked.connect(
            lambda: self.switch_view("Dashboard", self.dashboard_screen)
        )
        self.sidebar.live_feed_clicked.connect(
            lambda: self.switch_view("Live Feed", self.live_feed_screen)
        )
        self.sidebar.playback_clicked.connect(
            lambda: self.switch_view("Playback", self.playback_screen)
        )
        self.sidebar.alerts_clicked.connect(
            lambda: self.switch_view("Alerts", self.alerts_screen)  
        )
        self.sidebar.user_management_clicked.connect(
            lambda: self.switch_view("User Management",  self.user_management_screen)  
        )
        self.sidebar.settings_clicked.connect(
            lambda: self.switch_view("Settings", self.settings_screen)
        )
        self.sidebar.logout_clicked.connect(self.handle_logout)  # Connect logout signal

        content_layout.addWidget(self.stacked_widget)
        main_layout.addWidget(content_widget, 1)  # Give content area stretch factor of 1

        # Initial view
        self.switch_view("Dashboard", self.dashboard_screen)

    def switch_view(self, title, widget):
        """Change the active view in the application"""
        if not widget:
            logger.warning(f"Screen '{title}' not implemented")
            return
            
        try:
            # Désactiver temporairement tous les signaux pour éviter les crashes
            # lors du changement d'écran
            previous_widget = self.stacked_widget.currentWidget()
            if previous_widget:
                previous_widget.blockSignals(True)
                
            # Display the new page
            self.header.set_title(title)
            self.stacked_widget.setCurrentWidget(widget)
            
            # Réactiver les signaux du widget précédent
            if previous_widget:
                previous_widget.blockSignals(False)

            # Also update the sidebar active button
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
                # If you have a filter to connect:
                # self.header.search_text_changed.connect(self.dashboard_screen.filter_items)

            elif title == "Live Feed":
                self.header.set_search_box_visibility(True)
                self.header.set_search_placeholder("Search cameras...")
                # Connect search to camera filter
                self.header.search_text_changed.connect(self.live_feed_screen.filter_cameras)

            elif title == "Alerts":
                # Show the search box and change the placeholder
                self.header.set_search_box_visibility(True)
                self.header.set_search_placeholder("Search alerts…")

                # Disconnect old connections and connect to the filter
                try: self.header.search_text_changed.disconnect()
                except: pass
                self.header.search_text_changed.connect(self.alerts_screen.filter_alerts)

                # No action button here
                self.header.set_action_button("", False)

            elif title == "User Management":
                self.header.set_search_box_visibility(True)
                self.header.set_search_placeholder("Search users...")
                # "Add User" button
                self.header.set_action_button("Add User", visible=True)
                self.header.action_button_clicked.connect(
                    self.user_management_screen.on_add_user_clicked
                )
                # Search filter for users
                self.header.search_text_changed.connect(self.user_management_screen.filter_users)

            elif title == "Settings":
                self.header.set_search_box_visibility(False)
                self.header.set_action_button("", visible=False)

            else:
                # Future screens
                self.header.set_search_box_visibility(True)
                self.header.set_search_placeholder(f"Search {title.lower()}…")
                # No default action button
        except Exception as e:
            logger.error(f"Error during screen switch: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())

    def initialize_screens(self, user_data):
        """Initialize different screens for the application"""
        try:
            db_session = get_session()
            self.dashboard_screen = DashboardScreen(user_data=user_data)
            self.live_feed_screen = LiveFeedScreen(user_data=user_data, ros_node=self.ros_node, ros_bridge=self.ros_bridge)
            self.alerts_screen = AlertsScreen(user_data=user_data, ros_node=self.ros_node)
            self.user_management_screen = UserManagementScreen(user_data=user_data, db_session=db_session)
            self.playback_screen = PlaybackScreen(user_data=user_data, ros_node=self.ros_node)
            self.settings_screen = SettingsScreen(user=user_data, db_session=db_session)

            # Connect LiveFeedScreen camera signals to DashboardScreen
            self.live_feed_screen.frame_updated.connect(self.dashboard_screen.update_camera_feed)
            self.live_feed_screen.feed_stopped.connect(self.dashboard_screen.camera_feed_stopped)
            
            # Connect DashboardScreen signals to LiveFeedScreen navigation
            self.dashboard_screen.navigate_to_live_feed.connect(self.handle_live_feed_navigation)
            
            # Connecter les signaux du watchdog aux écrans
            if hasattr(self, 'ros_watchdog'):
                self.ros_watchdog.cameras_status_changed.connect(self.on_cameras_status_changed)
                self.ros_watchdog.ros_status_changed.connect(self.on_ros_status_changed)

            # Add screens to the stacked widget
            self.stacked_widget.addWidget(self.dashboard_screen)
            self.stacked_widget.addWidget(self.live_feed_screen)
            self.stacked_widget.addWidget(self.alerts_screen)
            self.stacked_widget.addWidget(self.user_management_screen)
            self.stacked_widget.addWidget(self.playback_screen)
            self.stacked_widget.addWidget(self.settings_screen)
            
            # Ajouter un mécanisme de préparation et nettoyage des écrans
            self.stacked_widget.currentChanged.connect(self.on_screen_changed)
            
        except Exception as e:
            logger.error(f"Error initializing screens: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def on_screen_changed(self, index):
        """
        Appelé quand l'écran actif change pour préparer le nouvel écran
        et nettoyer l'ancien
        """
        try:
            current_widget = self.stacked_widget.widget(index)
            
            # Préparer le nouvel écran si nécessaire
            if hasattr(current_widget, 'prepare_screen'):
                current_widget.prepare_screen()
                
            # Pour tous les autres écrans, appeler cleanup si disponible
            for i in range(self.stacked_widget.count()):
                if i != index:
                    widget = self.stacked_widget.widget(i)
                    if widget and hasattr(widget, 'cleanup'):
                        widget.cleanup()
        except Exception as e:
            logger.error(f"Error in screen transition: {e}")

    def on_cameras_status_changed(self, camera_ids):
        """Gérer le changement d'état des caméras signalé par le watchdog"""
        logger.info(f"État des caméras modifié pour IDs: {camera_ids}")
        
        # Mettre à jour les écrans Dashboard et LiveFeed
        if hasattr(self, 'dashboard_screen'):
            self.dashboard_screen.refresh_cameras()
            
        if hasattr(self, 'live_feed_screen'):
            self.live_feed_screen.refresh_cameras()
    
    def on_ros_status_changed(self, connected):
        """Gérer le changement d'état global de ROS"""
        status_msg = "connecté" if connected else "déconnecté"
        logger.warning(f"Le système ROS est maintenant {status_msg}")
        
        # Afficher un message à l'utilisateur si ROS est déconnecté
        if not connected:
            QMessageBox.warning(
                self, 
                "Système ROS déconnecté", 
                "La connexion au système ROS a été perdue. Les flux vidéo et détections ne sont plus disponibles."
            )
        else:
            # ROS s'est reconnecté
            if hasattr(self, 'header'):
                self.header.show_notification("Système ROS reconnecté", "success")

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
            import traceback
            logger.error(traceback.format_exc())

    def handle_logout(self):
        """Handle user logout."""
        logger.info("User logged out")
        QMessageBox.information(self, "Logout", "You have been logged out.")
        self.reset_to_login_screen()

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