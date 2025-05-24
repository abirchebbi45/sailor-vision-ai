from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='camera_manager',
            executable='camera_manager',
            name='camera_manager_node',
            output='screen'
        ),
        Node(
            package='camera_manager',
            executable='camera_publisher',
            name='camera_publisher_node',
            output='screen'
        ),
        Node(
            package='yolov8_detector',
            executable='yolo_node',
            name='yolo_node',
            output='screen'
        )
    ])
