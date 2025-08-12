# Camera Management System - Sailor Vision AI

## Overview

The Sailor Vision AI system implements a sophisticated camera management architecture that enables automatic camera detection, approval workflows, real-time video processing with AI-based object detection, and seamless integration with a maritime surveillance GUI. The system is built on ROS 2 (Robot Operating System) and provides a complete end-to-end pipeline from camera discovery to live feed visualization with YOLO-based maritime object detection.

## System Architecture

### Core Components

```
┌─────────────────────────────────────────────────────────────────┐
│                    Camera Management Architecture                │
├─────────────────────────────────────────────────────────────────┤
│                                                                │
│  ROS 2 Layer                     GUI Layer                     │
│  ┌─────────────────┐            ┌─────────────────┐             │
│  │  camera_manager │◄──────────►│  CameraDetector │             │
│  │  yolov8_detector│            │  LiveFeedScreen │             │
│  │  gazebo_sim     │            │  Dashboard      │             │
│  └─────────────────┘            │  ROSWatchdog    │             │
│           │                     └─────────────────┘             │
│           ▼                             │                       │
│  ┌─────────────────┐            ┌─────────────────┐             │
│  │   ROS Topics    │◄──────────►│   Services      │             │
│  │  /camera/list   │   Monitor  │  CameraService  │             │
│  │  /yolo/*/image  │◄──────────►│  AlertService   │             │
│  │  /yolo/alerts   │   Health   │  Watchdog       │             │
│  └─────────────────┘            └─────────────────┘             │
│                                          │                     │
│                                          ▼                     │
│                              ┌─────────────────┐               │
│                              │    Database     │               │
│                              │   PostgreSQL    │               │
│                              │  SQLite/SQLAlch │               │
│                              └─────────────────┘               │
└─────────────────────────────────────────────────────────────────┘
```

## 1. ROS 2 Camera Management Module

### 1.1 Camera Manager Package (`camera_manager`)

**Location**: `ros2_ws/src/camera_manager/`

**Files Involved**:
- `camera_manager/camera_manager.py` - Main camera detection node
- `camera_manager/camera_publisher.py` - Video stream publisher
- `package.xml` - Package metadata and dependencies
- `setup.py` - Package configuration and entry points
- `launch/surveillance.launch.py` - Launch file for complete system

#### Camera Manager Node (`camera_manager.py`)

**Role**: Automated hardware camera detection and device listing

**Key Responsibilities**:
- Scans `/dev/video*` devices every 2 seconds using `glob.glob('/dev/video*')`
- Publishes detected camera devices to `/camera/list` ROS topic
- Responds to immediate scan requests via `/camera/scan_request` topic
- Provides real-time camera availability status to the system

**Core Functionality**:
```python
class CameraManager(Node):
    def __init__(self):
        super().__init__('camera_manager')
        self.pub = self.create_publisher(String, '/camera/list', 10)
        self.timer = self.create_timer(2.0, self.publish_camera_list)
        self.scan_request_sub = self.create_subscription(
            String, '/camera/scan_request', self.handle_scan_request, 10
        )

    def publish_camera_list(self):
        devices = sorted(glob.glob('/dev/video*'))
        msg = String()
        msg.data = json.dumps({'cameras': devices})
        self.pub.publish(msg)
```

**ROS Topics**:
- **Publisher**: `/camera/list` (std_msgs/String) - JSON list of available cameras
- **Subscriber**: `/camera/scan_request` (std_msgs/String) - Force immediate scan

#### Camera Publisher Node (`camera_publisher.py`)

**Role**: Raw video stream publisher for detected cameras

**Key Responsibilities**:
- Subscribes to `/camera/list` to track available cameras
- Creates individual video capture instances for each detected device
- Publishes raw video streams to `/camera/{device}/image_raw` topics
- Manages camera lifecycle (connection/disconnection)

**Stream Publication Logic**:
```python
class CameraPublisher(Node):
    def cb_camera_list(self, msg):
        data = json.loads(msg.data)
        devices = data.get('cameras', [])
        for dev in devices:
            if dev not in self._caps:
                cap = cv2.VideoCapture(dev)
                if cap.isOpened():
                    topic = f'/camera/{dev.split("/")[-1]}/image_raw'
                    pub = self.create_publisher(Image, topic, 10)
                    self._publisher_map[dev] = pub
                    self.create_timer(1/30.0, lambda d=dev: self.publish_frame(d))
```

