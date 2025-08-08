#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script pour créer un split de test alternatif depuis les données de validation
CORRIGÉ: Les annotations .txt sont maintenant placées avec les images
Étant donné que le test set de SeaDronesSee n'a pas d'annotations GT
"""

import os
import json
import shutil
import random
from pathlib import Path
import yaml

def create_validation_test_split(val_ratio=0.7, test_ratio=0.3, seed=42):
    """
    Divise l'ensemble de validation en deux parties :
    - Nouvelle validation (70%)
    - Test interne avec GT (30%)
    CORRIGÉ: Gère la structure YOLO (annotations avec images)
    """
    
    print("=== CREATION D'UN SPLIT DE TEST ALTERNATIF ===")
    print("CORRECTIF: Structure YOLO détectée (annotations avec images)")
    print("=" * 50)
    print("Contexte: SeaDronesSee test set n'a pas d'annotations GT")
    print(f"Solution: Diviser validation -> {val_ratio*100:.0f}% val + {test_ratio*100:.0f}% test")
    
    # Définir les chemins - STRUCTURE YOLO
    original_val_dir = Path("data/images/val")
    
    # Nouveaux dossiers (images ET labels dans le même dossier)
    new_val_dir = Path("data/images/val_new")
    new_test_dir = Path("data/images/test_internal")
    
    # Dossiers de sauvegarde
    backup_val_dir = Path("data/images/val_original_backup")
    
    # Vérifier que le dossier original existe
    if not original_val_dir.exists():
        print(f"❌ Dossier validation non trouvé: {original_val_dir}")
        return False
    
    # Vérifier qu'il contient des images ET des annotations
    images = list(original_val_dir.glob("*.jpg")) + list(original_val_dir.glob("*.png"))
    labels = list(original_val_dir.glob("*.txt"))
    
    if not images:
        print("❌ Aucune image trouvée dans le dossier de validation!")
        return False
    
    if not labels:
        print("❌ Aucune annotation trouvée dans le dossier de validation!")
        return False
    
    print(f"✅ Structure YOLO détectée: {len(images)} images, {len(labels)} annotations")
    
    # Créer les nouveaux dossiers
    for folder in [new_val_dir, new_test_dir, backup_val_dir]:
        folder.mkdir(parents=True, exist_ok=True)
    
    # Mélanger avec seed fixe pour reproductibilité
    random.seed(seed)
    random.shuffle(images)
    
    # Calculer les tailles des splits
    total_images = len(images)
    val_size = int(total_images * val_ratio)
    test_size = total_images - val_size
    
    print(f"Division:")
    print(f"   Nouvelle validation: {val_size} images ({val_ratio*100:.0f}%)")
    print(f"   Nouveau test interne: {test_size} images ({test_ratio*100:.0f}%)")
    
    # Diviser les fichiers
    val_files = images[:val_size]
    test_files = images[val_size:]
    
    # SAUVEGARDE ORIGINALE (une seule fois)
    if not backup_val_dir.exists() or len(list(backup_val_dir.glob("*"))) == 0:
        print("\nSauvegarde des données originales...")
        shutil.copytree(original_val_dir, backup_val_dir, dirs_exist_ok=True)
        print("✅ Sauvegarde terminée")
    
    # Copier les fichiers - NOUVELLE VALIDATION
    print(f"\nCopie nouvelle validation ({len(val_files)} fichiers)...")
    val_copied = 0
    val_labels_copied = 0
    
    for img_file in val_files:
        # Copier l'image
        shutil.copy2(img_file, new_val_dir / img_file.name)
        val_copied += 1
        
        # Copier le label correspondant (même dossier source)
        label_name = img_file.stem + ".txt"
        label_file = original_val_dir / label_name  # Même dossier que l'image
        if label_file.exists():
            shutil.copy2(label_file, new_val_dir / label_name)
            val_labels_copied += 1
    
    print(f"✅ Validation: {val_copied} images, {val_labels_copied} annotations")
    
    # Copier les fichiers - NOUVEAU TEST INTERNE  
    print(f"\nCopie test interne ({len(test_files)} fichiers)...")
    test_copied = 0
    test_labels_copied = 0
    
    for img_file in test_files:
        # Copier l'image
        shutil.copy2(img_file, new_test_dir / img_file.name)
        test_copied += 1
        
        # Copier le label correspondant (même dossier source)
        label_name = img_file.stem + ".txt"
        label_file = original_val_dir / label_name  # Même dossier que l'image
        if label_file.exists():
            shutil.copy2(label_file, new_test_dir / label_name)
            test_labels_copied += 1
    
    print(f"✅ Test interne: {test_copied} images, {test_labels_copied} annotations")
    
    # Créer les fichiers de configuration YAML
    create_dataset_configs()
    
    # Vérifier la structure finale
    verify_structure()
    
    return True

def create_dataset_configs():
    """Créer les configurations YAML pour les nouveaux splits"""
    
    print("\nCréation des configurations YAML...")
    
    # Configuration pour test interne (avec GT)
    internal_config = {
        'train': '../data/images/train',
        'val': '../data/images/val_new',
        'test': '../data/images/test_internal',  # Avec annotations GT
        'nc': 4,
        'names': ['swimmer', 'swimmer with life jacket', 'boat', 'life jacket']
    }
    
    # Configuration originale (test sans GT)
    original_config = {
        'train': '../data/images/train',
        'val': '../data/images/val_new', 
        'test': '../data/images/test',  # Test SeaDronesSee original sans GT
        'nc': 4,
        'names': ['swimmer', 'swimmer with life jacket', 'boat', 'life jacket']
    }
    
    # Sauvegarder les configurations
    with open('data/dataset_internal_test.yaml', 'w', encoding='utf-8') as f:
        yaml.dump(internal_config, f, default_flow_style=False)
    
    with open('data/dataset_original.yaml', 'w', encoding='utf-8') as f:
        yaml.dump(original_config, f, default_flow_style=False)
    
    print("✅ Fichiers YAML créés:")
    print("   - data/dataset_internal_test.yaml (test interne avec GT)")
    print("   - data/dataset_original.yaml (test SeaDronesSee)")

def verify_structure():
    """Vérifier que la structure est correcte pour YOLO"""
    
    print("\n=== VERIFICATION DE LA STRUCTURE ===")
    
    folders_to_check = [
        ("Train", "data/images/train"),
        ("Validation", "data/images/val_new"), 
        ("Test interne", "data/images/test_internal")
    ]
    
    for name, folder_path in folders_to_check:
        folder = Path(folder_path)
        if not folder.exists():
            print(f"⚠️  {name}: Dossier non trouvé - {folder}")
            continue
            
        images = list(folder.glob("*.jpg")) + list(folder.glob("*.png"))
        labels = list(folder.glob("*.txt"))
        
        print(f"✅ {name}: {len(images)} images, {len(labels)} annotations")
        
        # Vérifier que chaque image a son annotation
        missing_labels = []
        for img in images[:5]:  # Vérifier les 5 premiers
            label_file = folder / (img.stem + ".txt")
            if not label_file.exists():
                missing_labels.append(img.name)
        
        if missing_labels:
            print(f"   ⚠️  Annotations manquantes: {missing_labels}")
        else:
            print(f"   ✅ Structure YOLO correcte")

def analyze_class_distribution():
    """Analyser la distribution des classes dans les nouveaux splits"""
    
    print("\n=== ANALYSE DES CLASSES ===")
    
    splits = {
        'Train': 'data/images/train',
        'Validation': 'data/images/val_new',
        'Test interne': 'data/images/test_internal'
    }
    
    class_names = ['swimmer', 'swimmer with life jacket', 'boat', 'life jacket']
    
    for split_name, folder_path in splits.items():
        folder = Path(folder_path)
        if not folder.exists():
            continue
            
        print(f"\n{split_name}:")
        
        label_files = list(folder.glob("*.txt"))
        if not label_files:
            print("   Aucune annotation trouvée")
            continue
            
        # Compter les classes
        class_counts = [0] * 4
        total_objects = 0
        
        for label_file in label_files:
            try:
                with open(label_file, 'r') as f:
                    lines = f.readlines()
                    for line in lines:
                        line = line.strip()
                        if line:
                            class_id = int(line.split()[0])
                            if 0 <= class_id < 4:
                                class_counts[class_id] += 1
                                total_objects += 1
            except:
                continue
        
        print(f"   Total objets: {total_objects}")
        for i, count in enumerate(class_counts):
            percentage = (count / total_objects * 100) if total_objects > 0 else 0
            print(f"   {class_names[i]}: {count} ({percentage:.1f}%)")

def main():
    """Fonction principale"""
    
    print("=== PREPARATION DU SPLIT DE TEST - VERSION CORRIGEE ===")
    print("CORRECTIF: Les annotations .txt seront maintenant avec les images")
    
    print("Contexte:")
    print("   SeaDronesSee test set n'a pas d'annotations ground truth")
    print("   Solution: Créer un test interne depuis la validation")
    print("   YOLO nécessite images + annotations dans le même dossier")
    
    # Créer le nouveau split
    print("\nDémarrage du split...")
    success = create_validation_test_split()
    
    if success:
        print("\n🎉 SPLIT DE TEST CREE AVEC SUCCES!")
        
        # Analyser la distribution des classes
        analyze_class_distribution()
        
        print(f"\nSTRUCTURE FINALE:")
        print("data/images/")
        print("├── train/                    # Entraînement (images + .txt)")
        print("├── val_new/                  # Nouvelle validation (images + .txt)")
        print("├── test_internal/            # Test interne avec GT (images + .txt)")
        print("├── test/                     # Test SeaDronesSee (images seulement)")
        print("└── val_original_backup/      # Sauvegarde")
        
        print(f"\nFICHIERS DE CONFIGURATION:")
        print("✅ data/dataset_internal_test.yaml (pour entraînement/évaluation)")
        print("✅ data/dataset_original.yaml (pour soumission SeaDronesSee)")
        
        print(f"\nPROCHAINES ETAPES:")
        print("1. Lancez: python optimize_model.py")
        print("2. Le pipeline utilisera automatiquement le test interne")
        print("3. Vous aurez des métriques fiables sur test_internal")
        
    else:
        print("\n❌ Erreur lors de la création du split")

if __name__ == "__main__":
    main()