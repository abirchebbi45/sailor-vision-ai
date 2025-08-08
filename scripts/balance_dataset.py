#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script d'équilibrage du dataset - VERSION DEBUG
Ajoute des logs détaillés pour diagnostiquer les blocages
"""

import os
import sys
import shutil
import random
import cv2
import numpy as np
from pathlib import Path
import yaml
from collections import Counter, defaultdict
import time
import traceback

# Configuration des logs
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('balance_dataset_debug.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def log_progress(message, step=None, total=None):
    """Log avec progression"""
    if step is not None and total is not None:
        percentage = (step / total) * 100
        logger.info(f"{message} - [{step}/{total}] ({percentage:.1f}%)")
    else:
        logger.info(message)

def analyze_dataset_structure():
    """Analyse la structure du dataset avec logs détaillés"""
    
    logger.info("=== DÉBUT ANALYSE DATASET ===")
    
    # Vérifier les dossiers principaux
    data_dir = Path("data")
    if not data_dir.exists():
        logger.error(f"Dossier data/ non trouvé: {data_dir}")
        return None
    
    # Détecter la configuration à utiliser
    configs_to_check = [
        "data/dataset_internal_test.yaml",
        "data/dataset.yaml",
        "data/dataset_original.yaml"
    ]
    
    config_file = None
    for config_path in configs_to_check:
        if Path(config_path).exists():
            config_file = config_path
            break
    
    if not config_file:
        logger.error("Aucune configuration YAML trouvée")
        return None
    
    logger.info(f"Configuration utilisée: {config_file}")
    
    # Charger la configuration
    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        logger.info(f"Configuration chargée: {config}")
    except Exception as e:
        logger.error(f"Erreur chargement config: {e}")
        return None
    
    # Analyser chaque split
    structure = {}
    class_names = config.get('names', ['swimmer', 'swimmer with life jacket', 'boat', 'life jacket'])
    
    splits = ['train', 'val']
    for split_name in splits:
        logger.info(f"Analyse du split: {split_name}")
        
        split_path = config.get(split_name)
        if not split_path:
            logger.warning(f"Split {split_name} non défini dans config")
            continue
        
        # Convertir chemin relatif en absolu
        if split_path.startswith('../'):
            split_path = split_path.replace('../', '')
        
        split_dir = Path(split_path)
        if not split_dir.exists():
            logger.error(f"Dossier split non trouvé: {split_dir}")
            continue
        
        logger.info(f"Dossier trouvé: {split_dir}")
        
        # Compter les fichiers
        images = list(split_dir.glob("*.jpg")) + list(split_dir.glob("*.png"))
        labels = list(split_dir.glob("*.txt"))
        
        logger.info(f"{split_name}: {len(images)} images, {len(labels)} labels")
        
        if len(images) == 0:
            logger.warning(f"Aucune image dans {split_name}")
            continue
        
        # Analyser les classes
        class_counts = defaultdict(int)
        total_objects = 0
        files_processed = 0
        
        logger.info(f"Début analyse des classes pour {split_name}...")
        
        for i, label_file in enumerate(labels):
            try:
                if i % 1000 == 0 and i > 0:
                    log_progress(f"Analyse classes {split_name}", i, len(labels))
                
                with open(label_file, 'r') as f:
                    lines = f.readlines()
                    for line in lines:
                        line = line.strip()
                        if line:
                            parts = line.split()
                            if len(parts) >= 5:
                                class_id = int(parts[0])
                                if 0 <= class_id < len(class_names):
                                    class_counts[class_id] += 1
                                    total_objects += 1
                files_processed += 1
                
            except Exception as e:
                logger.warning(f"Erreur fichier {label_file}: {e}")
                continue
        
        logger.info(f"{split_name}: {files_processed} fichiers traités, {total_objects} objets")
        
        # Afficher distribution
        for class_id, count in class_counts.items():
            percentage = (count / total_objects * 100) if total_objects > 0 else 0
            logger.info(f"  {class_names[class_id]}: {count} ({percentage:.1f}%)")
        
        structure[split_name] = {
            'path': split_dir,
            'images': len(images),
            'labels': len(labels),
            'class_counts': dict(class_counts),
            'total_objects': total_objects
        }
    
    logger.info("=== FIN ANALYSE DATASET ===")
    return structure, class_names, config

def calculate_balance_strategy(structure, class_names):
    """Calcule la stratégie d'équilibrage avec logs"""
    
    logger.info("=== CALCUL STRATÉGIE D'ÉQUILIBRAGE ===")
    
    # Fusionner les comptages train + val
    total_class_counts = defaultdict(int)
    for split_data in structure.values():
        for class_id, count in split_data['class_counts'].items():
            total_class_counts[class_id] += count
    
    total_objects = sum(total_class_counts.values())
    logger.info(f"Total objets dans dataset: {total_objects}")
    
    # Trouver les déséquilibres
    max_count = max(total_class_counts.values()) if total_class_counts else 1
    min_count = min(total_class_counts.values()) if total_class_counts else 1
    imbalance_ratio = max_count / min_count if min_count > 0 else float('inf')
    
    logger.info(f"Ratio déséquilibre: {imbalance_ratio:.1f}:1")
    
    # Stratégie: augmenter les classes minoritaires
    target_count = max_count // 2  # Cible à 50% de la classe majoritaire
    
    augmentation_needed = {}
    for class_id, count in total_class_counts.items():
        if count < target_count:
            multiplier = target_count / count if count > 0 else 2
            augmentation_needed[class_id] = max(1, int(multiplier))
            logger.info(f"{class_names[class_id]}: {count} -> {count * augmentation_needed[class_id]} (x{augmentation_needed[class_id]})")
    
    logger.info("=== FIN CALCUL STRATÉGIE ===")
    return augmentation_needed, target_count