**ROS Topics**:
- **Subscriber**: `/camera/list` (std_msgs/String)
- **Publishers**: `/camera/video{X}/image_raw` (sensor_msgs/Image) - 30 FPS raw streams

### 1.2 YOLO Detection Package (`yolov8_detector`)

**Location**: `ros2_ws/src/yolov8_detector/`

**Files Involved**:
- `yolov8_detector/yolo_node.py` - AI detection processor
- `package.xml` - Package dependencies
- `setup.py` - Entry points configuration

#### YOLO Node (`yolo_node.py`)

**Role**: Real-time AI-powered maritime object detection

**Key Responsibilities**:
- Dynamically subscribes to all `/camera/*/image_raw` topics
- Processes video frames using YOLOv8 model (`/model/yolov8_best.pt`)
- Publishes annotated detection results to `/yolo/{device}/image_raw`
- Generates structured detection alerts on `/yolo/alerts`

**Detection Pipeline**:
```python
class YoloNode(Node):
    def update_camera_subscriptions(self):
        topics = self.get_topic_names_and_types()
        for topic, types in topics:
            if topic.startswith('/camera/') and topic.endswith('/image_raw'):
                if topic not in self._camera_subs:
                    sub = self.create_subscription(
                        Image, topic, lambda msg, t=topic: self.image_callback(msg, t), 10
                    )

    def process_and_publish(self, frame, topic):
        results = self.model.predict(frame, verbose=False)
        annotated = results[0].plot()
        video_name = topic.split('/')[2]  # Extract video device
        yolo_topic = f'/yolo/{video_name}/image_raw'
        self._yolo_publishers[yolo_topic].publish(annotated_msg)
        self.process_detections(results[0], frame, topic)
```

**AI Detection Features**:
- Maritime-specific object classes (swimmers, life jackets, vessels)
- Configurable confidence threshold (default: 0.5)
- Real-time bounding box annotations
- Structured JSON alert format with timestamps and coordinates

**ROS Topics**:
- **Subscribers**: `/camera/*/image_raw` (sensor_msgs/Image) - Dynamic subscription
- **Publishers**: 
  - `/yolo/{device}/image_raw` (sensor_msgs/Image) - Annotated streams
  - `/yolo/alerts` (std_msgs/String) - JSON detection alerts

### 1.3 Gazebo Simulation Package (`gazebo_sim`)

**Location**: `ros2_ws/src/gazebo_sim/`

**Files Involved**:
- `urdf/robot_camera.urdf` - Camera robot model
- `worlds/empty_world.world` - Simulation environment
- `launch/sim_and_yolo.launch.py` - Simulation launcher

**Role**: Provides simulated camera feeds for development and testing

**Key Features**:
- Virtual camera sensor publishing to `/camera/image_raw`
- Integration with YOLO detection pipeline
- Maritime environment simulation

## 2. GUI Camera Management Layer

### 2.1 Camera Detection Service (`camera_detector.py`)

**Location**: `sailor_vision_gui/src/services/camera_detector.py`

**Role**: Bridge between ROS camera detection and GUI approval workflow

**Key Responsibilities**:
- Subscribes to ROS `/camera/list` topic
- Filters already-approved cameras from database
- Adds new cameras to pending approval queue
- Emits Qt signals for GUI notification system

**Detection Logic**:
```python
class CameraDetector(QObject):
    new_camera_detected = pyqtSignal(str, str, str)
    
    def handle_camera_list(self, msg):
        data = json.loads(msg.data)
        devices = data.get('cameras', [])
        for dev in devices:
            if not self.is_device_approved(dev) and not already_detected:
                self.add_camera_to_pending_list(dev)
                self.new_camera_detected.emit(camera_id, camera_name, device_path)
```

### 2.2 Pending Camera Manager (`pending_camera_manager.py`)

**Location**: `sailor_vision_gui/src/services/pending_camera_manager.py`

**Role**: Manages the approval workflow for newly detected cameras

