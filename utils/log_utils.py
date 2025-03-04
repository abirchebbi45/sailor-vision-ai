import os
from datetime import datetime

def log_event(event_message):
    """
    Enregistre un événement dans le fichier log.txt à la racine du projet.
    """
    log_file_path = os.path.join(os.path.dirname(__file__), '..', 'log.txt')

    # S'assure que le dossier parent existe
    if not os.path.exists(os.path.dirname(log_file_path)):
        os.makedirs(os.path.dirname(log_file_path))

    # Enregistre le message avec horodatage
    with open(log_file_path, "a", encoding="utf-8") as log_file:
        timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        log_file.write(f"{timestamp} {event_message}\n")
