import sys
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QStackedWidget, QWidget, QVBoxLayout, QHBoxLayout
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
from src.components.shared import Sidebar, HeaderWidget

from database import init_db
from models import User, Camera, Alert, Recording
from config import load_config

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MainWindow(QMainWindow):
    def __init__(self, ros_node):
        super().__init__()
        self.ros_node = ros_node
        
        # Initialize database
        init_db()
        
        # Main window configuration
        self.setWindowTitle("Sailor Vision AI - Maritime Surveillance")
        self.setMinimumSize(960, 680)  # Further reduced size for better adaptability
        
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
        """Handle successful login"""
        logger.debug("Login successful, loading main interface")
        
        # Clean up login screen
        self.login_screen.setParent(None)
        self.main_layout.removeWidget(self.login_screen)
        
        # Create new interface
        self.initialize_main_interface(user_data)

    def initialize_main_interface(self, user_data):
        """Initialize main interface after login"""
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
            lambda: self.switch_view("Playback", None)  # To be implemented
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

        content_layout.addWidget(self.stacked_widget)
        main_layout.addWidget(content_widget, 1)  # Give content area stretch factor of 1

        # Initial view
        self.switch_view("Dashboard", self.dashboard_screen)

    def initialize_screens(self, user_data):
        """Initialize different screens"""
        self.dashboard_screen  = DashboardScreen(user_data=user_data)
        self.live_feed_screen  = LiveFeedScreen(user_data=user_data, ros_node=self.ros_node)
        self.alerts_screen     = AlertsScreen(user_data=user_data,    ros_node=self.ros_node)
        self.user_management_screen = UserManagementScreen(user_data=user_data)

        
        self.stacked_widget.addWidget(self.dashboard_screen)
        self.stacked_widget.addWidget(self.live_feed_screen)
        self.stacked_widget.addWidget(self.alerts_screen)
        self.stacked_widget.addWidget(self.user_management_screen)

    def switch_view(self, title, widget):
        """Change active view"""
        if not widget:
            logger.warning(f"Screen '{title}' not implemented")
            return

        # Afficher la nouvelle page
        self.header.set_title(title)
        self.stacked_widget.setCurrentWidget(widget)

        # 1) Déconnecter et cacher systématiquement l’ancien bouton d’action
        try:
            self.header.action_button_clicked.disconnect()
        except (TypeError, RuntimeError):
            pass
        self.header.set_action_button("", visible=False)

        # 2) Déconnecter l’ancien handler de recherche (si utilisé)
        try:
            self.header.search_text_changed.disconnect()
        except (TypeError, RuntimeError):
            pass

        # 3) Configuration spécifique à chaque écran
        if title == "Dashboard":
            self.header.set_search_box_visibility(True)
            self.header.set_search_placeholder("Search cameras, alerts...")
            # Si vous avez un filtre à connecter :
            # self.header.search_text_changed.connect(self.dashboard_screen.filter_items)

        elif title == "Live Feed":
            self.header.set_search_box_visibility(True)
            self.header.set_search_placeholder("Search cameras...")
            # Réactiver le bouton "Add Camera"
            self.header.set_action_button("Add Camera", visible=True)
            self.header.action_button_clicked.connect(
                self.live_feed_screen.show_add_camera_dialog
            )

        elif title == "Alerts":
            # Affiche la searchbox et change le placeholder
            self.header.set_search_box_visibility(True)
            self.header.set_search_placeholder("Search alerts…")

            # Déconnecte les anciennes connexions et connecte au filtre
            try: self.header.search_text_changed.disconnect()
            except: pass
            self.header.search_text_changed.connect(self.alerts_screen.filter_alerts)

            # Pas de bouton d’action ici
            self.header.set_action_button("", False)

        elif title == "User Management":
            self.header.set_search_box_visibility(True)
            self.header.set_search_placeholder("Search users...")
            # Bouton "Add User"
            self.header.set_action_button("Add User", visible=True)
            self.header.action_button_clicked.connect(
                self.user_management_screen.on_add_user_clicked
            )
            # Filtre de recherche pour les utilisateurs
            self.header.search_text_changed.connect(self.user_management_screen.filter_users)

        else:
            # Écrans futurs
            self.header.set_search_box_visibility(True)
            self.header.set_search_placeholder(f"Search {title.lower()}…")
            # aucun bouton d’action par défaut


    def clear_layout(self, layout):
        """Recursively clear a layout"""
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

    rclpy.init()
    ros_node = Node('sailor_vision_bridge')
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    
    # Setup style
    style_path = os.path.join(os.path.dirname(__file__), "src", "assets", "style.qss")
    print(f"Loading style from {style_path}")
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
    # 3) Boucle ROS ↔ Qt
    timer = QTimer()
    timer.timeout.connect(lambda: rclpy.spin_once(ros_node, timeout_sec=0.0))
    timer.start(10)

    exit_code = app.exec_()

    # 4) Arrêt propre
    rclpy.shutdown()
    sys.exit(exit_code)

if __name__ == "__main__":
    main()