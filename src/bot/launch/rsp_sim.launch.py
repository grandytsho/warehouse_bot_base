import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from launch.actions import RegisterEventHandler, TimerAction
from launch.event_handlers import OnProcessStart
import xacro

def generate_launch_description():
    pkg_name = 'bot'
    
    # Process Xacro
    xacro_file = os.path.join(get_package_share_directory(pkg_name), 'description', 'warehouse.urdf.xacro')
    robot_description_config = xacro.process_file(xacro_file).toxml()
    
    # 1. Robot State Publisher
    node_robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[{'robot_description': robot_description_config, 'use_sim_time': True}]
    )

    # 2. Gazebo Ignition
    world_path = os.path.join(get_package_share_directory(pkg_name), 'worlds', 'basic_world.sdf')
 
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([os.path.join(
            get_package_share_directory('ros_gz_sim'), 'launch', 'gz_sim.launch.py')]),
        launch_arguments={'gz_args': f'-r {world_path}'}.items(),
    )

    # 3. Spawn Robot
    spawn_entity = Node(
        package='ros_gz_sim',
        executable='create',
        output='screen',
        arguments=[
            '-name', 'my_bot', 
            '-topic', 'robot_description',
            '-x', '0.0',
            '-y', '0.0',
            '-z', '0.1',
        ]
    )

    # 4. Bridge
    bridge_config = os.path.join(get_package_share_directory(pkg_name), 'config', 'bridge_config.yaml')
    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        parameters=[{
            'config_file': bridge_config,
            'use_sim_time': True,
        }],
        # The remapping below is only needed if publish_odom_tf is false and you
        # rely on the fallback /model/my_bot/tf topic. Since publish_odom_tf=true
        # in the plugin, /tf is already published directly. Keeping it here is
        # harmless but redundant.
        # remappings=[
        #     ('/model/my_bot/tf', '/tf'),
        #     ('/model/my_bot/odometry', '/odom'),   # add this
        # ],
        output='screen'
    )
    # 5. RViz (Forced to use sim time)
    rviz = Node(
        package='rviz2',
        executable='rviz2',
        parameters=[{'use_sim_time': True}],
        output='screen'
    )

    # Replace your spawner nodes with:
    joint_state_broadcaster_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_state_broadcaster", "--controller-manager-timeout", "60"],
    )

    mecanum_drive_controller_spawner = RegisterEventHandler(
        event_handler=OnProcessStart(
            target_action=joint_state_broadcaster_spawner,
            on_start=[
                TimerAction(
                    period=2.0,
                    actions=[Node(
                        package="controller_manager",
                        executable="spawner",
                        arguments=["mecanum_drive_controller",
                                "--controller-manager-timeout", "60"],
                    )]
                )
            ]
        )
    )

    return LaunchDescription([
        node_robot_state_publisher,
        gazebo,
        spawn_entity,
        bridge,
        rviz,
        joint_state_broadcaster_spawner,
        mecanum_drive_controller_spawner,
    ])