"""
Script de diagnostic complet pour analyser les problèmes du dataset YOLOv8
et proposer des solutions d'optimisation
"""

import os
import json
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter, defaultdict
from pathlib import Path
import pandas as pd
from PIL import Image
import yaml

def count_files_and_annotations():
    """Compter les fichiers et analyser les annotations"""
    print("="*60)
    print("📊 ANALYSE DU DATASET - SAILOR VISION AI")
    print("="*60)
    
    splits = {'train': 'data/images/train', 'val': 'data/images/val', 'test': 'data/images/test'}
    class_names = ['swimmer', 'swimmer with life jacket', 'boat', 'life jacket']
    
    results = {}
    
    for split, path in splits.items():
        print(f"\n🔍 Analyse du split '{split.upper()}':")
        print("-" * 40)
        
        if not os.path.exists(path):
            print(f"❌ Dossier non trouvé: {path}")
            continue
            
        # Compter les images et labels
        images = [f for f in os.listdir(path) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        labels = [f for f in os.listdir(path) if f.endswith('.txt')]
        
        print(f"📸 Images: {len(images)}")
        print(f"🏷️  Labels: {len(labels)}")
        
        # Analyser les annotations
        class_counts = Counter()
        total_objects = 0
        images_with_objects = 0
        images_without_objects = 0
        bbox_areas = []
        bbox_aspects = []
        
        for label_file in labels:
            label_path = os.path.join(path, label_file)
            try:
                with open(label_path, 'r') as f:
                    lines = f.readlines()
                    
                if lines:
                    images_with_objects += 1
                    for line in lines:
                        parts = line.strip().split()
                        if len(parts) >= 5:
                            class_id = int(parts[0])
                            x_center, y_center, width, height = map(float, parts[1:5])
                            
                            class_counts[class_id] += 1
                            total_objects += 1
                            
                            # Calculer l'aire et le ratio d'aspect
                            area = width * height
                            aspect_ratio = width / height if height > 0 else 0
                            
                            bbox_areas.append(area)
                            bbox_aspects.append(aspect_ratio)
                else:
                    images_without_objects += 1
                    
            except Exception as e:
                print(f"⚠️  Erreur lecture {label_file}: {e}")
        
        # Statistiques par classe
        print(f"\n📈 Statistiques des objets:")
        print(f"   Total objets: {total_objects}")
        print(f"   Images avec objets: {images_with_objects}")
        print(f"   Images sans objets: {images_without_objects}")
        
        print(f"\n🏷️  Distribution des classes:")
        for class_id, count in sorted(class_counts.items()):
            if class_id < len(class_names):
                percentage = (count / total_objects * 100) if total_objects > 0 else 0
                print(f"   {class_names[class_id]}: {count} ({percentage:.1f}%)")
        
        # Analyser les tailles de bounding boxes
        if bbox_areas:
            print(f"\n📏 Analyse des bounding boxes:")
            print(f"   Aire moyenne: {np.mean(bbox_areas):.4f}")
            print(f"   Aire médiane: {np.median(bbox_areas):.4f}")
            print(f"   Aire min/max: {np.min(bbox_areas):.4f} / {np.max(bbox_areas):.4f}")
            print(f"   Ratio d'aspect moyen: {np.mean(bbox_aspects):.2f}")
        
        # Calculer le déséquilibre des classes
        if class_counts:
            max_count = max(class_counts.values())
            min_count = min(class_counts.values())
            imbalance_ratio = max_count / min_count if min_count > 0 else float('inf')
            print(f"\n⚖️  Déséquilibre des classes: {imbalance_ratio:.2f}:1")
            
            if imbalance_ratio > 10:
                print("   🚨 PROBLÈME MAJEUR: Déséquilibre très élevé!")
            elif imbalance_ratio > 5:
                print("   ⚠️  PROBLÈME MODÉRÉ: Déséquilibre notable")
            else:
                print("   ✅ Déséquilibre acceptable")
        
        results[split] = {
            'images': len(images),
            'labels': len(labels),
            'total_objects': total_objects,
            'class_counts': dict(class_counts),
            'images_with_objects': images_with_objects,
            'images_without_objects': images_without_objects,
            'bbox_areas': bbox_areas,
            'bbox_aspects': bbox_aspects,
            'imbalance_ratio': imbalance_ratio if class_counts else 0
        }
    
    return results

def analyze_image_quality(sample_size=100):
    """Analyser la qualité des images"""
    print(f"\n🖼️  ANALYSE DE LA QUALITÉ DES IMAGES (échantillon: {sample_size})")
    print("-" * 50)
    
    splits = ['train', 'val', 'test']
    image_stats = {}
    
    for split in splits:
        path = f"data/images/{split}"
        if not os.path.exists(path):
            continue
            
        images = [f for f in os.listdir(path) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        
        # Échantillonner des images
        sample_images = np.random.choice(images, min(sample_size, len(images)), replace=False)
        
        widths, heights, channels = [], [], []
        
        for img_name in sample_images:
            try:
                img_path = os.path.join(path, img_name)
                with Image.open(img_path) as img:
                    w, h = img.size
                    widths.append(w)
                    heights.append(h)
                    
                    # Vérifier le nombre de canaux
                    if hasattr(img, 'mode'):
                        if img.mode == 'RGB':
                            channels.append(3)
                        elif img.mode == 'RGBA':
                            channels.append(4)
                        elif img.mode == 'L':
                            channels.append(1)
                        else:
                            channels.append(0)
            except Exception as e:
                print(f"⚠️  Erreur lecture image {img_name}: {e}")
        
        if widths:
            print(f"\n📊 {split.upper()}:")
            print(f"   Résolution moyenne: {np.mean(widths):.0f}x{np.mean(heights):.0f}")
            print(f"   Résolution min: {np.min(widths)}x{np.min(heights)}")
            print(f"   Résolution max: {np.max(widths)}x{np.max(heights)}")
            print(f"   Ratio d'aspect moyen: {np.mean(np.array(widths)/np.array(heights)):.2f}")
            
            image_stats[split] = {
                'avg_width': np.mean(widths),
                'avg_height': np.mean(heights),
                'min_width': np.min(widths),
                'max_width': np.max(widths),
                'min_height': np.min(heights),
                'max_height': np.max(heights)
            }
    
    return image_stats

def check_data_leakage():
    """Vérifier les fuites de données entre les splits"""
    print(f"\n🔍 VÉRIFICATION DES FUITES DE DONNÉES")
    print("-" * 40)
    
    splits = {'train': 'data/images/train', 'val': 'data/images/val', 'test': 'data/images/test'}
    image_sets = {}
    
    for split, path in splits.items():
        if os.path.exists(path):
            images = {f.split('.')[0] for f in os.listdir(path) if f.lower().endswith(('.jpg', '.jpeg', '.png'))}
            image_sets[split] = images
            print(f"{split}: {len(images)} images uniques")
    
    # Vérifier les intersections
    if len(image_sets) >= 2:
        splits_list = list(image_sets.keys())
        for i in range(len(splits_list)):
            for j in range(i+1, len(splits_list)):
                split1, split2 = splits_list[i], splits_list[j]
                intersection = image_sets[split1] & image_sets[split2]
                if intersection:
                    print(f"🚨 FUITE DÉTECTÉE: {len(intersection)} images communes entre {split1} et {split2}")
                    if len(intersection) <= 5:
                        print(f"   Exemples: {list(intersection)[:5]}")
                else:
                    print(f"✅ Aucune fuite entre {split1} et {split2}")

def generate_optimization_recommendations(results):
    """Générer des recommandations d'optimisation"""
    print(f"\n💡 RECOMMANDATIONS D'OPTIMISATION")
    print("=" * 50)
    
    recommendations = []
    
    # Analyser le déséquilibre des classes
    train_results = results.get('train', {})
    imbalance_ratio = train_results.get('imbalance_ratio', 0)
    
    if imbalance_ratio > 10:
        recommendations.append("🎯 PRIORITÉ HAUTE - Déséquilibre des classes critique")
        recommendations.append("   • Utiliser weighted loss function")
        recommendations.append("   • Augmentation de données ciblée pour classes minoritaires")
        recommendations.append("   • Considérer le sous-échantillonnage des classes majoritaires")
    elif imbalance_ratio > 5:
        recommendations.append("⚠️  PRIORITÉ MOYENNE - Déséquilibre des classes modéré")
        recommendations.append("   • Utiliser class weights dans la loss function")
        recommendations.append("   • Augmentation de données pour classes minoritaires")
    
    # Analyser la taille du dataset
    total_train_images = train_results.get('images', 0)
    if total_train_images < 1000:
        recommendations.append("📸 PRIORITÉ HAUTE - Dataset trop petit")
        recommendations.append("   • Augmentation de données intensive")
        recommendations.append("   • Transfer learning obligatoire")
        recommendations.append("   • Considérer l'acquisition de plus de données")
    elif total_train_images < 5000:
        recommendations.append("📸 PRIORITÉ MOYENNE - Dataset de taille modérée")
        recommendations.append("   • Augmentation de données recommandée")
        recommendations.append("   • Transfer learning recommandé")
    
    # Analyser les objets sans annotations
    images_without_objects = train_results.get('images_without_objects', 0)
    total_images = train_results.get('images', 1)
    empty_ratio = images_without_objects / total_images if total_images > 0 else 0
    
    if empty_ratio > 0.3:
        recommendations.append("🗂️  PRIORITÉ HAUTE - Trop d'images sans objets")
        recommendations.append("   • Supprimer ou réduire les images vides")
        recommendations.append("   • Vérifier la qualité des annotations")
    elif empty_ratio > 0.1:
        recommendations.append("🗂️  PRIORITÉ MOYENNE - Images sans objets")
        recommendations.append("   • Considérer la réduction des images vides")
    
    # Recommandations générales
    recommendations.extend([
        "",
        "🛠️  STRATÉGIES D'OPTIMISATION RECOMMANDÉES:",
        "",
        "1. 📊 AUGMENTATION DE DONNÉES",
        "   • Rotation (±15°), flip horizontal",
        "   • Variation de luminosité/contraste (±20%)",
        "   • Zoom aléatoire (0.8-1.2)",
        "   • Mixup ou CutMix pour la régularisation",
        "",
        "2. ⚖️  GESTION DU DÉSÉQUILIBRE",
        "   • Focal Loss au lieu de CrossEntropy",
        "   • Class weights basés sur la fréquence inverse",
        "   • SMOTE pour l'augmentation synthétique",
        "",
        "3. 🏗️  ARCHITECTURE ET ENTRAÎNEMENT",
        "   • Multi-scale training (différentes tailles)",
        "   • Learning rate scheduling (cosine annealing)",
        "   • Early stopping avec patience=10-15",
        "   • Gradient clipping pour la stabilité",
        "",
        "4. 📏 OPTIMISATION DES HYPERPARAMÈTRES",
        "   • Batch size: 16-32 (selon GPU)",
        "   • Learning rate: 0.001-0.01 (avec warm-up)",
        "   • Weight decay: 1e-4 à 1e-5",
        "   • Mosaic augmentation: 0.5-1.0",
        "",
        "5. 🧪 VALIDATION ET TEST",
        "   • K-fold cross-validation",
        "   • Test Time Augmentation (TTA)",
        "   • Ensemble de modèles (YOLOv8n+s+m)",
        "",
        "6. 📈 MÉTRIQUES DE SURVEILLANCE",
        "   • mAP@0.5 et mAP@0.5:0.95",
        "   • Précision/Rappel par classe",
        "   • Confusion matrix par époque",
        "   • Learning curves (train/val loss)"
    ])
    
    for rec in recommendations:
        print(rec)

def create_training_script():
    """Créer un script d'entraînement optimisé"""
    script_content = '''"""
Script d'entraînement YOLOv8 optimisé pour Sailor Vision AI
"""

import os
import yaml
from ultralytics import YOLO
import torch
from pathlib import Path

def train_optimized_yolo():
    """Entraînement optimisé avec gestion du déséquilibre des classes"""
    
    # Configuration optimisée
    config = {
        'model': 'yolov8n.pt',  # Commencer avec le modèle le plus léger
        'data': 'data/dataset.yaml',
        'epochs': 100,
        'batch': 16,  # Ajuster selon votre GPU
        'imgsz': 640,
        'lr0': 0.01,
        'lrf': 0.01,
        'momentum': 0.937,
        'weight_decay': 0.0005,
        'warmup_epochs': 3,
        'warmup_momentum': 0.8,
        'warmup_bias_lr': 0.1,
        'box': 7.5,
        'cls': 0.5,
        'dfl': 1.5,
        'pose': 12.0,
        'kobj': 1.0,
        'label_smoothing': 0.0,
        'nbs': 64,
        'overlap_mask': True,
        'mask_ratio': 4,
        'dropout': 0.0,
        'val': True,
        'plots': True,
        'save': True,
        'save_period': 10,
        'cache': False,
        'device': 0 if torch.cuda.is_available() else 'cpu',
        'workers': 8,
        'project': 'outputs/train_optimized',
        'name': 'sailor_vision_v2',
        'exist_ok': True,
        'pretrained': True,
        'optimizer': 'auto',
        'verbose': True,
        'seed': 42,
        'deterministic': True,
        'single_cls': False,
        'rect': False,
        'cos_lr': True,
        'close_mosaic': 10,
        'resume': False,
        'amp': True,
        'fraction': 1.0,
        'profile': False,
        'freeze': None,
        # Augmentations spécifiques
        'hsv_h': 0.015,
        'hsv_s': 0.7,
        'hsv_v': 0.4,
        'degrees': 15.0,
        'translate': 0.1,
        'scale': 0.2,
        'shear': 0.0,
        'perspective': 0.0001,
        'flipud': 0.0,
        'fliplr': 0.5,
        'mosaic': 1.0,
        'mixup': 0.1,
        'copy_paste': 0.1
    }
    
    print("🚀 Démarrage de l'entraînement optimisé YOLOv8")
    print("=" * 50)
    
    # Charger le modèle
    model = YOLO(config['model'])
    
    # Commencer l'entraînement
    results = model.train(**config)
    
    print("✅ Entraînement terminé!")
    return results

if __name__ == "__main__":
    train_optimized_yolo()
'''
    
    script_path = "scripts/train_optimized.py"
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    print(f"\n📝 Script d'entraînement optimisé créé: {script_path}")

def main():
    """Fonction principale d'analyse"""
    print("🔬 DIAGNOSTIC COMPLET DU DATASET SAILOR VISION AI")
    print("=" * 60)
    
    # 1. Analyser les fichiers et annotations
    results = count_files_and_annotations()
    
    # 2. Analyser la qualité des images
    image_stats = analyze_image_quality(sample_size=50)
    
    # 3. Vérifier les fuites de données
    check_data_leakage()
    
    # 4. Générer les recommandations
    generate_optimization_recommendations(results)
    
    # 5. Créer le script d'entraînement optimisé
    create_training_script()
    
    print(f"\n🎯 RÉSUMÉ EXÉCUTIF")
    print("=" * 30)
    train_data = results.get('train', {})
    print(f"📊 Dataset: {train_data.get('images', 0)} images d'entraînement")
    print(f"🏷️  Objets: {train_data.get('total_objects', 0)} annotations totales")
    print(f"⚖️  Déséquilibre: {train_data.get('imbalance_ratio', 0):.1f}:1")
    
    if train_data.get('imbalance_ratio', 0) > 5:
        print("🚨 ACTION REQUISE: Déséquilibre critique des classes")
    else:
        print("✅ Déséquilibre acceptable")
    
    print(f"\n💡 Prochaines étapes:")
    print("1. Exécuter le script train_optimized.py")
    print("2. Surveiller les métriques d'entraînement")
    print("3. Ajuster les hyperparamètres selon les résultats")

if __name__ == "__main__":
    main()
