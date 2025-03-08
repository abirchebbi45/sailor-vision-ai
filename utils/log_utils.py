import os
from datetime import datetime


def log_event(event_message):
    """
    Enregistre un événement dans le fichier log.txt à la racine du projet et l'affiche dans la console.

    Args:
        event_message (str): Le message à enregistrer et à afficher.
    """
    log_file_path = os.path.join(os.path.dirname(__file__), "..", "log.txt")

    # S'assure que le dossier parent existe
    if not os.path.exists(os.path.dirname(log_file_path)):
        os.makedirs(os.path.dirname(log_file_path))

    # Enregistre le message avec horodatage
    timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    log_message = f"{timestamp} {event_message}"

    # Écrire dans le fichier log.txt
    with open(log_file_path, "a", encoding="utf-8") as log_file:
        log_file.write(log_message + "\n")

    # Afficher le message dans la console
    print(log_message)
