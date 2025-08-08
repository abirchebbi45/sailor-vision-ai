"""
Script d'évaluation avancée du modèle Sailor Vision AI
"""

import os
import json
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from ultralytics import YOLO
import cv2
from PIL import Image
import pandas as pd
from sklearn.metrics import confusion_matrix, classification_report
from pathlib import Path

def load_model(model_path):
    """Charger le modèle YOLO"""
    if not os.path.exists(model_path):
        print(f"❌ Modèle non trouvé: {model_path}")
        return None
    
    print(f"📥 Chargement du modèle: {model_path}")
    try:
        model = YOLO(model_path)
        print("✅ Modèle chargé avec succès")
        return model
    except Exception as e:
        print(f"❌ Erreur chargement: {e}")
        return None

def evaluate_on_validation(model, data_config="data/dataset.yaml"):
    """Évaluer le modèle sur l'ensemble de validation"""
    print("\n📊 ÉVALUATION SUR L'ENSEMBLE DE VALIDATION")
    print("-" * 45)
    
    try:
        results = model.val(data=data_config, split='val', save_json=True, plots=True)
        
        if hasattr(results, 'results_dict'):
            metrics = results.results_dict
            
            print("📈 Métriques globales:")
            metric_names = {
                'metrics/precision(B)': 'Précision',
                'metrics/recall(B)': 'Rappel', 
                'metrics/mAP50(B)': 'mAP@0.5',
                'metrics/mAP50-95(B)': 'mAP@0.5:0.95'
            }
            
            for key, name in metric_names.items():
                if key in metrics:
                    print(f"   {name}: {metrics[key]:.3f}")
            
            # Métriques par classe si disponibles
            class_names = ['swimmer', 'swimmer with life jacket', 'boat', 'life jacket']
            
            print(f"\n📊 Métriques par classe:")
            for i, class_name in enumerate(class_names):
                precision_key = f'metrics/precision(B)_{i}'
                recall_key = f'metrics/recall(B)_{i}'
                map50_key = f'metrics/mAP50(B)_{i}'
                
                if precision_key in metrics:
                    print(f"   {class_name}:")
                    print(f"      Précision: {metrics.get(precision_key, 0):.3f}")
                    print(f"      Rappel: {metrics.get(recall_key, 0):.3f}")
                    print(f"      mAP@0.5: {metrics.get(map50_key, 0):.3f}")
        
        return results
        
    except Exception as e:
        print(f"❌ Erreur évaluation: {e}")
        return None

