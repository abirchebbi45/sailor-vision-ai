"""
Composant de notification pour les nouvelles caméras détectées
Affiche une notification temporaire en haut de l'écran
"""

from PyQt5.QtWidgets import (QWidget, QLabel, QHBoxLayout, QPushButton, 
                           QGraphicsOpacityEffect, QFrame)
from PyQt5.QtCore import QTimer, QPropertyAnimation, QEasingCurve, pyqtSignal
from PyQt5.QtGui import QFont, QPalette
from PyQt5.QtCore import Qt
import logging

logger = logging.getLogger(__name__)

class CameraNotification(QFrame):
    """
    Widget de notification pour les nouvelles caméras détectées
    Affiche une barre de notification temporaire avec animation
    """
    
    # Signal émis quand l'utilisateur clique sur "Voir les caméras"
    view_cameras_clicked = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.setup_animation()
        self.auto_hide_timer = QTimer()
        self.auto_hide_timer.setSingleShot(True)
        self.auto_hide_timer.timeout.connect(self.hide_notification)
    
    def setup_ui(self):
        """Configuration de l'interface utilisateur"""
        self.setFixedHeight(60)
        self.setFrameStyle(QFrame.Box)
        self.setLineWidth(2)
        
        # Style de la notification
        self.setStyleSheet("""
            CameraNotification {
                background-color: #2E7D32;
                border: 2px solid #1B5E20;
                border-radius: 8px;
                color: white;
            }
            QLabel {
                color: white;
                font-weight: bold;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #66BB6A;
            }
            QPushButton:pressed {
                background-color: #388E3C;
            }
        """)
        
        # Layout principal
        layout = QHBoxLayout()
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(15)
        
        # Icône (emoji ou texte)
        icon_label = QLabel("📷")
        icon_label.setFont(QFont("Arial", 16))
        layout.addWidget(icon_label)
        
        # Message de notification
        self.message_label = QLabel("Nouvelle caméra détectée!")
        self.message_label.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(self.message_label)
        
        # Spacer pour pousser les boutons à droite
        layout.addStretch()
        
        # Bouton "Voir les caméras"
        self.view_button = QPushButton("Voir les caméras")
        self.view_button.clicked.connect(self.view_cameras_clicked.emit)
        layout.addWidget(self.view_button)
        
        # Bouton fermer
        self.close_button = QPushButton("✕")
        self.close_button.setFixedSize(30, 30)
        self.close_button.clicked.connect(self.hide_notification)
        layout.addWidget(self.close_button)
        
        self.setLayout(layout)
        
        # Cacher initialement
        self.hide()
    
    def setup_animation(self):
        """Configuration des animations"""
        self.opacity_effect = QGraphicsOpacityEffect()
        self.setGraphicsEffect(self.opacity_effect)
        
        # Animation de fondu
        self.fade_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_animation.setDuration(300)
        self.fade_animation.setEasingCurve(QEasingCurve.OutCubic)
        self.fade_animation.finished.connect(self._animation_finished)
        
        self._hiding = False
    
    def show_notification(self, camera_name: str, camera_ip: str, pending_count: int = 1):
        """
        Afficher la notification pour une nouvelle caméra
        
        Args:
            camera_name: Nom de la caméra détectée
            camera_ip: Adresse IP de la caméra
            pending_count: Nombre total de caméras en attente
        """
        try:
            # Mettre à jour le message
            if pending_count == 1:
                message = f"Nouvelle caméra détectée: {camera_name} ({camera_ip})"
            else:
                message = f"Nouvelle caméra détectée: {camera_name} ({camera_ip}) - {pending_count} caméras en attente"
            
            self.message_label.setText(message)
            
            # Montrer le widget
            self.show()
            
            # Animation de fondu entrant
            self.fade_animation.setStartValue(0.0)
            self.fade_animation.setEndValue(1.0)
            self.fade_animation.start()
            
            # Auto-masquer après 10 secondes
            self.auto_hide_timer.start(10000)
            
            logger.info(f"[CameraNotification] Notification affichée: {camera_name}")
        except Exception as e:
            logger.error(f"Error showing notification: {e}")
    
    def hide_notification(self):
        """Masquer la notification avec animation"""
        try:
            if self._hiding:
                return
                
            self._hiding = True
            self.auto_hide_timer.stop()
            
            # Animation de fondu sortant
            self.fade_animation.setStartValue(1.0)
            self.fade_animation.setEndValue(0.0)
            self.fade_animation.start()
        except Exception as e:
            logger.error(f"Error hiding notification: {e}")
            # Fallback in case of animation failure
            self.hide()
            self._hiding = False
    
    def _animation_finished(self):
        """Appelé à la fin de l'animation"""
        try:
            if self._hiding:
                self.hide()
                self._hiding = False
        except Exception as e:
            logger.error(f"Error in animation finished: {e}")
            # Force hide in case of error
            self.hide()
            self._hiding = False
    
    def update_pending_count(self, pending_count: int):
        """Mettre à jour le nombre de caméras en attente dans la notification"""
        try:
            if self.isVisible() and pending_count > 0:
                current_text = self.message_label.text()
                # Extraire le nom de la caméra du texte actuel
                if " - " in current_text:
                    base_text = current_text.split(" - ")[0]
                else:
                    base_text = current_text
                
                if pending_count == 1:
                    self.message_label.setText(base_text)
                else:
                    self.message_label.setText(f"{base_text} - {pending_count} caméras en attente")
        except Exception as e:
            logger.error(f"Error updating pending count: {e}")


