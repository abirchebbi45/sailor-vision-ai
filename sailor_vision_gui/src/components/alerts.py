# Fichier: src/components/alerts.py

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QFrame, QScrollArea, QLineEdit,
                            QDateEdit, QComboBox, QDialog, QTextEdit)
from PyQt5.QtCore import Qt, QDate, QSize, pyqtSignal, QTimer
from PyQt5.QtGui import QPixmap, QIcon
import os
import json
import logging
import csv
from PyQt5.QtWidgets import QFileDialog, QMessageBox

from shared.alert_subscriber import ROSAlertBridge
from src.services.alert_service import AlertService
from models import AlertType, Alert

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AlertItem(QFrame):
    """Widget qui représente un élément d'alerte individuel"""
    acknowledge_clicked = pyqtSignal(int)
    archive_clicked = pyqtSignal(int)
    details_clicked = pyqtSignal(int)
    
    def __init__(self, alert, show_actions=True, show_details=True):
        super().__init__()
        self.alert = alert
        self.show_actions = show_actions
        self.show_details = show_details
        self.init_ui()
    
    def init_ui(self):
        """Initialiser l'interface utilisateur de l'élément d'alerte"""
        self.setObjectName("alertItem")
        self.setFrameShape(QFrame.StyledPanel)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        
        # Information d'alerte
        info_layout = QVBoxLayout()
        
        # Titre et temps
        title_layout = QHBoxLayout()
        
        # Titre de l'alerte avec type
        alert_title = QLabel(str(self.alert.type))
        alert_title.setObjectName("alertTitle")
        title_layout.addWidget(alert_title)
        
        title_layout.addStretch()
        
        # Temps écoulé
        time_label = QLabel(f"{self.alert.timestamp.strftime('%-d mins ago') if hasattr(self.alert, 'timestamp') else '2 mins ago'}")
        time_label.setObjectName("alertTime")
        title_layout.addWidget(time_label)
        
        info_layout.addLayout(title_layout)
        
        # Description
        description_text = f"""
        {self.alert.message}
        Classe: {self.alert.type}
        Position: {self.alert.image_data if hasattr(self.alert, 'image_data') else 'N/A'}
        """
        description = QLabel(description_text.strip())
        description.setObjectName("alertDescription")
        description.setWordWrap(True)  # Activer le retour à la ligne
        info_layout.addWidget(description)
        info_layout.addWidget(description)
        
        layout.addLayout(info_layout, 1)  # Stretch factor 1
        
        # Boutons d'action
        if self.show_actions:
            acknowledge_btn = QPushButton("Acknowledge Alert")
            acknowledge_btn.setObjectName("primaryButton")
            acknowledge_btn.clicked.connect(lambda: self.acknowledge_clicked.emit(self.alert.id))
            layout.addWidget(acknowledge_btn)
            
            archive_btn = QPushButton("Archive")
            archive_btn.setObjectName("secondaryButton")
            archive_btn.clicked.connect(lambda: self.archive_clicked.emit(self.alert.id))
            layout.addWidget(archive_btn)
        
        # Bouton détails
        if self.show_details:
            details_btn = QPushButton("View Details")
            details_btn.setObjectName("outlineButton")
            details_btn.clicked.connect(lambda: self.details_clicked.emit(self.alert.id))
            layout.addWidget(details_btn)

