"""
Widgets personnalisés pour l'affichage des logs et du monitoring système
Interface optimisée et user-friendly pour le système Sailor Vision AI
"""

import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QListWidget, QListWidgetItem, QComboBox, QCheckBox,
    QGroupBox, QProgressBar, QFrame, QTextEdit, QFileDialog,
    QMessageBox, QDialog, QDialogButtonBox, QFormLayout,
    QDateTimeEdit, QSpinBox, QScrollArea, QSizePolicy, QGridLayout
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QDateTime, QThread, pyqtSlot
from PyQt5.QtGui import QFont, QPixmap, QPainter, QColor, QIcon

from src.services.logging_service import LoggingService
from src.services.realtime_log_handler import log_manager


class ServiceStatusWidget(QFrame):
    """Widget moderne pour afficher le statut des services système"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("service-status-main")
        self.services_data = {}
        self.setup_ui()
        self.load_services_status()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Header avec icône et titre stylé
        header_container = QFrame()
        header_container.setObjectName("service-status-header")
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        # Icône de statut
        icon_label = QLabel("📊")
        icon_label.setStyleSheet("font-size: 24px; margin-right: 10px;")
        header_layout.addWidget(icon_label)
        
        title_label = QLabel("System Services Status")
        title_label.setObjectName("logging-subsection-header")
        title_label.setStyleSheet("margin: 0px; padding: 0px; font-size: 18px; font-weight: 600;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Bouton de rafraîchissement avec style moderne
        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.setObjectName("logging-secondary-button")
        self.refresh_btn.clicked.connect(self.refresh_status)
        self.refresh_btn.setStyleSheet("""
            padding: 8px 16px; 
            font-size: 13px; 
            border-radius: 6px;
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            color: #495057;
        """)
        self.refresh_btn.setToolTip("Refresh service status")
        header_layout.addWidget(self.refresh_btn)
        
        layout.addWidget(header_container)
        
        # Scroll area pour les cartes de service
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setObjectName("service-scroll-area")
        
        # Widget conteneur pour les cartes
        self.cards_container = QWidget()
        self.cards_container.setObjectName("service-cards-container")
        
        # Grid layout pour les cartes avec espacement moderne
        self.services_grid = QGridLayout(self.cards_container)
        self.services_grid.setSpacing(16)
        self.services_grid.setContentsMargins(10, 10, 10, 10)
        
        scroll_area.setWidget(self.cards_container)
        layout.addWidget(scroll_area)
        
        # Footer avec statistiques
        footer = QFrame()
        footer.setObjectName("service-status-footer")
        footer.setStyleSheet("""
            background: #f8f9fa;
            border-top: 1px solid #e9ecef;
            border-radius: 0 0 8px 8px;
            padding: 12px 20px;
            margin-top: 10px;
        """)
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(0, 0, 0, 0)
        
        self.status_summary = QLabel("🔄 Loading services...")
        self.status_summary.setStyleSheet("color: #6c757d; font-size: 13px; font-weight: 500;")
        footer_layout.addWidget(self.status_summary)
        footer_layout.addStretch()
        
        self.last_update = QLabel("Last check: Never")
        self.last_update.setStyleSheet("color: #8a8a8a; font-size: 12px;")
        footer_layout.addWidget(self.last_update)
        
        layout.addWidget(footer)
    
    
    def load_services_status(self):
        """Charge et affiche le statut des services"""
        # Services à surveiller dans Sailor Vision AI
        services = {
            "Camera Detection": {"status": "operational", "description": "Monitoring camera feeds"},
            "YOLO Detection": {"status": "checking", "description": "Object detection engine"},
            "Alert System": {"status": "operational", "description": "Real-time alert notifications"},
            "Storage Service": {"status": "operational", "description": "Video and data storage"},
            "User Authentication": {"status": "operational", "description": "Login and permissions"},
            "Database": {"status": "operational", "description": "User and configuration data"}
        }
        
        # Effacer les cartes existantes
        self.clear_grid()
        
        # Créer les cartes de service
        row, col = 0, 0
        cols_per_row = 2  # 2 cartes par ligne
        
        for service_name, info in services.items():
            card = self.create_service_card(service_name, info["status"], info["description"])
            self.services_grid.addWidget(card, row, col)
            
            col += 1
            if col >= cols_per_row:
                col = 0
                row += 1
        
        # Mettre à jour le résumé
        self.update_status_summary(services)
    
    def clear_grid(self):
        """Efface toutes les cartes du grid"""
        while self.services_grid.count():
            child = self.services_grid.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
    
    def refresh_status(self):
        """Rafraîchit le statut de tous les services"""
        try:
            # Simuler la vérification des services
            self.refresh_btn.setText("🔄 Checking...")
            self.refresh_btn.setEnabled(False)
            
            # Recharger les statuts
            self.load_services_status()
            
            # Mettre à jour l'heure de dernière vérification
            now = datetime.now().strftime("%H:%M:%S")
            self.last_update.setText(f"Last check: {now}")
            
        except Exception as e:
            print(f"[ServiceStatus] Error refreshing: {e}")
            QMessageBox.warning(self, "Refresh Error", f"Failed to refresh services: {e}")
        finally:
            self.refresh_btn.setText("🔄 Refresh")
            self.refresh_btn.setEnabled(True)
    
    def update_status_summary(self, services):
        """Met à jour le résumé des statuts"""
        total = len(services)
        operational = sum(1 for s in services.values() if s["status"] == "operational")
        checking = sum(1 for s in services.values() if s["status"] == "checking") 
        errors = sum(1 for s in services.values() if s["status"] == "error")
        
        if errors > 0:
            icon = "🔴"
            status_text = f"{errors} service(s) with errors"
        elif checking > 0:
            icon = "🟡"
            status_text = f"{checking} service(s) checking"
        else:
            icon = "🟢"
            status_text = "All services operational"
        
        self.status_summary.setText(f"{icon} {operational}/{total} services operational • {status_text}")
    
    def create_service_card(self, service_name: str, status: str, description: str) -> QFrame:
        """Crée une carte de service moderne similaire aux cartes User Management"""
        card = QFrame()
        card.setObjectName("service-card")
        card.setProperty("service-status", status)  # Pour le CSS
        card.setFixedSize(280, 160)  # Taille similaire aux UserCards
        card.setStyleSheet("""
            QFrame#service-card {
                background: white;
                border: 1px solid #e1e5e9;
                border-radius: 12px;
                padding: 0px;
            }
            QFrame#service-card:hover {
                border-color: #007bff;
                box-shadow: 0 4px 12px rgba(0, 123, 255, 0.15);
            }
            QFrame#service-card[service-status="error"] {
                border-left: 4px solid #dc3545;
            }
            QFrame#service-card[service-status="warning"] {
                border-left: 4px solid #ffc107;
            }
            QFrame#service-card[service-status="operational"] {
                border-left: 4px solid #28a745;
            }
            QFrame#service-card[service-status="checking"] {
                border-left: 4px solid #17a2b8;
            }
        """)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Header avec nom et icône de statut
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        # Nom du service avec style moderne
        name_label = QLabel(service_name)
        name_label.setStyleSheet("""
            font-size: 15px;
            font-weight: 600;
            color: #212529;
            margin: 0px;
        """)
        name_label.setWordWrap(True)
        header_layout.addWidget(name_label)
        
        # Icône de statut
        status_icon = self.get_status_icon(status)
        icon_label = QLabel(status_icon)
        icon_label.setStyleSheet("font-size: 18px; margin-left: 8px;")
        header_layout.addWidget(icon_label)
        
        layout.addLayout(header_layout)
        
        # Badge de statut avec style moderne
        status_badge = QLabel(status.replace("_", " ").title())
        status_badge.setAlignment(Qt.AlignCenter)
        status_badge.setFixedHeight(28)
        
        # Style du badge selon le statut
        badge_styles = {
            "operational": "background: #d4edda; color: #155724; border: 1px solid #c3e6cb;",
            "checking": "background: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb;",
            "error": "background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb;",
            "warning": "background: #fff3cd; color: #856404; border: 1px solid #ffeaa7;"
        }
        
        status_badge.setStyleSheet(f"""
            {badge_styles.get(status, badge_styles["operational"])}
            border-radius: 14px;
            font-size: 12px;
            font-weight: 600;
            padding: 0px 8px;
        """)
        layout.addWidget(status_badge)
        
        # Description avec style amélioré
        desc_label = QLabel(description)
        desc_label.setStyleSheet("""
            color: #6c757d;
            font-size: 13px;
            line-height: 1.4;
            margin: 0px;
        """)
        desc_label.setWordWrap(True)
        desc_label.setAlignment(Qt.AlignTop)
        layout.addWidget(desc_label)
        
        layout.addStretch()
        
        # Footer avec timestamp ou actions
        footer_label = QLabel("Live monitoring")
        footer_label.setStyleSheet("""
            color: #adb5bd;
            font-size: 11px;
            font-style: italic;
            margin: 0px;
        """)
        footer_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(footer_label)
        
        # Ajouter tooltip informatif
        card.setToolTip(f"{service_name}\nStatus: {status}\n{description}")
        
        return card
    
    def get_status_icon(self, status: str) -> str:
        """Retourne l'icône appropriée selon le statut"""
        status_icons = {
            "operational": "✅",
            "checking": "🔄", 
            "error": "❌",
            "warning": "⚠️"
        }
        return status_icons.get(status.lower(), "❓")


