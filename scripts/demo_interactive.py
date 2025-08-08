"""
Démo interactive du modèle Sailor Vision AI
"""

import os
import cv2
import numpy as np
from ultralytics import YOLO
import threading
import time

class SailorVisionDemo:
    def __init__(self):
        self.model = None
        self.conf_threshold = 0.4
        
    def load_model(self, model_path=None):
        """Charger un modèle YOLO"""
        if not model_path:
            # Chercher automatiquement le meilleur modèle
            model_paths = [
                "outputs/train_balanced/sailor_vision_balanced/weights/best.pt",
                "outputs/train/train_yolo/weights/best.pt", 
                "outputs/exports/yolov8_best.pt",
                "yolov8n.pt"
            ]
            
            for path in model_paths:
                if os.path.exists(path):
                    model_path = path
                    break
        
        if not model_path or not os.path.exists(model_path):
            print("❌ Aucun modèle trouvé!")
            return False
        
        try:
            print(f"📥 Chargement du modèle: {model_path}")
            self.model = YOLO(model_path)
            print("✅ Modèle chargé avec succès")
            return True
        except Exception as e:
            print(f"❌ Erreur chargement: {e}")
            return False
    
    def test_image(self, image_path):
        """Tester le modèle sur une image"""
        if not self.model:
            print("❌ Veuillez d'abord charger un modèle")
            return
        
        if not os.path.exists(image_path):
            print(f"❌ Image non trouvée: {image_path}")
            return
        
        print(f"🖼️  Analyse de l'image: {os.path.basename(image_path)}")
        
        try:
            # Prédiction
            results = self.model.predict(image_path, conf=self.conf_threshold, save=True)
            
            if results and len(results) > 0:
                result = results[0]
                
                if result.boxes is not None and len(result.boxes) > 0:
                    boxes = result.boxes
                    detections = len(boxes)
                    
                    print(f"🎯 {detections} détection(s) trouvée(s):")
                    
                    class_names = ['swimmer', 'swimmer with life jacket', 'boat', 'life jacket']
                    
                    for i, box in enumerate(boxes):
                        conf = box.conf[0].cpu().numpy()
                        cls = int(box.cls[0].cpu().numpy())
                        
                        if cls < len(class_names):
                            class_name = class_names[cls]
                            print(f"   {i+1}. {class_name}: {conf:.3f}")
                    
                    print("✅ Image traitée avec succès")
                    print(f"📁 Image sauvegardée dans: runs/detect/predict/")
                else:
                    print("❌ Aucune détection trouvée")
            
        except Exception as e:
            print(f"❌ Erreur traitement: {e}")
    
    def test_video(self, video_path, save_video=False):
        """Tester le modèle sur une vidéo"""
        if not self.model:
            print("❌ Veuillez d'abord charger un modèle")
            return
        
        if not os.path.exists(video_path):
            print(f"❌ Vidéo non trouvée: {video_path}")
            return
        
        print(f"🎬 Analyse de la vidéo: {os.path.basename(video_path)}")
        
        try:
            cap = cv2.VideoCapture(video_path)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            
            print(f"📊 Propriétés: {total_frames} frames, {fps:.1f} FPS")
            
            # Configuration de l'enregistrement vidéo
            if save_video:
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                out = cv2.VideoWriter('output_demo.mp4', fourcc, fps, 
                                    (int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), 
                                     int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))))
            
            detections_count = 0
            frames_with_detections = 0
            frame_count = 0
            
            class_names = ['swimmer', 'swimmer with life jacket', 'boat', 'life jacket']
            class_counts = {name: 0 for name in class_names}
            
            print("🔍 Traitement en cours... (Appuyez sur 'q' pour arrêter)")
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                frame_count += 1
                
                # Prédiction
                results = self.model.predict(frame, conf=self.conf_threshold, verbose=False)
                
                # Traiter les détections
                if results and len(results) > 0:
                    result = results[0]
                    
                    if result.boxes is not None and len(result.boxes) > 0:
                        frames_with_detections += 1
                        boxes = result.boxes
                        
                        # Dessiner les bounding boxes
                        for box in boxes:
                            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                            conf = box.conf[0].cpu().numpy()
                            cls = int(box.cls[0].cpu().numpy())
                            
                            if cls < len(class_names):
                                class_name = class_names[cls]
                                class_counts[class_name] += 1
                                detections_count += 1
                                
                                # Couleur selon la classe
                                color = (0, 255, 0) if 'life jacket' in class_name else (255, 0, 0)
                                
                                # Dessiner la bounding box
                                cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
                                
                                # Texte
                                label = f"{class_name}: {conf:.2f}"
                                cv2.putText(frame, label, (int(x1), int(y1)-10), 
                                          cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                
                # Affichage et enregistrement
                cv2.imshow('Sailor Vision AI - Démo Vidéo', frame)
                
                if save_video:
                    out.write(frame)
                
                # Afficher le progrès
                if frame_count % 30 == 0:
                    progress = (frame_count / total_frames) * 100
                    print(f"   📊 Progrès: {progress:.1f}%")
                
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            
            cap.release()
            if save_video:
                out.release()
                print(f"📹 Vidéo sauvegardée: output_demo.mp4")
            
            cv2.destroyAllWindows()
            
            # Résultats
            print(f"\n📊 RÉSULTATS:")
            print(f"   Frames traitées: {frame_count}")
            print(f"   Frames avec détections: {frames_with_detections}")
            print(f"   Total détections: {detections_count}")
            
            if detections_count > 0:
                print(f"\n📈 Détections par classe:")
                for class_name, count in class_counts.items():
                    if count > 0:
                        percentage = (count / detections_count) * 100
                        print(f"   {class_name}: {count} ({percentage:.1f}%)")
            
            print("✅ Vidéo analysée avec succès")
            
        except Exception as e:
            print(f"❌ Erreur traitement vidéo: {e}")
    
    def start_camera(self):
        """Démarrer la caméra en temps réel"""
        if not self.model:
            print("❌ Veuillez d'abord charger un modèle")
            return
        
        print("📹 Démarrage de la caméra...")
        
        try:
            cap = cv2.VideoCapture(0)
            
            if not cap.isOpened():
                print("❌ Impossible d'ouvrir la caméra")
                return
            
            print("✅ Caméra démarrée - Appuyez sur 'q' pour arrêter")
            
            class_names = ['swimmer', 'swimmer with life jacket', 'boat', 'life jacket']
            detection_count = 0
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Prédiction
                results = self.model.predict(frame, conf=self.conf_threshold, verbose=False)
                
                # Dessiner les détections
                if results and len(results) > 0:
                    result = results[0]
                    
                    if result.boxes is not None and len(result.boxes) > 0:
                        boxes = result.boxes
                        
                        for box in boxes:
                            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                            conf = box.conf[0].cpu().numpy()
                            cls = int(box.cls[0].cpu().numpy())
                            
                            if cls < len(class_names):
                                class_name = class_names[cls]
                                detection_count += 1
                                
                                # Couleur selon la classe
                                if 'life jacket' in class_name:
                                    color = (0, 255, 0)  # Vert pour gilets de sauvetage
                                elif 'swimmer' in class_name:
                                    color = (255, 255, 0)  # Cyan pour nageurs
                                else:
                                    color = (255, 0, 0)  # Rouge pour bateaux
                                
                                # Dessiner la bounding box
                                cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
                                
                                # Texte
                                label = f"{class_name}: {conf:.2f}"
                                cv2.putText(frame, label, (int(x1), int(y1)-10), 
                                          cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                
                # Informations à l'écran
                cv2.putText(frame, f"Detections: {detection_count}", (10, 30), 
                          cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                cv2.putText(frame, f"Confidence: {self.conf_threshold:.2f}", (10, 60), 
                          cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                
                # Afficher
                cv2.imshow('Sailor Vision AI - Caméra en Temps Réel', frame)
                
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                elif key == ord('+') or key == ord('='):
                    self.conf_threshold = min(0.9, self.conf_threshold + 0.05)
                    print(f"Seuil confiance: {self.conf_threshold:.2f}")
                elif key == ord('-'):
                    self.conf_threshold = max(0.1, self.conf_threshold - 0.05)
                    print(f"Seuil confiance: {self.conf_threshold:.2f}")
            
            cap.release()
            cv2.destroyAllWindows()
            print("📹 Caméra arrêtée")
            print(f"📊 Total détections: {detection_count}")
            
        except Exception as e:
            print(f"❌ Erreur caméra: {e}")

def demo_simple():
    """Démo simple en ligne de commande"""
    print("🌊 SAILOR VISION AI - DÉMO SIMPLE")
    print("=" * 40)
    
    demo = SailorVisionDemo()
    
    # Charger le modèle
    if not demo.load_model():
        return
    
    # Test sur images d'exemple
    test_dir = "data/images/test"
    if os.path.exists(test_dir):
        images = [f for f in os.listdir(test_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        
        if images:
            print(f"\n🖼️  Test sur quelques images...")
            
            # Prendre quelques images au hasard
            import random
            sample_images = random.sample(images, min(3, len(images)))
            
            for img_file in sample_images:
                img_path = os.path.join(test_dir, img_file)
                demo.test_image(img_path)
                print()
    
    # Test vidéo si disponible
    video_dir = "data/test"
    if os.path.exists(video_dir):
        videos = [f for f in os.listdir(video_dir) if f.lower().endswith(('.mp4', '.avi', '.mov'))]
        
        if videos:
            print(f"🎬 Vidéos disponibles:")
            for i, video in enumerate(videos[:3]):
                print(f"   {i+1}. {video}")
            
            choice = input("\\nVoulez-vous tester une vidéo? (o/n): ")
            if choice.lower() == 'o':
                video_path = os.path.join(video_dir, videos[0])
                demo.test_video(video_path)
    
    print(f"\\n✅ Démo terminée!")

def demo_interactive():
    """Démo interactive avec menu"""
    print("🌊 SAILOR VISION AI - DÉMO INTERACTIVE")
    print("=" * 45)
    
    demo = SailorVisionDemo()
    
    # Charger le modèle
    if not demo.load_model():
        return
    
    while True:
        print(f"\\n📋 MENU PRINCIPAL:")
        print("1. 📸 Test sur image")
        print("2. 🎬 Test sur vidéo")
        print("3. 📹 Caméra en temps réel")
        print("4. ⚙️  Changer seuil confiance")
        print("5. 🚪 Quitter")
        
        try:
            choice = int(input("\\nChoisissez une option (1-5): "))
        except ValueError:
            print("❌ Choix invalide")
            continue
        
        if choice == 1:
            image_path = input("Chemin de l'image: ")
            demo.test_image(image_path)
            
        elif choice == 2:
            video_path = input("Chemin de la vidéo: ")
            save = input("Sauvegarder la vidéo avec détections? (o/n): ").lower() == 'o'
            demo.test_video(video_path, save)
            
        elif choice == 3:
            demo.start_camera()
            
        elif choice == 4:
            try:
                new_conf = float(input(f"Nouveau seuil (actuel: {demo.conf_threshold:.2f}): "))
                if 0.1 <= new_conf <= 0.9:
                    demo.conf_threshold = new_conf
                    print(f"✅ Seuil mis à jour: {demo.conf_threshold:.2f}")
                else:
                    print("❌ Seuil doit être entre 0.1 et 0.9")
            except ValueError:
                print("❌ Valeur invalide")
        
        elif choice == 5:
            print("👋 Au revoir!")
            break
        
        else:
            print("❌ Choix invalide")

def main():
    """Fonction principale"""
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--simple":
            demo_simple()
        elif sys.argv[1] == "--interactive":
            demo_interactive()
        elif sys.argv[1] == "--image" and len(sys.argv) > 2:
            demo = SailorVisionDemo()
            if demo.load_model():
                demo.test_image(sys.argv[2])
        elif sys.argv[1] == "--video" and len(sys.argv) > 2:
            demo = SailorVisionDemo()
            if demo.load_model():
                demo.test_video(sys.argv[2])
        elif sys.argv[1] == "--camera":
            demo = SailorVisionDemo()
            if demo.load_model():
                demo.start_camera()
        else:
            print("Usage:")
            print("  python demo.py --simple         # Démo simple")
            print("  python demo.py --interactive    # Démo interactive")
            print("  python demo.py --image <path>   # Test sur image")
            print("  python demo.py --video <path>   # Test sur vidéo")
            print("  python demo.py --camera         # Caméra temps réel")
    else:
        demo_interactive()

if __name__ == "__main__":
    main()