**Key Features**:
- JSON-based pending camera storage (`shared/pending_cameras.json`)
- Status tracking (pending, approved, rejected)
- Admin approval/rejection workflow
- Automatic cleanup of old rejected cameras

**Data Structure**:
```python
@dataclass
class PendingCamera:
    camera_id: str
    name: str
    ip_address: str  # Device path (e.g., /dev/video0)
    status: str = "pending"
    detected_at: datetime = field(default_factory=datetime.now)
```

**Workflow States**:
- **Pending**: Awaiting admin approval in Settings screen
- **Approved**: Transferred to database, removed from JSON
- **Rejected**: Marked for cleanup, hidden from pending list

### 2.3 Camera Service (`camera_service.py`)

**Location**: `sailor_vision_gui/src/services/camera_service.py`

**Role**: Database operations for camera management

**Key Operations**:
- CRUD operations for Camera entities
- Status management (active/inactive)
- Integration with SQLAlchemy ORM
- Session management for database transactions

### 2.4 Live Feed Screen (`live_feed.py`)

**Location**: `sailor_vision_gui/src/components/live_feed.py`

**Role**: Real-time video feed display and camera control interface

**Key Components**:

#### CameraFeedWidget
- Displays individual camera feeds with status indicators
- Supports feed expansion for detailed viewing
- Real-time status updates (active/inactive)
- Click-to-expand functionality

#### ROSImageBridge Integration
- Subscribes to `/yolo/*/image_raw` topics for processed feeds
- Dynamic topic discovery and subscription management
- Frame rate control (30 FPS target)
- Error handling and connection management

**Topic Mapping Logic**:
```python
def handle_new_yolo_topic(self, topic):
    # Extract device number from /yolo/video1/image_raw
    topic_parts = topic.split('/')
    if len(topic_parts) >= 3:
        device_name = topic_parts[2]  # e.g., "video1"
        device_num = device_name.replace('video', '')
        
    # Map to database camera by device path
    for cam in self.cameras:
        if cam.get('ip_address') == f'/dev/video{device_num}':
            self.topic_to_camera_id[topic] = cam["id"]
```

### 2.5 Dashboard Screen (`dashboard.py`)

**Location**: `sailor_vision_gui/src/components/dashboard.py`

**Role**: System overview with camera status and live preview thumbnails

**Features**:
- Compact camera widgets with live previews
- Status indicators (green/red for active/inactive)
- Quick camera overview for system monitoring
- Integration with camera feed updates

### 2.6 ROS Watchdog System (`ros_watchdog.py`)

**Location**: `sailor_vision_gui/shared/ros_watchdog.py`

**Role**: Critical system monitoring and health management component that ensures reliable communication between ROS nodes and the GUI, while maintaining accurate camera status tracking.

#### Architecture Overview

The ROS Watchdog system implements a sophisticated monitoring architecture with two main components:

```
┌─────────────────────────────────────────────────────────────────┐
│                    ROS Watchdog Architecture                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                │
│  Main Thread (Qt GUI)           Worker Thread (Background)     │
│  ┌─────────────────┐            ┌─────────────────┐             │
│  │   ROSWatchdog   │◄──────────►│ROSWatchdogWorker│             │
│  │   (QObject)     │   Signals  │   (QObject)     │             │
│  └─────────────────┘            └─────────────────┘             │
│           │                             │                       │
│           ▼                             ▼                       │
│  ┌─────────────────┐            ┌─────────────────┐             │
│  │  GUI Updates    │            │  ROS Monitoring │             │
│  │  Status Changes │            │  Topic Activity │             │
│  │  Camera States  │            │  Health Checks  │             │
│  └─────────────────┘            └─────────────────┘             │
│                                          │                     │
│                                          ▼                     │
│                              ┌─────────────────┐               │
│                              │   Database      │               │
│                              │   Updates       │               │
│                              │ Camera Status   │               │
│                              └─────────────────┘               │
└─────────────────────────────────────────────────────────────────┘
```

#### Core Components

##### ROSWatchdog (Main Controller)
**Primary Responsibilities**:
- Initializes and manages the watchdog worker thread
- Provides thread-safe interface for registering topic activity
- Emits Qt signals for GUI integration
- Handles system cleanup and graceful shutdown

