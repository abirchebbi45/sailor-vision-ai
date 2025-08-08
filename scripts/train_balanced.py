"""
Script pour créer un entraînement optimisé avec gestion du déséquilibre des classes
Version optimisée GPU
"""

import os
import yaml
import numpy as np
from ultralytics import YOLO
import torch
from collections import Counter
from pathlib import Path
import sys

# Importer l'optimiseur GPU
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from scripts.gpu_optimizer import load_gpu_config, setup_gpu_optimizations, create_training_config, monitor_gpu_usage

def get_optimal_cache_setting():
    """Déterminer le meilleur paramètre de cache selon la RAM disponible"""
    try:
        import psutil
        ram_gb = psutil.virtual_memory().total / (1024**3)
        
        if ram_gb >= 32:
            return 'ram'  # Cache en RAM si >32GB
        elif ram_gb >= 16:
            return True   # Cache disque si 16-32GB
        else:
            return False  # Pas de cache si <16GB
    except:
        return False  # Sécurité

def calculate_class_weights():
    """Calculer les poids des classes pour gérer le déséquilibre"""
    print("🔢 Calcul des poids des classes...")
    
    class_counts = {}
    total_objects = 0
    
    # Parcourir les annotations d'entraînement
    train_path = "data/images/train"
    if os.path.exists(train_path):
        for file in os.listdir(train_path):
            if file.endswith('.txt'):
                file_path = os.path.join(train_path, file)
                try:
                    with open(file_path, 'r') as f:
                        for line in f:
                            parts = line.strip().split()
                            if len(parts) >= 5:
                                class_id = int(parts[0])
                                class_counts[class_id] = class_counts.get(class_id, 0) + 1
                                total_objects += 1
                except:
                    continue
    
    # Calculer les poids inversement proportionnels à la fréquence
    class_weights = {}
    if class_counts and total_objects > 0:
        max_count = max(class_counts.values())
        for class_id, count in class_counts.items():
            # Weight = max_count / count (plus la classe est rare, plus le poids est élevé)
            class_weights[class_id] = max_count / count
    
    print(f"📊 Distribution des classes:")
    for class_id, count in sorted(class_counts.items()):
        weight = class_weights.get(class_id, 1.0)
        percentage = (count / total_objects * 100) if total_objects > 0 else 0
        print(f"   Classe {class_id}: {count} samples ({percentage:.1f}%) - Poids: {weight:.2f}")
    
    return class_weights

def create_balanced_dataset_config():
    """Créer une configuration de dataset avec augmentation ciblée"""
    
    # Charger la configuration existante
    with open("data/dataset.yaml", "r") as f:
        config = yaml.safe_load(f)
    
    # Mettre à jour les chemins pour être absolus
    config['train'] = 'data/images/train'
    config['val'] = 'data/images/val'
    config['test'] = 'data/images/test'
    
    # Sauvegarder la nouvelle configuration
    with open("data/dataset_optimized.yaml", "w") as f:
        yaml.dump(config, f, default_flow_style=False)
    
    print("✅ Configuration de dataset optimisée créée: data/dataset_optimized.yaml")
    return "data/dataset_optimized.yaml"