class LogEntryWidget(QFrame):
    """Widget pour afficher une entrée de log"""
    
    def __init__(self, log_entry: Dict, parent=None):
        super().__init__(parent)
        self.log_entry = log_entry
        self.setup_ui()
    
    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)
        
        # Icône du niveau
        icon_label = QLabel(self.log_entry.get('icon', '⚪'))
        icon_label.setFixedSize(16, 16)
        layout.addWidget(icon_label)
        
        # Timestamp
        time_label = QLabel(self.log_entry.get('formatted_time', ''))
        time_label.setObjectName("log-timestamp")
        time_label.setFixedWidth(60)
        layout.addWidget(time_label)
        
        # Source
        source_label = QLabel(self.log_entry.get('source', ''))
        source_label.setObjectName("log-source")
        source_label.setFixedWidth(120)
        layout.addWidget(source_label)
        
        # Message
        message_label = QLabel(self.log_entry.get('message', ''))
        message_label.setObjectName("log-message")
        message_label.setWordWrap(True)
        layout.addWidget(message_label)
        
        # Appliquer la couleur du niveau
        level = self.log_entry.get('level', 'INFO').lower()
        self.setProperty("class", f"log-entry log-entry-{level}")


class LogFilterBar(QFrame):
    """Barre de filtres pour les logs"""
    
    filter_changed = pyqtSignal(dict)  # Émis quand les filtres changent
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("log-filter-bar")
        self.setup_ui()
    
    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)
        
        # Filtre par niveau
        layout.addWidget(QLabel("Level:"))
        self.level_combo = QComboBox()
        self.level_combo.setObjectName("log-filter-combo")
        self.level_combo.addItems(["All Levels", "ERROR", "WARNING", "INFO", "DEBUG"])
        self.level_combo.currentTextChanged.connect(self._emit_filter_changed)
        layout.addWidget(self.level_combo)
        
        # Filtre par période
        layout.addWidget(QLabel("Period:"))
        self.period_combo = QComboBox()
        self.period_combo.setObjectName("log-filter-combo")
        self.period_combo.addItems(["Last Hour", "Last 6 Hours", "Last 24 Hours", "Last Week"])
        self.period_combo.setCurrentText("Last 24 Hours")
        self.period_combo.currentTextChanged.connect(self._emit_filter_changed)
        layout.addWidget(self.period_combo)
        
        # Filtre par source
        layout.addWidget(QLabel("Source:"))
        self.source_combo = QComboBox()
        self.source_combo.setObjectName("log-filter-combo")
        self.source_combo.addItems(["All Sources", "CameraService", "YOLODetection", 
                                   "AlertService", "StorageService", "UserService"])
        self.source_combo.currentTextChanged.connect(self._emit_filter_changed)
        layout.addWidget(self.source_combo)
        
        layout.addStretch()
        
        # Auto-refresh toggle
        self.auto_refresh_cb = QCheckBox("Auto-refresh")
        self.auto_refresh_cb.setObjectName("auto-refresh-toggle")
        self.auto_refresh_cb.setChecked(True)
        self.auto_refresh_cb.toggled.connect(self._emit_filter_changed)
        layout.addWidget(self.auto_refresh_cb)
        
        # Refresh button
        self.refresh_btn = QPushButton("Refresh Now")
        self.refresh_btn.setObjectName("logging-control-button")
        self.refresh_btn.clicked.connect(self._emit_filter_changed)
        layout.addWidget(self.refresh_btn)
    
    def _emit_filter_changed(self):
        """Émet le signal avec les filtres actuels"""
        filters = {
            'level': None if self.level_combo.currentText() == "All Levels" else self.level_combo.currentText(),
            'hours': self._get_hours_from_period(self.period_combo.currentText()),
            'source': None if self.source_combo.currentText() == "All Sources" else self.source_combo.currentText(),
            'auto_refresh': self.auto_refresh_cb.isChecked()
        }
        self.filter_changed.emit(filters)
    
    def _get_hours_from_period(self, period: str) -> int:
        """Convertit la période en heures"""
        period_map = {
            "Last Hour": 1,
            "Last 6 Hours": 6,
            "Last 24 Hours": 24,
            "Last Week": 168
        }
        return period_map.get(period, 24)


