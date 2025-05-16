"""
Docker utilities package.

This package provides classes and functions for interacting with Docker and Docker Compose.
It replaces the monolithic docker_utils.py with a more modular and maintainable structure.
"""

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

# Export constants
DOCKER_COMPOSE_DIR = DOCKER_COMPOSE_DIR

# Base Docker functionality
ensure_docker_installed = _docker_base.ensure_docker_installed
install_docker = _docker_base.install_docker

# Docker Compose operations
download_compose_file = _compose_manager.download_compose_file
check_for_updates = _compose_manager.check_for_updates
update_compose_file = _compose_manager.update_compose_file
run_compose = _compose_manager.run_compose
stop_compose = _compose_manager.stop_compose
restart_compose = _compose_manager.restart_compose
pull_images = _compose_manager.pull_images
check_compose_status = _compose_manager.check_compose_status

# Container operations
get_container_logs = _container_manager.get_container_logs
get_containers = _container_manager.get_containers
start_container = _container_manager.start_container
stop_container = _container_manager.stop_container
restart_container = _container_manager.restart_container
remove_container = _container_manager.remove_container
exec_container_command = _container_manager.exec_container_command
get_container_stats = _container_manager.get_container_stats
inspect_container = _container_manager.inspect_container

# Image operations
get_images = _image_manager.get_images
pull_image = _image_manager.pull_image
remove_image = _image_manager.remove_image
build_image = _image_manager.build_image
inspect_image = _image_manager.inspect_image

# Volume operations
get_volumes = _volume_manager.get_volumes
create_volume = _volume_manager.create_volume
remove_volume = _volume_manager.remove_volume
inspect_volume = _volume_manager.inspect_volume

# Network operations
get_networks = _network_manager.get_networks
create_network = _network_manager.create_network
remove_network = _network_manager.remove_network
inspect_network = _network_manager.inspect_network
connect_container_to_network = _network_manager.connect_container_to_network
disconnect_container_from_network = _network_manager.disconnect_container_from_network
