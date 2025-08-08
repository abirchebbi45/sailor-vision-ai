import os
import json
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter, defaultdict
from pathlib import Path
import yaml
from PIL import Image
import pandas as pd

def analyze_dataset():
    """
    Analyse complète du dataset pour identifier les problèmes potentiels
    """
    print("🔍 Analyse du dataset en cours...")
    
    # Configuration
    project_root = Path(os.path.dirname(os.path.dirname(__file__)))
    
    # Analyser la distribution des classes
    class_distribution = analyze_class_distribution()
    
    # Analyser la taille des images
    image_size_analysis = analyze_image_sizes()
    
    # Analyser la qualité des annotations
    annotation_quality = analyze_annotation_quality()
    
    # Analyser les déséquilibres
    balance_analysis = analyze_class_balance()
    
    # Vérifier la disponibilité du test
    test_availability = check_test_availability()
    
    # Générer le rapport
    generate_report(class_distribution, image_size_analysis, annotation_quality, balance_analysis, test_availability)
    
    return {
        'class_distribution': class_distribution,
        'image_size_analysis': image_size_analysis,
        'annotation_quality': annotation_quality,
        'balance_analysis': balance_analysis
    }

def analyze_class_distribution():
    """Analyser la distribution des classes dans chaque split"""
    print("📊 Analyse de la distribution des classes...")
    
    # Vérifier quels splits sont disponibles
    possible_splits = ['train', 'val', 'val_new', 'test_internal', 'test']
    available_splits = []
    
    for split in possible_splits:
        labels_path = f"data/labels/{split}"
        if os.path.exists(labels_path):
            available_splits.append(split)
    
    if not available_splits:
        print("⚠️  Aucun dossier de labels trouvé dans data/labels/")
        return {}
    
    print(f"📁 Splits détectés: {', '.join(available_splits)}")
    
    class_names = ['swimmer', 'swimmer with life jacket', 'boat', 'life jacket']
    distribution = {}
    
    for split in available_splits:
        labels_path = f"data/labels/{split}"
            
        class_counts = Counter()
        total_annotations = 0
        files_with_classes = defaultdict(int)
        
        for label_file in os.listdir(labels_path):
            if label_file.endswith('.txt'):
                filepath = os.path.join(labels_path, label_file)
                with open(filepath, 'r') as f:
                    lines = f.readlines()
                    if lines:  # Fichier non vide
                        classes_in_file = set()
                        for line in lines:
                            if line.strip():
                                class_id = int(line.split()[0])
                                class_counts[class_id] += 1
                                classes_in_file.add(class_id)
                                total_annotations += 1
                        
                        for class_id in classes_in_file:
                            files_with_classes[class_id] += 1
        
        distribution[split] = {
            'class_counts': dict(class_counts),
            'total_annotations': total_annotations,
            'files_with_classes': dict(files_with_classes),
            'class_percentages': {k: (v/total_annotations)*100 for k, v in class_counts.items()} if total_annotations > 0 else {}
        }
    
    return distribution

