from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QFrame, QScrollArea, QLineEdit,
                             QToolButton, QComboBox, QPushButton, QSlider,
                             QDateEdit, QMessageBox, QSplitter)
from PyQt5.QtCore import Qt, QDate, QTime, QSize, QTimer
from PyQt5.QtGui import QPixmap, QIcon
import datetime
import logging
import os

from ..services.camera_service import CameraService
from ..services.storage_service import StorageService
from src.components.dashboard import SectionFrame 
from ..components.shared import HeaderWidget, VideoPlayerWidget
from models import Recording

logger = logging.getLogger(__name__)

class RecordingItem(QFrame):
    """Widget représentant un élément d'enregistrement dans la liste"""
    def __init__(self, recording, playback_screen):
        super().__init__()
        self.recording = recording
        self.playback_screen = playback_screen  # Store reference to PlaybackScreen
        self.setObjectName("recordingItem")
        self.setMinimumHeight(80)
        self.setMaximumHeight(80)
        
        self.init_ui()
        
    def init_ui(self):
        """Initialiser l'interface utilisateur"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        
        # Information container
        info_container = QVBoxLayout()
        
        # Première ligne : titre et date/heure
        title_row = QHBoxLayout()
        
        # Titre
        class_name = getattr(self.recording, 'class_name', 'Detection')
        title = QLabel(f"{class_name}")
        title.setObjectName("recordingTitle")
        title_row.addWidget(title)
        
        title_row.addStretch()
        
        # Date et heure
        date_time = QLabel(self.recording.start_time.strftime("%d/%m/%Y %H:%M:%S"))
        date_time.setObjectName("recordingDateTime")
        title_row.addWidget(date_time)
        
        info_container.addLayout(title_row)
        
        # Deuxième ligne : détails
        details_row = QHBoxLayout()
        
        # Caméra
        camera_name = self.recording.camera.name if self.recording.camera else "Unknown Camera"
        camera = QLabel(f"Camera: {camera_name}")
        camera.setObjectName("recordingDetail")
        details_row.addWidget(camera)
        
        # Durée
        duration_text = "--:--:--"
        if self.recording.duration:
            minutes, seconds = divmod(int(self.recording.duration), 60)
            hours, minutes = divmod(minutes, 60)
            duration_text = f"{hours:02}:{minutes:02}:{seconds:02}"
        duration = QLabel(f"Duration: {duration_text}")
        duration.setObjectName("recordingDetail")
        details_row.addWidget(duration)
        
        # Résolution
        resolution = QLabel(f"Resolution: {self.recording.resolution or 'Unknown'}")
        resolution.setObjectName("recordingDetail")
        details_row.addWidget(resolution)
        
        details_row.addStretch()
        
        info_container.addLayout(details_row)
        
        layout.addLayout(info_container)
        
        # Actions container
        actions_container = QVBoxLayout()
        actions_container.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        # Boutons d'action
        actions_row = QHBoxLayout()
        
        # Bouton Visualiser
        self.view_button = QPushButton("View")
        self.view_button.setObjectName("actionButton")
        self.view_button.clicked.connect(self.on_view_clicked)
        actions_row.addWidget(self.view_button)
        
        # Bouton Télécharger
        self.download_button = QPushButton("Download")
        self.download_button.setObjectName("actionButton")
        self.download_button.clicked.connect(self.on_download_clicked)
        actions_row.addWidget(self.download_button)
        
        # Bouton Supprimer
        self.delete_button = QPushButton("Delete")
        self.delete_button.setObjectName("dangerButton")
        self.delete_button.clicked.connect(self.on_delete_clicked)
        actions_row.addWidget(self.delete_button)
        
        actions_container.addLayout(actions_row)
        
        layout.addLayout(actions_container)
        
    def on_view_clicked(self):
        """Gérer le clic sur le bouton de visualisation"""
        self.playback_screen.play_recording(self.recording.id)  # Use the reference to call play_recording
        
    def on_download_clicked(self):
        """Gérer le clic sur le bouton de téléchargement"""
        self.playback_screen.download_recording(self.recording.id)
        
    def on_delete_clicked(self):
        """Gérer le clic sur le bouton de suppression"""
        self.playback_screen.delete_recording(self.recording.id)

class PlaybackScreen(QWidget):
    def __init__(self, user_data=None, ros_node=None):
        super().__init__()
        self.user_data = user_data
        self.ros_node = ros_node
        self.camera_service = CameraService()
        self.storage_service = StorageService()
        
        # État et configuration
        self.current_page = 1
        self.recordings_per_page = 5
        self.date_filter = None
        self.camera_filter = None
        self.search_text = ""
        
        self.init_ui()
        
        # Charger les données initiales
        self.load_recordings()
    
    def init_ui(self):
        """Initialiser les composants de l'interface utilisateur"""
        # Main scrollable layout
        main_scroll = QScrollArea(self)
        main_scroll.setWidgetResizable(True)
        main_scroll.setObjectName("mainScroll")  # Assign an object name for styling

        main_widget = QWidget()
        main_widget.setObjectName("mainWidget")  # Assign an object name for styling

        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)  # Add margins for responsiveness
        main_layout.setSpacing(15)  # Add spacing between sections
        main_scroll.setWidget(main_widget)

        layout = QVBoxLayout(self)
        layout.addWidget(main_scroll)
        self.setLayout(layout)

        # Filter elements section
        filter_frame = SectionFrame()
        filter_frame.setObjectName("filterFrame")  # Assign an object name for styling
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setContentsMargins(10, 10, 10, 10)
        filter_layout.setSpacing(10)  # Add spacing between filter elements

        # Search input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Rechercher...")
        self.search_input.setFixedWidth(200)
        self.search_input.textChanged.connect(self.on_search_changed)
        filter_layout.addWidget(self.search_input)

        # Camera filter
        camera_filter = QHBoxLayout()
        camera_label = QLabel("Caméra:")
        self.camera_combo = QComboBox()
        self.camera_combo.addItem("Toutes", None)

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
        self.date_edit.dateChanged.connect(self.on_date_filter_changed)
        date_filter.addWidget(date_label)
        date_filter.addWidget(self.date_edit)
        filter_layout.addLayout(date_filter)

        # Shortcut buttons for date filters
        self.today_button = QPushButton("Aujourd'hui")
        self.today_button.clicked.connect(self.filter_today)
        filter_layout.addWidget(self.today_button)

        self.week_button = QPushButton("Cette semaine")
        self.week_button.clicked.connect(self.filter_this_week)
        filter_layout.addWidget(self.week_button)

        # Reset filters button
        self.reset_button = QPushButton("Réinitialiser")
        self.reset_button.clicked.connect(self.reset_filters)
        filter_layout.addWidget(self.reset_button)

        # Add filter frame to the main layout
        main_layout.addWidget(filter_frame)

        # Section des enregistrements
        recordings_frame = SectionFrame()
        recordings_frame.setObjectName("contentSection")
        recordings_layout = QVBoxLayout(recordings_frame)
        recordings_layout.setContentsMargins(0, 0, 0, 0)
        recordings_layout.setSpacing(10)

        recordings_header = QLabel("Enregistrements")
        recordings_header.setObjectName("sectionHeader")
        recordings_layout.addWidget(recordings_header)

        self.recordings_scroll = QScrollArea()
        self.recordings_scroll.setWidgetResizable(True)
        self.recordings_scroll.setFrameShape(QFrame.NoFrame)

        self.recordings_container = QWidget()
        self.recordings_list = QVBoxLayout(self.recordings_container)
        self.recordings_list.setAlignment(Qt.AlignTop)
        self.recordings_list.setSpacing(10)

        self.recordings_scroll.setWidget(self.recordings_container)
        recordings_layout.addWidget(self.recordings_scroll)

        # Pagination
        pagination = QHBoxLayout()
        pagination.setAlignment(Qt.AlignCenter)

        self.prev_button = QPushButton("<")
        self.prev_button.clicked.connect(self.previous_page)
        pagination.addWidget(self.prev_button)

        # Initialize page_buttons_layout
        self.page_buttons_layout = QHBoxLayout()
        pagination.addLayout(self.page_buttons_layout)

        self.next_button = QPushButton(">")
        self.next_button.clicked.connect(self.next_page)
        pagination.addWidget(self.next_button)

        # Add pagination layout to recordings frame
        recordings_layout.addLayout(pagination)

        # Add recordings frame to the main layout
        main_layout.addWidget(recordings_frame)

        # Section du lecteur vidéo
        self.video_player = VideoPlayerWidget()
        self.video_player.setVisible(False)  # Initially hide the video player
        main_layout.addWidget(self.video_player)

        # Video details popup
        self.details_popup = QFrame()
        self.details_popup.setObjectName("detailsPopup")  # Assign an object name for styling
        self.details_popup.setVisible(False)  # Initially hide the details popup
        details_layout = QVBoxLayout(self.details_popup)

        details_header = QLabel("Détails de l'enregistrement")
        details_header.setObjectName("sectionHeader")
        details_layout.addWidget(details_header)

        details_grid = QHBoxLayout()

        # Colonnes de détails
        labels_column = QVBoxLayout()
        values_column = QVBoxLayout()

        labels = ["Date:", "Caméra:", "Résolution:", "Durée:", "Taille:"]
        for label_text in labels:
            label = QLabel(label_text)
            label.setObjectName("detailLabel")
            labels_column.addWidget(label)

        # Initialize detail attributes
        self.details_date = QLabel("--/--/----")
        self.details_camera = QLabel("--")
        self.details_resolution = QLabel("----x----")
        self.details_duration = QLabel("--:--:--")
        self.details_size = QLabel("-- MB")

        values_column.addWidget(self.details_date)
        values_column.addWidget(self.details_camera)
        values_column.addWidget(self.details_resolution)
        values_column.addWidget(self.details_duration)
        values_column.addWidget(self.details_size)

        details_grid.addLayout(labels_column)
        details_grid.addLayout(values_column)
        details_grid.addStretch()

        details_layout.addLayout(details_grid)

        # Add details popup to the main layout
        main_layout.addWidget(self.details_popup)
    
    def create_page_button(self, page_num, is_active=False):
        """Créer un bouton de pagination"""
        btn = QPushButton(str(page_num))
        btn.setFixedSize(30, 30)
        
        if is_active:
            btn.setObjectName("activePageButton")
        else:
            btn.setObjectName("pageButton")
        
        btn.clicked.connect(lambda: self.go_to_page(page_num))
        
        return btn
    
    def update_pagination(self, total_recordings):
        """Mettre à jour les boutons de pagination"""
        # Effacer les boutons existants
        while self.page_buttons_layout.count():
            item = self.page_buttons_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        
        # Calculer le nombre total de pages
        total_pages = max(1, (total_recordings + self.recordings_per_page - 1) // self.recordings_per_page)
        
        # Activer/désactiver les boutons de navigation
        self.prev_button.setEnabled(self.current_page > 1)
        self.next_button.setEnabled(self.current_page < total_pages)
        
        # Créer les boutons de page
        # Si peu de pages, montrer toutes
        if total_pages <= 7:
            for i in range(1, total_pages + 1):
                self.page_buttons_layout.addWidget(self.create_page_button(i, i == self.current_page))
        else:
            # Sinon, montrer une sélection
            # Toujours montrer la première page
            self.page_buttons_layout.addWidget(self.create_page_button(1, 1 == self.current_page))
            
            # Déterminer la plage à afficher
            start_page = max(2, self.current_page - 2)
            end_page = min(total_pages - 1, self.current_page + 2)
            
            # Ajouter des ellipses si nécessaire
            if start_page > 2:
                ellipsis = QLabel("...")
                ellipsis.setAlignment(Qt.AlignCenter)
                self.page_buttons_layout.addWidget(ellipsis)
            
            # Ajouter les pages intermédiaires
            for i in range(start_page, end_page + 1):
                self.page_buttons_layout.addWidget(self.create_page_button(i, i == self.current_page))
            
            # Ajouter des ellipses si nécessaire
            if end_page < total_pages - 1:
                ellipsis = QLabel("...")
                ellipsis.setAlignment(Qt.AlignCenter)
                self.page_buttons_layout.addWidget(ellipsis)
            
            # Toujours montrer la dernière page
            self.page_buttons_layout.addWidget(self.create_page_button(total_pages, total_pages == self.current_page))
    
    def load_recordings(self):
        """Charger et afficher les enregistrements"""
        # Calculer l'offset pour la pagination
        offset = (self.current_page - 1) * self.recordings_per_page
        
        # Convertir le filtre de date si nécessaire
        date_filter = None
        if self.date_filter:
            date_filter = self.date_filter.toPyDate()
        
        # Obtenir le nombre total d'enregistrements (pour la pagination)
        # Note: Dans une implémentation réelle, vous auriez une méthode pour compter seulement
        all_recordings = self.storage_service.get_recordings(
            camera_id=self.camera_filter,
            start_date=date_filter if date_filter else None
        )
        total_recordings = len(all_recordings)
        
        # Obtenir les enregistrements pour la page actuelle
        recordings = self.storage_service.get_recordings(
            limit=self.recordings_per_page,
            offset=offset,
            camera_id=self.camera_filter,
            start_date=date_filter if date_filter else None
        )
        
        # Effacer les enregistrements existants
        self.clear_layout(self.recordings_list)
        
        # Ajouter les éléments d'enregistrement à la liste
        if recordings:
            for recording in recordings:
                recording_item = RecordingItem(recording, self)  # Pass self to RecordingItem
                self.recordings_list.addWidget(recording_item)
        else:
            # Message si aucun enregistrement
            no_recordings = QLabel("Aucun enregistrement trouvé")
            no_recordings.setAlignment(Qt.AlignCenter)
            self.recordings_list.addWidget(no_recordings)
        
        # Mettre à jour la pagination
        self.update_pagination(total_recordings)
    
    def play_recording(self, recording_id):
        """Lire un enregistrement"""
        recording = self.storage_service.get_recording(recording_id)
        if recording and os.path.exists(recording.file_path):
            absolute_path = os.path.abspath(recording.file_path)
            logger.info(f"Absolute video path: {absolute_path}")
            
            # Update the video player
            self.video_player.set_source(absolute_path)
            self.video_player.setVisible(True)
            self.video_player.play()
            
            # Show the details popup
            self.details_popup.setVisible(True)  # Display the details popup
            
            # Update recording details
            self.update_details(recording)
        else:
            QMessageBox.warning(self, "Erreur", "Impossible de lire la vidéo. Fichier introuvable.")
            logger.error(f"Video file not found or invalid: {recording.file_path if recording else 'None'}")
    
    def update_details(self, recording):
        """Mettre à jour l'affichage des détails de l'enregistrement"""
        if recording:
            self.details_date.setText(recording.start_time.strftime("%d/%m/%Y %H:%M:%S"))
            
            camera_name = recording.camera.name if recording.camera else "Inconnu"
            self.details_camera.setText(camera_name)
            
            self.details_resolution.setText(recording.resolution or "Inconnue")
            
            if recording.duration:
                minutes, seconds = divmod(int(recording.duration), 60)
                hours, minutes = divmod(minutes, 60)
                self.details_duration.setText(f"{hours:02}:{minutes:02}:{seconds:02}")
            else:
                self.details_duration.setText("--:--:--")
            
            if recording.size:
                size_mb = recording.size / (1024 * 1024)  # Convertir octets en MB
                self.details_size.setText(f"{size_mb:.2f} MB")
            else:
                self.details_size.setText("-- MB")
    
    def download_recording(self, recording_id):
        """Télécharger un enregistrement"""
        recording = self.storage_service.get_recording(recording_id)
        if recording:
            # Dans une application réelle, ceci déclencherait un téléchargement
            # ou une copie vers un emplacement choisi par l'utilisateur
            QMessageBox.information(
                self,
                "Téléchargement",
                f"Téléchargement de l'enregistrement: {recording.file_path}\n"
                "Cette fonctionnalité n'est pas complètement implémentée."
            )
    
    def delete_recording(self, recording_id):
        """Supprimer un enregistrement"""
        # Confirmer la suppression
        reply = QMessageBox.question(
            self,
            "Confirmer la suppression",
            "Êtes-vous sûr de vouloir supprimer cet enregistrement ?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            success = self.storage_service.delete_recording(recording_id)
            if success:
                QMessageBox.information(self, "Succès", "Enregistrement supprimé avec succès.")
                self.load_recordings()
            else:
                QMessageBox.warning(self, "Erreur", "Échec de la suppression de l'enregistrement.")
    
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

    def filter_today(self):
        """Filter recordings to show only today's recordings"""
        self.date_filter = QDate.currentDate()
        self.load_recordings()

    def filter_this_week(self):
        """Filter recordings to show only this week's recordings"""
        today = QDate.currentDate()
        start_of_week = today.addDays(-today.dayOfWeek() + 1)  # Start of the week (Monday)
        self.date_filter = start_of_week
        self.load_recordings()

    def reset_filters(self):
        """Reset all filters and reload recordings"""
        self.date_filter = None
        self.camera_filter = None
        self.search_text = ""
        self.search_input.clear()
        self.camera_combo.setCurrentIndex(0)  # Reset to "Toutes"
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
        self.date_filter = date
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