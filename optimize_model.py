#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import subprocess
import time
from pathlib import Path
import yaml

# Configuration d'encodage pour Windows
if sys.platform == "win32":
    import locale
    try:
        locale.setlocale(locale.LC_ALL, 'fr_FR.UTF-8')
    except:
        pass

def check_test_split():
    """Vérifie et crée le split de test - VERSION YOLO STRUCTURE"""
    
    data_dir = Path("data")
    test_internal = data_dir / "images" / "test_internal"
    val_new = data_dir / "images" / "val_new"
    val_original = data_dir / "images" / "val"
    
    if test_internal.exists() and val_new.exists():
        # Vérifier que les annotations sont bien présentes
        test_images = list(test_internal.glob("*.jpg")) + list(test_internal.glob("*.png"))
        test_labels = list(test_internal.glob("*.txt"))
        val_images = list(val_new.glob("*.jpg")) + list(val_new.glob("*.png"))
        val_labels = list(val_new.glob("*.txt"))
        
        if len(test_labels) > 0 and len(val_labels) > 0:
            print("✅ Split de test interne déjà créé avec structure YOLO correcte")
            print(f"   Validation: {len(val_images)} images, {len(val_labels)} annotations")
            print(f"   Test interne: {len(test_images)} images, {len(test_labels)} annotations")
            return True
    
    print("⚠️  Split de test interne non trouvé")
    print("💡 Création du split avec structure YOLO...")
    
    if not val_original.exists():
        print("❌ Dossier val/ non trouvé")
        return False
    
    # Version intégrée adaptée à votre structure
    return create_yolo_split()

def create_yolo_split():
    """Crée le split adapté à la structure YOLO existante"""
    
    import random
    import shutil
    
    print("\n=== CREATION DU SPLIT YOLO ===")
    
    val_dir = Path("data/images/val")
    
    # Vérifier structure YOLO
    images = list(val_dir.glob("*.jpg")) + list(val_dir.glob("*.png"))
    labels = list(val_dir.glob("*.txt"))
    
    print(f"Détecté: {len(images)} images, {len(labels)} annotations")
    
    if len(images) == 0:
        print("❌ Aucune image trouvée")
        return False
    
    # Créer dossiers
    val_new_dir = Path("data/images/val_new")
    test_internal_dir = Path("data/images/test_internal")
    backup_dir = Path("data/images/val_original_backup")
    
    for folder in [val_new_dir, test_internal_dir, backup_dir]:
        folder.mkdir(parents=True, exist_ok=True)
    
    # Sauvegarde
    if len(list(backup_dir.glob("*"))) == 0:
        shutil.copytree(val_dir, backup_dir, dirs_exist_ok=True)
        print("✅ Sauvegarde effectuée")
    
    # Split 70-30
    random.seed(42)
    random.shuffle(images)
    
    split_point = int(len(images) * 0.7)
    val_images = images[:split_point]
    test_images = images[split_point:]
    
    print(f"Split: {len(val_images)} val, {len(test_images)} test")
    
    # Copier validation
    val_copied = val_labels_copied = 0
    for img_file in val_images:
        shutil.copy2(img_file, val_new_dir / img_file.name)
        val_copied += 1
        
        label_file = val_dir / (img_file.stem + ".txt")
        if label_file.exists():
            shutil.copy2(label_file, val_new_dir / (img_file.stem + ".txt"))
            val_labels_copied += 1
    
    # Copier test
    test_copied = test_labels_copied = 0
    for img_file in test_images:
        shutil.copy2(img_file, test_internal_dir / img_file.name)
        test_copied += 1
        
        label_file = val_dir / (img_file.stem + ".txt")
        if label_file.exists():
            shutil.copy2(label_file, test_internal_dir / (img_file.stem + ".txt"))
            test_labels_copied += 1
    
    print(f"✅ Val: {val_copied} img, {val_labels_copied} labels")
    print(f"✅ Test: {test_copied} img, {test_labels_copied} labels")
    
    # Créer configs YAML
    create_yaml_configs()
    
    return True

def create_yaml_configs():
    """Crée les fichiers YAML"""
    
    config_internal = {
        'train': '../data/images/train',
        'val': '../data/images/val_new', 
        'test': '../data/images/test_internal',
        'nc': 4,
        'names': ['swimmer', 'swimmer with life jacket', 'boat', 'life jacket']
    }
    
    with open('data/dataset_internal_test.yaml', 'w', encoding='utf-8') as f:
        yaml.dump(config_internal, f, default_flow_style=False)
    
    print("✅ Configuration YAML créée")