def create_balanced_dataset(structure, class_names, config, augmentation_needed):
    """Crée le dataset équilibré avec logs détaillés"""
    
    logger.info("=== CRÉATION DATASET ÉQUILIBRÉ ===")
    
    # Créer le dossier de sortie
    output_dir = Path("data_balanced")
    output_dir.mkdir(exist_ok=True)
    
    # Créer la structure
    for split_name in structure.keys():
        split_output_dir = output_dir / "images" / split_name
        split_output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Dossier créé: {split_output_dir}")
    
    # Copier et augmenter les données
    for split_name, split_data in structure.items():
        logger.info(f"Traitement split: {split_name}")
        
        source_dir = split_data['path']
        target_dir = output_dir / "images" / split_name
        
        # Copier tous les fichiers existants
        source_images = list(source_dir.glob("*.jpg")) + list(source_dir.glob("*.png"))
        logger.info(f"Copie de {len(source_images)} images existantes...")
        
        copied_count = 0
        for i, img_file in enumerate(source_images):
            if i % 500 == 0 and i > 0:
                log_progress(f"Copie {split_name}", i, len(source_images))
            
            try:
                # Copier image
                shutil.copy2(img_file, target_dir / img_file.name)
                
                # Copier label
                label_file = source_dir / (img_file.stem + ".txt")
                if label_file.exists():
                    shutil.copy2(label_file, target_dir / label_file.name)
                
                copied_count += 1
                
            except Exception as e:
                logger.warning(f"Erreur copie {img_file}: {e}")
        
        logger.info(f"{split_name}: {copied_count} fichiers copiés")
        
        # Générer augmentations pour classes minoritaires
        logger.info(f"Génération augmentations pour {split_name}...")
        
        augmented_count = 0
        for class_id, multiplier in augmentation_needed.items():
            if multiplier <= 1:
                continue
            
            logger.info(f"Augmentation classe {class_names[class_id]} (x{multiplier})...")
            
            # Trouver les images de cette classe
            class_images = find_images_with_class(source_dir, class_id)
            logger.info(f"Trouvé {len(class_images)} images avec classe {class_names[class_id]}")
            
            if len(class_images) == 0:
                continue
            
            # Générer les augmentations
            augmentations_to_create = len(class_images) * (multiplier - 1)
            logger.info(f"Création de {augmentations_to_create} augmentations...")
            
            for i in range(augmentations_to_create):
                if i % 100 == 0 and i > 0:
                    log_progress(f"Augmentation classe {class_names[class_id]}", i, augmentations_to_create)
                
                # Sélectionner image source aléatoire
                source_img_path = random.choice(class_images)
                
                try:
                    # Créer augmentation
                    create_augmentation(
                        source_img_path,
                        target_dir,
                        f"aug_{class_id}_{i}_{source_img_path.stem}"
                    )
                    augmented_count += 1
                    
                except Exception as e:
                    logger.warning(f"Erreur augmentation {source_img_path}: {e}")
        
        logger.info(f"{split_name}: {augmented_count} augmentations créées")
    
    # Créer la configuration YAML
    create_balanced_config(config, output_dir)
    
    logger.info("=== FIN CRÉATION DATASET ÉQUILIBRÉ ===")