```python
class ROSWatchdog(QObject):
    ros_status_changed = pyqtSignal(bool)        # ROS connection status
    cameras_status_changed = pyqtSignal(list)    # Camera status changes
    
    def start_watchdog(self):
        self.worker_thread = QThread()
        self.worker = ROSWatchdogWorker(self.ros_node)
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.run)
```

##### ROSWatchdogWorker (Background Monitor)
**Core Monitoring Functions**:
- **ROS Health Monitoring**: Continuously checks ROS node availability and topic health
- **Topic Activity Tracking**: Monitors video stream activity across all camera topics
- **Camera Status Management**: Updates database with real-time camera states
- **Failure Detection**: Implements circuit breaker pattern for connection failures

#### Monitoring Mechanisms

##### 1. ROS System Health Monitoring

The watchdog implements a robust health checking mechanism:

```python
def check_ros_health(self):
    try:
        # Verify ROS context is alive
        if not rclpy.ok():
            self.ros_health_failures += 1
        else:
            # Test ROS API responsiveness
            node_names = self.node.get_node_names_and_namespaces()
            topics = self.node.get_topic_names_and_types()
            
            # Check for camera-related topics
            has_camera_topics = any(
                ('/camera/' in topic and '/image_raw' in topic) or 
                ('/yolo/' in topic and '/image_raw' in topic)
                for topic, _ in topics
            )
            
            # Reset failure count on successful check
            self.ros_health_failures = 0 if has_camera_topics else self.ros_health_failures + 1
            
    except Exception as e:
        self.ros_health_failures += 1
```

**Health Check Parameters**:
- **Check Interval**: 2 seconds for responsive detection
- **Failure Threshold**: 3 consecutive failures before marking ROS as disconnected
- **Recovery Detection**: Automatic reconnection detection when ROS becomes available

##### 2. Camera Topic Activity Monitoring

**Dynamic Topic Discovery**:
```python
def initialize_camera_mappings(self):
    # Map database cameras to ROS topics
    for camera in cameras:
        if camera.ip_address and "/dev/video" in camera.ip_address:
            device_name = camera.ip_address.split('/')[-1]  # Extract 'video2'
            
            # Create topic mappings
            camera_topic = f"/camera/{device_name}/image_raw"
            yolo_topic = f"/yolo/{device_name}/image_raw"
            
            # Initialize monitoring structures
            self.topic_to_camera_id[camera_topic] = camera.id
            self.topic_to_camera_id[yolo_topic] = camera.id
            self.camera_topics[camera_topic] = 0  # No activity initially
            self.camera_topics[yolo_topic] = 0
```

**Activity Registration**:
```python
def register_topic_activity(self, topic):
    current_time = time.time()
    if topic in self.camera_topics:
        self.camera_topics[topic] = current_time
        
        # Reset ROS health on successful data reception
        if self.ros_health_failures > 0:
            self.ros_health_failures = 0
            if not self.ros_connected:
                self.ros_connected = True
                self.ros_status_changed.emit(True)
```

##### 3. Camera Status Management

**Status Determination Logic**:
```python
def update_camera_status(self):
    current_time = time.time()
    changed_cameras = []
    
    for camera_id in self.camera_active_status.keys():
        # Find all topics for this camera
        camera_topics = [topic for topic, cam_id in self.topic_to_camera_id.items() 
                        if cam_id == camera_id]
        
        # Check for recent activity (within timeout period)
        has_recent_activity = False
        for topic in camera_topics:
            topic_last_activity = self.camera_topics.get(topic, 0)
            if topic_last_activity > 0:
                time_since_activity = current_time - topic_last_activity
                if time_since_activity < self.topic_timeout:  # 5 seconds
                    has_recent_activity = True
                    break
        
        # Update status if changed
        should_be_active = has_recent_activity
        if should_be_active != self.camera_active_status.get(camera_id, False):
            self.camera_active_status[camera_id] = should_be_active
            changed_cameras.append(camera_id)
```

#### Workflow and State Management

##### Connection State Machine