def test_on_sample_images(model, test_dir="data/images/test", num_samples=10):
    """Tester le modèle sur un échantillon d'images"""
    print(f"\n🖼️  TEST SUR ÉCHANTILLON D'IMAGES")
    print("-" * 35)
    
    if not os.path.exists(test_dir):
        print(f"❌ Dossier test non trouvé: {test_dir}")
        return
    
    # Obtenir les images de test
    image_files = [f for f in os.listdir(test_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    
    if not image_files:
        print(f"❌ Aucune image trouvée dans {test_dir}")
        return
    
    # Échantillonner des images
    sample_images = np.random.choice(image_files, min(num_samples, len(image_files)), replace=False)
    
    print(f"🎯 Test sur {len(sample_images)} images...")
    
    results_summary = {
        'total_detections': 0,
        'detections_by_class': {0: 0, 1: 0, 2: 0, 3: 0},
        'average_confidence': 0,
        'images_with_detections': 0
    }
    
    class_names = ['swimmer', 'swimmer with life jacket', 'boat', 'life jacket']
    
    for i, img_file in enumerate(sample_images):
        img_path = os.path.join(test_dir, img_file)
        print(f"   📸 {i+1}/{len(sample_images)}: {img_file}")
        
        try:
            # Faire la prédiction
            results = model.predict(img_path, conf=0.25, save=False, verbose=False)
            
            if results and len(results) > 0:
                result = results[0]
                
                if result.boxes is not None and len(result.boxes) > 0:
                    boxes = result.boxes
                    detections = len(boxes)
                    results_summary['total_detections'] += detections
                    results_summary['images_with_detections'] += 1
                    
                    confidences = boxes.conf.cpu().numpy()
                    classes = boxes.cls.cpu().numpy().astype(int)
                    
                    results_summary['average_confidence'] += np.mean(confidences)
                    
                    print(f"      🎯 {detections} détection(s):")
                    for j, (cls, conf) in enumerate(zip(classes, confidences)):
                        if cls < len(class_names):
                            print(f"         - {class_names[cls]}: {conf:.2f}")
                            results_summary['detections_by_class'][cls] += 1
                else:
                    print(f"      ❌ Aucune détection")
            
        except Exception as e:
            print(f"      ❌ Erreur: {e}")
    
    # Résumé des résultats
    print(f"\n📊 RÉSUMÉ DES TESTS:")
    print(f"   Détections totales: {results_summary['total_detections']}")
    print(f"   Images avec détections: {results_summary['images_with_detections']}/{len(sample_images)}")
    
    if results_summary['images_with_detections'] > 0:
        avg_conf = results_summary['average_confidence'] / results_summary['images_with_detections']
        print(f"   Confiance moyenne: {avg_conf:.3f}")
        
        print(f"   Détections par classe:")
        for cls, count in results_summary['detections_by_class'].items():
            if cls < len(class_names):
                print(f"      {class_names[cls]}: {count}")

def benchmark_inference_speed(model, test_image_path="data/images/val", num_tests=50):
    """Tester la vitesse d'inférence"""
    print(f"\n⚡ BENCHMARK DE VITESSE D'INFÉRENCE")
    print("-" * 35)
    
    if not os.path.exists(test_image_path):
        print(f"❌ Chemin test non trouvé: {test_image_path}")
        return
    
    # Obtenir une image de test
    if os.path.isfile(test_image_path):
        test_img = test_image_path
    else:
        images = [f for f in os.listdir(test_image_path) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        if not images:
            print("❌ Aucune image trouvée pour le test")
            return
        test_img = os.path.join(test_image_path, images[0])
    
    print(f"🖼️  Image de test: {test_img}")
    print(f"🔢 Nombre de tests: {num_tests}")
    
    # Tests de vitesse
    times = []
    
    # Warm-up
    for _ in range(5):
        model.predict(test_img, verbose=False)
    
    print("⏱️  Tests en cours...")
    
    import time
    for i in range(num_tests):
        start_time = time.time()
        results = model.predict(test_img, verbose=False)
        end_time = time.time()
        
        inference_time = (end_time - start_time) * 1000  # en millisecondes
        times.append(inference_time)
        
        if (i + 1) % 10 == 0:
            print(f"   ✓ {i+1}/{num_tests} tests complétés")
    
    # Statistiques
    times = np.array(times)
    print(f"\n📊 RÉSULTATS DE VITESSE:")
    print(f"   Temps moyen: {np.mean(times):.1f} ms")
    print(f"   Temps médian: {np.median(times):.1f} ms")
    print(f"   Temps min: {np.min(times):.1f} ms")
    print(f"   Temps max: {np.max(times):.1f} ms")
    print(f"   Écart-type: {np.std(times):.1f} ms")
    print(f"   FPS moyen: {1000/np.mean(times):.1f}")

def test_different_confidence_thresholds(model, test_images_dir="data/images/val", sample_size=20):
    """Tester différents seuils de confiance"""
    print(f"\n🎯 TEST DES SEUILS DE CONFIANCE")
    print("-" * 30)
    
    if not os.path.exists(test_images_dir):
        print(f"❌ Dossier non trouvé: {test_images_dir}")
        return
    
    # Obtenir des images de test
    image_files = [f for f in os.listdir(test_images_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    sample_images = np.random.choice(image_files, min(sample_size, len(image_files)), replace=False)
    
    # Tester différents seuils
    thresholds = [0.1, 0.25, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
    threshold_results = {}
    
    for threshold in thresholds:
        print(f"   🎯 Test seuil {threshold}...")
        
        total_detections = 0
        images_with_detections = 0
        
        for img_file in sample_images:
            img_path = os.path.join(test_images_dir, img_file)
            
            try:
                results = model.predict(img_path, conf=threshold, verbose=False)
                
                if results and len(results) > 0:
                    result = results[0]
                    if result.boxes is not None and len(result.boxes) > 0:
                        detections = len(result.boxes)
                        total_detections += detections
                        images_with_detections += 1
                        
            except:
                continue
        
        threshold_results[threshold] = {
            'total_detections': total_detections,
            'images_with_detections': images_with_detections,
            'avg_detections_per_image': total_detections / len(sample_images)
        }
    
    # Afficher les résultats
    print(f"\n📊 RÉSULTATS PAR SEUIL:")
    print("Seuil | Détections | Images | Moy/Image")
    print("-" * 40)
    
    for threshold, results in threshold_results.items():
        print(f"{threshold:4.2f} | {results['total_detections']:10d} | {results['images_with_detections']:6d} | {results['avg_detections_per_image']:8.2f}")
    
    # Recommandation
    # Trouver le seuil optimal (équilibre entre précision et rappel)
    optimal_threshold = 0.25
    for threshold in [0.3, 0.4, 0.5]:
        if threshold in threshold_results:
            if threshold_results[threshold]['avg_detections_per_image'] > 0.5:
                optimal_threshold = threshold
                break
    
    print(f"\n💡 SEUIL RECOMMANDÉ: {optimal_threshold}")
    print(f"   Basé sur l'équilibre détections/précision")

def generate_evaluation_report(model_path, output_dir="evaluation_results"):
    """Générer un rapport d'évaluation complet"""
    print(f"\n📋 GÉNÉRATION DU RAPPORT D'ÉVALUATION")
    print("-" * 40)
    
    # Créer le dossier de sortie
    os.makedirs(output_dir, exist_ok=True)
    
    # Charger le modèle
    model = load_model(model_path)
    if not model:
        return
    
    # Créer le rapport
    report_path = os.path.join(output_dir, "evaluation_report.md")
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("# Rapport d'Évaluation - Sailor Vision AI\n\n")
        f.write(f"**Modèle**: {model_path}\n")
        f.write(f"**Date**: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("## Résumé Exécutif\n\n")
        f.write("Ce rapport présente l'évaluation complète du modèle YOLOv8 ")
        f.write("pour la détection d'objets maritimes (nageurs, gilets de sauvetage, bateaux).\n\n")
        
        f.write("## Métriques de Performance\n\n")
        f.write("### Validation Set\n")
        f.write("*(Exécuter l'évaluation complète pour obtenir ces métriques)*\n\n")
        
        f.write("### Tests sur Échantillon\n")
        f.write("*(Résultats des tests sur images de test)*\n\n")
        
        f.write("## Analyse de Vitesse\n\n")
        f.write("### Temps d'Inférence\n")
        f.write("*(Résultats du benchmark de vitesse)*\n\n")
        
        f.write("## Recommandations\n\n")
        f.write("### Seuils de Confiance\n")
        f.write("- **Production**: Utiliser seuil 0.4-0.5 pour équilibrer précision/rappel\n")
        f.write("- **Surveillance critique**: Réduire à 0.25-0.3 pour maximiser le rappel\n")
        f.write("- **Applications temps réel**: Optimiser selon contraintes de vitesse\n\n")
        
        f.write("### Améliorations Possibles\n")
        f.write("1. **Augmentation de données**: Plus d'exemples de conditions difficiles\n")
        f.write("2. **Post-processing**: Filtrage temporel pour vidéos\n")
        f.write("3. **Ensemble de modèles**: Combiner plusieurs variants YOLOv8\n")
        f.write("4. **Fine-tuning**: Ajustement spécifique au domaine maritime\n\n")
    
    print(f"✅ Rapport généré: {report_path}")

def main():
    """Fonction principale d'évaluation"""
    print("🌊 ÉVALUATION AVANCÉE - SAILOR VISION AI")
    print("=" * 50)
    
    # Chercher le meilleur modèle disponible
    model_paths = [
        "outputs/train_balanced/sailor_vision_balanced/weights/best.pt",
        "outputs/train/train_yolo/weights/best.pt",
        "outputs/exports/yolov8_best.pt",
        "yolov8n.pt"  # fallback
    ]
    
    model_path = None
    for path in model_paths:
        if os.path.exists(path):
            model_path = path
            break
    
    if not model_path:
        print("❌ Aucun modèle trouvé!")
        print("Entraînez d'abord un modèle avec optimize_model.py")
        return
    
    print(f"🎯 Modèle sélectionné: {model_path}")
    
    # Charger le modèle
    model = load_model(model_path)
    if not model:
        return
    
    # Menu d'évaluation
    print(f"\n📋 MENU D'ÉVALUATION:")
    print("1. 📊 Évaluation complète sur validation")
    print("2. 🖼️  Test sur échantillon d'images")
    print("3. ⚡ Benchmark de vitesse")
    print("4. 🎯 Test des seuils de confiance")
    print("5. 📋 Rapport complet")
    print("6. 🚀 Évaluation complète (toutes les options)")
    
    try:
        choice = int(input("\nChoisissez une option (1-6): "))
    except ValueError:
        choice = 6
    
    # Exécuter selon le choix
    if choice == 1 or choice == 6:
        evaluate_on_validation(model)
    
    if choice == 2 or choice == 6:
        test_on_sample_images(model)
    
    if choice == 3 or choice == 6:
        benchmark_inference_speed(model)
    
    if choice == 4 or choice == 6:
        test_different_confidence_thresholds(model)
    
    if choice == 5 or choice == 6:
        generate_evaluation_report(model_path)
    
    print(f"\n🎉 Évaluation terminée!")
    print(f"💡 Pour l'inférence en production, utilisez:")
    print(f"   model = YOLO('{model_path}')")
    print(f"   results = model.predict(image, conf=0.4)")

if __name__ == "__main__":
    main()
