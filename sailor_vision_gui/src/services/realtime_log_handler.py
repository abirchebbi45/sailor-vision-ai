"""
Handler personnalisé pour capturer les logs Python en temps réel
et les intégrer dans le système de monitoring
"""

import logging
import json
from datetime import datetime
from collections import deque
from typing import List, Callable
from PyQt5.QtCore import QObject, pyqtSignal
import weakref

from database import create_new_session, close_session
from models import SystemLog

class RealtimeLogHandler(logging.Handler, QObject):
    """Handler personnalisé pour capturer les logs Python en temps réel"""
    
    # Signaux PyQt
    log_captured = pyqtSignal(dict)  # Émis quand un nouveau log est capturé
    
    def __init__(self, level=logging.INFO):
        logging.Handler.__init__(self, level)
        QObject.__init__(self)
        
        # Buffer circulaire pour les logs récents
        self.recent_logs = deque(maxlen=500)
        
        # Observers faibles pour éviter les fuites mémoire
        self.observers = weakref.WeakSet()
        
        # Configuration
        self.store_to_db = True
        self.emit_signals = True
        
        # Filtres pour éviter le spam
        self.ignored_sources = {
            'urllib3.connectionpool',
            'requests.packages.urllib3.connectionpool',
            'PIL.PngImagePlugin'
        }
        
        # Compteurs pour les statistiques
        self.log_counts = {
            'INFO': 0,
            'WARNING': 0,
            'ERROR': 0,
            'DEBUG': 0
        }
        
        self.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
    
    def emit(self, record):
        """Traite un nouveau log record"""
        try:
            # Filtrer les sources ignorées
            if record.name in self.ignored_sources:
                return
            
            # Créer l'entrée de log
            log_entry = self._format_log_entry(record)
            
            # Ajouter au buffer
            self.recent_logs.append(log_entry)
            
            # Mettre à jour les compteurs
            level = record.levelname
            if level in self.log_counts:
                self.log_counts[level] += 1
            
            # Stocker en base de données si configuré
            if self.store_to_db and level in ['WARNING', 'ERROR']:
                self._store_to_database(log_entry)
            
            # Émettre le signal si configuré
            if self.emit_signals:
                self.log_captured.emit(log_entry)
            
            # Notifier les observers
            self._notify_observers(log_entry)
            
        except Exception as e:
            # Éviter les boucles infinies en cas d'erreur dans le handler
            print(f"Error in RealtimeLogHandler: {e}")
    
    def _format_log_entry(self, record) -> dict:
        """Formate un log record en dictionnaire"""
        timestamp = datetime.fromtimestamp(record.created)
        
        # Extraire des informations supplémentaires du message
        message = record.getMessage()
        
        # Déterminer la source principale
        source = self._extract_main_source(record.name)
        
        return {
            'id': None,  # Sera défini lors de l'insertion en DB
            'timestamp': timestamp,
            'level': record.levelname,
            'source': source,
            'message': message,
            'module': record.name,
            'filename': record.filename,
            'line_number': record.lineno,
            'function_name': record.funcName,
            'formatted_time': timestamp.strftime('%H:%M:%S'),
            'formatted_date': timestamp.strftime('%Y-%m-%d'),
            'icon': self._get_level_icon(record.levelname),
            'color': self._get_level_color(record.levelname),
            'severity_score': self._calculate_severity_score(record)
        }
    
    def _extract_main_source(self, module_name: str) -> str:
        """Extrait le nom principal du service depuis le nom du module"""
        if 'camera' in module_name.lower():
            return 'CameraService'
        elif 'yolo' in module_name.lower() or 'detection' in module_name.lower():
            return 'YOLODetection'
        elif 'alert' in module_name.lower():
            return 'AlertService'
        elif 'auth' in module_name.lower() or 'user' in module_name.lower():
            return 'UserService'
        elif 'storage' in module_name.lower() or 'database' in module_name.lower():
            return 'StorageService'
        elif 'ros' in module_name.lower():
            return 'ROSCommunication'
        elif 'gui' in module_name.lower() or 'component' in module_name.lower():
            return 'GUIApplication'
        else:
            return module_name.split('.')[-1] if '.' in module_name else module_name
    
    def _calculate_severity_score(self, record) -> int:
        """Calcule un score de sévérité pour le log"""
        base_scores = {
            'DEBUG': 1,
            'INFO': 2,
            'WARNING': 5,
            'ERROR': 8,
            'CRITICAL': 10
        }
        
        score = base_scores.get(record.levelname, 2)
        
        # Augmenter le score pour certains mots-clés critiques
        message = record.getMessage().lower()
        critical_keywords = {
            'failed': 2,
            'error': 1,
            'timeout': 2,
            'connection': 1,
            'database': 1,
            'camera': 1,
            'detection': 1
        }
        
        for keyword, bonus in critical_keywords.items():
            if keyword in message:
                score += bonus
        
        return min(score, 15)  # Limiter le score maximum
    
    def _store_to_database(self, log_entry: dict):
        """Stocke le log en base de données"""
        try:
            session = create_new_session()
            
            system_log = SystemLog(
                level=log_entry['level'],
                source=log_entry['source'],
                message=log_entry['message'],
                timestamp=log_entry['timestamp']
            )
            
            session.add(system_log)
            session.commit()
            
            # Mettre à jour l'ID dans l'entrée
            log_entry['id'] = system_log.id
            
        except Exception as e:
            print(f"Error storing log to database: {e}")
        finally:
            close_session(session)
    
    def _notify_observers(self, log_entry: dict):
        """Notifie tous les observers enregistrés"""
        # Utiliser une liste pour éviter les modifications pendant l'itération
        observers_list = list(self.observers)
        for observer in observers_list:
            try:
                if hasattr(observer, 'on_new_log'):
                    observer.on_new_log(log_entry)
            except Exception as e:
                print(f"Error notifying observer: {e}")
    
    def add_observer(self, observer):
        """Ajoute un observer pour les nouveaux logs"""
        self.observers.add(observer)
    
    def remove_observer(self, observer):
        """Supprime un observer"""
        self.observers.discard(observer)
    
    def get_recent_logs(self, count: int = 50) -> List[dict]:
        """Récupère les logs récents du buffer"""
        recent_count = min(count, len(self.recent_logs))
        return list(self.recent_logs)[-recent_count:]
    
    def get_log_statistics(self) -> dict:
        """Récupère les statistiques des logs capturés"""
        total_logs = sum(self.log_counts.values())
        
        return {
            'total_logs': total_logs,
            'by_level': dict(self.log_counts),
            'buffer_size': len(self.recent_logs),
            'error_rate': (self.log_counts['ERROR'] / max(total_logs, 1)) * 100,
            'warning_rate': (self.log_counts['WARNING'] / max(total_logs, 1)) * 100
        }
    
    def clear_statistics(self):
        """Remet à zéro les statistiques"""
        for level in self.log_counts:
            self.log_counts[level] = 0
    
    def set_database_storage(self, enabled: bool):
        """Active/désactive le stockage en base de données"""
        self.store_to_db = enabled
    
    def set_signal_emission(self, enabled: bool):
        """Active/désactive l'émission des signaux PyQt"""
        self.emit_signals = enabled
    
    def _get_level_icon(self, level: str) -> str:
        """Retourne l'icône pour un niveau de log"""
        icons = {
            'DEBUG': '🔵',
            'INFO': '🟢',
            'WARNING': '🟡',
            'ERROR': '🔴',
            'CRITICAL': '🚨'
        }
        return icons.get(level, '⚪')
    
    def _get_level_color(self, level: str) -> str:
        """Retourne la couleur pour un niveau de log"""
        colors = {
            'DEBUG': '#2196F3',
            'INFO': '#4CAF50',
            'WARNING': '#FF9800',
            'ERROR': '#F44336',
            'CRITICAL': '#E91E63'
        }
        return colors.get(level, '#9E9E9E')


