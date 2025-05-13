import subprocess
import os
import requests
import yaml
import json
import tempfile
import shutil
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime

# Base directory for storing Docker Compose files
DOCKER_COMPOSE_DIR = '/opt/miniman/docker-compose'

def ensure_docker_installed() -> bool:
    """
    Ensure Docker and Docker Compose are installed
    
    Returns:
        bool: True if Docker and Docker Compose are installed, False otherwise
    """
    try:
        # Check Docker
        docker_version = subprocess.run(
            ['docker', '--version'],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Check Docker Compose
        compose_version = subprocess.run(
            ['docker', 'compose', 'version'],
            capture_output=True,
            text=True,
            check=True
        )
        
        return True
    except Exception as e:
        print(f"Docker or Docker Compose not installed: {str(e)}")
        return False

def install_docker() -> Tuple[bool, str]:
    """
    Install Docker and Docker Compose
    
    Returns:
        Tuple[bool, str]: Success status and output message
    """
    try:
        # Update package index
        subprocess.run(['apt-get', 'update'], check=True)
        
        # Install prerequisites
        subprocess.run([
            'apt-get', 'install', '-y',
            'apt-transport-https', 'ca-certificates',
            'curl', 'gnupg', 'lsb-release'
        ], check=True)
        
        # Add Docker's official GPG key
        subprocess.run([
            'curl', '-fsSL', 'https://download.docker.com/linux/ubuntu/gpg',
            '-o', '/tmp/docker.gpg'
        ], check=True)
        subprocess.run([
            'gpg', '--dearmor', '-o', '/usr/share/keyrings/docker-archive-keyring.gpg',
            '/tmp/docker.gpg'
        ], check=True)
        
        # Set up the stable repository
        subprocess.run([
            'echo', 
            'deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] '
            'https://download.docker.com/linux/ubuntu '
            '$(lsb_release -cs) stable',
            '>', '/etc/apt/sources.list.d/docker.list'
        ], check=True)
        
        # Install Docker Engine
        subprocess.run(['apt-get', 'update'], check=True)
        subprocess.run(['apt-get', 'install', '-y', 'docker-ce', 'docker-ce-cli', 'containerd.io'], check=True)
        
        # Enable and start Docker service
        subprocess.run(['systemctl', 'enable', 'docker'], check=True)
        subprocess.run(['systemctl', 'start', 'docker'], check=True)
        
        return True, "Docker installed successfully"
    except Exception as e:
        return False, f"Error installing Docker: {str(e)}"

def download_compose_file(url: str, name: str) -> Tuple[bool, str, Optional[str]]:
    """
    Download a Docker Compose file from a URL
    
    Args:
        url (str): URL to download from
        name (str): Name for the configuration
        
    Returns:
        Tuple[bool, str, Optional[str]]: Success status, message, and local path if successful
    """
    try:
        # Create directory if it doesn't exist
        os.makedirs(DOCKER_COMPOSE_DIR, exist_ok=True)
        
        # Create directory for this configuration
        config_dir = os.path.join(DOCKER_COMPOSE_DIR, name)
        os.makedirs(config_dir, exist_ok=True)
        
        # Download the file
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # Save the file
        compose_path = os.path.join(config_dir, 'docker-compose.yml')
        with open(compose_path, 'w') as f:
            f.write(response.text)
        
        # Validate the file
        with open(compose_path, 'r') as f:
            yaml.safe_load(f)
        
        return True, "Docker Compose file downloaded successfully", compose_path
    except requests.exceptions.RequestException as e:
        return False, f"Error downloading Docker Compose file: {str(e)}", None
    except yaml.YAMLError as e:
        return False, f"Invalid Docker Compose file: {str(e)}", None
    except Exception as e:
        return False, f"Error processing Docker Compose file: {str(e)}", None

def check_for_updates(config_path: str, source_url: str) -> Tuple[bool, bool]:
    """
    Check if updates are available for a Docker Compose configuration
    
    Args:
        config_path (str): Path to local Docker Compose file
        source_url (str): URL to check for updates
        
    Returns:
        Tuple[bool, bool]: Success status and whether updates are available
    """
    try:
        # Download the remote file to a temporary location
        response = requests.get(source_url, timeout=30)
        response.raise_for_status()
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            temp_file.write(response.text)
            temp_path = temp_file.name
        
        # Compare the files
        with open(config_path, 'r') as f1, open(temp_path, 'r') as f2:
            local_content = f1.read()
            remote_content = f2.read()
        
        # Clean up temporary file
        os.unlink(temp_path)
        
        # Return whether the files are different
        return True, local_content != remote_content
    except Exception as e:
        print(f"Error checking for updates: {str(e)}")
        return False, False

def update_compose_file(config_path: str, source_url: str) -> Tuple[bool, str]:
    """
    Update a Docker Compose file from its source URL
    
    Args:
        config_path (str): Path to local Docker Compose file
        source_url (str): URL to update from
        
    Returns:
        Tuple[bool, str]: Success status and message
    """
    try:
        # Download the file
        response = requests.get(source_url, timeout=30)
        response.raise_for_status()
        
        # Validate the file
        try:
            yaml.safe_load(response.text)
        except yaml.YAMLError as e:
            return False, f"Invalid Docker Compose file: {str(e)}"
        
        # Backup the existing file
        backup_path = f"{config_path}.bak"
        shutil.copy2(config_path, backup_path)
        
        # Save the new file
        with open(config_path, 'w') as f:
            f.write(response.text)
        
        return True, "Docker Compose file updated successfully"
    except Exception as e:
        # Restore backup if it exists
        if os.path.exists(backup_path):
            shutil.copy2(backup_path, config_path)
        
        return False, f"Error updating Docker Compose file: {str(e)}"

def run_compose(config_path: str) -> Tuple[bool, str]:
    """
    Run Docker Compose up
    
    Args:
        config_path (str): Path to Docker Compose file
        
    Returns:
        Tuple[bool, str]: Success status and output
    """
    try:
        # Get the directory containing the compose file
        config_dir = os.path.dirname(config_path)
        
        # Run docker-compose up -d
        result = subprocess.run(
            ['docker', 'compose', '-f', config_path, 'up', '-d'],
            capture_output=True,
            text=True,
            cwd=config_dir,
            check=True
        )
        
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, f"Error: {e.stderr}"
    except Exception as e:
        return False, f"Error running Docker Compose: {str(e)}"

def stop_compose(config_path: str) -> Tuple[bool, str]:
    """
    Stop Docker Compose
    
    Args:
        config_path (str): Path to Docker Compose file
        
    Returns:
        Tuple[bool, str]: Success status and output
    """
    try:
        # Get the directory containing the compose file
        config_dir = os.path.dirname(config_path)
        
        # Run docker-compose down
        result = subprocess.run(
            ['docker', 'compose', '-f', config_path, 'down'],
            capture_output=True,
            text=True,
            cwd=config_dir,
            check=True
        )
        
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, f"Error: {e.stderr}"
    except Exception as e:
        return False, f"Error stopping Docker Compose: {str(e)}"

def restart_compose(config_path: str) -> Tuple[bool, str]:
    """
    Restart Docker Compose
    
    Args:
        config_path (str): Path to Docker Compose file
        
    Returns:
        Tuple[bool, str]: Success status and output
    """
    try:
        # Get the directory containing the compose file
        config_dir = os.path.dirname(config_path)
        
        # Run docker-compose restart
        result = subprocess.run(
            ['docker', 'compose', '-f', config_path, 'restart'],
            capture_output=True,
            text=True,
            cwd=config_dir,
            check=True
        )
        
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, f"Error: {e.stderr}"
    except Exception as e:
        return False, f"Error restarting Docker Compose: {str(e)}"

def get_container_logs(container_id: str, tail: int = 100) -> Tuple[bool, str]:
    """
    Get logs for a container
    
    Args:
        container_id (str): Container ID or name
        tail (int): Number of lines to tail
        
    Returns:
        Tuple[bool, str]: Success status and logs
    """
    try:
        result = subprocess.run(
            ['docker', 'logs', '--tail', str(tail), container_id],
            capture_output=True,
            text=True,
            check=True
        )
        
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, f"Error: {e.stderr}"
    except Exception as e:
        return False, f"Error getting container logs: {str(e)}"

def get_containers(config_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Get list of running containers
    
    Args:
        config_id (int, optional): Filter by configuration ID
        
    Returns:
        List[Dict[str, Any]]: List of container information
    """
    try:
        # Get all containers
        result = subprocess.run(
            ['docker', 'ps', '-a', '--format', '{{json .}}'],
            capture_output=True,
            text=True,
            check=True
        )
        
        containers = []
        for line in result.stdout.strip().split('\n'):
            if line:
                container = json.loads(line)
                containers.append({
                    'id': container.get('ID', ''),
                    'name': container.get('Names', ''),
                    'image': container.get('Image', ''),
                    'status': container.get('Status', ''),
                    'created': container.get('CreatedAt', ''),
                    'ports': container.get('Ports', '')
                })
        
        return containers
    except Exception as e:
        print(f"Error getting containers: {str(e)}")
        return []

def get_images() -> List[Dict[str, Any]]:
    """
    Get list of Docker images
    
    Returns:
        List[Dict[str, Any]]: List of image information
    """
    try:
        result = subprocess.run(
            ['docker', 'images', '--format', '{{json .}}'],
            capture_output=True,
            text=True,
            check=True
        )
        
        images = []
        for line in result.stdout.strip().split('\n'):
            if line:
                image = json.loads(line)
                images.append({
                    'repository': image.get('Repository', ''),
                    'tag': image.get('Tag', ''),
                    'id': image.get('ID', ''),
                    'created': image.get('CreatedAt', ''),
                    'size': image.get('Size', '')
                })
        
        return images
    except Exception as e:
        print(f"Error getting images: {str(e)}")
        return []

def pull_images(config_path: str) -> Tuple[bool, str]:
    """
    Pull images for a Docker Compose configuration
    
    Args:
        config_path (str): Path to Docker Compose file
        
    Returns:
        Tuple[bool, str]: Success status and output
    """
    try:
        # Get the directory containing the compose file
        config_dir = os.path.dirname(config_path)
        
        # Run docker-compose pull
        result = subprocess.run(
            ['docker', 'compose', '-f', config_path, 'pull'],
            capture_output=True,
            text=True,
            cwd=config_dir,
            check=True
        )
        
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, f"Error: {e.stderr}"
    except Exception as e:
        return False, f"Error pulling images: {str(e)}"