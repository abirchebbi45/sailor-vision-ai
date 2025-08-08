# 🚀 GPU SETUP GUIDE FOR SAILOR VISION AI

## 🎯 Overview

Complete setup guide for optimal GPU performance with GTX 1050 and maritime object detection.

## 💻 Hardware Requirements

### ✅ **Minimum Configuration**
- **GPU**: GTX 1050 (2GB VRAM minimum)
- **RAM**: 8GB system RAM
- **Storage**: 10GB free space for dataset
- **CUDA**: Version 11.8+ recommended

### 🏆 **Recommended Configuration**
- **GPU**: GTX 1050 Ti or higher
- **RAM**: 16GB system RAM
- **Storage**: SSD with 20GB+ free space
- **CUDA**: Latest stable version

## 🔧 Installation Steps

### **STEP 1: CUDA Installation**

```bash
# Check if CUDA is installed
nvidia-smi

# If not installed, download from:
# https://developer.nvidia.com/cuda-downloads
```

### **STEP 2: Python Environment**

```bash
# Create virtual environment
python -m venv sailor-vision-env

# Activate environment
# Windows:
sailor-vision-env\Scripts\activate
# Linux/Mac:
source sailor-vision-env/bin/activate

# Install requirements
pip install -r requirements_gpu.txt
```

### **STEP 3: Verify Installation**

```bash
python scripts/check_gpu.py
```

**Expected output:**
```
✅ CUDA available: True
✅ GPU detected: GeForce GTX 1050
✅ GPU memory: 2048MB
✅ PyTorch GPU support: True
```

## ⚙️ Optimization Configuration

### **GTX 1050 Optimized Settings (`gpu_config.yaml`)**

```yaml
# Optimal settings for GTX 1050
batch_size: 4          # Max for 2GB VRAM
workers: 2             # CPU threads
image_size: 640        # Standard YOLO
mixed_precision: true  # Memory saving
device: 'cuda:0'       # GPU device
```

### **Memory Management**

```python
# Automatic settings in optimize_model.py
if gpu_memory < 4096:  # Less than 4GB
    config['batch_size'] = 4
    config['workers'] = 2
    config['mixed_precision'] = True
```

## 🔍 Troubleshooting

### **Problem: CUDA Out of Memory**
```bash
# Solution 1: Reduce batch size
batch_size: 2  # Instead of 4

# Solution 2: Reduce image size
image_size: 416  # Instead of 640

# Solution 3: Enable mixed precision
mixed_precision: true
```

### **Problem: Slow Training**
```bash
# Check GPU utilization
nvidia-smi -l 1

# Optimize workers
workers: 4  # If CPU allows

# Use SSD storage for faster I/O
```

### **Problem: Driver Issues**
```bash
# Update NVIDIA drivers
# Download from: https://www.nvidia.com/drivers

# Verify installation
nvidia-smi
python -c "import torch; print(torch.cuda.is_available())"
```

## 📊 Performance Benchmarks

### **GTX 1050 Expected Performance**

| Configuration | Speed (img/sec) | Memory Usage | Quality |
|---------------|----------------|--------------|---------|
| **Balanced** | 12-15 | 1.8GB | High |
| **Speed** | 20-25 | 1.2GB | Medium |
| **Quality** | 8-12 | 2.0GB | Highest |

### **Training Times (27k images)**

- **Balanced config**: 2-3 hours
- **Speed config**: 1.5-2 hours  
- **Quality config**: 3-4 hours

## 🎯 Best Practices

### ✅ **DO**
- Monitor GPU temperature (< 80°C)
- Use virtual environments
- Close other GPU applications
- Use SSD for dataset storage
- Enable mixed precision training

### ❌ **DON'T**
- Use batch_size > 8 on GTX 1050
- Train without monitoring GPU memory
- Mix CUDA versions
- Use image_size > 640 on 2GB GPU
- Forget to activate virtual environment

## 🚀 Quick Start Commands

```bash
# 1. Setup environment
python -m venv sailor-vision-env
sailor-vision-env\Scripts\activate
pip install -r requirements_gpu.txt

# 2. Verify GPU
python scripts/check_gpu.py

# 3. Run optimization
python optimize_model.py

# 4. Monitor training
tensorboard --logdir=outputs/
```

## 📞 Support

### **Common Commands**
```bash
# Check GPU status
nvidia-smi

# Monitor training
watch -n 5 nvidia-smi

# Check CUDA version
nvcc --version

# Verify PyTorch GPU
python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}, Device: {torch.cuda.get_device_name()}')"
```

---

🚀 **Your GTX 1050 is ready for maritime object detection optimization!** 🌊