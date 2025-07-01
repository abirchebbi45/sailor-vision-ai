from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QFrame, QScrollArea, QLineEdit,
                             QToolButton, QComboBox, QSlider, QGridLayout,
                             QDateEdit, QMessageBox, QSplitter, QSizePolicy, QGraphicsScene, QGraphicsView, QMenu)
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
    """Widget representing a recording item in the list"""
    def __init__(self, recording, playback_screen):
        super().__init__()
        self.recording = recording
        self.playback_screen = playback_screen  # Store reference to PlaybackScreen
        self.setObjectName("recordingItem")
        self.setMinimumHeight(80)
        self.setMaximumHeight(80)
        
        self.init_ui()
        
    def init_ui(self):
        """Initialize the user interface"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        
        # Information container
        info_container = QVBoxLayout()
        
        # First row: title and date/time
        title_row = QHBoxLayout()
        
        # Title
        record_name = getattr(self.recording, 'name', 'Unnamed Recording')  # Fetch the actual name
        title = QLabel(f"{record_name}")
        title.setObjectName("recordingTitle")
        title_row.addWidget(title)
        
        title_row.addStretch()
        
        # Date and time
        date_time = QLabel(self.recording.start_time.strftime("%d/%m/%Y %H:%M:%S"))
        date_time.setObjectName("recordingDateTime")
        title_row.addWidget(date_time)
        
        info_container.addLayout(title_row)
        
        # Second row: details
        details_row = QHBoxLayout()
        
        # Camera
        camera_name = self.recording.camera.name if self.recording.camera else "Unknown Camera"
        camera = QLabel(f"Camera: {camera_name}")
        camera.setObjectName("recordingDetail")
        details_row.addWidget(camera)
        
        # Duration
        duration_text = "--:--:--"
        if self.recording.duration:
            minutes, seconds = divmod(int(self.recording.duration), 60)
            hours, minutes = divmod(minutes, 60)
            duration_text = f"{hours:02}:{minutes:02}:{seconds:02}"
        duration = QLabel(f"Duration: {duration_text}")
        duration.setObjectName("recordingDetail")
        details_row.addWidget(duration)
        
        # Resolution
        resolution = QLabel(f"Resolution: {self.recording.resolution or 'Unknown'}")
        resolution.setObjectName("recordingDetail")
        details_row.addWidget(resolution)
        
        details_row.addStretch()
        
        info_container.addLayout(details_row)
        
        layout.addLayout(info_container)
        
        # Actions container
        actions_container = QVBoxLayout()
        actions_container.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        # Action buttons
        actions_row = QHBoxLayout()
        
        # View button
        self.view_button = QPushButton("View")
        self.view_button.setObjectName("actionButton")
        self.view_button.clicked.connect(self.on_view_clicked)
        actions_row.addWidget(self.view_button)
        
        # Download button
        self.download_button = QPushButton("Download")
        self.download_button.setObjectName("actionButton")
        self.download_button.clicked.connect(self.on_download_clicked)
        actions_row.addWidget(self.download_button)
        
        # Delete button
        self.delete_button = QPushButton("Delete")
        self.delete_button.setObjectName("dangerButton")
        self.delete_button.clicked.connect(self.on_delete_clicked)
        actions_row.addWidget(self.delete_button)
        
        actions_container.addLayout(actions_row)
        
        layout.addLayout(actions_container)
        
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
        """Initialize the user interface components"""
        # Main container widget for scrollable content
        content_widget = QWidget()
        content_widget.setObjectName("mainContentWidget")  # Add object name for styling
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(10, 10, 10, 10)
        content_layout.setSpacing(15)

        # Main layout with a splitter for responsiveness
        main_splitter = QSplitter(Qt.Vertical, content_widget)
        main_splitter.setObjectName("mainSplitter")

        # Top section: Filters and recordings
        top_section = QWidget()
        top_layout = QVBoxLayout(top_section)
        top_layout.setContentsMargins(10, 10, 10, 10)
        top_layout.setSpacing(15)

        # Filter elements section
        filter_frame = SectionFrame()
        filter_frame.setObjectName("filterFrame")
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setContentsMargins(10, 10, 10, 10)
        filter_layout.setSpacing(10)

        # Search input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search...")
        self.search_input.setObjectName("roundedSearchBox")  # Add object name for styling
        self.search_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.search_input.textChanged.connect(self.on_search_changed)
        filter_layout.addWidget(self.search_input)

        # Camera filter
        camera_filter = QHBoxLayout()
        camera_label = QLabel("Camera:")
        self.camera_combo = QComboBox()
        self.camera_combo.addItem("All", None)
        self.camera_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # Add cameras to the combo box
        cameras = self.camera_service.get_all_cameras()
        for camera in cameras:
            self.camera_combo.addItem(camera.name, camera.id)

        self.camera_combo.currentIndexChanged.connect(self.on_camera_filter_changed)
        camera_filter.addWidget(camera_label)
        camera_filter.addWidget(self.camera_combo)
        filter_layout.addLayout(camera_filter)

        # Date filter
        date_filter = QHBoxLayout()
        date_label = QLabel("Date:")
        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.date_edit.dateChanged.connect(self.on_date_filter_changed)
        date_filter.addWidget(date_label)
        date_filter.addWidget(self.date_edit)
        filter_layout.addLayout(date_filter)

        # Reset filters button
        self.reset_button = QPushButton("Reset Filters")
        self.reset_button.setObjectName("smallButton")  # Add object name for styling
        self.reset_button.clicked.connect(self.reset_filters)
        filter_layout.addWidget(self.reset_button)

        # Add filter frame to the top layout
        top_layout.addWidget(filter_frame)

        # Recordings section
        recordings_frame = SectionFrame()
        recordings_frame.setObjectName("contentSection")
        recordings_layout = QVBoxLayout(recordings_frame)
        recordings_layout.setContentsMargins(0, 0, 0, 0)
        recordings_layout.setSpacing(10)

        recordings_header = QLabel("Recordings")
        recordings_header.setObjectName("sectionHeader")
        recordings_layout.addWidget(recordings_header)

        self.recordings_scroll = QScrollArea()
        self.recordings_scroll.setWidgetResizable(True)
        self.recordings_scroll.setFrameShape(QFrame.NoFrame)
        self.recordings_scroll.setFixedHeight(300)  # Set fixed height for the video list

        self.recordings_container = QWidget()
        self.recordings_list = QVBoxLayout(self.recordings_container)
        self.recordings_list.setAlignment(Qt.AlignTop)
        self.recordings_list.setSpacing(10)

        self.recordings_scroll.setWidget(self.recordings_container)
        recordings_layout.addWidget(self.recordings_scroll)

        # Pagination
        pagination = QHBoxLayout()
        pagination.setObjectName("paginationSection")
        pagination.setAlignment(Qt.AlignCenter)

        self.prev_button = QPushButton("<")
        self.prev_button.setObjectName("pageButton")
        self.prev_button.clicked.connect(self.previous_page)
        pagination.addWidget(self.prev_button)

        self.page_buttons_layout = QHBoxLayout()
        pagination.addLayout(self.page_buttons_layout)

        self.next_button = QPushButton(">")
        self.next_button.setObjectName("pageButton")
        self.next_button.clicked.connect(self.next_page)
        pagination.addWidget(self.next_button)

        recordings_layout.addLayout(pagination)
        top_layout.addWidget(recordings_frame)

        # Bottom section: Video player and details
        bottom_section = QWidget()
        bottom_layout = QVBoxLayout(bottom_section)
        bottom_layout.setContentsMargins(10, 10, 10, 10)
        bottom_layout.setSpacing(15)

        # Video player section
        self.video_player = VideoPlayerWidget()  # Use the optimized VideoPlayerWidget
        self.video_player.setVisible(False)
        self.video_player.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_player.setMinimumHeight(500)  # Increase minimum height from 400 to 500
        bottom_layout.addWidget(self.video_player)

        # Video details popup
        self.details_popup = QFrame()
        self.details_popup.setObjectName("detailsPopup")
        self.details_popup.setVisible(False)
        details_layout = QVBoxLayout(self.details_popup)
        details_layout.setContentsMargins(10, 10, 10, 10)  # Reduce margins
        details_layout.setSpacing(8)  # Slightly reduce spacing

        details_header = QLabel("Recording Details")
        details_header.setObjectName("sectionHeader")
        details_header.setAlignment(Qt.AlignLeft)  # Align header text to the left
        details_layout.addWidget(details_header)

        details_grid = QGridLayout()
        details_grid.setHorizontalSpacing(15)  # Reduce horizontal spacing
        details_grid.setVerticalSpacing(8)  # Reduce vertical spacing

        labels = ["Date:", "Camera:", "Resolution:", "Duration:", "Size:"]
        self.details_values = [
            QLabel("--/--/----"),
            QLabel("--"),
            QLabel("----x----"),
            QLabel("--:--:--"),
            QLabel("-- MB"),
        ]

        for i, label_text in enumerate(labels):
            label = QLabel(label_text)
            label.setObjectName("detailLabel")
            label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)  # Align labels to the left
            details_grid.addWidget(label, i, 0)

            value = self.details_values[i]
            value.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)  # Align values to the left
            details_grid.addWidget(value, i, 1)

        details_layout.addLayout(details_grid)
        bottom_layout.addWidget(self.details_popup)

        # Add top and bottom sections to the splitter
        main_splitter.addWidget(top_section)
        main_splitter.addWidget(bottom_section)
        main_splitter.setStretchFactor(0, 1)  # Changed from 2 to 1 (top section)
        main_splitter.setStretchFactor(1, 4)  # Increased from 3 to 4 (bottom section)

        # Add splitter to the content layout
        content_layout.addWidget(main_splitter)

        # Scroll area for the entire screen
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(content_widget)
        scroll_area.setObjectName("playbackScrollArea")

        # Main layout
        layout = QVBoxLayout(self)
        layout.addWidget(scroll_area)
        self.setLayout(layout)
    
    def create_page_button(self, page_num, is_active=False):
        """Create a pagination button"""
        btn = QPushButton(str(page_num))
        btn.setFixedSize(30, 30)
        
        if is_active:
            btn.setObjectName("activePageButton")
        else:
            btn.setObjectName("pageButton")
        
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
        recording = self.storage_service.get_recording(recording_id)
        if recording:
            QMessageBox.information(
                self,
                "Download",
                f"Downloading recording: {recording.file_path}\n"
                "This feature is not fully implemented."
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
    """Optimized Video Player Widget with enhanced controls."""
    def __init__(self):
        super().__init__()
        self.mediaPlayer = QMediaPlayer()
        self.playlist = QMediaPlaylist()
        self.mediaPlayer.setPlaylist(self.playlist)

        self.videoItem = QGraphicsVideoItem()
        self.videoItem.setAspectRatioMode(Qt.KeepAspectRatio)

        scene = QGraphicsScene(self)
        self.graphicsView = QGraphicsView(scene)
        self.graphicsView.setMinimumHeight(450)  # Set minimum height for the graphics view
        self.graphicsView.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        scene.addItem(self.videoItem)
        self.mediaPlayer.setVideoOutput(self.videoItem)

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)  # Remove margins to maximize video space

        # Video display
        layout.addWidget(self.graphicsView, 1)  # Add stretch factor of 1

        # Playback controls
        controls = QHBoxLayout()
        self.playButton = QPushButton("Play")
        self.playButton.clicked.connect(self.toggle_play)
        controls.addWidget(self.playButton)

        self.stopButton = QPushButton("Stop")
        self.stopButton.clicked.connect(self.mediaPlayer.stop)
        controls.addWidget(self.stopButton)

        self.skipBackButton = QPushButton("<<")
        self.skipBackButton.clicked.connect(lambda: self.mediaPlayer.setPosition(self.mediaPlayer.position() - 5000))
        controls.addWidget(self.skipBackButton)

        self.skipForwardButton = QPushButton(">>")
        self.skipForwardButton.clicked.connect(lambda: self.mediaPlayer.setPosition(self.mediaPlayer.position() + 5000))
        controls.addWidget(self.skipForwardButton)

        self.volumeSlider = QSlider(Qt.Horizontal)
        self.volumeSlider.setRange(0, 100)
        self.volumeSlider.setValue(50)
        self.volumeSlider.valueChanged.connect(self.mediaPlayer.setVolume)
        controls.addWidget(self.volumeSlider)

        layout.addLayout(controls)

        # Playback speed control
        self.speedButton = QPushButton("1x")
        self.speedMenu = QMenu()
        for speed in ["0.5x", "1x", "1.5x", "2x"]:
            action = self.speedMenu.addAction(speed)
            action.triggered.connect(lambda _, s=speed: self.set_playback_speed(s))
        self.speedButton.setMenu(self.speedMenu)
        controls.addWidget(self.speedButton)

        # Aspect ratio control
        self.aspectRatioButton = QPushButton("Aspect Ratio")
        self.aspectRatioButton.setCheckable(True)
        self.aspectRatioButton.toggled.connect(self.toggle_aspect_ratio)
        controls.addWidget(self.aspectRatioButton)

    def toggle_play(self):
        if self.mediaPlayer.state() == QMediaPlayer.PlayingState:
            self.mediaPlayer.pause()
            self.playButton.setText("Play")
        else:
            self.mediaPlayer.play()
            self.playButton.setText("Pause")

    def play(self):
        """Start media playback and update button text"""
        self.mediaPlayer.play()
        self.playButton.setText("Pause")

    def set_playback_speed(self, speed):
        rate = float(speed[:-1])
        self.mediaPlayer.setPlaybackRate(rate)
        self.speedButton.setText(speed)

    def toggle_aspect_ratio(self, checked):
        mode = Qt.KeepAspectRatio if checked else Qt.IgnoreAspectRatio
        self.videoItem.setAspectRatioMode(mode)

    def set_source(self, file_path):
        self.playlist.clear()
        self.playlist.addMedia(QMediaContent(QUrl.fromLocalFile(file_path)))
        self.playlist.setCurrentIndex(0)
        self.mediaPlayer.play()