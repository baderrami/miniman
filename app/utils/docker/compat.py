"""
Compatibility layer for the old docker_utils.py functions.

This module provides backward compatibility with the old docker_utils.py functions.
It re-exports all the functions from the old docker_utils.py with the same signatures,
but implements them using the new class-based architecture.
"""

from typing import Dict, List, Tuple, Any, Optional
from app.utils.docker.base import DockerBase
from app.utils.docker.container import ContainerManager
from app.utils.docker.image import ImageManager
from app.utils.docker.volume import VolumeManager
from app.utils.docker.network import NetworkManager
from app.utils.docker.compose import ComposeManager, DOCKER_COMPOSE_DIR

# Initialize managers
_docker_base = DockerBase()
_container_manager = ContainerManager()
_image_manager = ImageManager()
_volume_manager = VolumeManager()
_network_manager = NetworkManager()
_compose_manager = ComposeManager()

# Re-export constants
DOCKER_COMPOSE_DIR = DOCKER_COMPOSE_DIR

# Base Docker functionality
def ensure_docker_installed() -> bool:
    """
    Ensure Docker and Docker Compose are installed.

    Returns:
        bool: True if Docker and Docker Compose are installed, False otherwise
    """
    return _docker_base.ensure_docker_installed()

def install_docker() -> Tuple[bool, str]:
    """
    Install Docker and Docker Compose.

    Returns:
        Tuple[bool, str]: Success status and output message
    """
    return _docker_base.install_docker()

# Docker Compose operations
def download_compose_file(url: str, name: str) -> Tuple[bool, str, Optional[str]]:
    """
    Download a Docker Compose file from a URL.

    Args:
        url (str): URL to download from
        name (str): Name for the configuration

    Returns:
        Tuple[bool, str, Optional[str]]: Success status, message, and local path if successful
    """
    return _compose_manager.download_compose_file(url, name)

def check_for_updates(config_path: str, source_url: str) -> Tuple[bool, bool]:
    """
    Check if updates are available for a Docker Compose configuration.

    Args:
        config_path (str): Path to local Docker Compose file
        source_url (str): URL to check for updates

    Returns:
        Tuple[bool, bool]: Success status and whether updates are available
    """
    return _compose_manager.check_for_updates(config_path, source_url)

def update_compose_file(config_path: str, source_url: str) -> Tuple[bool, str]:
    """
    Update a Docker Compose file from its source URL.

    Args:
        config_path (str): Path to local Docker Compose file
        source_url (str): URL to update from

    Returns:
        Tuple[bool, str]: Success status and message
    """
    return _compose_manager.update_compose_file(config_path, source_url)

def run_compose(config_path: str, operation_log=None) -> Tuple[bool, str]:
    """
    Run Docker Compose up.

    Args:
        config_path (str): Path to Docker Compose file
        operation_log (DockerOperationLog, optional): Operation log object to record logs

    Returns:
        Tuple[bool, str]: Success status and output
    """
    return _compose_manager.run_compose(config_path, operation_log)

def stop_compose(config_path: str, operation_log=None) -> Tuple[bool, str]:
    """
    Stop Docker Compose.

    Args:
        config_path (str): Path to Docker Compose file
        operation_log (DockerOperationLog, optional): Operation log object to record logs

    Returns:
        Tuple[bool, str]: Success status and output
    """
    return _compose_manager.stop_compose(config_path, operation_log)

def restart_compose(config_path: str, operation_log=None) -> Tuple[bool, str]:
    """
    Restart Docker Compose.

    Args:
        config_path (str): Path to Docker Compose file
        operation_log (DockerOperationLog, optional): Operation log object to record logs

    Returns:
        Tuple[bool, str]: Success status and output
    """
    return _compose_manager.restart_compose(config_path, operation_log)