class NotificationManager(QWidget):
    """
    Gestionnaire de notifications qui peut être intégré dans la fenêtre principale
    """
    
    # Signal émis quand l'utilisateur veut voir les caméras en attente
    view_pending_cameras = pyqtSignal()
    # Signal for navigating to live feed
    navigate_to_live_feed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.current_notifications = []
    
    def setup_ui(self):
        """Configuration de l'interface utilisateur"""
        self.setFixedHeight(0)  # Hauteur dynamique
        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(10, 5, 10, 5)
        self.setLayout(self.layout)
        
        # Style du conteneur
        self.setStyleSheet("""
            NotificationManager {
                background-color: transparent;
            }
        """)
    
    def show_camera_notification(self, camera_name: str, camera_ip: str, pending_count: int = 1):
        """
        Afficher une notification pour une nouvelle caméra
        """
        try:
            # Créer la notification
            notification = CameraNotification(self)
            notification.view_cameras_clicked.connect(self.view_pending_cameras.emit)
            
            # Ajouter au layout
            self.layout.addWidget(notification)
            self.current_notifications.append(notification)
            
            # Ajuster la hauteur
            self.setFixedHeight(70)
            
            # Afficher la notification
            notification.show_notification(camera_name, camera_ip, pending_count)
            
            # Connecter le signal de fermeture
            notification.close_button.clicked.connect(
                lambda: self.remove_notification(notification)
            )
            
            logger.info(f"Camera notification shown for {camera_name} ({camera_ip})")
        except Exception as e:
            logger.error(f"Error showing camera notification: {e}")
    
    def show_approval_notification(self, camera_name: str):
        """
        Afficher une notification pour une caméra approuvée
        """
        try:
            # Créer la notification
            notification = CameraNotification(self)
            
            # Modifier le style pour le succès
            notification.setStyleSheet("""
                CameraNotification {
                    background-color: #28a745;
                    border: 2px solid #1e7e34;
                    border-radius: 8px;
                    color: white;
                }
                QLabel {
                    color: white;
                    font-weight: bold;
                }
                QPushButton {
                    background-color: #34ce57;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #28a745;
                }
            """)
            
            # Ajouter au layout
            self.layout.addWidget(notification)
            self.current_notifications.append(notification)
            
            # Ajuster la hauteur
            self.setFixedHeight(70)
            
            # Afficher la notification avec un message personnalisé
            notification.message_label.setText(f"✅ Caméra {camera_name} approuvée avec succès!")
            notification.view_button.setText("Voir Live Feed")
            
            # Connecter pour naviguer vers le Live Feed
            notification.view_button.clicked.connect(
                lambda: self.navigate_to_live_feed.emit() if hasattr(self, 'navigate_to_live_feed') else None
            )
            
            # Afficher
            notification.show()
            notification.fade_animation.setStartValue(0.0)
            notification.fade_animation.setEndValue(1.0)
            notification.fade_animation.start()
            
            # Auto-masquer après 5 secondes (plus court pour les notifications de succès)
            notification.auto_hide_timer.start(5000)
            
            # Connecter le signal de fermeture
            notification.close_button.clicked.connect(
                lambda: self.remove_notification(notification)
            )
            
            logger.info(f"Camera approval notification shown for {camera_name}")
        except Exception as e:
            logger.error(f"Error showing approval notification: {e}")

    def remove_notification(self, notification: CameraNotification):
        """Supprimer une notification"""
        try:
            if notification in self.current_notifications:
                self.current_notifications.remove(notification)
                notification.deleteLater()
                
                # Ajuster la hauteur
                if not self.current_notifications:
                    self.setFixedHeight(0)
        except Exception as e:
            logger.error(f"Error removing notification: {e}")
    
    def update_pending_count(self, pending_count: int):
        """Update the pending count in all active notifications"""
        try:
            for notification in self.current_notifications:
                notification.update_pending_count(pending_count)
        except Exception as e:
            logger.error(f"Error updating pending count: {e}")
    
    def clear_all_notifications(self):
        """Supprimer toutes les notifications"""
        try:
            for notification in self.current_notifications:
                notification.deleteLater()
            self.current_notifications.clear()
            self.setFixedHeight(0)
            logger.info("All notifications cleared")
        except Exception as e:
            logger.error(f"Error clearing notifications: {e}")