```
ROS States:
┌─────────────┐    Health Check OK     ┌─────────────┐
│ Disconnected│───────────────────────►│  Connected  │
│             │                        │             │
└─────────────┘◄───────────────────────└─────────────┘
                3+ Health Check Failures

Camera States:
┌─────────────┐    Topic Activity      ┌─────────────┐
│   Inactive  │───────────────────────►│   Active    │
│             │                        │             │
└─────────────┘◄───────────────────────└─────────────┘
                5+ Seconds No Activity
```

##### Failure Scenarios and Recovery

**ROS Disconnection Handling**:
```python
def update_all_cameras_inactive(self):
    """Mark all cameras as inactive when ROS disconnects"""
    changed_cameras = []
    for camera_id in self.camera_active_status.keys():
        if self.camera_active_status.get(camera_id, False):
            self.camera_active_status[camera_id] = False
            changed_cameras.append(camera_id)
    
    # Update database atomically
    session = create_new_session()
    camera_service = CameraService(session)
    camera_service.set_cameras_active(changed_cameras, False)
    close_session(session)
    
    # Notify GUI
    self.cameras_status_changed.emit(changed_cameras)
```

**Graceful Recovery**:
- Automatic detection of ROS system recovery
- Incremental camera reactivation based on actual feed availability
- Database consistency maintenance during state transitions

#### Integration Points

##### GUI Integration
The watchdog integrates seamlessly with the GUI through Qt's signal-slot mechanism:

```python
# Main application connection
def setup_ros_watchdog(self):
    self.ros_watchdog = ROSWatchdog(self.ros_node)
    self.ros_watchdog.ros_status_changed.connect(self.on_ros_status_changed)
    self.ros_watchdog.cameras_status_changed.connect(self.on_cameras_status_changed)

# Component-level integration
def on_ros_image_received(self, topic, pixmap):
    # Register activity for watchdog monitoring
    if self.ros_watchdog:
        self.ros_watchdog.register_topic_activity(topic)
```

##### Database Synchronization
- **Batch Updates**: Efficient database operations for multiple camera status changes
- **Transaction Management**: Ensures data consistency during status updates
- **Session Handling**: Proper database session lifecycle management

#### Performance Characteristics

**Resource Efficiency**:
- **CPU Usage**: Minimal overhead with 2-second check intervals
- **Memory Footprint**: Lightweight mapping structures for topic tracking
- **Thread Safety**: Proper thread isolation between monitoring and GUI operations

**Responsiveness Metrics**:
- **Detection Speed**: ROS disconnection detected within 6 seconds (3 × 2-second checks)
- **Recovery Time**: Camera reactivation within 5 seconds of stream availability
- **GUI Updates**: Real-time status propagation via Qt signals

#### Error Handling and Resilience

**Exception Management**:
```python
def run(self):
    try:
        while True:
            current_time = time.time()
            if current_time - last_check_time >= self.check_interval:
                self.check_ros_health()
                self.update_camera_status()
                last_check_time = current_time
            time.sleep(0.1)  # Prevent excessive CPU usage
            
    except Exception as e:
        logger.error(f"Error in ROS watchdog loop: {e}")
        # Fail-safe: mark ROS as disconnected
        if self.ros_connected:
            self.ros_connected = False
            self.ros_status_changed.emit(False)
            self.update_all_cameras_inactive()
```

**Failure Recovery Strategies**:
- **Circuit Breaker Pattern**: Prevents excessive reconnection attempts
- **Graceful Degradation**: System remains functional with reduced capabilities
- **Automatic Cleanup**: Proper resource cleanup on critical failures

#### Configuration Parameters

| Parameter | Default Value | Purpose |
|-----------|---------------|---------|
| `check_interval` | 2 seconds | Frequency of health checks |
| `topic_timeout` | 5 seconds | Camera inactivity threshold |
| `max_failures` | 3 attempts | ROS disconnection threshold |
| `ros_health_failures` | 0 (reset) | Consecutive failure counter |

#### Use Cases and Benefits

**Operational Scenarios**:
1. **Normal Operation**: Continuous monitoring ensures accurate camera status
2. **ROS Node Restart**: Automatic detection and graceful reconnection
3. **Camera Disconnection**: Immediate status updates and GUI notification
4. **Network Issues**: Robust handling of intermittent connectivity
5. **System Shutdown**: Clean resource cleanup and thread termination