def pull_images(config_path: str, operation_log=None) -> Tuple[bool, str]:
    """
    Pull images for a Docker Compose configuration.

    Args:
        config_path (str): Path to Docker Compose file
        operation_log (DockerOperationLog, optional): Operation log object to record logs

    Returns:
        Tuple[bool, str]: Success status and output
    """
    return _compose_manager.pull_images(config_path, operation_log)

def check_compose_status(config_path: str) -> str:
    """
    Check the status of a Docker Compose configuration.

    Args:
        config_path (str): Path to Docker Compose file

    Returns:
        str: Status of the configuration ('up', 'down', 'partial', 'error')
    """
    return _compose_manager.check_compose_status(config_path)

# Container operations
def get_container_logs(container_id: str, tail: int = 100) -> Tuple[bool, str]:
    """
    Get logs for a container.

    Args:
        container_id (str): Container ID or name
        tail (int): Number of lines to tail

    Returns:
        Tuple[bool, str]: Success status and logs
    """
    return _container_manager.get_container_logs(container_id, tail)

def get_containers(config_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Get list of running containers.

    Args:
        config_id (int, optional): Filter by configuration ID

    Returns:
        List[Dict[str, Any]]: List of container information
    """
    return _container_manager.get_containers(config_id)

def start_container(container_id: str) -> Tuple[bool, str]:
    """
    Start a container.

    Args:
        container_id (str): Container ID or name

    Returns:
        Tuple[bool, str]: Success status and output
    """
    return _container_manager.start_container(container_id)

def stop_container(container_id: str) -> Tuple[bool, str]:
    """
    Stop a container.

    Args:
        container_id (str): Container ID or name

    Returns:
        Tuple[bool, str]: Success status and output
    """
    return _container_manager.stop_container(container_id)

def restart_container(container_id: str) -> Tuple[bool, str]:
    """
    Restart a container.

    Args:
        container_id (str): Container ID or name

    Returns:
        Tuple[bool, str]: Success status and output
    """
    return _container_manager.restart_container(container_id)

def remove_container(container_id: str, force: bool = False) -> Tuple[bool, str]:
    """
    Remove a container.

    Args:
        container_id (str): Container ID or name
        force (bool): Force removal of running container

    Returns:
        Tuple[bool, str]: Success status and output
    """
    return _container_manager.remove_container(container_id, force)

def exec_container_command(container_id: str, command: str) -> Tuple[bool, str]:
    """
    Execute a command in a container.

    Args:
        container_id (str): Container ID or name
        command (str): Command to execute

    Returns:
        Tuple[bool, str]: Success status and output
    """
    return _container_manager.exec_container_command(container_id, command)

def get_container_stats(container_id: str) -> Tuple[bool, Dict[str, Any]]:
    """
    Get stats for a container.

    Args:
        container_id (str): Container ID or name

    Returns:
        Tuple[bool, Dict[str, Any]]: Success status and stats
    """
    return _container_manager.get_container_stats(container_id)

def inspect_container(container_id: str) -> Tuple[bool, Dict[str, Any]]:
    """
    Inspect a container.

    Args:
        container_id (str): Container ID or name

    Returns:
        Tuple[bool, Dict[str, Any]]: Success status and container details
    """
    return _container_manager.inspect_container(container_id)

# Image operations
def get_images() -> List[Dict[str, Any]]:
    """
    Get list of Docker images.

    Returns:
        List[Dict[str, Any]]: List of image information
    """
    return _image_manager.get_images()

def pull_image(image_name: str, operation_log=None) -> Tuple[bool, str]:
    """
    Pull a Docker image.

    Args:
        image_name (str): Image name (and tag)
        operation_log (DockerOperationLog, optional): Operation log object to record logs

    Returns:
        Tuple[bool, str]: Success status and output
    """
    return _image_manager.pull_image(image_name, operation_log)

def remove_image(image_id: str, force: bool = False) -> Tuple[bool, str]:
    """
    Remove a Docker image.

    Args:
        image_id (str): Image ID or name
        force (bool): Force removal of the image

    Returns:
        Tuple[bool, str]: Success status and output
    """
    return _image_manager.remove_image(image_id, force)

def build_image(dockerfile_path: str, tag: str) -> Tuple[bool, str]:
    """
    Build a Docker image.

    Args:
        dockerfile_path (str): Path to the directory containing the Dockerfile
        tag (str): Tag for the image

    Returns:
        Tuple[bool, str]: Success status and output
    """
    return _image_manager.build_image(dockerfile_path, tag)

def inspect_image(image_id: str) -> Tuple[bool, Dict[str, Any]]:
    """
    Inspect a Docker image.

    Args:
        image_id (str): Image ID or name

    Returns:
        Tuple[bool, Dict[str, Any]]: Success status and image details
    """
    return _image_manager.inspect_image(image_id)

# Volume operations
def get_volumes() -> List[Dict[str, Any]]:
    """
    Get list of Docker volumes.

    Returns:
        List[Dict[str, Any]]: List of volume information
    """
    return _volume_manager.get_volumes()

def create_volume(name: str, driver: str = 'local', labels: Dict[str, str] = None) -> Tuple[bool, str]:
    """
    Create a Docker volume.

    Args:
        name (str): Volume name
        driver (str): Volume driver
        labels (Dict[str, str]): Volume labels

    Returns:
        Tuple[bool, str]: Success status and output
    """
    return _volume_manager.create_volume(name, driver, labels)

def remove_volume(name: str, force: bool = False) -> Tuple[bool, str]:
    """
    Remove a Docker volume.

    Args:
        name (str): Volume name
        force (bool): Force removal of the volume

    Returns:
        Tuple[bool, str]: Success status and output
    """
    return _volume_manager.remove_volume(name, force)

def inspect_volume(name: str) -> Tuple[bool, Dict[str, Any]]:
    """
    Inspect a Docker volume.

    Args:
        name (str): Volume name

    Returns:
        Tuple[bool, Dict[str, Any]]: Success status and volume details
    """
    return _volume_manager.inspect_volume(name)

# Network operations
def get_networks() -> List[Dict[str, Any]]:
    """
    Get list of Docker networks.

    Returns:
        List[Dict[str, Any]]: List of network information
    """
    return _network_manager.get_networks()

def create_network(name: str, driver: str = 'bridge', subnet: str = None, gateway: str = None) -> Tuple[bool, str]:
    """
    Create a Docker network.

    Args:
        name (str): Network name
        driver (str): Network driver
        subnet (str): Subnet in CIDR format
        gateway (str): Gateway IP address

    Returns:
        Tuple[bool, str]: Success status and output
    """
    return _network_manager.create_network(name, driver, subnet, gateway)

def remove_network(name: str) -> Tuple[bool, str]:
    """
    Remove a Docker network.

    Args:
        name (str): Network name or ID

    Returns:
        Tuple[bool, str]: Success status and output
    """
    return _network_manager.remove_network(name)

def inspect_network(name: str) -> Tuple[bool, Dict[str, Any]]:
    """
    Inspect a Docker network.

    Args:
        name (str): Network name or ID

    Returns:
        Tuple[bool, Dict[str, Any]]: Success status and network details
    """
    return _network_manager.inspect_network(name)

def connect_container_to_network(container_id: str, network_id: str) -> Tuple[bool, str]:
    """
    Connect a container to a network.

    Args:
        container_id (str): Container ID or name
        network_id (str): Network ID or name

    Returns:
        Tuple[bool, str]: Success status and output
    """
    return _network_manager.connect_container_to_network(container_id, network_id)

def disconnect_container_from_network(container_id: str, network_id: str) -> Tuple[bool, str]:
    """
    Disconnect a container from a network.

    Args:
        container_id (str): Container ID or name
        network_id (str): Network ID or name

    Returns:
        Tuple[bool, str]: Success status and output
    """
    return _network_manager.disconnect_container_from_network(container_id, network_id)