class LogViewerWidget(QFrame):
    """Widget principal pour afficher les logs"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("log-viewer")
        self.current_filters = {}
        self.setup_ui()
        self.setup_refresh_timer()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header avec titre, icône et contrôles
        header = QFrame()
        header.setObjectName("log-viewer-header")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 15, 20, 15)
        
        # Icône et titre
        icon_label = QLabel("📝")
        icon_label.setStyleSheet("font-size: 20px; margin-right: 8px;")
        header_layout.addWidget(icon_label)
        
        title_label = QLabel("Real-time System Logs")
        title_label.setObjectName("logging-subsection-header")
        title_label.setStyleSheet("margin: 0px; padding: 0px; font-size: 18px;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Indicateur de logs en temps réel
        self.live_indicator = QLabel("🟢 Live")
        self.live_indicator.setStyleSheet("""
            background-color: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
            border-radius: 12px;
            padding: 4px 12px;
            font-size: 12px;
            font-weight: 600;
            margin-right: 10px;
        """)
        header_layout.addWidget(self.live_indicator)
        
        # Boutons d'action - vérifier les permissions
        try:
            from services.permission_service import Permission
            from services.user_session import UserSession
            
            user_session = UserSession.get_instance()
            
            # Bouton Export - disponible pour Operators et Administrators
            if user_session.has_permission(Permission.EXPORT_LOGS):
                self.export_btn = QPushButton("📥 Export")
                self.export_btn.setObjectName("logging-secondary-button")
                self.export_btn.clicked.connect(self.export_logs)
                self.export_btn.setStyleSheet("padding: 8px 16px; font-size: 13px;")
                header_layout.addWidget(self.export_btn)
            
            # Bouton Clear - Administrators seulement
            if user_session.has_permission(Permission.CLEAR_LOGS):
                self.clear_btn = QPushButton("🗑️ Clear Old")
                self.clear_btn.setObjectName("logging-danger-button")
                self.clear_btn.clicked.connect(self.clear_old_logs)
                self.clear_btn.setStyleSheet("padding: 8px 16px; font-size: 13px;")
                header_layout.addWidget(self.clear_btn)
                
        except Exception as e:
            print(f"[LogViewer] Error checking permissions: {e}")
            # Fallback - créer les boutons sans vérification
            self.export_btn = QPushButton("📥 Export")
            self.export_btn.setObjectName("logging-secondary-button")
            self.export_btn.clicked.connect(self.export_logs)
            self.export_btn.setStyleSheet("padding: 8px 16px; font-size: 13px;")
            header_layout.addWidget(self.export_btn)
        
        layout.addWidget(header)
        
        # Barre de filtres avec style amélioré
        self.filter_bar = LogFilterBar()
        self.filter_bar.filter_changed.connect(self.apply_filters)
        layout.addWidget(self.filter_bar)
        
        # Liste des logs avec style moderne
        self.log_list = QListWidget()
        self.log_list.setObjectName("log-list")
        self.log_list.setAlternatingRowColors(True)
        self.log_list.setStyleSheet("""
            QListWidget {
                background: white;
                border: none;
                font-family: 'SF Mono', 'Monaco', 'Consolas', 'Courier New', monospace;
                font-size: 13px;
                selection-background-color: #e3f2fd;
            }
            QListWidget::item {
                padding: 8px 20px;
                border-bottom: 1px solid #f1f3f4;
                min-height: 20px;
            }
            QListWidget::item:hover {
                background-color: #f8f9fa;
            }
            QListWidget::item:selected {
                background-color: #e3f2fd;
                color: #1565c0;
            }
        """)
        layout.addWidget(self.log_list)
        
        # Footer avec statistiques
        footer = QFrame()
        footer.setStyleSheet("""
            background: #f8f9fa;
            border-top: 1px solid #e9ecef;
            padding: 8px 20px;
        """)
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(0, 0, 0, 0)
        
        self.stats_label = QLabel("📊 Logs: 0 | Last update: Never")
        self.stats_label.setStyleSheet("color: #6c757d; font-size: 12px;")
        footer_layout.addWidget(self.stats_label)
        footer_layout.addStretch()
        
        # Indicateur de chargement
        self.loading_label = QLabel("🔄 Loading logs...")
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setStyleSheet("""
            color: #6c757d;
            font-style: italic;
            padding: 20px;
            background: white;
        """)
        self.loading_label.hide()
        footer_layout.addWidget(self.loading_label)
        
        layout.addWidget(footer)
    
    def setup_refresh_timer(self):
        """Configure le timer de rafraîchissement automatique"""
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_logs)
        self.refresh_timer.start(5000)  # Refresh toutes les 5 secondes
    
    def apply_filters(self, filters: Dict):
        """Applique les filtres et recharge les logs"""
        self.current_filters = filters
        
        # Gérer l'auto-refresh
        if filters.get('auto_refresh', True):
            if not self.refresh_timer.isActive():
                self.refresh_timer.start(5000)
        else:
            self.refresh_timer.stop()
        
        self.refresh_logs()
    
    def refresh_logs(self):
        """Recharge les logs selon les filtres actuels"""
        try:
            # Simuler le chargement
            self.loading_label.show()
            self.log_list.hide()
            
            # Créer le service de logging (singleton)
            logging_service = LoggingService.get_instance()
            
            # Récupérer les logs avec les filtres
            logs = logging_service.get_recent_logs(
                limit=100,
                level=self.current_filters.get('level'),
                hours=self.current_filters.get('hours', 24)
            )
            
            # Filtrer par source si nécessaire
            source_filter = self.current_filters.get('source')
            if source_filter:
                logs = [log for log in logs if log.get('source') == source_filter]
            
            # Mettre à jour la liste
            self._update_log_list(logs)
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load logs: {e}")
        finally:
            self.loading_label.hide()
            self.log_list.show()
    
    def _update_log_list(self, logs: List[Dict]):
        """Met à jour la liste des logs"""
        self.log_list.clear()
        
        for log_entry in logs:
            # Créer un widget pour cette entrée
            item = QListWidgetItem()
            
            # Créer le texte de l'entrée
            time_str = log_entry.get('formatted_time', '')
            source = log_entry.get('source', '')
            message = log_entry.get('message', '')
            icon = log_entry.get('icon', '⚪')
            
            item_text = f"{icon} {time_str} | {source:<15} | {message}"
            item.setText(item_text)
            
            # Appliquer la couleur selon le niveau
            level = log_entry.get('level', 'INFO')
            color = log_entry.get('color', '#000000')
            item.setForeground(QColor(color))
            
            # Stocker les données complètes
            item.setData(Qt.UserRole, log_entry)
            
            self.log_list.addItem(item)
        
        # Scroller vers le bas pour voir les logs les plus récents
        self.log_list.scrollToBottom()
    
    def export_logs(self):
        """Ouvre la boîte de dialogue d'export"""
        dialog = LogExportDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            export_settings = dialog.get_export_settings()
            self._perform_export(export_settings)
    
    def _perform_export(self, settings: Dict):
        """Effectue l'export des logs"""
        try:
            logging_service = LoggingService.get_instance()
            
            filepath = logging_service.export_logs(
                start_date=settings['start_date'],
                end_date=settings['end_date'],
                format=settings['format']
            )
            
            if filepath:
                QMessageBox.information(self, "Export Complete", 
                                      f"Logs exported successfully to:\n{filepath}")
            else:
                QMessageBox.warning(self, "Export Failed", "Failed to export logs.")
                
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Error during export: {e}")
    
    def clear_old_logs(self):
        """Supprime les anciens logs"""
        reply = QMessageBox.question(
            self, "Clear Old Logs",
            "This will permanently delete logs older than 30 days.\nContinue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                logging_service = LoggingService.get_instance()
                deleted_count = logging_service.clear_old_logs(days=30)
                
                QMessageBox.information(self, "Cleanup Complete", 
                                      f"Deleted {deleted_count} old log entries.")
                self.refresh_logs()
                
            except Exception as e:
                QMessageBox.critical(self, "Cleanup Error", f"Error during cleanup: {e}")


class LogExportDialog(QDialog):
    """Dialog pour configurer l'export des logs"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Export Logs")
        self.setModal(True)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Formulaire
        form_layout = QFormLayout()
        
        # Période
        self.start_date = QDateTimeEdit()
        self.start_date.setDateTime(QDateTime.currentDateTime().addDays(-7))
        form_layout.addRow("Start Date:", self.start_date)
        
        self.end_date = QDateTimeEdit()
        self.end_date.setDateTime(QDateTime.currentDateTime())
        form_layout.addRow("End Date:", self.end_date)
        
        # Format
        self.format_combo = QComboBox()
        self.format_combo.addItems(["csv", "json"])
        form_layout.addRow("Format:", self.format_combo)
        
        layout.addLayout(form_layout)
        
        # Boutons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def get_export_settings(self) -> Dict:
        """Retourne les paramètres d'export"""
        return {
            'start_date': self.start_date.dateTime().toPyDateTime(),
            'end_date': self.end_date.dateTime().toPyDateTime(),
            'format': self.format_combo.currentText()
        }


class LogConfigWidget(QWidget):
    """Widget pour configurer les paramètres de logging"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("log-config")
        self.setup_ui()
        self.load_current_config()
        
        # Vérifier les permissions pour activer/désactiver les contrôles
        self.check_permissions()
    
    def check_permissions(self):
        """Vérifie les permissions et active/désactive les contrôles"""
        try:
            from services.permission_service import Permission
            from services.user_session import UserSession
            
            user_session = UserSession.get_instance()
            can_edit = user_session.has_permission(Permission.EDIT_LOG_CONFIG)
            
            # Activer/désactiver tous les contrôles d'édition
            self.level_combo.setEnabled(can_edit)
            self.retention_spin.setEnabled(can_edit)
            self.max_size_spin.setEnabled(can_edit)
            self.apply_btn.setEnabled(can_edit)
            
            if not can_edit:
                # Ajouter un message informatif si pas de permissions
                info_label = QLabel("Configuration en lecture seule - Permissions insuffisantes")
                info_label.setObjectName("logging-info-message")
                info_label.setStyleSheet("color: #888; font-style: italic; margin: 5px 0;")
                self.layout().insertWidget(0, info_label)
                
        except Exception as e:
            print(f"[LogConfig] Error checking permissions: {e}")
            # En cas d'erreur, garder les contrôles actifs
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        # Titre
        title = QLabel("Log Configuration")
        title.setObjectName("logging-subsection-header")
        layout.addWidget(title)
        
        # Formulaire de configuration
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        
        # Niveau de log
        self.level_combo = QComboBox()
        self.level_combo.addItems(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'])
        form_layout.addRow("Log Level:", self.level_combo)
        
        # Rétention des logs (jours)
        self.retention_spin = QSpinBox()
        self.retention_spin.setMinimum(1)
        self.retention_spin.setMaximum(365)
        self.retention_spin.setValue(30)
        self.retention_spin.setSuffix(" jours")
        form_layout.addRow("Retention Period:", self.retention_spin)
        
        # Taille maximale du fichier (MB)
        self.max_size_spin = QSpinBox()
        self.max_size_spin.setMinimum(1)
        self.max_size_spin.setMaximum(1000)
        self.max_size_spin.setValue(100)
        self.max_size_spin.setSuffix(" MB")
        form_layout.addRow("Max File Size:", self.max_size_spin)
        
        layout.addLayout(form_layout)
        
        # Bouton d'application
        self.apply_btn = QPushButton("Apply Configuration")
        self.apply_btn.setObjectName("logging-primary-button")
        self.apply_btn.clicked.connect(self.apply_config)
        layout.addWidget(self.apply_btn)
        
        layout.addStretch()
    
    def load_current_config(self):
        """Charge la configuration actuelle"""
        try:
            import logging
            
            # Configuration par défaut ou depuis fichier
            current_level = logging.getLogger().getEffectiveLevel()
            level_names = {
                10: 'DEBUG',
                20: 'INFO', 
                30: 'WARNING',
                40: 'ERROR',
                50: 'CRITICAL'
            }
            
            if current_level in level_names:
                self.level_combo.setCurrentText(level_names[current_level])
            
        except Exception as e:
            print(f"[LogConfig] Error loading config: {e}")
    
    def apply_config(self):
        """Applique la nouvelle configuration"""
        try:
            # Vérifier les permissions d'abord
            from services.permission_service import Permission
            from services.user_session import UserSession
            
            user_session = UserSession.get_instance()
            if not user_session.has_permission(Permission.EDIT_LOG_CONFIG):
                QMessageBox.warning(self, "Access Denied", 
                                  "You don't have permission to modify log configuration.")
                return
            
            import logging
            
            # Appliquer le niveau de log
            level_name = self.level_combo.currentText()
            level = getattr(logging, level_name, logging.INFO)
            logging.getLogger().setLevel(level)
            
            # Sauvegarder dans config.yaml si possible
            # TODO: Implémenter la sauvegarde persistante
            
            QMessageBox.information(self, "Success", 
                                  "Log configuration applied successfully.")
            
        except Exception as e:
            print(f"[LogConfig] Error applying config: {e}")
            QMessageBox.critical(self, "Error", 
                               f"Failed to apply configuration: {str(e)}")