**System Benefits**:
- **Reliability**: Ensures accurate system state representation
- **User Experience**: Real-time status updates prevent confusion
- **Maintenance**: Facilitates system debugging and monitoring
- **Scalability**: Supports multiple cameras with minimal overhead

## 3. Database Schema

### 3.1 Camera Model (`models.py`)

**Location**: `sailor_vision_gui/models.py`

```python
class Camera(Base):
    __tablename__ = "cameras"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    ip_address = Column(String(50))  # Device path (/dev/videoX)
    port = Column(Integer)
    location = Column(String(100))
    rtsp_url = Column(String(256))
    is_active = Column(Boolean, default=True)
    is_recording = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    last_online = Column(DateTime)
    camera_type = Column(String(50))
```

**Key Fields**:
- `ip_address`: Stores device path (e.g., `/dev/video0`) for ROS topic mapping
- `is_active`: Operational status for GUI display logic
- `name`: Human-readable identifier for admin interface

### 3.2 Related Models

- **User**: Admin/Operator roles for camera approval workflow
- **Alert**: Detection alerts linked to specific cameras
- **Recording**: Video recording metadata and file paths

## 4. Camera Management Workflow

### 4.1 Detection and Approval Process

```
1. Physical Camera Connection
   ↓
2. ROS camera_manager detects /dev/videoX
   ↓
3. Device published to /camera/list topic
   ↓
4. CameraDetector receives ROS message
   ↓
5. New camera added to pending_cameras.json
   ↓
6. Admin notification in Settings screen
   ↓
7. Admin approval creates database Camera entity
   ↓
8. Camera appears in Live Feed and Dashboard
   ↓
9. ROS publishes video stream to /camera/videoX/image_raw
   ↓
10. YOLO processes stream → /yolo/videoX/image_raw
   ↓
11. GUI displays processed feed with detections
```

### 4.2 Data Flow Architecture

```
Hardware Layer:    [USB Camera] → [/dev/video0]
                        ↓
ROS Detection:     [camera_manager] → [/camera/list]
                        ↓
ROS Streaming:     [camera_publisher] → [/camera/video0/image_raw]
                        ↓
AI Processing:     [yolo_node] → [/yolo/video0/image_raw] + [/yolo/alerts]
                        ↓                           ↑
GUI Bridge:        [ROSImageBridge] → [Qt Signals] │
                        ↓                           │
Monitoring:        [ROSWatchdog] ← [Topic Activity]┘
                        ↓
Database:          [Camera Service] → [PostgreSQL/SQLite]
                        ↓
User Interface:    [Live Feed] + [Dashboard] + [Settings]
```

### 4.3 State Management

#### Camera States
- **Detected**: Found by ROS, pending approval
- **Pending**: In JSON queue, awaiting admin action
- **Approved**: In database, visible in GUI
- **Active**: Streaming and processing video
- **Inactive**: Configured but not currently streaming

#### State Transitions
- **Detection → Pending**: Automatic via ROS topic
- **Pending → Approved**: Admin action in Settings
- **Approved → Active**: Video stream availability
- **Active ↔ Inactive**: Stream connectivity status

## 5. ROS Topic Architecture

### 5.1 Core Topics

| Topic | Type | Publisher | Subscriber | Purpose |
|-------|------|-----------|------------|---------|
| `/camera/list` | std_msgs/String | camera_manager | camera_publisher, CameraDetector | Device list JSON |
| `/camera/scan_request` | std_msgs/String | GUI | camera_manager | Force immediate scan |
| `/camera/video{X}/image_raw` | sensor_msgs/Image | camera_publisher | yolo_node | Raw video streams |
| `/yolo/video{X}/image_raw` | sensor_msgs/Image | yolo_node | ROSImageBridge | Processed streams |
| `/yolo/alerts` | std_msgs/String | yolo_node | AlertService | Detection alerts |

### 5.2 Dynamic Topic Management

The system employs dynamic topic discovery and subscription:

