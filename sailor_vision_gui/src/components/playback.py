from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QFrame, QScrollArea, QLineEdit,
                             QToolButton, QComboBox, QSlider, QGridLayout,
                             QDateEdit, QMessageBox, QSplitter, QSizePolicy, QGraphicsScene, QGraphicsView, QMenu, QFileDialog)
from PyQt5.QtCore import Qt, QDate, QTime, QSize, QTimer, QThread, pyqtSignal, QUrl
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtMultimedia import QMediaPlayer, QMediaPlaylist, QMediaContent
from PyQt5.QtMultimediaWidgets import QGraphicsVideoItem
import datetime
import logging
import os

from services.camera_service import CameraService
from database import get_session
from ..services.storage_service import StorageService
from src.components.dashboard import SectionFrame 
from ..components.shared import HeaderWidget, VideoPlayerWidget
from models import Recording

logger = logging.getLogger(__name__)

class RecordingItem(QFrame):
    """Widget representing a recording item in the list with enhanced UI"""
    def __init__(self, recording, playback_screen):
        super().__init__()
        self.recording = recording
        self.playback_screen = playback_screen  # Store reference to PlaybackScreen
        self.setObjectName("recordingItem")
        
        # Modern card-like styling
        self.setStyleSheet("""
            QFrame#recordingItem {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
            }
            QFrame#recordingItem:hover {
                border-color: #BBDEFB;
                background-color: #F5F9FF;
            }
            QFrame#recordingItem:pressed {
                border-color: #2196F3;
                background-color: #E3F2FD;
            }
            QLabel#recordingTitle {
                font-size: 13px;
                font-weight: bold;
                color: #37474F;
            }
            QLabel#recordingDateTime {
                font-size: 11px;
                color: #607D8B;
            }
            QLabel#recordingDetail {
                font-size: 11px;
                color: #78909C;
            }
            QLabel#recordingIcon {
                min-width: 40px;
                max-width: 40px;
            }
            QPushButton#actionButton {
                background-color: #2196F3;
                color: white;
                border-radius: 4px;
                padding: 4px 8px;
                min-width: 60px;
                font-size: 11px;
                border: none;
            }
            QPushButton#actionButton:hover {
                background-color: #1E88E5;
            }
            QPushButton#dangerButton {
                background-color: #f44336;
                color: white;
                border-radius: 4px;
                padding: 4px 8px;
                min-width: 60px;
                font-size: 11px;
                border: none;
            }
            QPushButton#dangerButton:hover {
                background-color: #E53935;
            }
            QPushButton#downloadButton {
                background-color: #4CAF50;
                color: white;
                border-radius: 4px;
                padding: 4px 8px;
                min-width: 60px;
                font-size: 11px;
                border: none;
            }
            QPushButton#downloadButton:hover {
                background-color: #43A047;
            }
        """)
        
        self.setMinimumHeight(90)
        self.setMaximumHeight(90)
        
        self.init_ui()

        # Enable mouse click events
        self.setCursor(Qt.PointingHandCursor)
        self.mousePressEvent = self.on_item_clicked  # Connect the click event to the handler

        
    def init_ui(self):
        """Initialize the user interface with enhanced visual elements"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        
        # Information container with improved layout
        info_container = QVBoxLayout()
        info_container.setSpacing(5)
        
        # First row: title with visual prominence
        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        
        # Title with icon
        record_name = getattr(self.recording, 'name', 'Unnamed Recording')
        title = QLabel(f"{record_name}")
        title.setObjectName("recordingTitle")
        title_row.addWidget(title)
        
        title_row.addStretch()
        
        # Date and time with calendar icon styling
        date_time_container = QHBoxLayout()
        date_time_container.setSpacing(5)
        
        date_time = QLabel(self.recording.start_time.strftime("%d/%m/%Y %H:%M:%S"))
        date_time.setObjectName("recordingDateTime")
        date_time_container.addWidget(date_time)
        
        title_row.addLayout(date_time_container)
        info_container.addLayout(title_row)
        
        # Divider for visual separation
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setFrameShadow(QFrame.Sunken)
        divider.setStyleSheet("background-color: #E0E0E0; max-height: 1px; margin-top: 3px; margin-bottom: 3px;")
        info_container.addWidget(divider)
        
        # Details row with icons for better visual hierarchy
        details_row = QHBoxLayout()
        details_row.setSpacing(15)
        
        # Camera with icon
        camera_name = self.recording.camera.name if self.recording.camera else "Unknown Camera"
        camera = QLabel(f"📹 {camera_name}")
        camera.setObjectName("recordingDetail")
        details_row.addWidget(camera)
        
        # Duration with icon
        duration_text = "--:--:--"
        if self.recording.duration:
            minutes, seconds = divmod(int(self.recording.duration), 60)
            hours, minutes = divmod(minutes, 60)
            duration_text = f"{hours:02}:{minutes:02}:{seconds:02}"
        duration = QLabel(f"⏱️ {duration_text}")
        duration.setObjectName("recordingDetail")
        details_row.addWidget(duration)
        
        # Resolution with icon
        resolution = QLabel(f"🔍 {self.recording.resolution or 'Unknown'}")
        resolution.setObjectName("recordingDetail")
        details_row.addWidget(resolution)
        
        details_row.addStretch()
        info_container.addLayout(details_row)
        
        layout.addLayout(info_container)
        layout.setStretch(1, 1)  # Give the info section more stretch
        
        # Actions container with modern button styling
        actions_container = QVBoxLayout()
        actions_container.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        actions_container.setSpacing(8)
        
        # Action buttons with improved layout
        actions_row = QHBoxLayout()
        actions_row.setSpacing(6)
        
        
        # Download button
        self.download_button = QPushButton("Download")
        self.download_button.setObjectName("downloadButton")
        self.download_button.setCursor(Qt.PointingHandCursor)
        self.download_button.clicked.connect(self.on_download_clicked)
        actions_row.addWidget(self.download_button)
        
        # Delete button
        self.delete_button = QPushButton("Delete")
        self.delete_button.setObjectName("dangerButton")
        self.delete_button.setCursor(Qt.PointingHandCursor)
        self.delete_button.clicked.connect(self.on_delete_clicked)
        actions_row.addWidget(self.delete_button)
        
        actions_container.addLayout(actions_row)
        layout.addLayout(actions_container)

    def on_item_clicked(self, event):
        """Handle click on the recording item"""
        try:
            self.playback_screen.play_recording(self.recording.id)  # Call play_recording on click
        except Exception as e:
            logger.error(f"Error while playing recording: {e}")
            QMessageBox.critical(self, "Error", "Failed to play the recording. Please try again.")    
        
    def on_view_clicked(self):
        """Handle click on the view button"""
        try:
            self.playback_screen.play_recording(self.recording.id)  # Use the reference to call play_recording
        except Exception as e:
            logger.error(f"Error while viewing recording: {e}")
            QMessageBox.critical(self, "Error", "Failed to view the recording. Please try again.")
        
    def on_download_clicked(self):
        """Handle click on the download button"""
        self.playback_screen.download_recording(self.recording.id)
        
    def on_delete_clicked(self):
        """Handle click on the delete button"""
        self.playback_screen.delete_recording(self.recording.id)

class VideoPlaybackThread(QThread):
    """Thread to handle video playback to avoid blocking the main thread."""
    playback_started = pyqtSignal(str)

    def __init__(self, recording_path):
        super().__init__()
        self.recording_path = recording_path

    def run(self):
        # Emit signal to start playback
        self.playback_started.emit(self.recording_path)

class PlaybackScreen(QWidget):
    def __init__(self, user_data=None, ros_node=None):
        super().__init__()
        self.user_data = user_data
        self.ros_node = ros_node
        self.db_session = get_session()  # Obtain a database session
        self.camera_service = CameraService(db_session=self.db_session)
        self.storage_service = StorageService()
        
        # Connecter le signal de nouvel enregistrement
        self.storage_service.recording_added.connect(self.on_new_recording)
        
        # State and configuration
        self.current_page = 1
        self.recordings_per_page = 5
        self.date_filter = None
        self.camera_filter = None
        self.search_text = ""
        
        self.init_ui()
        
        # Load initial data
        self.load_recordings()
    
    def init_ui(self):
        """Initialize the user interface components with modern surveillance-style UI"""
        # Main container widget for scrollable content
        content_widget = QWidget()
        content_widget.setObjectName("mainContentWidget")
        # Use a darker background for professional surveillance look
        content_widget.setStyleSheet("QWidget#mainContentWidget { background-color: rgba(240, 240, 245, 0.7); border-radius: 8px; border: 1px solid rgba(220, 220, 225, 0.9);}")
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(15, 15, 15, 15)
        content_layout.setSpacing(10)  # Reduced spacing for tighter layout

        # Main layout with a splitter for dynamic layout adjustment
        main_splitter = QSplitter(Qt.Horizontal)  # Changed to horizontal for side-by-side view
        main_splitter.setObjectName("mainSplitter")
        main_splitter.setHandleWidth(1)  # Thinner splitter handle
        main_splitter.setChildrenCollapsible(False)  # Prevent sections from collapsing
        main_splitter.setStyleSheet("""
            QSplitter#mainSplitter {
                background-color: rgba(240, 240, 245, 0.7);
            }
        """)

        # Left section: Filters and recordings list
        left_section = QWidget()
        left_section.setObjectName("leftPanel")
        left_layout = QVBoxLayout(left_section)
        left_layout.setContentsMargins(0, 0, 10, 0)
        left_layout.setSpacing(10)

        # Title for the recordings panel
        recordings_title = QLabel("Incident Recordings")
        recordings_title.setObjectName("panelTitle")
        recordings_title.setStyleSheet("QLabel#panelTitle { font-size: 16px; font-weight: bold; color: #333333; margin-bottom: 5px; }")
        left_layout.addWidget(recordings_title)

        # Filter elements section with modern styling
        filter_frame = QFrame()
        filter_frame.setObjectName("filterFrame")
        filter_frame.setStyleSheet("""
            QFrame#filterFrame {
                background-color: white;
                border-radius: 6px;
                border: 1px solid #e0e0e0;
            }
        """)
        filter_layout = QVBoxLayout(filter_frame)  # Changed to vertical for better mobile responsiveness
        filter_layout.setContentsMargins(12, 12, 12, 12)
        filter_layout.setSpacing(10)

        # Search input with icon styling
        search_container = QHBoxLayout()
        search_icon = QLabel()
        """ search_icon.setPixmap(QIcon.fromTheme("search").pixmap(16, 16))
        search_container.addWidget(search_icon) """
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search recordings...")
        self.search_input.setObjectName("roundedSearchBox")
        self.search_input.setStyleSheet("""
            QLineEdit#roundedSearchBox:focus {
                border: 1px solid #2196F3;
                background-color: white;
            }
        """)
        self.search_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.search_input.textChanged.connect(self.on_search_changed)
        search_container.addWidget(self.search_input)
        filter_layout.addLayout(search_container)

        # Filter controls in a grid for better organization
        filter_grid = QGridLayout()
        filter_grid.setHorizontalSpacing(10)
        filter_grid.setVerticalSpacing(10)

        # Camera filter with improved styling
        camera_label = QLabel("Camera:")
        camera_label.setStyleSheet("font-weight: 500; color: #333333; background-color: white;")
        filter_grid.addWidget(camera_label, 0, 0)
        
        self.camera_combo = QComboBox()
        self.camera_combo.setObjectName("filterCombo")
        self.camera_combo.setStyleSheet("""
            QComboBox#filterCombo {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                padding: 5px;
                background-color: white;
            }
            QComboBox#filterCombo:hover {
                border-color: #BBDEFB;
            }
        """)
        self.camera_combo.addItem("All Cameras", None)
        self.camera_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # Add cameras to the combo box
        cameras = self.camera_service.get_all_cameras()
        for camera in cameras:
            self.camera_combo.addItem(camera.name, camera.id)

        self.camera_combo.currentIndexChanged.connect(self.on_camera_filter_changed)
        filter_grid.addWidget(self.camera_combo, 0, 1)

        # Date filter with calendar icon and improved styling
        date_label = QLabel("Date:")
        date_label.setStyleSheet("font-weight: 500; color: #333333; background-color: white;")
        filter_grid.addWidget(date_label, 1, 0)
        
        date_container = QHBoxLayout()
        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setObjectName("dateFilter")
        self.date_edit.setStyleSheet("""
            QDateEdit#dateFilter {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                padding: 5px;
                background-color: white;
            }
            QDateEdit#dateFilter:hover {
                border-color: #BBDEFB;
            }
        """)
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd/MM/yyyy")
        self.date_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.date_edit.dateChanged.connect(self.on_date_filter_changed)
        date_container.addWidget(self.date_edit)
        date_container.setStretch(0, 1)
        filter_grid.addLayout(date_container, 1, 1)

        filter_layout.addLayout(filter_grid)

        # Reset filters button with modern styling
        self.reset_button = QPushButton("Reset Filters")
        self.reset_button.setObjectName("resetButton")
        self.reset_button.setStyleSheet("""
            QPushButton#resetButton {
                background-color: #f5f5f5;
                color: #555;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: normal;
            }
            QPushButton#resetButton:hover {
                background-color: #e0e0e0;
                border-color: #bbb;
            }
        """)
        self.reset_button.clicked.connect(self.reset_filters)
        filter_layout.addWidget(self.reset_button)

        # Add filter frame to the left layout
        left_layout.addWidget(filter_frame)

        # Recordings section with improved styling
        recordings_frame = QFrame()
        recordings_frame.setObjectName("recordingsFrame")
        recordings_frame.setStyleSheet("""
            QFrame#recordingsFrame {
                background-color: white;
                border-radius: 6px;
                border: 1px solid #e0e0e0;
            }
        """)
        recordings_layout = QVBoxLayout(recordings_frame)
        recordings_layout.setContentsMargins(12, 12, 12, 12)
        recordings_layout.setSpacing(8)

        # Recording count indicator
        recordings_header = QHBoxLayout()
        recordings_count = QLabel("Recordings")
        recordings_count.setObjectName("sectionHeader")
        recordings_count.setStyleSheet("""
            QLabel#sectionHeader {
                font-size: 14px;
                font-weight: bold;
                color: #333333;
                background-color: background-color: white;
            }
        """)
        recordings_header.addWidget(recordings_count)
        
        recordings_header.addStretch()
        recordings_layout.addLayout(recordings_header)

        # Recordings scroll area with improved styling
        self.recordings_scroll = QScrollArea()
        self.recordings_scroll.setObjectName("recordingsScroll")
        self.recordings_scroll.setStyleSheet("""
            QScrollArea#recordingsScroll {
                border: none;
                background-color: transparent;
            }
        """)
        self.recordings_scroll.setWidgetResizable(True)
        self.recordings_scroll.setFrameShape(QFrame.NoFrame)
        self.recordings_scroll.setMinimumHeight(350)  # Increased height for better visibility

        self.recordings_container = QWidget()
        self.recordings_container.setObjectName("recordingsContainer")
        self.recordings_container.setStyleSheet("""
            QWidget#recordingsContainer {
                background-color: transparent;
            }
        """)
        self.recordings_list = QVBoxLayout(self.recordings_container)
        self.recordings_list.setAlignment(Qt.AlignTop)
        self.recordings_list.setSpacing(8)
        self.recordings_list.setContentsMargins(0, 0, 0, 0)

        self.recordings_scroll.setWidget(self.recordings_container)
        recordings_layout.addWidget(self.recordings_scroll)

        # Pagination with modern button styling
        pagination = QHBoxLayout()
        pagination.setObjectName("paginationSection")
        pagination.setAlignment(Qt.AlignCenter)

        self.prev_button = QPushButton("<")
        self.prev_button.setObjectName("pageButton")
        self.prev_button.setStyleSheet("""
            QPushButton#pageButton {
                background-color: #f5f5f5;
                color: #333;
                border: 1px solid #ddd;
                border-radius: 15px;
                min-width: 30px;
                max-width: 30px;
                min-height: 30px;
                max-height: 30px;
                padding: 0px;
                font-weight: bold;
            }
            QPushButton#pageButton:hover {
                background-color: #e0e0e0;
            }
            QPushButton#pageButton:disabled {
                color: #aaa;
                background-color: #f8f8f8;
                border-color: #eee;
            }
        """)
        self.prev_button.clicked.connect(self.previous_page)
        pagination.addWidget(self.prev_button)

        self.page_buttons_layout = QHBoxLayout()
        self.page_buttons_layout.setSpacing(5)
        pagination.addLayout(self.page_buttons_layout)

        self.next_button = QPushButton(">")
        self.next_button.setObjectName("pageButton")
        self.next_button.setStyleSheet("""
            QPushButton#pageButton {
                background-color: #f5f5f5;
                color: #333;
                border: 1px solid #ddd;
                border-radius: 15px;
                min-width: 30px;
                max-width: 30px;
                min-height: 30px;
                max-height: 30px;
                padding: 0px;
                font-weight: bold;
            }
            QPushButton#pageButton:hover {
                background-color: #e0e0e0;
            }
            QPushButton#pageButton:disabled {
                color: #aaa;
                background-color: #f8f8f8;
                border-color: #eee;
            }
        """)
        self.next_button.clicked.connect(self.next_page)
        pagination.addWidget(self.next_button)

        recordings_layout.addLayout(pagination)
        left_layout.addWidget(recordings_frame)
        
        # Right section: Video player and details with improved styling
        right_section = QWidget()
        right_section.setObjectName("rightPanel") 
        right_layout = QVBoxLayout(right_section)
        right_layout.setContentsMargins(10, 0, 0, 0)
        right_layout.setSpacing(10)
        
        # Title for the playback panel
        playback_title = QLabel("Video Playback")
        playback_title.setObjectName("panelTitle")
        playback_title.setStyleSheet("QLabel#panelTitle { font-size: 16px; font-weight: bold; color: #333333; margin-bottom: 5px; }")
        right_layout.addWidget(playback_title)

        # Video player section with modern styling
        player_frame = QFrame()
        player_frame.setObjectName("playerFrame")
        player_frame.setStyleSheet("""
            QFrame#playerFrame {
                background-color: #1e1e1e; /* Dark background like pro surveillance systems */
                border-radius: 6px;
                border: 1px solid #333;
            }
        """)
        player_layout = QVBoxLayout(player_frame)
        player_layout.setContentsMargins(1, 1, 1, 1)  # Minimal margins for maximum video space
        player_layout.setSpacing(0)  # No spacing for professional look

        self.video_player = VideoPlayerWidget()  # Use the optimized VideoPlayerWidget
        self.video_player.setVisible(False)
        self.video_player.setObjectName("videoDisplay")
        self.video_player.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_player.setMinimumHeight(400)
        player_layout.addWidget(self.video_player)
        
        right_layout.addWidget(player_frame, 1)  # Add stretch factor for responsive sizing

        # Video details section with modern card styling
        # Details card with modern styling
        self.details_popup = QFrame()
        self.details_popup.setObjectName("detailsPopup")
        self.details_popup.setStyleSheet("""
            QFrame#detailsPopup {
                background-color: white;
                border-radius: 6px;
                border: 1px solid #e0e0e0;
            }
            QLabel#detailLabel {
                color: #546E7A;
                font-weight: 500;
            }
            QLabel#detailValue {
                color: #263238;
                font-weight: normal;
            }
        """)
        self.details_popup.setVisible(False)
        self.details_popup.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        
        details_layout = QVBoxLayout(self.details_popup)
        details_layout.setContentsMargins(15, 15, 15, 15)
        details_layout.setSpacing(10)

        # Header with icon
        header_layout = QHBoxLayout()
        details_icon = QLabel()
        # You could set an icon here if available
        # details_icon.setPixmap(QIcon.fromTheme("document-properties").pixmap(16, 16))
        header_layout.addWidget(details_icon)
        
        details_header = QLabel("Recording Details")
        details_header.setObjectName("sectionHeader")
        details_header.setStyleSheet("""
            QLabel#sectionHeader {
                font-size: 14px;
                font-weight: bold;
                color: #2c3e50;
                background-color: rgba(240, 240, 245, 0.7);
            }
        """)
        details_header.setAlignment(Qt.AlignLeft)
        header_layout.addWidget(details_header)
        header_layout.addStretch()
        
        details_layout.addLayout(header_layout)
        
        # Separator line for visual distinction
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("background-color: #e0e0e0; min-height: 1px; max-height: 1px;")
        details_layout.addWidget(separator)

        # Details grid with improved styling and organization
        details_grid = QGridLayout()
        details_grid.setHorizontalSpacing(20)
        details_grid.setVerticalSpacing(8)
        
        # Left column
        left_labels = ["Date:", "Camera:"]
        self.details_values = [
            QLabel("--/--/----"),  # Date
            QLabel("--"),          # Camera
            QLabel("----x----"),   # Resolution
            QLabel("--:--:--"),    # Duration
            QLabel("-- MB"),       # Size
        ]
        
        # Style all value labels
        for value in self.details_values:
            value.setObjectName("detailValue")
            value.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        
        # Left column setup
        for i, label_text in enumerate(left_labels):
            label = QLabel(label_text)
            label.setObjectName("detailLabel")
            label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            details_grid.addWidget(label, i, 0)
            details_grid.addWidget(self.details_values[i], i, 1)
        
        # Right column
        right_labels = ["Resolution:", "Duration:", "Size:"]
        for i, label_text in enumerate(right_labels):
            label = QLabel(label_text)
            label.setObjectName("detailLabel")
            label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            details_grid.addWidget(label, i, 2)
            details_grid.addWidget(self.details_values[i+2], i, 3)

        details_layout.addLayout(details_grid)
        right_layout.addWidget(self.details_popup)

        # Add sections to the main splitter
        main_splitter.addWidget(left_section)
        main_splitter.addWidget(right_section)
        main_splitter.setStretchFactor(0, 1)  # Left panel (recordings list)
        main_splitter.setStretchFactor(1, 2)  # Right panel (video player) gets more space
        
        # Add splitter to the content layout
        content_layout.addWidget(main_splitter)
        
        # Main scroll area with improved styling
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(content_widget)
        scroll_area.setObjectName("playbackScrollArea")
        scroll_area.setStyleSheet("""
            QScrollArea#playbackScrollArea {
                border: none;
                background-color: transparent;
            }
        """)

        # Main layout - use entire window space with no margins
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(scroll_area)
        
        # Set overall styling for the playback screen
        self.setStyleSheet("""
            QWidget {
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QLabel#panelTitle {
                font-size: 16px;
                font-weight: bold;
                color: #2c3e50;
                margin-bottom: 5px;
            }
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            #activePageButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 15px;
                min-width: 30px;
                max-width: 30px;
                min-height: 30px;
                max-height: 30px;
                font-weight: bold;
            }
            QComboBox::down-arrow {
                image: url('path/to/dropdown-arrow.png');
                width: 12px;
                height: 12px;
            }
            QDateEdit::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: center right;
                width: 15px;
                border-left: none;
            }
            QFrame#mainSplitter::handle {
                background-color: #e0e0e0;
            }
            QLabel#noRecordings {
                color: #9e9e9e;
                font-style: italic;
                padding: 20px;
                font-size: 14px;
            }
        """)
        self.setLayout(layout)
    
    def create_page_button(self, page_num, is_active=False):
        """Create a modern, circular pagination button"""
        btn = QPushButton(str(page_num))
        btn.setFixedSize(30, 30)
        btn.setCursor(Qt.PointingHandCursor)
        
        if is_active:
            btn.setObjectName("activePageButton")
            btn.setStyleSheet("""
                QPushButton#activePageButton {
                    background-color: #2196F3;
                    color: white;
                    border: none;
                    border-radius: 15px;
                    font-weight: bold;
                    min-width: 30px;
                    max-width: 30px;
                    min-height: 30px;
                    max-height: 30px;
                }
            """)
        else:
            btn.setObjectName("pageButton")
            btn.setStyleSheet("""
                QPushButton#pageButton {
                    background-color: #f5f5f5;
                    color: #333;
                    border: 1px solid #ddd;
                    border-radius: 15px;
                    min-width: 30px;
                    max-width: 30px;
                    min-height: 30px;
                    max-height: 30px;
                }
                QPushButton#pageButton:hover {
                    background-color: #e0e0e0;
                    border-color: #ccc;
                }
            """)
        
        btn.clicked.connect(lambda: self.go_to_page(page_num))
        
        return btn
    
    def update_pagination(self, total_recordings):
        """Update pagination buttons based on the total number of recordings"""
        # Clear existing buttons
        while self.page_buttons_layout.count():
            item = self.page_buttons_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        
        # Calculate the total number of pages
        total_pages = max(1, (total_recordings + self.recordings_per_page - 1) // self.recordings_per_page)
        
        # Enable/disable navigation buttons
        self.prev_button.setEnabled(self.current_page > 1)
        self.next_button.setEnabled(self.current_page < total_pages)
        
        # Create page buttons
        if total_pages <= 7:
            for i in range(1, total_pages + 1):
                self.page_buttons_layout.addWidget(self.create_page_button(i, i == self.current_page))
        else:
            # Show a subset of pages
            self.page_buttons_layout.addWidget(self.create_page_button(1, 1 == self.current_page))
            
            start_page = max(2, self.current_page - 2)
            end_page = min(total_pages - 1, self.current_page + 2)
            
            if start_page > 2:
                ellipsis = QLabel("...")
                ellipsis.setAlignment(Qt.AlignCenter)
                self.page_buttons_layout.addWidget(ellipsis)
            
            for i in start_page, end_page + 1:
                self.page_buttons_layout.addWidget(self.create_page_button(i, i == self.current_page))
            
            if end_page < total_pages - 1:
                ellipsis = QLabel("...")
                ellipsis.setAlignment(Qt.AlignCenter)
                self.page_buttons_layout.addWidget(ellipsis)
            
            self.page_buttons_layout.addWidget(self.create_page_button(total_pages, total_pages == self.current_page))
    
    def load_recordings(self):
        """Load and display recordings based on filters and pagination"""
        try:
            # Calculate the offset for pagination
            offset = (self.current_page - 1) * self.recordings_per_page

            # Convert the date filter to a Python date object if necessary
            date_filter = self.date_filter.toPyDate() if self.date_filter else None

            # Get the total number of recordings (for pagination)
            all_recordings = self.storage_service.get_recordings(
                camera_id=self.camera_filter,
                start_date=date_filter,
                search_term=self.search_text
            )
            total_recordings = len(all_recordings)

            # Get the recordings for the current page
            recordings = self.storage_service.get_recordings(
                limit=self.recordings_per_page,
                offset=offset,
                camera_id=self.camera_filter,
                start_date=date_filter,
                search_term=self.search_text
            )
            
            # Clear existing recordings
            self.clear_layout(self.recordings_list)
            
            # Add recording items to the list
            if recordings:
                for recording in recordings:
                    recording_item = RecordingItem(recording, self)
                    self.recordings_list.addWidget(recording_item)
            else:
                no_recordings = QLabel("Aucun enregistrement trouvé")
                no_recordings.setAlignment(Qt.AlignCenter)
                no_recordings.setObjectName("noRecordings")
                self.recordings_list.addWidget(no_recordings)
            
            # Update pagination
            self.update_pagination(total_recordings)
        except Exception as e:
            logger.error(f"Error loading recordings: {e}")
            QMessageBox.critical(self, "Error", "An error occurred while loading recordings. Please try again later.")

    def play_recording(self, recording_id):
        """Play a recording"""
        try:
            recording = self.storage_service.get_recording(recording_id)
            if recording and os.path.exists(recording.file_path):
                absolute_path = os.path.abspath(recording.file_path)
                logger.info(f"Absolute video path: {absolute_path}")

                # Use a thread to handle video playback
                self.video_thread = VideoPlaybackThread(absolute_path)
                self.video_thread.playback_started.connect(self.start_video_playback)
                self.video_thread.start()

                # Show the details popup
                self.details_popup.setVisible(True)
                self.update_details(recording)
            else:
                raise FileNotFoundError(f"Video file not found: {recording.file_path if recording else 'None'}")
        except Exception as e:
            logger.error(f"Error while playing recording: {e}")
            QMessageBox.critical(self, "Error", "Unable to play the video. Please check the file and try again.")

    def start_video_playback(self, file_path):
        """Start video playback in the video player."""
        self.video_player.set_source(file_path)
        self.video_player.setVisible(True)
        self.video_player.play()
    
    def update_details(self, recording):
        """Update the recording details display"""
        if recording:
            self.details_values[0].setText(recording.start_time.strftime("%d/%m/%Y %H:%M:%S"))
            self.details_values[1].setText(recording.camera.name if recording.camera else "Unknown")
            self.details_values[2].setText(recording.resolution or "Unknown")
            if recording.duration:
                minutes, seconds = divmod(int(recording.duration), 60)
                hours, minutes = divmod(minutes, 60)
                self.details_values[3].setText(f"{hours:02}:{minutes:02}:{seconds:02}")
            else:
                self.details_values[3].setText("--:--:--")
            if recording.size:
                size_mb = recording.size / (1024 * 1024)  # Convert bytes to MB
                self.details_values[4].setText(f"{size_mb:.2f} MB")
            else:
                self.details_values[4].setText("-- MB")
            
        self.details_popup.setVisible(True)  # Ensure the details popup is visible
    
    def download_recording(self, recording_id):
        """Download a recording"""
        try:
            # Récupérer l'enregistrement depuis le service de stockage
            recording = self.storage_service.get_recording(recording_id)
            if not recording or not os.path.exists(recording.file_path):
                raise FileNotFoundError("The recording file does not exist.")

            # Ouvrir une boîte de dialogue pour sélectionner l'emplacement de téléchargement
            save_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Recording",
                os.path.basename(recording.file_path),
                "Video Files (*.mp4 *.avi *.mkv);;All Files (*)"
            )

            # Si l'utilisateur annule la boîte de dialogue, ne rien faire
            if not save_path:
                return

            # Copier le fichier vers l'emplacement sélectionné
            import shutil
            shutil.copy(recording.file_path, save_path)

            # Afficher un message de confirmation
            QMessageBox.information(
                self,
                "Download Complete",
                f"The recording has been successfully downloaded to:\n{save_path}"
            )
        except FileNotFoundError as e:
            logger.error(f"Download failed: {e}")
            QMessageBox.critical(
                self,
                "Download Error",
                "The recording file could not be found. Please check the file and try again."
            )
        except Exception as e:
            logger.error(f"An error occurred during the download: {e}")
            QMessageBox.critical(
                self,
                "Download Error",
                "An unexpected error occurred while downloading the recording. Please try again."
            )
    
    def delete_recording(self, recording_id):
        """Delete a recording"""
        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            "Are you sure you want to delete this recording?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            success = self.storage_service.delete_recording(recording_id)
            if success:
                QMessageBox.information(self, "Success", "Recording deleted successfully.")
                self.load_recordings()
            else:
                QMessageBox.warning(self, "Error", "Failed to delete the recording.")
    
    def previous_page(self):
        """Navigate to the previous page of recordings"""
        if self.current_page > 1:
            self.current_page -= 1
            self.load_recordings()

    def next_page(self):
        """Navigate to the next page of recordings"""
        self.current_page += 1
        self.load_recordings()

    def go_to_page(self, page_num):
        """Navigate to a specific page of recordings"""
        self.current_page = page_num
        self.load_recordings()

    def reset_filters(self):
        """Reset all filters and reload recordings"""
        self.date_filter = None
        self.camera_filter = None
        self.search_text = ""
        self.search_input.clear()
        self.camera_combo.setCurrentIndex(0)  # Reset to "All"
        self.date_edit.setDate(QDate.currentDate())  # Reset to today's date
        self.load_recordings()

    def on_search_changed(self, text):
        """Handle changes in the search input"""
        self.search_text = text
        self.load_recordings()

    def on_camera_filter_changed(self, index):
        """Handle changes in the camera filter"""
        self.camera_filter = self.camera_combo.itemData(index)
        self.load_recordings()

    def on_date_filter_changed(self, date):
        """Handle changes in the date filter"""
        self.date_filter = date  # Ensure the date is stored as a QDate object
        self.load_recordings()

    def clear_layout(self, layout):
        """Remove all widgets from a given layout"""
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
            else:
                sub_layout = item.layout()
                if sub_layout:
                    self.clear_layout(sub_layout)

    def on_new_recording(self, recording_id):
        """Méthode appelée quand un nouvel enregistrement est ajouté"""
        logger.info(f"New recording notification received: ID={recording_id}")
        
        # Si on est sur la première page, actualiser immédiatement
        if self.current_page == 1:
            self.load_recordings()
            
            # Afficher une notification à l'utilisateur
            recording = self.storage_service.get_recording(recording_id)
            if recording:
                class_name = recording.name
                camera_name = recording.camera.name if recording.camera else "Unknown"
                
                notification_label = QLabel(f"Nouveau {class_name} détecté par {camera_name}")
                notification_label.setObjectName("newRecordingNotification")
                notification_label.setStyleSheet("""
                    background-color: #2196F3;
                    color: white;
                    padding: 8px;
                    border-radius: 4px;
                    font-weight: bold;
                """)
                
                # Ajouter la notification au début de la liste
                if self.recordings_list.count() > 0:
                    self.recordings_list.insertWidget(0, notification_label)
                else:
                    self.recordings_list.addWidget(notification_label)
                
                # Timer pour effacer la notification après 5 secondes
                QTimer.singleShot(5000, lambda: notification_label.deleteLater())

class VideoPlayerWidget(QWidget):
    """Professional Video Player Widget with surveillance-style controls."""
    def __init__(self):
        super().__init__()
        self.mediaPlayer = QMediaPlayer()
        self.playlist = QMediaPlaylist()
        self.mediaPlayer.setPlaylist(self.playlist)

        # Configure video display
        self.videoItem = QGraphicsVideoItem()
        self.videoItem.setAspectRatioMode(Qt.KeepAspectRatio)

        # Create scene and view with professional styling
        scene = QGraphicsScene(self)
        scene.setBackgroundBrush(Qt.black)  # Black background like professional CCTV
        
        self.graphicsView = QGraphicsView(scene)
        self.graphicsView.setFrameShape(QFrame.NoFrame)  # Remove frame for seamless look
        self.graphicsView.setMinimumHeight(450)
        self.graphicsView.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.graphicsView.setStyleSheet("""
            QGraphicsView {
                background-color: #000000;
                border: none;
            }
        """)
        
        # Add video item to scene
        scene.addItem(self.videoItem)
        self.mediaPlayer.setVideoOutput(self.videoItem)
        
        # Initialize timestamp display
        self.timestampLabel = QLabel("00:00:00")
        self.timestampLabel.setStyleSheet("""
            QLabel {
                color: white;
                background-color: rgba(0, 0, 0, 0.7);
                padding: 3px 8px;
                border-radius: 3px;
                font-family: monospace;
            }
        """)
        self.durationLabel = QLabel("00:00:00")
        self.durationLabel.setStyleSheet("""
            QLabel {
                color: white;
                background-color: rgba(0, 0, 0, 0.7);
                padding: 3px 8px;
                border-radius: 3px;
                font-family: monospace;
            }
        """)
        
        # Initialize position slider
        self.positionSlider = QSlider(Qt.Horizontal)
        self.positionSlider.setRange(0, 0)
        self.positionSlider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #999999;
                height: 4px;
                background: #4d4d4d;
                margin: 2px 0;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #2196F3;
                border: none;
                width: 10px;
                height: 10px;
                margin: -4px 0;
                border-radius: 5px;
            }
            QSlider::sub-page:horizontal {
                background: #2196F3;
            }
        """)
        
        # Timer for position updates
        self.timer = QTimer(self)
        self.timer.setInterval(100)  # Update every 100ms
        self.timer.timeout.connect(self.update_position)
        
        self.init_ui()

    def init_ui(self):
        """Initialize UI with professional surveillance system style"""
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # Video display area
        layout.addWidget(self.graphicsView, 1)  # Give most space to the video

        # Controls area with dark theme
        controls_frame = QFrame()
        controls_frame.setObjectName("controlsFrame")
        controls_frame.setStyleSheet("""
            QFrame#controlsFrame {
                background-color: #1e1e1e;
                border-radius: 4px;
                padding: 2px;
            }
            QPushButton {
                background-color: #333333;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 5px;
                min-width: 30px;
                max-width: 30px;
                min-height: 24px;
                max-height: 24px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #555555;
            }
            QPushButton:pressed {
                background-color: #2196F3;
            }
            QPushButton:checked {
                background-color: #2196F3;
            }
            QPushButton#actionButton {
                min-width: 60px;
                max-width: 60px;
            }
            QLabel {
                color: white;
                font-size: 11px;
            }
        """)
        
        controls_layout = QVBoxLayout(controls_frame)
        controls_layout.setContentsMargins(8, 5, 8, 5)
        controls_layout.setSpacing(5)
        
        # Timeline section with timestamp displays
        timeline_layout = QHBoxLayout()
        timeline_layout.setSpacing(5)
        
        # Current position timestamp
        timeline_layout.addWidget(self.timestampLabel)
        
        # Playback position slider
        timeline_layout.addWidget(self.positionSlider, 1)
        self.positionSlider.sliderMoved.connect(self.set_position)
        self.mediaPlayer.durationChanged.connect(self.update_duration)
        self.mediaPlayer.positionChanged.connect(self.position_changed)
        
        # Total duration timestamp
        timeline_layout.addWidget(self.durationLabel)
        
        controls_layout.addLayout(timeline_layout)
        
        # Control buttons with modern icons
        controls_row = QHBoxLayout()
        controls_row.setSpacing(5)
        
        # Play/Pause button
        self.playButton = QPushButton("▶")
        self.playButton.setToolTip("Play/Pause")
        self.playButton.setCursor(Qt.PointingHandCursor)
        self.playButton.clicked.connect(self.toggle_play)
        controls_row.addWidget(self.playButton)
        
        # Stop button
        self.stopButton = QPushButton("■")
        self.stopButton.setToolTip("Stop")
        self.stopButton.setCursor(Qt.PointingHandCursor)
        self.stopButton.clicked.connect(self.stop)
        controls_row.addWidget(self.stopButton)
        
        # Skip back button
        self.skipBackButton = QPushButton("⏪")
        self.skipBackButton.setToolTip("Back 5 seconds")
        self.skipBackButton.setCursor(Qt.PointingHandCursor)
        self.skipBackButton.clicked.connect(lambda: self.skip(-5000))
        controls_row.addWidget(self.skipBackButton)
        
        # Frame by frame back button
        self.frameBackButton = QPushButton("◀|")
        self.frameBackButton.setToolTip("Previous frame")
        self.frameBackButton.setCursor(Qt.PointingHandCursor)
        self.frameBackButton.clicked.connect(lambda: self.skip(-200))
        controls_row.addWidget(self.frameBackButton)
        
        # Frame by frame forward button
        self.frameForwardButton = QPushButton("|▶")
        self.frameForwardButton.setToolTip("Next frame")
        self.frameForwardButton.setCursor(Qt.PointingHandCursor)
        self.frameForwardButton.clicked.connect(lambda: self.skip(200))
        controls_row.addWidget(self.frameForwardButton)
        
        # Skip forward button
        self.skipForwardButton = QPushButton("⏩")
        self.skipForwardButton.setToolTip("Forward 5 seconds")
        self.skipForwardButton.setCursor(Qt.PointingHandCursor)
        self.skipForwardButton.clicked.connect(lambda: self.skip(5000))
        controls_row.addWidget(self.skipForwardButton)
        
        controls_row.addStretch(1)  # Add space between control groups
        
        # Volume control
        volume_layout = QHBoxLayout()
        
        volume_icon = QLabel("🔊")
        volume_icon.setStyleSheet("margin-right: 3px;")
        volume_layout.addWidget(volume_icon)
        
        self.volumeSlider = QSlider(Qt.Horizontal)
        self.volumeSlider.setRange(0, 100)
        self.volumeSlider.setValue(50)
        self.volumeSlider.setFixedWidth(80)
        self.volumeSlider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #777777;
                height: 3px;
                background: #555555;
                margin: 0px;
                border-radius: 1px;
            }
            QSlider::handle:horizontal {
                background: #2196F3;
                border: none;
                width: 8px;
                height: 8px;
                margin: -3px 0;
                border-radius: 4px;
            }
            QSlider::sub-page:horizontal {
                background: #2196F3;
            }
        """)
        self.volumeSlider.valueChanged.connect(self.mediaPlayer.setVolume)
        volume_layout.addWidget(self.volumeSlider)
        
        controls_row.addLayout(volume_layout)
        controls_row.addStretch(1)  # Add space between control groups
        
        # Advanced controls
        # Speed button with dropdown menu
        self.speedButton = QPushButton("1×")
        self.speedButton.setObjectName("actionButton")
        self.speedButton.setToolTip("Playback Speed")
        self.speedButton.setCursor(Qt.PointingHandCursor)
        
        self.speedMenu = QMenu()
        self.speedMenu.setStyleSheet("""
            QMenu {
                background-color: #2c2c2c;
                border: 1px solid #444444;
                color: white;
            }
            QMenu::item {
                padding: 5px 15px;
            }
            QMenu::item:selected {
                background-color: #2196F3;
            }
        """)
        
        for speed in ["0.25×", "0.5×", "0.75×", "1×", "1.25×", "1.5×", "2×"]:
            action = self.speedMenu.addAction(speed)
            action.triggered.connect(lambda checked, s=speed: self.set_playback_speed(s))
        
        self.speedButton.setMenu(self.speedMenu)
        controls_row.addWidget(self.speedButton)
        
        # Aspect ratio toggle
        self.aspectRatioButton = QPushButton("◫")
        self.aspectRatioButton.setObjectName("actionButton")
        self.aspectRatioButton.setCheckable(True)
        self.aspectRatioButton.setToolTip("Toggle Aspect Ratio")
        self.aspectRatioButton.setCursor(Qt.PointingHandCursor)
        self.aspectRatioButton.toggled.connect(self.toggle_aspect_ratio)
        controls_row.addWidget(self.aspectRatioButton)
        
        # Full screen button
        self.fullscreenButton = QPushButton("⛶")
        self.fullscreenButton.setObjectName("actionButton")
        self.fullscreenButton.setToolTip("Toggle Fullscreen")
        self.fullscreenButton.setCursor(Qt.PointingHandCursor)
        # In a real implementation, you would connect this to a fullscreen toggle
        controls_row.addWidget(self.fullscreenButton)
        
        controls_layout.addLayout(controls_row)
        layout.addWidget(controls_frame)
        
        # Set up media player connections
        self.mediaPlayer.stateChanged.connect(self.media_state_changed)

    def toggle_play(self):
        """Toggle between play and pause states"""
        if self.mediaPlayer.state() == QMediaPlayer.PlayingState:
            self.mediaPlayer.pause()
        else:
            self.mediaPlayer.play()
            # Start the timer when playing
            self.timer.start()

    def media_state_changed(self, state):
        """Update UI based on media player state"""
        if state == QMediaPlayer.PlayingState:
            self.playButton.setText("❚❚")  # Pause symbol
            self.timer.start()  # Ensure timer is running
        else:
            self.playButton.setText("▶")  # Play symbol
            if state == QMediaPlayer.StoppedState:
                self.timer.stop()  # Stop timer when stopped

    def stop(self):
        """Stop playback and reset position"""
        self.mediaPlayer.stop()
        self.timer.stop()

    def skip(self, msec):
        """Skip forward or backward by the specified milliseconds"""
        self.mediaPlayer.setPosition(self.mediaPlayer.position() + msec)

    def update_position(self):
        """Update position labels and slider"""
        position = self.mediaPlayer.position()
        if position >= 0:
            self.positionSlider.setValue(position)
            self.update_timestamp_label(position)

    def position_changed(self, position):
        """Handle position change event from media player"""
        if not self.positionSlider.isSliderDown():
            self.positionSlider.setValue(position)
            self.update_timestamp_label(position)

    def update_timestamp_label(self, position):
        """Update the timestamp label with the current position"""
        seconds = position // 1000
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        self.timestampLabel.setText(f"{hours:02}:{minutes:02}:{seconds:02}")

    def update_duration(self, duration):
        """Update slider range and duration label when media duration changes"""
        self.positionSlider.setRange(0, duration)
        
        # Update duration label
        seconds = duration // 1000
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        self.durationLabel.setText(f"{hours:02}:{minutes:02}:{seconds:02}")

    def set_position(self, position):
        """Set media position when slider is moved"""
        self.mediaPlayer.setPosition(position)
        self.update_timestamp_label(position)

    def play(self):
        """Start media playback"""
        self.mediaPlayer.play()
        self.timer.start()

    def set_playback_speed(self, speed):
        """Set playback speed"""
        rate = float(speed[:-1])  # Remove the 'x' character
        self.mediaPlayer.setPlaybackRate(rate)
        self.speedButton.setText(speed)

    def toggle_aspect_ratio(self, checked):
        """Toggle between aspect ratio modes"""
        mode = Qt.KeepAspectRatio if checked else Qt.IgnoreAspectRatio
        self.videoItem.setAspectRatioMode(mode)

    def set_source(self, file_path):
        """Set the media source for playback"""
        self.playlist.clear()
        self.playlist.addMedia(QMediaContent(QUrl.fromLocalFile(file_path)))
        self.playlist.setCurrentIndex(0)
        self.mediaPlayer.play()
        
        # Start timer for position updates
        self.timer.start()