def train_with_class_balancing():
    """Entraîner le modèle avec gestion du déséquilibre des classes et optimisation GPU"""
    
    print("🚀 ENTRAÎNEMENT YOLOV8 OPTIMISÉ POUR SAILOR VISION")
    print("=" * 60)
    
    # Configuration GPU
    print("🔧 Configuration GPU...")
    gpu_available = torch.cuda.is_available()
    if gpu_available:
        setup_gpu_optimizations()
        gpu_usage = monitor_gpu_usage()
        if gpu_usage:
            print(f"📊 GPU: {gpu_usage['device_name']}")
            print(f"💾 Mémoire GPU: {gpu_usage['memory_total_gb']:.1f} GB disponible")
    else:
        print("⚠️  GPU non disponible - entraînement sur CPU (sera plus lent)")
    
    # Calculer les poids des classes
    class_weights = calculate_class_weights()
    
    # Créer la configuration optimisée
    data_config = create_balanced_dataset_config()
    
    # Configuration GPU optimisée selon la mémoire disponible
    if gpu_available:
        try:
            device = torch.cuda.current_device()
            total_memory = torch.cuda.get_device_properties(device).total_memory / (1024**3)
            
            if total_memory >= 12:
                batch_size = 32
                workers = 8
            elif total_memory >= 8:
                batch_size = 24
                workers = 6
            elif total_memory >= 6:
                batch_size = 16
                workers = 4
            else:
                batch_size = 8
                workers = 2
        except:
            batch_size = 16
            workers = 4
    else:
        batch_size = 4
        workers = 2
    
    print(f"⚙️  Configuration adaptée:")
    print(f"   Batch size: {batch_size}")
    print(f"   Workers: {workers}")
    print(f"   Device: {'GPU' if gpu_available else 'CPU'}")
    
    # Configuration d'entraînement optimisée
    train_config = {
        'data': data_config,
        'epochs': 150,  # Augmenté pour de meilleures performances
        'batch': batch_size,  # Adapté au GPU
        'imgsz': 640,
        'device': 0 if gpu_available else 'cpu',
        'workers': workers,  # Adapté au système
        'project': 'outputs/train_balanced',
        'name': 'sailor_vision_balanced',
        'exist_ok': True,
        'pretrained': True,
        'optimizer': 'AdamW',  # Souvent meilleur que SGD
        'lr0': 0.001,  # Learning rate initial plus bas
        'lrf': 0.1,    # Learning rate final
        'momentum': 0.937,
        'weight_decay': 0.0005,
        'warmup_epochs': 5,    # Plus de warm-up
        'warmup_momentum': 0.8,
        'warmup_bias_lr': 0.1,
        'cos_lr': True,        # Cosine learning rate scheduling
        'close_mosaic': 15,    # Désactiver mosaic dans les dernières époques
        'amp': gpu_available,  # Mixed precision seulement avec GPU
        'save_period': 10,     # Sauvegarder tous les 10 epochs
        'val': True,
        'plots': True,
        'verbose': True,
        'seed': 42,
        
        # Cache intelligent selon la RAM disponible
        'cache': get_optimal_cache_setting(),
        
        # Hyperparamètres de loss optimisés pour le déséquilibre
        'box': 7.5,
        'cls': 1.0,  # Augmenter le poids de la classification
        'dfl': 1.5,
        
        # Augmentations spécifiques pour les données maritimes
        'hsv_h': 0.02,     # Variation de teinte (pour les différents éclairages maritimes)
        'hsv_s': 0.8,      # Variation de saturation
        'hsv_v': 0.5,      # Variation de luminosité (important pour les conditions maritimes)
        'degrees': 10.0,   # Rotation légère
        'translate': 0.1,  # Translation
        'scale': 0.3,      # Échelle (important pour différentes distances)
        'shear': 2.0,      # Cisaillement léger
        'perspective': 0.0001,  # Perspective
        'flipud': 0.0,     # Pas de flip vertical (pas naturel en maritime)
        'fliplr': 0.5,     # Flip horizontal OK
        'mosaic': 1.0,     # Mosaic augmentation
        'mixup': 0.15,     # Mixup pour la régularisation
        'copy_paste': 0.3, # Copy-paste augmentation
        
        # Early stopping
        'patience': 15,    # Arrêt si pas d'amélioration pendant 15 epochs
    }
    
    print("🔧 Configuration d'entraînement:")
    for key, value in train_config.items():
        if key not in ['data']:
            print(f"   {key}: {value}")
    
    # Charger le modèle
    print("\n📥 Chargement du modèle YOLOv8n...")
    model = YOLO('yolov8n.pt')  # Commencer avec le plus petit modèle
    
    # Afficher les informations sur le device
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"🖥️  Device utilisé: {device}")
    if torch.cuda.is_available():
        print(f"   GPU: {torch.cuda.get_device_name(0)}")
        print(f"   Mémoire GPU: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
    
    print("\n🏃‍♂️ Démarrage de l'entraînement...")
    print("-" * 40)
    
    # Lancer l'entraînement
    try:
        results = model.train(**train_config)
        
        print("\n✅ ENTRAÎNEMENT TERMINÉ!")
        print("-" * 30)
        
        # Afficher les résultats
        if hasattr(results, 'results_dict'):
            metrics = results.results_dict
            print(f"📊 Meilleurs résultats:")
            if 'metrics/mAP50(B)' in metrics:
                print(f"   mAP@0.5: {metrics['metrics/mAP50(B)']:.3f}")
            if 'metrics/mAP50-95(B)' in metrics:
                print(f"   mAP@0.5:0.95: {metrics['metrics/mAP50-95(B)']:.3f}")
        
        # Chemin du meilleur modèle
        best_model_path = f"outputs/train_balanced/sailor_vision_balanced/weights/best.pt"
        if os.path.exists(best_model_path):
            print(f"🏆 Meilleur modèle sauvegardé: {best_model_path}")
        
        return results
        
    except Exception as e:
        print(f"❌ Erreur pendant l'entraînement: {e}")
        return None

def evaluate_model(model_path="outputs/train_balanced/sailor_vision_balanced/weights/best.pt"):
    """Évaluer le modèle entraîné"""
    
    if not os.path.exists(model_path):
        print(f"❌ Modèle non trouvé: {model_path}")
        return
    
    print(f"\n📊 ÉVALUATION DU MODÈLE")
    print("-" * 30)
    
    # Charger le modèle
    model = YOLO(model_path)
    
    # Évaluer sur le set de validation
    try:
        results = model.val(data="data/dataset_optimized.yaml", split='val')
        
        print("📈 Résultats de validation:")
        if hasattr(results, 'results_dict'):
            metrics = results.results_dict
            for key, value in metrics.items():
                if 'metrics/' in key:
                    metric_name = key.replace('metrics/', '')
                    print(f"   {metric_name}: {value:.3f}")
        
        return results
        
    except Exception as e:
        print(f"❌ Erreur pendant l'évaluation: {e}")
        return None

def main():
    """Fonction principale"""
    print("🌊 OPTIMISATION DU MODÈLE SAILOR VISION AI")
    print("=" * 50)
    
    # Vérifier la structure des données
    required_paths = ["data/images/train", "data/images/val", "data/dataset.yaml"]
    for path in required_paths:
        if not os.path.exists(path):
            print(f"❌ Chemin manquant: {path}")
            return
    
    print("✅ Structure des données vérifiée")
    
    # 1. Entraîner le modèle avec optimisations
    print("\n🎯 PHASE 1: Entraînement optimisé")
    results = train_with_class_balancing()
    
    if results:
        # 2. Évaluer le modèle
        print("\n🎯 PHASE 2: Évaluation")
        evaluate_model()
        
        print("\n💡 RECOMMANDATIONS POST-ENTRAÎNEMENT:")
        print("1. Vérifiez les courbes d'apprentissage dans outputs/train_balanced/")
        print("2. Si overfitting: augmentez weight_decay ou ajoutez dropout")
        print("3. Si underfitting: augmentez la complexité du modèle (yolov8s)")
        print("4. Considérez un ensemble de modèles pour de meilleures performances")
    
    print("\n🎉 Optimisation terminée!")

if __name__ == "__main__":
    main()
