# Sailor Vision AI

<p align="center">
  <img src="assets/Sailor vision logo.png" alt="Sailor Vision AI Logo" width="200">
</p>

## Project Overview

Sailor Vision AI is an advanced maritime surveillance system designed to enhance safety and situational awareness on water surfaces. The system integrates AI-powered vision modules, real-time object detection, and a desktop GUI for monitoring and managing maritime environments. It leverages **NVIDIA Orin**, **YOLOv8**, and **ROS 2** to provide a scalable and efficient solution for maritime surveillance.

This project is part of the **SailorTech** initiative, which focuses on transforming traditional watercraft into autonomous vessels using cutting-edge technologies like AI, robotics, and edge computing.

---

## System Architecture

The Sailor Vision AI system is composed of the following key components:

### 1. **ROS 2 Modules**
   - **Camera Manager**: Detects and manages connected cameras (e.g., `/dev/video*`) and publishes their list to the `/camera/list` topic.
   - **YOLOv8 Detector**: Performs real-time object detection using the YOLOv8 model and publishes detection results.
   - **Gazebo Simulation**: Simulates maritime environments for testing and development.

### 2. **Desktop GUI**
   - Built with **PyQt5**, the GUI provides an intuitive interface for managing cameras, viewing live feeds, and monitoring alerts.
   - Includes features like user management, playback of recordings, and system settings.

### 3. **Virtual Camera Integration**
   - Uses the `v4l2loopback` kernel module to simulate virtual cameras for testing and development.
   - Supports feeding video streams into virtual cameras using `ffmpeg`.

### 4. **AI Pipeline**
   - **YOLOv8 Object Detection**: Detects objects like boats, debris, and life jackets in real-time.
   - **Model Training and Evaluation**: Includes scripts for training, evaluating, and exporting YOLOv8 models.

---

## Features and Functionalities

### Core Features
- **Real-Time Object Detection**: Detects floating objects such as swimmers, life jackets, and boats using YOLOv8.
- **SAR Mission Focus**: The system is designed with Search and Rescue (SAR) missions in mind, focusing on detecting critical objects like swimmers and life jackets. The currently implemented model is optimized for SAR scenarios, with plans to extend coverage to additional maritime objects in future updates.
- **Camera Management**: Automatically detects and manages connected cameras.
- **Desktop GUI**: Provides a user-friendly interface for monitoring and managing the system.
- **Simulation Support**: Includes Gazebo simulation for testing in virtual maritime environments.
- **Virtual Camera Integration**: Simulates camera feeds for testing without physical hardware.

### Additional Functionalities
- **User Management**: Manage user accounts and permissions through the GUI.
- **Playback and Recording**: View and manage recorded video feeds.
- **Alerts and Notifications**: Receive real-time alerts for detected objects or system events.
- **ROS 2 Integration**: Modular and scalable architecture using ROS 2 for communication between components.

---

## Component Interaction

1. **ROS 2 Modules**:
   - The `camera_manager` node detects connected cameras and publishes their list to the `/camera/list` topic.
   - The `yolo_node` subscribes to camera feeds and performs object detection, publishing results to relevant topics.
   - The `gazebo_sim` module provides a simulated environment for testing.

2. **Desktop GUI**:
   - Subscribes to ROS topics to display live camera feeds and detection results.
   - Provides controls for managing cameras, viewing alerts, and configuring system settings.

3. **Virtual Camera Integration**:
   - Simulates camera feeds using `v4l2loopback` and `ffmpeg`, enabling testing without physical cameras.

---

## Installation

### Prerequisites
- **Operating System**: Ubuntu 22.04 or later
- **Python**: Version 3.10 or later
- **ROS 2**: Humble Hawksbill
- **Dependencies**:
  - `PyQt5`
  - `torch`, `ultralytics`
  - `v4l2loopback`
  - `ffmpeg`

### Setup Instructions

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/yourusername/sailor-vision-ai.git
   cd sailor-vision-ai
   ```

2. **Set Up a Python Virtual Environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install Python Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Install ROS 2 Dependencies**:
   ```bash
   sudo apt update
   sudo apt install ros-humble-desktop python3-colcon-common-extensions
   ```

5. **Build ROS 2 Workspace**:
   ```bash
   cd ros2_ws
   colcon build
   source install/setup.bash
   ```

6. **Install `v4l2loopback`**:
   ```bash
   sudo apt install v4l2loopback-dkms
   ```

---

## Usage

### 1. **Launch the ROS 2 System**
   ```bash
   ros2 launch camera_manager surveillance.launch.py
   ```

### 2. **Start the Desktop GUI**
   ```bash
   QT_QPA_PLATFORM=xcb python app.py
   ```

### 3. **Simulate a Virtual Camera**
   - **Create a Virtual Camera**:
     ```bash
     sudo modprobe v4l2loopback video_nr=10 card_label="FakeCam1" exclusive_caps=1
     ls -l /dev/video10
     ```
   - **Feed a Video into the Virtual Camera**:
     ```bash
     ffmpeg -re -stream_loop -1 \
       -i "/path/to/your/video.mp4" \
       -f v4l2 /dev/video10
     ```
   - **Display the Virtual Camera Stream**:
     ```bash
     ffplay /dev/video10
     ```

---

## Environment Variables

- `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE`: PostgreSQL database configuration for the GUI.
- `DATABASE_URL`: Full database connection URL.
- `ROS_DISTRO`: Set to `humble` for ROS 2 Humble Hawksbill.

---

## Notes

The desktop system uses **PostgreSQL** as its database backend for managing user accounts, system settings, and logs.

---

## Roadmap

- [x] Implement YOLOv8 for object detection.
- [x] Develop a PyQt5-based desktop GUI.
- [x] Integrate ROS 2 for modular communication.
- [ ] Extend object detection to include additional maritime objects (e.g., debris, rescue equipment, buoys, and vessels).
- [ ] Optimize YOLOv8 inference using TensorRT.
- [ ] Add cloud-based data analysis and remote monitoring.
- [ ] Deploy the system in real maritime environments.

---

## Contributing

We welcome contributions! Please submit a pull request or open an issue for any improvements or bug reports.

---

## License

This project is currently **not licensed**. Please contact the author if you intend to use it for commercial purposes.

---

## Contact

For any inquiries, please contact **Abir Chebbi** via GitHub or email.

---

🚢 **Sailor Vision AI - Enhancing Maritime Surveillance with AI and Computer Vision** 🌊