class AlertDetailsDialog(QDialog):
    def __init__(self, alert, parent=None):
        super().__init__(parent)
        self.alert = alert
        self.setWindowTitle("Alert Details")
        self.setFixedSize(600, 400)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        
        self.init_ui()
    
    def init_ui(self):
        """Initialiser l'interface utilisateur de la boîte de dialogue"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Titre
        title = QLabel("Alert Details")
        title.setObjectName("dialogTitle")
        layout.addWidget(title)
        
        # Détails de l'alerte
        details_frame = QFrame()
        details_frame.setObjectName("contentSection")
        details_layout = QVBoxLayout(details_frame)
        
        # Créer une mise en page pour les détails en deux colonnes
        grid_layout = QVBoxLayout()
        grid_layout.setSpacing(10)
        
        # Type
        type_row = self.create_detail_row("Type:", self.alert.type.value if hasattr(self.alert.type, "value") else str(self.alert.type))
        grid_layout.addLayout(type_row)
        
        # Date
        date_row = self.create_detail_row("Date:", self.alert.timestamp.strftime("%d/%m/%Y") if hasattr(self.alert, "timestamp") else "01/10/2023")
        grid_layout.addLayout(date_row)
        
        # Heure
        time_row = self.create_detail_row("Time:", self.alert.timestamp.strftime("%H:%M:%S") if hasattr(self.alert, "timestamp") else "14:35:20")
        grid_layout.addLayout(time_row)
        
        # Emplacement
        location_row = self.create_detail_row("Location:", self.alert.camera.location if hasattr(self.alert, "camera") and self.alert.camera else "Main Entrance")
        grid_layout.addLayout(location_row)
        
        # Statut
        status_text = "Acknowledged" if hasattr(self.alert, "is_acknowledged") and self.alert.is_acknowledged else "Pending"
        status_row = self.create_detail_row("Status:", status_text)
        grid_layout.addLayout(status_row)
        
        details_layout.addLayout(grid_layout)
        layout.addWidget(details_frame)
        
        # Bouton Fermer
        close_button = QPushButton("Close")
        close_button.setObjectName("primaryButton")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button, alignment=Qt.AlignRight)
    
    def create_detail_row(self, label_text, value_text):
        """Créer une ligne de détail avec étiquette et valeur"""
        row = QHBoxLayout()
        
        label = QLabel(label_text)
        label.setObjectName("detailLabel")
        label.setFixedWidth(100)
        
        value = QLabel(value_text)
        value.setObjectName("detailValue")
        
        row.addWidget(label)
        row.addWidget(value, 1)  # Stretch factor 1
        row.addStretch()
        
        return row

class AlertsScreen(QWidget):
    def __init__(self, user_data=None, ros_node=None):
        super().__init__()
        self.user_data = user_data
        self.alert_service = AlertService()
        
        # Initialiser le bridge ROS pour les alertes
        self.alert_bridge = ROSAlertBridge(ros_node)
        self.alert_bridge.alert_received.connect(self.on_alert_received)
        #self.alert_bridge.start()
        logger.info("Alert bridge started and connected to signal")
        
        self.init_ui()
        
        # Charger les données initiales
        self.load_alerts()
        self.load_alert_history()
    
    def init_ui(self):
        """Initialiser les composants UI"""
        # Mise en page principale
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Contenu des alertes
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(20)
        
        # Section Alertes en temps réel
        rt_alerts_section = QFrame()
        rt_alerts_section.setObjectName("contentSection")
        rt_alerts_layout = QVBoxLayout(rt_alerts_section)
        rt_alerts_layout.setContentsMargins(15, 15, 15, 15)
        
        rt_alerts_header = QLabel("Real-Time Alerts")
        rt_alerts_header.setObjectName("sectionHeader")
        rt_alerts_layout.addWidget(rt_alerts_header)
        
        # Liste des alertes en temps réel
        self.rt_alerts_list = QVBoxLayout()
        self.rt_alerts_list.setSpacing(10)
        rt_alerts_layout.addLayout(self.rt_alerts_list)
        
        content_layout.addWidget(rt_alerts_section)
        
        # Section Historique des alertes
        history_section = QFrame()
        history_section.setObjectName("contentSection")
        history_layout = QVBoxLayout(history_section)
        history_layout.setContentsMargins(15, 15, 15, 15)
        
        history_header = QLabel("Alert History")
        history_header.setObjectName("sectionHeader")
        history_layout.addWidget(history_header)
        
        # Barre de filtres
        filter_layout = QHBoxLayout()
        filter_layout.setContentsMargins(0, 10, 0, 15)
        
        # Filtre de date
        date_edit = QDateEdit()
        date_edit.setCalendarPopup(True)
        date_edit.setDate(QDate.currentDate())
        date_edit.setObjectName("dateFilter")
        date_edit.setFixedWidth(180)
        date_edit.setDisplayFormat("dd/MM/yyyy")
        filter_layout.addWidget(date_edit)
        
        # Filtre de type
        type_combo = QComboBox()
        type_combo.setObjectName("typeFilter")
        type_combo.addItem("Type")
        for alert_type in AlertType:
            if hasattr(alert_type, "value"):
                type_combo.addItem(alert_type.value)
        type_combo.setFixedWidth(180)
        filter_layout.addWidget(type_combo)
        
        # Spacer
        filter_layout.addStretch()
        
        # Bouton d'exportation
        export_btn = QPushButton("Export")
        export_btn.clicked.connect(self.export_alert_history)
        export_btn.setObjectName("secondaryButton")
        filter_layout.addWidget(export_btn)
        
        # Bouton d'options supplémentaires
        more_btn = QPushButton()
        more_btn.setIcon(QIcon.fromTheme("view-more"))
        more_btn.setObjectName("iconButton")
        more_btn.setFixedSize(32, 32)
        filter_layout.addWidget(more_btn)
        
        history_layout.addLayout(filter_layout)
        
        # Liste d'historique
        self.history_list = QVBoxLayout()
        self.history_list.setSpacing(10)
        history_layout.addLayout(self.history_list)
        
        # Pagination
        pagination = QHBoxLayout()
        pagination.setAlignment(Qt.AlignCenter)
        pagination.setContentsMargins(0, 15, 0, 0)
        
        prev_page = QPushButton("<")
        prev_page.setObjectName("paginationButton")
        prev_page.setFixedSize(32, 32)
        pagination.addWidget(prev_page)
        
        # Boutons de page
        pagination.addWidget(self.create_page_button("1", True))
        pagination.addWidget(self.create_page_button("2"))
        pagination.addWidget(self.create_page_button("3"))
        pagination.addWidget(self.create_page_button("4"))
        
        # Ellipsis
        ellipsis = QLabel("...")
        ellipsis.setAlignment(Qt.AlignCenter)
        pagination.addWidget(ellipsis)
        
        pagination.addWidget(self.create_page_button("10"))
        pagination.addWidget(self.create_page_button("11"))
        
        next_page = QPushButton(">")
        next_page.setObjectName("paginationButton")
        next_page.setFixedSize(32, 32)
        pagination.addWidget(next_page)
        
        history_layout.addLayout(pagination)
        
        content_layout.addWidget(history_section)
        
        # Section Détails de l'alerte (initialement masquée)
        self.details_section = QFrame()
        self.details_section.setObjectName("contentSection")
        self.details_section.setVisible(False)
        details_layout = QVBoxLayout(self.details_section)
        details_layout.setContentsMargins(15, 15, 15, 15)
        
        details_header = QLabel("Alert Details")
        details_header.setObjectName("sectionHeader")
        details_layout.addWidget(details_header)
        
        # Le contenu des détails sera rempli dynamiquement
        self.details_content = QVBoxLayout()
        details_layout.addLayout(self.details_content)
        
        # Bouton de fermeture
        close_btn = QPushButton("Close")
        close_btn.setObjectName("primaryButton")
        close_btn.clicked.connect(lambda: self.details_section.setVisible(False))
        details_layout.addWidget(close_btn, alignment=Qt.AlignRight)
        
        content_layout.addWidget(self.details_section)
        
        # Zone de défilement
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setWidget(content_widget)
        
        layout.addWidget(scroll_area)
    
    def create_page_button(self, text, is_active=False):
        """Créer un bouton de pagination"""
        btn = QPushButton(text)
        btn.setFixedSize(32, 32)
        
        if is_active:
            btn.setObjectName("activePageButton")
        else:
            btn.setObjectName("pageButton")
        
        return btn
    
    def load_alerts(self):
        """Charger et afficher les alertes en temps réel"""
        # Effacer les alertes existantes
        self.clear_layout(self.rt_alerts_list)
        
        # Obtenir les alertes en temps réel du service
        alerts = self.alert_service.get_unacknowledged_alerts()
        
        # Ajouter des widgets d'alerte à la liste
        for alert in alerts:
            alert_widget = AlertItem(alert, show_actions=True)
            alert_widget.acknowledge_clicked.connect(self.acknowledge_alert)
            alert_widget.archive_clicked.connect(self.archive_alert)
            
            self.rt_alerts_list.addWidget(alert_widget)
        
        # Si pas d'alertes, afficher un message
        if not alerts:
            no_alerts = QLabel("No active alerts")
            no_alerts.setObjectName("emptyStateMessage")
            no_alerts.setAlignment(Qt.AlignCenter)
            self.rt_alerts_list.addWidget(no_alerts)
    
    def load_alert_history(self):
        """Charger et afficher l'historique des alertes"""
        # Effacer l'historique existant
        self.clear_layout(self.history_list)
        
        # Obtenir l'historique des alertes du service
        history = self.alert_service.get_alert_history()
        
        # Ajouter des widgets d'alerte à la liste
        for alert in history:
            alert_widget = AlertItem(alert, show_actions=False, show_details=True)
            alert_widget.details_clicked.connect(self.show_alert_details)
            
            self.history_list.addWidget(alert_widget)
        
        # Si pas d'historique, afficher un message
        if not history:
            no_history = QLabel("No alert history available")
            no_history.setObjectName("emptyStateMessage")
            no_history.setAlignment(Qt.AlignCenter)
            self.history_list.addWidget(no_history)
    
    def acknowledge_alert(self, alert_id):
        """Valider une alerte"""
        user_id = self.user_data.get('id') if self.user_data else None
        success = self.alert_service.acknowledge_alert(alert_id, user_id)
        if success:
            # Recharger les alertes
            self.load_alerts()
            self.load_alert_history()
    
    def archive_alert(self, alert_id):
        """Archiver une alerte"""
        success = self.alert_service.archive_alert(alert_id)
        if success:
            # Recharger les alertes
            self.load_alerts()
            self.load_alert_history()
    
    def show_alert_details(self, alert_id):
        """Afficher les détails d'une alerte spécifique"""
        alert = self.alert_service.get_alert(alert_id)
        if alert:
            dialog = AlertDetailsDialog(alert, self)
            dialog.exec_()
    
    def on_alert_received(self, alert_data):
        """Reçoit les données ROS2 (dans un thread ROS)"""
        try:
            # Transfère le traitement au thread principal
            QTimer.singleShot(0, lambda: self._handle_alert(alert_data))
        except Exception as e:
            logger.error(f"Erreur de transfert thread: {e}")

    def _handle_alert(self, alert_data):
        """Exécuté dans le thread principal de Qt"""
        try:
            logger.info(f"Traitement des données: {json.dumps(alert_data)[:200]}...")  # Safe logging
            
            # 1. Enregistrement en base de données
            success = self.alert_service.process_yolo_detection(alert_data)
            
            if success:
                # 2. Mise à jour de l'interface
                logger.info("Mise à jour de l'interface utilisateur...")
                self.load_alerts()
                self.load_alert_history()
                
                logger.info("UI mise à jour avec succès")
            else:
                logger.warning("Échec du traitement d'alerte")
                
        except Exception as e:
            logger.error(f"Erreur traitement alerte: {e}")
            import traceback
            logger.error(traceback.format_exc())  # Full stack trace

    def clear_layout(self, layout):
        """Effacer le contenu d'une mise en page"""
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
            else:
                self.clear_layout(item.layout())
    
    def closeEvent(self, event):
        """Gérer la fermeture de la fenêtre"""
        logger.info("Closing AlertsScreen and stopping services")
        self.alert_bridge.stop()
        event.accept()
        # Fermer le service d'alerte - méthodes ajoutées dans le service
        self.alert_service.close()
        # Fermer le service de base de données
        self.alert_service.close_db()
    
    def export_alert_history(self):
        """ Exporter l'historique des alertes vers un fichier CSV"""
        file_path, _ = QFileDialog.getSaveFileName(self, "Save File", "", "CSV Files (*.csv)")
        
        if file_path:
            alerts = self.alert_service.get_alert_history()
            try:
                with open(file_path, mode='w', newline='', encoding='utf-8') as file:
                    writer = csv.writer(file)
                    writer.writerow(["ID", "Type", "Message", "Date", "Heure", "Caméra", "Classe"])
                    for alert in alerts:
                        writer.writerow([
                            alert.id,
                            alert.type if isinstance(alert.type, str) else alert.type.value,
                            alert.message,
                            alert.timestamp.strftime("%d/%m/%Y"),
                            alert.timestamp.strftime("%H:%M:%S"),
                            alert.camera.location if alert.camera else "N/A",
                            alert.detection_class
                        ])
                QMessageBox.information(self, "Export réussi", f"Historique exporté avec succès dans:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Erreur d'export", f"Erreur lors de l'export:\n{str(e)}")