def analyze_image_sizes():
    """Analyser les tailles d'images"""
    print("📏 Analyse des tailles d'images...")
    
    sizes = {'train': [], 'val': [], 'test': []}
    
    for split in ['train', 'val', 'test']:
        images_path = f"data/images/{split}"
        if not os.path.exists(images_path):
            continue
            
        # Échantillonner quelques images pour éviter de traiter toutes les images
        image_files = [f for f in os.listdir(images_path) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        sample_size = min(1000, len(image_files))  # Échantillon de 1000 images max
        
        for i, img_file in enumerate(image_files[:sample_size]):
            try:
                img_path = os.path.join(images_path, img_file)
                with Image.open(img_path) as img:
                    sizes[split].append(img.size)  # (width, height)
            except Exception as e:
                print(f"Erreur lors de l'ouverture de {img_file}: {e}")
            
            if i % 100 == 0:
                print(f"Analysé {i+1}/{sample_size} images de {split}")
    
    return sizes

def analyze_annotation_quality():
    """Analyser la qualité des annotations"""
    print("🎯 Analyse de la qualité des annotations...")
    
    quality_metrics = {}
    
    for split in ['train', 'val', 'test']:
        labels_path = f"data/yolo_labels/{split}"
        if not os.path.exists(labels_path):
            continue
            
        bbox_areas = []
        bbox_ratios = []
        empty_files = 0
        total_files = 0
        
        for label_file in os.listdir(labels_path):
            if label_file.endswith('.txt'):
                total_files += 1
                filepath = os.path.join(labels_path, label_file)
                with open(filepath, 'r') as f:
                    lines = f.readlines()
                    
                if not lines or all(not line.strip() for line in lines):
                    empty_files += 1
                    continue
                    
                for line in lines:
                    if line.strip():
                        parts = line.strip().split()
                        if len(parts) >= 5:
                            # Format YOLO: class_id center_x center_y width height
                            width = float(parts[3])
                            height = float(parts[4])
                            area = width * height
                            ratio = width / height if height > 0 else 0
                            
                            bbox_areas.append(area)
                            bbox_ratios.append(ratio)
        
        quality_metrics[split] = {
            'empty_files': empty_files,
            'total_files': total_files,
            'empty_ratio': empty_files / total_files if total_files > 0 else 0,
            'avg_bbox_area': np.mean(bbox_areas) if bbox_areas else 0,
            'std_bbox_area': np.std(bbox_areas) if bbox_areas else 0,
            'avg_bbox_ratio': np.mean(bbox_ratios) if bbox_ratios else 0,
            'std_bbox_ratio': np.std(bbox_ratios) if bbox_ratios else 0,
            'min_bbox_area': np.min(bbox_areas) if bbox_areas else 0,
            'max_bbox_area': np.max(bbox_areas) if bbox_areas else 0
        }
    
    return quality_metrics

def check_test_availability():
    """Vérifier la disponibilité des annotations de test"""
    print("🔍 Vérification de la disponibilité du test...")
    
    test_scenarios = {
        'test_internal': {
            'path': 'data/labels/test_internal',
            'description': 'Test interne avec GT (créé depuis validation)',
            'recommended': True
        },
        'test_original': {
            'path': 'data/labels/test',
            'description': 'Test SeaDronesSee original (sans GT)',
            'recommended': False
        },
        'val_new': {
            'path': 'data/labels/val_new',
            'description': 'Nouvelle validation (après split)',
            'recommended': True
        }
    }
    
    availability = {}
    
    for scenario, info in test_scenarios.items():
        exists = os.path.exists(info['path'])
        if exists:
            # Compter les fichiers de labels
            label_files = [f for f in os.listdir(info['path']) if f.endswith('.txt')]
            file_count = len(label_files)
        else:
            file_count = 0
            
        availability[scenario] = {
            'exists': exists,
            'file_count': file_count,
            'description': info['description'],
            'recommended': info['recommended']
        }
    
    return availability

def analyze_class_balance():
    """Analyser l'équilibre des classes"""
    print("⚖️ Analyse de l'équilibre des classes...")
    
    class_names = ['swimmer', 'swimmer with life jacket', 'boat', 'life jacket']
    balance_metrics = {}
    
    # Vérifier quels splits sont disponibles
    possible_splits = ['train', 'val', 'val_new', 'test_internal']
    available_splits = []
    
    for split in possible_splits:
        labels_path = f"data/labels/{split}"
        if os.path.exists(labels_path):
            available_splits.append(split)
    
    # Analyser pour chaque split disponible
    for split in available_splits:
        labels_path = f"data/labels/{split}"
        if not os.path.exists(labels_path):
            continue
            
        class_counts = Counter()
        
        for label_file in os.listdir(labels_path):
            if label_file.endswith('.txt'):
                filepath = os.path.join(labels_path, label_file)
                with open(filepath, 'r') as f:
                    for line in f:
                        if line.strip():
                            class_id = int(line.split()[0])
                            class_counts[class_id] += 1
        
        if class_counts:
            total = sum(class_counts.values())
            frequencies = [class_counts.get(i, 0) for i in range(len(class_names))]
            
            # Calculer les métriques de déséquilibre
            max_freq = max(frequencies) if frequencies else 0
            min_freq = min(f for f in frequencies if f > 0) if any(f > 0 for f in frequencies) else 0
            imbalance_ratio = max_freq / min_freq if min_freq > 0 else float('inf')
            
            # Calculer l'entropie (mesure de diversité)
            probs = [f/total for f in frequencies if f > 0]
            entropy = -sum(p * np.log2(p) for p in probs) if probs else 0
            
            balance_metrics[split] = {
                'class_frequencies': frequencies,
                'total_annotations': total,
                'imbalance_ratio': imbalance_ratio,
                'entropy': entropy,
                'max_class_freq': max_freq,
                'min_class_freq': min_freq,
                'class_percentages': [(f/total)*100 for f in frequencies]
            }
    
    return balance_metrics

def generate_report(class_distribution, image_size_analysis, annotation_quality, balance_analysis, test_availability):
    """Générer un rapport détaillé"""
    print("\n" + "="*80)
    print("📋 RAPPORT D'ANALYSE DU DATASET")
    print("="*80)
    
    class_names = ['swimmer', 'swimmer with life jacket', 'boat', 'life jacket']
    
    # 0. Disponibilité du test
    print("\n🧪 DISPONIBILITÉ DU TEST")
    print("-" * 40)
    
    for scenario, info in test_availability.items():
        status = "✅" if info['exists'] else "❌"
        recommended = "🌟 RECOMMANDÉ" if info['recommended'] and info['exists'] else ""
        print(f"{status} {scenario}: {info['description']}")
        if info['exists']:
            print(f"   📁 Fichiers: {info['file_count']} {recommended}")
        print()
    
    # Recommandations pour le test
    has_internal_test = test_availability.get('test_internal', {}).get('exists', False)
    if not has_internal_test:
        print("⚠️  RECOMMANDATION CRITIQUE:")
        print("   Créez un test interne avec: python scripts/prepare_test_split.py")
        print("   Nécessaire pour avoir des métriques de test fiables")
        print()
    
    # 1. Distribution des classes
    print("\n🏷️  DISTRIBUTION DES CLASSES")
    print("-" * 40)
    for split, data in class_distribution.items():
        print(f"\n{split.upper()}:")
        print(f"  Total annotations: {data['total_annotations']}")
        for class_id, count in data['class_counts'].items():
            percentage = data['class_percentages'].get(class_id, 0)
            print(f"  {class_names[class_id]}: {count} ({percentage:.1f}%)")
    
    # 2. Équilibre des classes
    print("\n⚖️  ANALYSE DE L'ÉQUILIBRE")
    print("-" * 40)
    for split, data in balance_analysis.items():
        print(f"\n{split.upper()}:")
        print(f"  Ratio de déséquilibre: {data['imbalance_ratio']:.2f}")
        print(f"  Entropie: {data['entropy']:.2f}")
        if data['imbalance_ratio'] > 10:
            print("  ⚠️  DÉSÉQUILIBRE CRITIQUE détecté!")
        elif data['imbalance_ratio'] > 5:
            print("  ⚠️  Déséquilibre modéré détecté")
    
    # 3. Qualité des annotations
    print("\n🎯 QUALITÉ DES ANNOTATIONS")
    print("-" * 40)
    for split, data in annotation_quality.items():
        print(f"\n{split.upper()}:")
        print(f"  Fichiers vides: {data['empty_files']}/{data['total_files']} ({data['empty_ratio']*100:.1f}%)")
        print(f"  Aire moyenne des bounding boxes: {data['avg_bbox_area']:.4f}")
        print(f"  Ratio moyen des bounding boxes: {data['avg_bbox_ratio']:.2f}")
    
    # 4. Recommandations
    print("\n💡 RECOMMANDATIONS D'OPTIMISATION")
    print("-" * 40)
    
    recommendations = []
    
    # Analyser le déséquilibre
    train_balance = balance_analysis.get('train', {})
    if train_balance.get('imbalance_ratio', 0) > 10:
        recommendations.append("🔥 CRITIQUE: Rééquilibrer les classes avec data augmentation ou class weights")
    elif train_balance.get('imbalance_ratio', 0) > 5:
        recommendations.append("⚠️  Appliquer des poids de classe ou augmentation des données")
    
    # Analyser la qualité
    train_quality = annotation_quality.get('train', {})
    if train_quality.get('empty_ratio', 0) > 0.1:
        recommendations.append("🗑️  Nettoyer les fichiers d'annotations vides")
    
    if train_quality.get('avg_bbox_area', 0) < 0.01:
        recommendations.append("🔍 Objets très petits détectés - considérer multi-scale training")
    
    # Analyser les métriques actuelles
    print("\n📊 ANALYSE DES MÉTRIQUES ACTUELLES")
    print("-" * 40)
    try:
        with open('outputs/evaluation/metrics.json', 'r') as f:
            metrics = json.load(f)
        
        precision = metrics.get('precision', 0)
        recall = metrics.get('recall', 0)
        
        print(f"Precision: {precision:.3f}")
        print(f"Recall: {recall:.3f}")
        print(f"mAP50: {metrics.get('mAP50', 0):.3f}")
        
        if precision > 0.85 and recall < 0.7:
            recommendations.append("📈 Modèle conservateur - augmenter le recall avec lower confidence threshold")
        elif precision < 0.7 and recall > 0.8:
            recommendations.append("🎯 Modèle trop permissif - améliorer la precision")
        
        if metrics.get('mAP50', 0) < 0.8:
            recommendations.append("🔧 Performance globale à améliorer - voir recommandations ci-dessous")
            
    except FileNotFoundError:
        print("Métriques non trouvées")
    
    # Afficher les recommandations
    for i, rec in enumerate(recommendations, 1):
        print(f"{i}. {rec}")
    
    print("\n🛠️  STRATÉGIES D'OPTIMISATION RECOMMANDÉES")
    print("-" * 40)
    strategies = [
        "1. Data Augmentation intelligente (rotation, flip, color jittering)",
        "2. Weighted loss pour gérer le déséquilibre des classes",
        "3. Multi-scale training (différentes tailles d'images)",
        "4. Label smoothing pour réduire l'overconfidence",
        "5. Ensemble de modèles (YOLOv8s, YOLOv8m)",
        "6. Optimisation des hyperparamètres (learning rate, batch size)",
        "7. Early stopping et regularization",
        "8. Test Time Augmentation (TTA)"
    ]
    
    for strategy in strategies:
        print(strategy)

if __name__ == "__main__":
    analyze_dataset()