class LogManager(QObject):
    """Gestionnaire principal pour l'intégration des logs temps réel"""
    
    log_received = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        
        # Créer le handler personnalisé
        self.realtime_handler = RealtimeLogHandler()
        
        # Connecter les signaux
        self.realtime_handler.log_captured.connect(self.log_received.emit)
        
        # Configuration du handler
        self.realtime_handler.setLevel(logging.INFO)
        
        # Liste des loggers Python à monitorer
        self.monitored_loggers = [
            'src.services.camera_service',
            'src.services.alert_service',
            'src.services.user_service',
            'src.services.storage_service',
            'shared.detection_recorder',
            'shared.ros_watchdog',
            'database'
        ]
        
        self.installed = False
    
    def install_handler(self):
        """Installe le handler sur les loggers système"""
        if self.installed:
            return
        
        # Ajouter à tous les loggers monitorés
        for logger_name in self.monitored_loggers:
            logger = logging.getLogger(logger_name)
            logger.addHandler(self.realtime_handler)
        
        # Ajouter au logger racine pour capturer tous les logs
        root_logger = logging.getLogger()
        root_logger.addHandler(self.realtime_handler)
        
        self.installed = True
        print("RealtimeLogHandler installed successfully")
    
    def uninstall_handler(self):
        """Désinstalle le handler"""
        if not self.installed:
            return
        
        # Retirer de tous les loggers
        for logger_name in self.monitored_loggers:
            logger = logging.getLogger(logger_name)
            logger.removeHandler(self.realtime_handler)
        
        root_logger = logging.getLogger()
        root_logger.removeHandler(self.realtime_handler)
        
        self.installed = False
        print("RealtimeLogHandler uninstalled")
    
    def get_handler(self) -> RealtimeLogHandler:
        """Retourne le handler pour accès direct"""
        return self.realtime_handler
    
    def add_observer(self, observer):
        """Ajoute un observer pour les logs"""
        self.realtime_handler.add_observer(observer)
    
    def remove_observer(self, observer):
        """Supprime un observer"""
        self.realtime_handler.remove_observer(observer)


# Instance globale pour l'application
log_manager = LogManager()
