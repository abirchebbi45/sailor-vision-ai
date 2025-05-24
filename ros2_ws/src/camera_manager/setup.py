from setuptools import find_packages, setup

package_name = 'camera_manager'

setup(
    name=package_name,
    version='0.0.1',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', ['launch/surveillance.launch.py']),

    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='abirc240',
    maintainer_email='abirc240@gmail.com',
    description='Détecte les périphériques /dev/video* et publie leur liste sur /camera/list',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'camera_manager   = camera_manager.camera_manager:main',
            'camera_publisher = camera_manager.camera_publisher:main',
        ],
    },
)
