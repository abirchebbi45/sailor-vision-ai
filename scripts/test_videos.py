"""
Script de test vidéo pour Sailor Vision AI
Teste le modèle sur les vidéos et génère des rapports de détection
"""

import os
import cv2
import json
import numpy as np
from ultralytics import YOLO
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

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

def analyze_video(model, video_path, output_dir, conf_threshold=0.4, save_frames=True):
    """Analyser une vidéo avec le modèle"""
    print(f"\n🎬 ANALYSE VIDÉO: {os.path.basename(video_path)}")
    print("-" * 50)
    
    if not os.path.exists(video_path):
        print(f"❌ Vidéo non trouvée: {video_path}")
        return None
    
    # Créer le dossier de sortie
    video_name = Path(video_path).stem
    video_output_dir = os.path.join(output_dir, video_name)
    os.makedirs(video_output_dir, exist_ok=True)
    
    if save_frames:
        frames_dir = os.path.join(video_output_dir, "frames_with_detections")
        os.makedirs(frames_dir, exist_ok=True)
    
    # Ouvrir la vidéo
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        print(f"❌ Impossible d'ouvrir la vidéo: {video_path}")
        return None
    
    # Propriétés de la vidéo
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps if fps > 0 else 0
    
    print(f"📊 Propriétés vidéo:")
    print(f"   FPS: {fps:.1f}")
    print(f"   Total frames: {total_frames}")
    print(f"   Durée: {duration:.1f} secondes")
    
    # Variables pour l'analyse
    detections_data = []
    frame_count = 0
    detections_count = 0
    frames_with_detections = 0
    
    class_names = ['swimmer', 'swimmer with life jacket', 'boat', 'life jacket']
    class_counts = {name: 0 for name in class_names}
    
    print(f"\n🔍 Analyse en cours...")
    
    # Analyser frame par frame
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        frame_count += 1
        timestamp = frame_count / fps if fps > 0 else frame_count
        
        # Prédiction sur la frame
        results = model.predict(frame, conf=conf_threshold, verbose=False)
        
        frame_detections = []
        
        if results and len(results) > 0:
            result = results[0]
            
            if result.boxes is not None and len(result.boxes) > 0:
                frames_with_detections += 1
                boxes = result.boxes
                
                # Traiter chaque détection
                for box in boxes:
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    conf = box.conf[0].cpu().numpy()
                    cls = int(box.cls[0].cpu().numpy())
                    
                    if cls < len(class_names):
                        class_name = class_names[cls]
                        class_counts[class_name] += 1
                        detections_count += 1
                        
                        detection = {
                            'frame': frame_count,
                            'timestamp': timestamp,
                            'class': class_name,
                            'confidence': float(conf),
                            'bbox': [float(x1), float(y1), float(x2), float(y2)]
                        }
                        
                        frame_detections.append(detection)
                        detections_data.append(detection)
                        
                        # Dessiner la bounding box sur la frame
                        if save_frames:
                            color = (0, 255, 0) if 'life jacket' in class_name else (255, 0, 0)
                            cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
                            cv2.putText(frame, f"{class_name}: {conf:.2f}", 
                                      (int(x1), int(y1)-10), cv2.FONT_HERSHEY_SIMPLEX, 
                                      0.5, color, 2)
                
                # Sauvegarder la frame avec détections
                if save_frames and frame_detections:
                    frame_filename = f"frame_{frame_count:06d}_{timestamp:.1f}s.jpg"
                    frame_path = os.path.join(frames_dir, frame_filename)
                    cv2.imwrite(frame_path, frame)
        
        # Afficher le progrès
        if frame_count % max(1, total_frames // 20) == 0:
            progress = (frame_count / total_frames) * 100
            print(f"   🎯 Progrès: {progress:.1f}% ({frame_count}/{total_frames})")
    
    cap.release()
    
    # Statistiques finales
    print(f"\n📊 RÉSULTATS D'ANALYSE:")
    print(f"   Frames analysées: {frame_count}")
    print(f"   Frames avec détections: {frames_with_detections}")
    print(f"   Pourcentage avec détections: {(frames_with_detections/frame_count)*100:.1f}%")
    print(f"   Total détections: {detections_count}")
    print(f"   Détections par frame (moyenne): {detections_count/frame_count:.2f}")
    
    print(f"\n📈 DÉTECTIONS PAR CLASSE:")
    for class_name, count in class_counts.items():
        percentage = (count / detections_count * 100) if detections_count > 0 else 0
        print(f"   {class_name}: {count} ({percentage:.1f}%)")
    
    # Sauvegarder les données
    analysis_results = {
        'video_info': {
            'filename': os.path.basename(video_path),
            'fps': fps,
            'total_frames': total_frames,
            'duration_seconds': duration
        },
        'analysis_summary': {
            'frames_analyzed': frame_count,
            'frames_with_detections': frames_with_detections,
            'total_detections': detections_count,
            'detection_rate': frames_with_detections / frame_count if frame_count > 0 else 0,
            'avg_detections_per_frame': detections_count / frame_count if frame_count > 0 else 0
        },
        'class_statistics': class_counts,
        'detections': detections_data,
        'analysis_timestamp': datetime.now().isoformat(),
        'confidence_threshold': conf_threshold
    }
    
    # Sauvegarder en JSON
    results_file = os.path.join(video_output_dir, "analysis_results.json")
    with open(results_file, 'w') as f:
        json.dump(analysis_results, f, indent=2)
    
    print(f"\n✅ Résultats sauvegardés:")
    print(f"   📄 Données: {results_file}")
    if save_frames:
        print(f"   🖼️  Frames: {frames_dir}")
    
    return analysis_results

def generate_video_report(analysis_results, output_dir):
    """Générer un rapport détaillé de l'analyse vidéo"""
    video_name = analysis_results['video_info']['filename']
    
    report_path = os.path.join(output_dir, "video_analysis_report.md")
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(f"# Rapport d'Analyse Vidéo - {video_name}\n\n")
        
        # Informations vidéo
        f.write("## Informations Vidéo\n\n")
        f.write(f"- **Fichier**: {video_name}\n")
        f.write(f"- **FPS**: {analysis_results['video_info']['fps']:.1f}\n")
        f.write(f"- **Frames totales**: {analysis_results['video_info']['total_frames']}\n")
        f.write(f"- **Durée**: {analysis_results['video_info']['duration_seconds']:.1f} secondes\n")
        f.write(f"- **Seuil de confiance**: {analysis_results['confidence_threshold']}\n\n")
        
        # Résumé des détections
        f.write("## Résumé des Détections\n\n")
        summary = analysis_results['analysis_summary']
        f.write(f"- **Frames analysées**: {summary['frames_analyzed']}\n")
        f.write(f"- **Frames avec détections**: {summary['frames_with_detections']}\n")
        f.write(f"- **Taux de détection**: {summary['detection_rate']*100:.1f}%\n")
        f.write(f"- **Total détections**: {summary['total_detections']}\n")
        f.write(f"- **Détections par frame (moyenne)**: {summary['avg_detections_per_frame']:.2f}\n\n")
        
        # Statistiques par classe
        f.write("## Détections par Classe\n\n")
        f.write("| Classe | Nombre | Pourcentage |\n")
        f.write("|--------|--------|-------------|\n")
        
        total_detections = summary['total_detections']
        for class_name, count in analysis_results['class_statistics'].items():
            percentage = (count / total_detections * 100) if total_detections > 0 else 0
            f.write(f"| {class_name} | {count} | {percentage:.1f}% |\n")
        
        f.write("\n")
        
        # Analyse temporelle
        f.write("## Analyse Temporelle\n\n")
        detections = analysis_results['detections']
        
        if detections:
            # Compter les détections par tranche de temps (10 secondes)
            time_buckets = {}
            bucket_size = 10  # secondes
            
            for detection in detections:
                bucket = int(detection['timestamp'] // bucket_size) * bucket_size
                if bucket not in time_buckets:
                    time_buckets[bucket] = 0
                time_buckets[bucket] += 1
            
            f.write(f"### Détections par tranche de {bucket_size} secondes\n\n")
            f.write("| Temps (s) | Détections |\n")
            f.write("|-----------|------------|\n")
            
            for bucket in sorted(time_buckets.keys()):
                f.write(f"| {bucket}-{bucket+bucket_size} | {time_buckets[bucket]} |\n")
        
        f.write("\n")
        
        # Recommandations
        f.write("## Recommandations\n\n")
        
        detection_rate = summary['detection_rate']
        
        if detection_rate > 0.5:
            f.write("✅ **Bonne couverture de détection**\n")
            f.write("- Le modèle détecte des objets dans plus de 50% des frames\n")
        elif detection_rate > 0.2:
            f.write("⚠️ **Couverture modérée**\n")
            f.write("- Considérer l'ajustement du seuil de confiance\n")
            f.write("- Vérifier la qualité de la vidéo\n")
        else:
            f.write("❌ **Couverture faible**\n")
            f.write("- Réduire le seuil de confiance\n")
            f.write("- Vérifier si le modèle est adapté au contenu\n")
        
        f.write("\n")
        
        # Analyse de sécurité
        life_jacket_count = analysis_results['class_statistics'].get('life jacket', 0)
        swimmer_count = analysis_results['class_statistics'].get('swimmer', 0)
        
        f.write("## Analyse de Sécurité Maritime\n\n")
        
        if life_jacket_count > swimmer_count * 0.8:
            f.write("✅ **Bonne utilisation des gilets de sauvetage**\n")
        elif life_jacket_count > swimmer_count * 0.5:
            f.write("⚠️ **Utilisation modérée des gilets de sauvetage**\n")
        else:
            f.write("❌ **Utilisation insuffisante des gilets de sauvetage**\n")
            f.write("- Situation potentiellement dangereuse détectée\n")
    
    print(f"📋 Rapport généré: {report_path}")

def analyze_multiple_videos(model, videos_dir="data/test", output_dir="video_analysis_results", conf_threshold=0.4):
    """Analyser plusieurs vidéos"""
    print(f"\n🎬 ANALYSE DE PLUSIEURS VIDÉOS")
    print("-" * 35)
    
    if not os.path.exists(videos_dir):
        print(f"❌ Dossier vidéos non trouvé: {videos_dir}")
        return
    
    # Trouver les vidéos
    video_extensions = ['.mp4', '.avi', '.mov', '.mkv']
    video_files = []
    
    for file in os.listdir(videos_dir):
        if any(file.lower().endswith(ext) for ext in video_extensions):
            video_files.append(os.path.join(videos_dir, file))
    
    if not video_files:
        print(f"❌ Aucune vidéo trouvée dans {videos_dir}")
        return
    
    print(f"🎯 {len(video_files)} vidéo(s) trouvée(s)")
    
    # Créer le dossier de sortie principal
    os.makedirs(output_dir, exist_ok=True)
    
    all_results = []
    
    # Analyser chaque vidéo
    for i, video_path in enumerate(video_files):
        print(f"\n📹 Vidéo {i+1}/{len(video_files)}")
        
        results = analyze_video(model, video_path, output_dir, conf_threshold)
        if results:
            all_results.append(results)
            
            # Générer le rapport pour cette vidéo
            video_output_dir = os.path.join(output_dir, Path(video_path).stem)
            generate_video_report(results, video_output_dir)
    
    # Générer un rapport global
    if all_results:
        generate_global_report(all_results, output_dir)

def generate_global_report(all_results, output_dir):
    """Générer un rapport global pour toutes les vidéos"""
    global_report_path = os.path.join(output_dir, "global_analysis_report.md")
    
    with open(global_report_path, 'w', encoding='utf-8') as f:
        f.write("# Rapport Global d'Analyse Vidéo - Sailor Vision AI\n\n")
        f.write(f"**Date d'analyse**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Nombre de vidéos**: {len(all_results)}\n\n")
        
        # Statistiques globales
        f.write("## Statistiques Globales\n\n")
        
        total_frames = sum(r['analysis_summary']['frames_analyzed'] for r in all_results)
        total_detections = sum(r['analysis_summary']['total_detections'] for r in all_results)
        
        f.write(f"- **Total frames analysées**: {total_frames:,}\n")
        f.write(f"- **Total détections**: {total_detections:,}\n")
        f.write(f"- **Détections par frame (moyenne)**: {total_detections/total_frames:.3f}\n\n")
        
        # Détails par vidéo
        f.write("## Détails par Vidéo\n\n")
        f.write("| Vidéo | Durée (s) | Détections | Taux |\n")
        f.write("|-------|-----------|------------|------|\n")
        
        for result in all_results:
            video_name = result['video_info']['filename']
            duration = result['video_info']['duration_seconds']
            detections = result['analysis_summary']['total_detections']
            rate = result['analysis_summary']['detection_rate']
            f.write(f"| {video_name} | {duration:.1f} | {detections} | {rate*100:.1f}% |\n")
        
        f.write("\n")
        
        # Statistiques par classe (global)
        f.write("## Distribution des Classes (Global)\n\n")
        global_class_counts = {}
        
        for result in all_results:
            for class_name, count in result['class_statistics'].items():
                if class_name not in global_class_counts:
                    global_class_counts[class_name] = 0
                global_class_counts[class_name] += count
        
        f.write("| Classe | Total | Pourcentage |\n")
        f.write("|--------|-------|-------------|\n")
        
        for class_name, count in global_class_counts.items():
            percentage = (count / total_detections * 100) if total_detections > 0 else 0
            f.write(f"| {class_name} | {count} | {percentage:.1f}% |\n")
    
    print(f"📋 Rapport global généré: {global_report_path}")

def main():
    """Fonction principale"""
    print("🌊 TEST VIDÉO - SAILOR VISION AI")
    print("=" * 40)
    
    # Chercher le meilleur modèle disponible
    model_paths = [
        "outputs/train_balanced/sailor_vision_balanced/weights/best.pt",
        "outputs/train/train_yolo/weights/best.pt",
        "outputs/exports/yolov8_best.pt",
        "yolov8n.pt"
    ]
    
    model_path = None
    for path in model_paths:
        if os.path.exists(path):
            model_path = path
            break
    
    if not model_path:
        print("❌ Aucun modèle trouvé!")
        return
    
    print(f"🎯 Modèle sélectionné: {model_path}")
    
    # Charger le modèle
    model = load_model(model_path)
    if not model:
        return
    
    # Configuration
    videos_dir = "data/test"
    output_dir = "video_analysis_results"
    conf_threshold = 0.4
    
    print(f"\n⚙️  CONFIGURATION:")
    print(f"   Dossier vidéos: {videos_dir}")
    print(f"   Sortie: {output_dir}")
    print(f"   Seuil confiance: {conf_threshold}")
    
    # Analyser les vidéos
    analyze_multiple_videos(model, videos_dir, output_dir, conf_threshold)
    
    print(f"\n🎉 Analyse terminée!")
    print(f"📁 Consultez les résultats dans: {output_dir}")

if __name__ == "__main__":
    main()
