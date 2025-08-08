"""
Script de surveillance et d'analyse des résultats d'entraînement
"""

import os
import json
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from pathlib import Path
import yaml

def plot_training_curves(results_dir):
    """Tracer les courbes d'apprentissage"""
    
    results_csv = os.path.join(results_dir, "results.csv")
    if not os.path.exists(results_csv):
        print(f"❌ Fichier results.csv non trouvé dans {results_dir}")
        return
    
    print("📈 Création des graphiques d'entraînement...")
    
    # Charger les données
    df = pd.read_csv(results_csv)
    df.columns = df.columns.str.strip()  # Nettoyer les noms de colonnes
    
    # Créer une figure avec plusieurs sous-graphiques
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    fig.suptitle('Courbes d\'entraînement YOLOv8 - Sailor Vision AI', fontsize=16)
    
    # 1. Loss curves
    if 'train/box_loss' in df.columns and 'val/box_loss' in df.columns:
        axes[0, 0].plot(df['epoch'], df['train/box_loss'], label='Train Box Loss', color='blue')
        axes[0, 0].plot(df['epoch'], df['val/box_loss'], label='Val Box Loss', color='red')
        axes[0, 0].set_title('Box Loss')
        axes[0, 0].set_xlabel('Epoch')
        axes[0, 0].set_ylabel('Loss')
        axes[0, 0].legend()
        axes[0, 0].grid(True)
    
    # 2. Classification Loss
    if 'train/cls_loss' in df.columns and 'val/cls_loss' in df.columns:
        axes[0, 1].plot(df['epoch'], df['train/cls_loss'], label='Train Cls Loss', color='blue')
        axes[0, 1].plot(df['epoch'], df['val/cls_loss'], label='Val Cls Loss', color='red')
        axes[0, 1].set_title('Classification Loss')
        axes[0, 1].set_xlabel('Epoch')
        axes[0, 1].set_ylabel('Loss')
        axes[0, 1].legend()
        axes[0, 1].grid(True)
    
    # 3. mAP@0.5
    if 'metrics/mAP50(B)' in df.columns:
        axes[0, 2].plot(df['epoch'], df['metrics/mAP50(B)'], label='mAP@0.5', color='green')
        axes[0, 2].set_title('mAP@0.5')
        axes[0, 2].set_xlabel('Epoch')
        axes[0, 2].set_ylabel('mAP')
        axes[0, 2].legend()
        axes[0, 2].grid(True)
    
    # 4. mAP@0.5:0.95
    if 'metrics/mAP50-95(B)' in df.columns:
        axes[1, 0].plot(df['epoch'], df['metrics/mAP50-95(B)'], label='mAP@0.5:0.95', color='purple')
        axes[1, 0].set_title('mAP@0.5:0.95')
        axes[1, 0].set_xlabel('Epoch')
        axes[1, 0].set_ylabel('mAP')
        axes[1, 0].legend()
        axes[1, 0].grid(True)
    
    # 5. Precision et Recall
    if 'metrics/precision(B)' in df.columns and 'metrics/recall(B)' in df.columns:
        axes[1, 1].plot(df['epoch'], df['metrics/precision(B)'], label='Precision', color='orange')
        axes[1, 1].plot(df['epoch'], df['metrics/recall(B)'], label='Recall', color='brown')
        axes[1, 1].set_title('Precision & Recall')
        axes[1, 1].set_xlabel('Epoch')
        axes[1, 1].set_ylabel('Score')
        axes[1, 1].legend()
        axes[1, 1].grid(True)
    
    # 6. Learning Rate
    if 'lr/pg0' in df.columns:
        axes[1, 2].plot(df['epoch'], df['lr/pg0'], label='Learning Rate', color='red')
        axes[1, 2].set_title('Learning Rate')
        axes[1, 2].set_xlabel('Epoch')
        axes[1, 2].set_ylabel('LR')
        axes[1, 2].legend()
        axes[1, 2].grid(True)
        axes[1, 2].set_yscale('log')
    
    plt.tight_layout()
    
    # Sauvegarder le graphique
    output_path = os.path.join(results_dir, "training_curves.png")
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✅ Graphiques sauvegardés: {output_path}")
    
    plt.show()