```python
# YOLO Node - Dynamic camera subscription
def update_camera_subscriptions(self):
    topics = self.get_topic_names_and_types()
    for topic, types in topics:
        if topic.startswith('/camera/') and topic.endswith('/image_raw'):
            if topic not in self._camera_subs:
                self.create_subscription(Image, topic, self.image_callback, 10)

# GUI Bridge - Dynamic YOLO topic subscription
def _check_yolo_topics(self, on_new_topic_cb):
    topics = self.ros_node.get_topic_names_and_types()
    for topic, types in topics:
        if topic.startswith('/yolo/') and topic.endswith('/image_raw'):
            if topic not in self._subs:
                sub = self.ros_node.create_subscription(Image, topic, self._on_image, 10)
```

## 6. Launch Configuration

### 6.1 Surveillance Launch File

**Location**: `ros2_ws/src/camera_manager/launch/surveillance.launch.py`

**Launched Nodes**:
- `camera_manager_node`: Device detection and listing
- `camera_publisher_node`: Video stream publishing
- `yolo_node`: AI detection processing

**Usage**:
```bash
cd ros2_ws
source install/setup.bash
ros2 launch camera_manager surveillance.launch.py
```

### 6.2 GUI Application Entry Point

**Location**: `sailor_vision_gui/app.py`

**Integration Features**:
- ROS 2 node initialization within Qt application
- Timer-based ROS spin integration with Qt event loop
- Service initialization (CameraDetector, PendingCameraManager)
- ROSImageBridge setup for video stream handling

## 7. Key Design Patterns

### 7.1 Service-Oriented Architecture
- Modular services (CameraService, AlertService, CameraDetector)
- Clear separation between ROS layer and GUI layer
- Database abstraction through service layer

### 7.2 Event-Driven Communication
- Qt signals for GUI updates
- ROS topics for inter-node communication
- JSON-based configuration and state persistence

### 7.3 Dynamic Resource Management
- Automatic topic subscription/unsubscription
- Camera lifecycle management
- Graceful handling of connection/disconnection

## 8. Error Handling and Resilience

### 8.1 Connection Management
- Automatic retry mechanisms for failed camera connections
- Graceful degradation when cameras become unavailable
- Error count tracking and circuit breaker patterns

### 8.2 Data Consistency
- Database transaction management
- Atomic operations for camera approval workflow
- Conflict resolution for duplicate camera detection

### 8.3 Resource Cleanup
- Automatic cleanup of old pending cameras
- Subscription management for disconnected topics
- Memory management for video frame processing

## 9. Configuration and Deployment

### 9.1 ROS 2 Package Dependencies
- **camera_manager**: `rclpy`, `std_msgs`, `sensor_msgs`, `cv_bridge`
- **yolov8_detector**: `rclpy`, `sensor_msgs`, `ultralytics`, `opencv-python`
- **gazebo_sim**: `gazebo_ros`, `robot_state_publisher`

### 9.2 GUI Application Dependencies
- **Qt Framework**: PyQt5 for user interface
- **Database**: SQLAlchemy with PostgreSQL/SQLite support
- **Computer Vision**: OpenCV for image processing
- **ROS Integration**: rclpy for ROS 2 communication

### 9.3 System Requirements
- **Operating System**: Linux (tested on Ubuntu 22.04)
- **ROS 2 Distribution**: Humble Hawksbill
- **Python Version**: 3.10+
- **Hardware**: USB cameras or IP cameras with V4L2 support

## 10. Best Practices and Recommendations

### 10.1 Development Guidelines
- Use the provided launch files for consistent system startup
- Follow the approval workflow for new camera integration
- Implement proper error handling for camera disconnections
- Monitor ROS topic health using the built-in watchdog system

### 10.2 Maintenance Procedures
- Regular cleanup of pending camera queue
- Database backup before system updates
- Performance monitoring of video processing pipeline
- Log analysis for debugging camera issues

### 10.3 Scalability Considerations
- The system supports multiple simultaneous cameras
- YOLO processing can be distributed across multiple nodes
- Database can be scaled with proper indexing
- GUI performance scales with proper frame rate limiting

## Conclusion

The Sailor Vision AI camera management system provides a robust, scalable solution for maritime surveillance applications. The architecture successfully combines ROS 2's real-time capabilities with a user-friendly Qt-based interface, enabling efficient camera discovery, approval workflows, and AI-powered object detection. The modular design ensures maintainability while the event-driven architecture provides responsive user experience and reliable operation in maritime environments.
