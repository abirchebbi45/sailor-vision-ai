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


from database import init_db
from models import User, Camera, Alert, Recording
from config import load_config
from shared.detection_recorder import DetectionRecorder

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MainWindow(QMainWindow):
    def __init__(self, ros_node):
        """Initialize the main application window"""
        super().__init__()
        self.ros_node = ros_node
        
        # Initialize database
        init_db()
        
        # Initialize the DetectionRecorder
        self.detection_recorder = DetectionRecorder(self.ros_node)
        logger.info("Detection recorder initialized")

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
            lambda: self.switch_view("Playback", self.playback_screen)  # To be implemented
        )
        self.sidebar.alerts_clicked.connect(
            lambda: self.switch_view("Alerts", self.alerts_screen )  
        )
        self.sidebar.user_management_clicked.connect(
            lambda: self.switch_view("User Management",  self.user_management_screen)  
        )
        self.sidebar.settings_clicked.connect(
            lambda: self.switch_view("Settings", None)  # To be implemented
        )
        self.sidebar.logout_clicked.connect(self.handle_logout)  # Connect logout signal

        content_layout.addWidget(self.stacked_widget)
        main_layout.addWidget(content_widget, 1)  # Give content area stretch factor of 1

        # Initial view
        self.switch_view("Dashboard", self.dashboard_screen)

    def initialize_screens(self, user_data):
        """Initialize different screens for the application"""
        self.dashboard_screen  = DashboardScreen(user_data=user_data)
        self.live_feed_screen  = LiveFeedScreen(user_data=user_data, ros_node=self.ros_node)
        self.alerts_screen     = AlertsScreen(user_data=user_data, ros_node=self.ros_node)
        self.user_management_screen = UserManagementScreen(user_data=user_data)
        self.playback_screen   = PlaybackScreen(user_data=user_data, ros_node=self.ros_node)

        # Connect dashboard's navigation signal
        self.dashboard_screen.navigate_to_alerts.connect(
            lambda: self.switch_view("Alerts", self.alerts_screen)
        )
        
        # Connect signals for cross-screen alert acknowledgment updates
        self.dashboard_screen.alerts_acknowledged.connect(self.alerts_screen.refresh_alerts)

        self.stacked_widget.addWidget(self.dashboard_screen)
        self.stacked_widget.addWidget(self.live_feed_screen)
        self.stacked_widget.addWidget(self.alerts_screen)
        self.stacked_widget.addWidget(self.user_management_screen)
        self.stacked_widget.addWidget(self.playback_screen)  # Add playback_screen to the stack

    def switch_view(self, title, widget):
        """Change the active view in the application"""
        if not widget:
            logger.warning(f"Screen '{title}' not implemented")
            return

        # Display the new page
        self.header.set_title(title)
        self.stacked_widget.setCurrentWidget(widget)

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
            # Enable the "Add Camera" button
            self.header.set_action_button("Add Camera", visible=True)
            self.header.action_button_clicked.connect(
                self.live_feed_screen.show_add_camera_dialog
            )

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

        else:
            # Future screens
            self.header.set_search_box_visibility(True)
            self.header.set_search_placeholder(f"Search {title.lower()}…")
            # No default action button

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