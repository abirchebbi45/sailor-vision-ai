import json
import yaml
import os

# 🔹 Charger la configuration depuis config.yaml
config_path = "config.yaml"  # Chemin du fichier de configuration

with open(config_path, "r", encoding="utf-8") as config_file:
    config = yaml.safe_load(config_file)

# 🔹 Récupérer les fichiers d'annotations depuis la configuration
annotations_files = {
    "train": config["paths"]["train_annotations_file"],
    "val": config["paths"]["val_annotations_file"],
    "test": config["paths"]["test_annotations_file"],
}

# 🔹 Fonction pour modifier les fichiers JSON
def update_annotations(file_path):
    if not os.path.exists(file_path):
        print(f"Fichier introuvable : {file_path}")
        return

    with open(file_path, "r", encoding="utf-8") as file:
        coco_data = json.load(file)

    if "images" not in coco_data:
        print(f"Clé 'images' non trouvée dans {file_path}")
        return

    # Modifier les noms de fichiers d'images (.png → .jpg)
    for img in coco_data["images"]:
        if "file_name" in img and img["file_name"].endswith(".png"):
            img["file_name"] = img["file_name"].replace(".png", ".jpg")

    # 🔹 Enregistrer un nouveau fichier sans écraser l'original
    new_file_path = file_path.replace(".json", "_updated.json")
    with open(new_file_path, "w", encoding="utf-8") as file:
        json.dump(coco_data, file, indent=4)

    print(f"Fichier mis à jour : {new_file_path}")

# Appliquer la mise à jour aux fichiers train, val et test
for key, path in annotations_files.items():
    print(f"Mise à jour du fichier d'annotations {key}...")
    update_annotations(path)

print("Tous les fichiers d'annotations ont été mis à jour !")
