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
from app.utils.docker.compose import ComposeManager
# Logger import removed as per requirements
# from app.utils.docker.logger import DockerLogger, WebSocketLogger

# For backward compatibility, re-export all the functions from the old docker_utils.py
# This allows existing code to continue working without changes
from app.utils.docker.compat import *