def analyze_overfitting(results_dir):
    """Analyser l'overfitting"""
    
    results_csv = os.path.join(results_dir, "results.csv")
    if not os.path.exists(results_csv):
        return
    
    print("\n🔍 ANALYSE DE L'OVERFITTING")
    print("-" * 30)
    
    df = pd.read_csv(results_csv)
    df.columns = df.columns.str.strip()
    
    # Analyser les 20 dernières époques
    if len(df) > 20:
        recent_df = df.tail(20)
    else:
        recent_df = df
    
    overfitting_indicators = []
    
    # 1. Divergence entre train et val loss
    if 'train/box_loss' in df.columns and 'val/box_loss' in df.columns:
        final_train_loss = df['train/box_loss'].iloc[-1]
        final_val_loss = df['val/box_loss'].iloc[-1]
        loss_ratio = final_val_loss / final_train_loss
        
        print(f"📊 Loss final - Train: {final_train_loss:.4f}, Val: {final_val_loss:.4f}")
        print(f"   Ratio Val/Train: {loss_ratio:.2f}")
        
        if loss_ratio > 1.5:
            overfitting_indicators.append("🚨 Loss de validation significativement plus élevée que train")
        elif loss_ratio > 1.2:
            overfitting_indicators.append("⚠️  Loss de validation modérément plus élevée")
    
    # 2. Tendance des métriques de validation
    if 'metrics/mAP50(B)' in df.columns and len(recent_df) > 5:
        val_map_trend = np.polyfit(range(len(recent_df)), recent_df['metrics/mAP50(B)'], 1)[0]
        print(f"📈 Tendance mAP@0.5 (20 dernières époques): {val_map_trend:.6f}")
        
        if val_map_trend < -0.001:
            overfitting_indicators.append("🚨 mAP de validation en déclin")
        elif val_map_trend < 0:
            overfitting_indicators.append("⚠️  mAP de validation stagnante")
    
    # 3. Variance des métriques
    if 'metrics/mAP50(B)' in df.columns and len(recent_df) > 10:
        val_map_std = recent_df['metrics/mAP50(B)'].std()
        print(f"📊 Variabilité mAP@0.5: {val_map_std:.4f}")
        
        if val_map_std > 0.02:
            overfitting_indicators.append("⚠️  Métriques de validation instables")
    
    # Résumé de l'overfitting
    if overfitting_indicators:
        print(f"\n🚨 SIGNAUX D'OVERFITTING DÉTECTÉS:")
        for indicator in overfitting_indicators:
            print(f"   {indicator}")
        
        print(f"\n💡 RECOMMANDATIONS:")
        print("   • Augmenter le weight_decay")
        print("   • Réduire le learning rate")
        print("   • Augmenter les augmentations de données")
        print("   • Considérer l'early stopping")
        print("   • Ajouter de la dropout si possible")
    else:
        print("✅ Aucun signe majeur d'overfitting détecté")

def analyze_class_performance(results_dir):
    """Analyser les performances par classe"""
    
    print(f"\n📊 ANALYSE DES PERFORMANCES PAR CLASSE")
    print("-" * 40)
    
    # Chercher les fichiers de résultats de validation
    val_results_path = None
    for file in os.listdir(results_dir):
        if 'val_batch' in file and file.endswith('.jpg'):
            # Les résultats détaillés sont souvent dans les images de validation
            continue
    
    # Chercher dans les sous-dossiers
    for root, dirs, files in os.walk(results_dir):
        for file in files:
            if 'confusion_matrix' in file.lower():
                print(f"📈 Matrice de confusion trouvée: {os.path.join(root, file)}")
            elif 'class_result' in file.lower():
                print(f"📊 Résultats par classe trouvés: {os.path.join(root, file)}")
    
    # Analyser les résultats finaux
    results_csv = os.path.join(results_dir, "results.csv")
    if os.path.exists(results_csv):
        df = pd.read_csv(results_csv)
        
        # Métriques finales
        if len(df) > 0:
            final_row = df.iloc[-1]
            print(f"\n📈 MÉTRIQUES FINALES:")
            
            metrics_to_show = [
                ('metrics/precision(B)', 'Précision globale'),
                ('metrics/recall(B)', 'Rappel global'),
                ('metrics/mAP50(B)', 'mAP@0.5'),
                ('metrics/mAP50-95(B)', 'mAP@0.5:0.95')
            ]
            
            for metric_key, metric_name in metrics_to_show:
                if metric_key in final_row:
                    print(f"   {metric_name}: {final_row[metric_key]:.3f}")