def load_gpu_config():
    """Charge la configuration GPU"""
    
    try:
        with open('gpu_config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        print("✅ Configuration GPU chargée:")
        print(f"   Batch size: {config.get('batch_size', 4)}")
        print(f"   Workers: {config.get('workers', 2)}")
        print(f"   Image size: {config.get('img_size', 640)}")
        return config
    except:
        print("⚠️  gpu_config.yaml non trouvé, utilisation des valeurs par défaut")
        return {
            'batch_size': 4,
            'workers': 2,
            'img_size': 640,
            'mixed_precision': True
        }

def run_script(script_name, description):
    """Exécute un script avec gestion d'erreurs"""
    
    print(f"\n🚀 Exécution: {description}")
    print(f"   Script: {script_name}")
    
    start_time = time.time()
    
    try:
        # Configuration d'environnement pour éviter les erreurs Unicode
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        env['PYTHONUTF8'] = '1'
        
        result = subprocess.run([
            sys.executable, script_name
        ], capture_output=True, text=True, encoding='utf-8', env=env)
        
        duration = time.time() - start_time
        print(f"⏱️  Durée d'exécution: {duration:.1f} secondes")
        
        if result.returncode == 0:
            print("✅ Succès!")
            if result.stdout:
                print("📋 Sortie:")
                print(result.stdout[-500:])  # Dernières 500 caractères
            return True
        else:
            print("❌ Erreur!")
            if result.stderr:
                print("🚨 Erreurs:")
                print(result.stderr[-500:])
            return False
            
    except Exception as e:
        duration = time.time() - start_time
        print(f"⏱️  Durée d'exécution: {duration:.1f} secondes")
        print(f"❌ Exception: {e}")
        return False

def main():
    """Pipeline principal d'optimisation - VERSION ADAPTÉE AU SCRIPT CORRIGÉ"""
    
    print("=" * 60)
    print("🌊 OPTIMISATION SAILOR VISION AI - VERSION ADAPTÉE")
    print("=" * 60)
    print("🎯 Pipeline adapté au script de split corrigé")
    print("📋 Fonctionnalités:")
    print("   • Split avec structure YOLO correcte")
    print("   • Diagnostic du dataset")
    print("   • Équilibrage des classes")
    print("   • Entraînement optimisé GTX 1050")
    print("   • Surveillance des performances")
    
    # Étape 0: Vérifications
    print(f"\n🎯 ÉTAPE 0: VÉRIFICATIONS")
    print("-" * 40)
    
    # Vérifier/créer le split de test avec le script corrigé
    if not check_test_split():
        print("❌ Impossible de créer le split de test")
        return
    
    # Charger la config GPU
    gpu_config = load_gpu_config()
    
    print("✅ Tous les prérequis sont satisfaits")
    
    # Menu interactif
    print(f"\n🎯 CHOISISSEZ UNE OPTION:")
    print("-" * 30)
    print("1. Pipeline complet (recommandé)")
    print("2. Diagnostic seulement")
    print("3. Équilibrage seulement") 
    print("4. Entraînement seulement")
    print("5. Évaluation seulement")
    print("0. Quitter")
    
    try:
        choice = input("\n🎯 Votre choix (1-5, 0 pour quitter): ").strip()
    except:
        choice = "1"  # Par défaut
    
    if choice == "0":
        print("👋 Au revoir!")
        return
    
    # Exécution selon le choix
    if choice in ["1", "2"]:
        print(f"\n🎯 ÉTAPE 1: DIAGNOSTIC DU DATASET")
        print("-" * 40)
        if not run_script("scripts/dataset_diagnostics.py", "Analyse du dataset"):
            print("⚠️  Diagnostic échoué, mais on continue...")
    
    if choice in ["1", "3"]:
        print(f"\n🎯 ÉTAPE 2: ÉQUILIBRAGE DES CLASSES")
        print("-" * 45)
        if not run_script("scripts/balance_dataset.py", "Équilibrage des données"):
            print("❌ Équilibrage échoué")
            return
    
    if choice in ["1", "4"]:
        print(f"\n🎯 ÉTAPE 3: ENTRAÎNEMENT OPTIMISÉ")
        print("-" * 42)
        if not run_script("scripts/train_balanced.py", "Entraînement YOLOv8 optimisé"):
            print("❌ Entraînement échoué")
            return
    
    if choice in ["1", "5"]:
        print(f"\n🎯 ÉTAPE 4: ÉVALUATION")
        print("-" * 28)
        if not run_script("scripts/advanced_evaluation.py", "Évaluation complète"):
            print("⚠️  Évaluation échouée, mais modèle entraîné")
    
    # Résumé final
    print(f"\n🎉 OPTIMISATION TERMINÉE!")
    print("=" * 35)
    print("📁 Résultats disponibles dans:")
    print("   • outputs/train_balanced/ (modèle entraîné)")
    print("   • data_balanced/ (dataset équilibré)")
    print("   • *.md (rapports d'analyse)")
    
    print(f"\n📋 PROCHAINES ÉTAPES:")
    print("1. Vérifiez outputs/train_balanced/sailor_vision_balanced/weights/best.pt")
    print("2. Testez avec: python scripts/advanced_evaluation.py")
    print("3. Démo: python scripts/demo_interactive.py")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Interruption utilisateur - Au revoir!")
    except Exception as e:
        print(f"\n❌ Erreur critique: {e}")
        import traceback
        traceback.print_exc()