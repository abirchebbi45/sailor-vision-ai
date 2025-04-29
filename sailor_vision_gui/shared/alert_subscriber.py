# alert_subscriber.py
from PyQt5.QtCore import QObject, pyqtSignal
from std_msgs.msg import String
import json, logging

logger = logging.getLogger(__name__)

class ROSAlertBridge(QObject):
    alert_received = pyqtSignal(object)

    def __init__(self, node):
        super().__init__()
        node.create_subscription(
            String,
            '/yolo/alerts',
            self.callback,
            10
        )

    def callback(self, msg):
        try:
            data = json.loads(msg.data)
            logger.info(f"ROSAlertBridge received {len(data.get('detections', []))} detections")
            self.alert_received.emit(data)
        except Exception as e:
            logger.error(f"Erreur dans ROSAlertBridge.callback: {e}")