def find_images_with_class(source_dir, target_class_id):
    """Trouve les images contenant une classe spécifique"""
    
    images_with_class = []
    label_files = list(source_dir.glob("*.txt"))
    
    for label_file in label_files:
        try:
            with open(label_file, 'r') as f:
                lines = f.readlines()
                for line in lines:
                    line = line.strip()
                    if line:
                        parts = line.split()
                        if len(parts) >= 5:
                            class_id = int(parts[0])
                            if class_id == target_class_id:
                                # Trouver l'image correspondante
                                img_name = label_file.stem
                                for ext in ['.jpg', '.png', '.jpeg']:
                                    img_file = source_dir / (img_name + ext)
                                    if img_file.exists():
                                        images_with_class.append(img_file)
                                        break
                                break
        except Exception as e:
            logger.warning(f"Erreur lecture {label_file}: {e}")
    
    return images_with_class

def create_augmentation(source_img_path, target_dir, new_name):
    """Crée une augmentation d'image avec logs"""
    
    try:
        # Lire l'image
        img = cv2.imread(str(source_img_path))
        if img is None:
            logger.warning(f"Impossible de lire {source_img_path}")
            return False
        
        # Appliquer augmentations simples et rapides
        augmented = apply_simple_augmentation(img)
        
        # Sauvegarder image augmentée
        new_img_path = target_dir / f"{new_name}.jpg"
        cv2.imwrite(str(new_img_path), augmented)
        
        # Copier le label
        source_label = source_img_path.parent / (source_img_path.stem + ".txt")
        if source_label.exists():
            new_label_path = target_dir / f"{new_name}.txt"
            shutil.copy2(source_label, new_label_path)
        
        return True
        
    except Exception as e:
        logger.warning(f"Erreur augmentation {source_img_path}: {e}")
        return False

def apply_simple_augmentation(img):
    """Applique des augmentations simples et rapides"""
    
    # Choisir une augmentation aléatoire
    augmentation_type = random.choice(['brightness', 'flip', 'noise', 'blur'])
    
    if augmentation_type == 'brightness':
        # Ajustement luminosité
        factor = random.uniform(0.7, 1.3)
        return cv2.convertScaleAbs(img, alpha=factor, beta=0)
    
    elif augmentation_type == 'flip':
        # Flip horizontal
        return cv2.flip(img, 1)
    
    elif augmentation_type == 'noise':
        # Bruit gaussien léger
        noise = np.random.normal(0, 10, img.shape).astype(np.uint8)
        return cv2.add(img, noise)
    
    elif augmentation_type == 'blur':
        # Flou léger
        return cv2.GaussianBlur(img, (3, 3), 0)
    
    return img

def create_balanced_config(original_config, output_dir):
    """Crée la configuration pour le dataset équilibré"""
    
    logger.info("Création configuration dataset équilibré...")
    
    balanced_config = original_config.copy()
    balanced_config['train'] = f"../{output_dir}/images/train"
    balanced_config['val'] = f"../{output_dir}/images/val"
    
    config_path = output_dir / "dataset_balanced.yaml"
    with open(config_path, 'w') as f:
        yaml.dump(balanced_config, f, default_flow_style=False)
    
    logger.info(f"Configuration sauvegardée: {config_path}")

def main():
    """Fonction principale avec gestion d'erreurs"""
    
    start_time = time.time()
    logger.info("=== DÉBUT ÉQUILIBRAGE DATASET ===")
    
    try:
        # Étape 1: Analyser la structure
        logger.info("ÉTAPE 1: Analyse structure dataset")
        result = analyze_dataset_structure()
        if not result:
            logger.error("Échec analyse dataset")
            return False
        
        structure, class_names, config = result
        logger.info("Analyse terminée avec succès")
        
        # Étape 2: Calculer stratégie
        logger.info("ÉTAPE 2: Calcul stratégie équilibrage")
        augmentation_needed, target_count = calculate_balance_strategy(structure, class_names)
        
        if not augmentation_needed:
            logger.info("Dataset déjà équilibré - Aucune action nécessaire")
            return True
        
        # Étape 3: Créer dataset équilibré
        logger.info("ÉTAPE 3: Création dataset équilibré")
        create_balanced_dataset(structure, class_names, config, augmentation_needed)
        
        duration = time.time() - start_time
        logger.info(f"=== ÉQUILIBRAGE TERMINÉ - Durée: {duration:.1f}s ===")
        
        return True
        
    except Exception as e:
        logger.error(f"Erreur critique: {e}")
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)