def compare_models(model_dirs):
    """Comparer plusieurs modèles"""
    
    print(f"\n🏆 COMPARAISON DES MODÈLES")
    print("-" * 30)
    
    results = []
    
    for model_dir in model_dirs:
        if not os.path.exists(model_dir):
            continue
            
        results_csv = os.path.join(model_dir, "results.csv")
        if os.path.exists(results_csv):
            df = pd.read_csv(results_csv)
            if len(df) > 0:
                final_row = df.iloc[-1]
                
                model_result = {
                    'model': os.path.basename(model_dir),
                    'mAP50': final_row.get('metrics/mAP50(B)', 0),
                    'mAP50-95': final_row.get('metrics/mAP50-95(B)', 0),
                    'precision': final_row.get('metrics/precision(B)', 0),
                    'recall': final_row.get('metrics/recall(B)', 0),
                    'epochs': len(df)
                }
                results.append(model_result)
    
    if results:
        # Trier par mAP@0.5
        results.sort(key=lambda x: x['mAP50'], reverse=True)
        
        print("📊 Classement des modèles:")
        print("-" * 50)
        for i, result in enumerate(results, 1):
            print(f"{i}. {result['model']}")
            print(f"   mAP@0.5: {result['mAP50']:.3f}")
            print(f"   mAP@0.5:0.95: {result['mAP50-95']:.3f}")
            print(f"   Précision: {result['precision']:.3f}")
            print(f"   Rappel: {result['recall']:.3f}")
            print(f"   Époques: {result['epochs']}")
            print()

def generate_report(results_dir):
    """Générer un rapport complet"""
    
    print(f"\n📋 GÉNÉRATION DU RAPPORT COMPLET")
    print("-" * 35)
    
    report_path = os.path.join(results_dir, "training_report.md")
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("# Rapport d'Entraînement - Sailor Vision AI\n\n")
        f.write(f"**Date**: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Résumé des hyperparamètres
        args_file = os.path.join(results_dir, "args.yaml")
        if os.path.exists(args_file):
            f.write("## Configuration d'Entraînement\n\n")
            with open(args_file, 'r') as args_f:
                args_content = args_f.read()
                f.write(f"```yaml\n{args_content}\n```\n\n")
        
        # Métriques finales
        results_csv = os.path.join(results_dir, "results.csv")
        if os.path.exists(results_csv):
            df = pd.read_csv(results_csv)
            if len(df) > 0:
                final_row = df.iloc[-1]
                f.write("## Résultats Finaux\n\n")
                f.write("| Métrique | Valeur |\n")
                f.write("|----------|--------|\n")
                f.write(f"| mAP@0.5 | {final_row.get('metrics/mAP50(B)', 0):.3f} |\n")
                f.write(f"| mAP@0.5:0.95 | {final_row.get('metrics/mAP50-95(B)', 0):.3f} |\n")
                f.write(f"| Précision | {final_row.get('metrics/precision(B)', 0):.3f} |\n")
                f.write(f"| Rappel | {final_row.get('metrics/recall(B)', 0):.3f} |\n")
                f.write(f"| Époques | {len(df)} |\n\n")
        
        # Graphiques
        f.write("## Courbes d'Entraînement\n\n")
        f.write("![Courbes d'entraînement](training_curves.png)\n\n")
        
        # Recommandations
        f.write("## Recommandations\n\n")
        f.write("- Surveiller l'overfitting en comparant train vs validation loss\n")
        f.write("- Considérer l'augmentation de données si les performances sont insuffisantes\n")
        f.write("- Évaluer l'équilibrage des classes avec la matrice de confusion\n")
        f.write("- Tester différents seuils de confiance pour l'inférence\n")
    
    print(f"✅ Rapport généré: {report_path}")

def main():
    """Fonction principale"""
    
    # Rechercher les dossiers de résultats
    results_dirs = []
    
    # Chercher dans outputs/
    if os.path.exists("outputs"):
        for subdir in ["train", "train_balanced", "train_optimized"]:
            base_path = os.path.join("outputs", subdir)
            if os.path.exists(base_path):
                # Chercher les sous-dossiers d'expériences
                for exp_dir in os.listdir(base_path):
                    exp_path = os.path.join(base_path, exp_dir)
                    if os.path.isdir(exp_path):
                        results_csv = os.path.join(exp_path, "results.csv")
                        if os.path.exists(results_csv):
                            results_dirs.append(exp_path)
    
    if not results_dirs:
        print("❌ Aucun résultat d'entraînement trouvé!")
        print("Lancez d'abord un entraînement avec train_balanced.py")
        return
    
    print(f"🔍 {len(results_dirs)} expérience(s) d'entraînement trouvée(s)")
    
    # Analyser chaque expérience
    for i, results_dir in enumerate(results_dirs, 1):
        print(f"\n{'='*60}")
        print(f"📊 ANALYSE {i}/{len(results_dirs)}: {os.path.basename(results_dir)}")
        print(f"{'='*60}")
        
        # Tracer les courbes
        plot_training_curves(results_dir)
        
        # Analyser l'overfitting
        analyze_overfitting(results_dir)
        
        # Analyser les performances par classe
        analyze_class_performance(results_dir)
        
        # Générer le rapport
        generate_report(results_dir)
    
    # Comparer les modèles si plusieurs
    if len(results_dirs) > 1:
        compare_models(results_dirs)
    
    print(f"\n🎉 Analyse terminée!")

if __name__ == "__main__":
    main()
