"""
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
