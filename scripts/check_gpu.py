import torch

# Vérifier si un GPU est disponible
gpu_available = torch.cuda.is_available()

if gpu_available:
    gpu_name = torch.cuda.get_device_name(0)
    gpu_count = torch.cuda.device_count()
    current_gpu = torch.cuda.current_device()
    
    print(f"GPU détecté : {gpu_name}")
    print(f"Nombre de GPU disponibles : {gpu_count}")
    print(f"GPU actuellement utilisé : {current_gpu}")
    
    # Tester une opération simple sur le GPU
    try:
        tensor = torch.rand(3, 3).to("cuda")
        print("Le GPU fonctionne correctement avec PyTorch.")
    except Exception as e:
        print("Erreur lors du test d'opération sur le GPU :", e)
else:
    print("Aucun GPU détecté. L'entraînement se fera sur CPU.")
