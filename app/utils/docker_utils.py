import subprocess
import os
import requests
import yaml
import json
import tempfile
import shutil
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime
import re
from dateutil import parser as date_parser

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

def run_compose(config_path: str, operation_log=None) -> Tuple[bool, str]:
    """
    Run Docker Compose up

    Args:
        config_path (str): Path to Docker Compose file
        operation_log (DockerOperationLog, optional): Operation log object to record logs

    Returns:
        Tuple[bool, str]: Success status and output
    """
    try:
        # Get the directory containing the compose file
        config_dir = os.path.dirname(config_path)

        # Log the start of the operation
        if operation_log:
            operation_log.add_log_line(f"Starting docker compose up for {config_path}")

        # Run docker-compose up -d with real-time output
        process = subprocess.Popen(
            ['docker', 'compose', '-f', config_path, 'up', '-d'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=config_dir,
            bufsize=1,
            universal_newlines=True
        )

        output = []
        for line in process.stdout:
            line = line.strip()
            output.append(line)
            if operation_log:
                operation_log.add_log_line(line)

        # Wait for the process to complete
        return_code = process.wait()

        # Check if the command was successful
        if return_code == 0:
            if operation_log:
                operation_log.add_log_line("Docker Compose started successfully")
                operation_log.complete(True)
            return True, "\n".join(output)
        else:
            if operation_log:
                operation_log.add_log_line(f"Docker Compose failed with return code {return_code}")
                operation_log.complete(False)
            return False, "\n".join(output)
    except Exception as e:
        error_message = f"Error running Docker Compose: {str(e)}"
        if operation_log:
            operation_log.add_log_line(error_message)
            operation_log.complete(False)
        return False, error_message

def stop_compose(config_path: str, operation_log=None) -> Tuple[bool, str]:
    """
    Stop Docker Compose

    Args:
        config_path (str): Path to Docker Compose file
        operation_log (DockerOperationLog, optional): Operation log object to record logs

    Returns:
        Tuple[bool, str]: Success status and output
    """
    try:
        # Get the directory containing the compose file
        config_dir = os.path.dirname(config_path)

        # Log the start of the operation
        if operation_log:
            operation_log.add_log_line(f"Starting docker compose down for {config_path}")

        # Run docker-compose down with real-time output
        process = subprocess.Popen(
            ['docker', 'compose', '-f', config_path, 'down'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=config_dir,
            bufsize=1,
            universal_newlines=True
        )

        output = []
        for line in process.stdout:
            line = line.strip()
            output.append(line)
            if operation_log:
                operation_log.add_log_line(line)

        # Wait for the process to complete
        return_code = process.wait()

        # Check if the command was successful
        if return_code == 0:
            if operation_log:
                operation_log.add_log_line("Docker Compose stopped successfully")
                operation_log.complete(True)
            return True, "\n".join(output)
        else:
            if operation_log:
                operation_log.add_log_line(f"Docker Compose failed with return code {return_code}")
                operation_log.complete(False)
            return False, "\n".join(output)
    except Exception as e:
        error_message = f"Error stopping Docker Compose: {str(e)}"
        if operation_log:
            operation_log.add_log_line(error_message)
            operation_log.complete(False)
        return False, error_message

def restart_compose(config_path: str, operation_log=None) -> Tuple[bool, str]:
    """
    Restart Docker Compose

    Args:
        config_path (str): Path to Docker Compose file
        operation_log (DockerOperationLog, optional): Operation log object to record logs

    Returns:
        Tuple[bool, str]: Success status and output
    """
    try:
        # Get the directory containing the compose file
        config_dir = os.path.dirname(config_path)

        # Log the start of the operation
        if operation_log:
            operation_log.add_log_line(f"Starting docker compose restart for {config_path}")

        # Run docker-compose restart with real-time output
        process = subprocess.Popen(
            ['docker', 'compose', '-f', config_path, 'restart'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=config_dir,
            bufsize=1,
            universal_newlines=True
        )

        output = []
        for line in process.stdout:
            line = line.strip()
            output.append(line)
            if operation_log:
                operation_log.add_log_line(line)

        # Wait for the process to complete
        return_code = process.wait()

        # Check if the command was successful
        if return_code == 0:
            if operation_log:
                operation_log.add_log_line("Docker Compose restarted successfully")
                operation_log.complete(True)
            return True, "\n".join(output)
        else:
            if operation_log:
                operation_log.add_log_line(f"Docker Compose failed with return code {return_code}")
                operation_log.complete(False)
            return False, "\n".join(output)
    except Exception as e:
        error_message = f"Error restarting Docker Compose: {str(e)}"
        if operation_log:
            operation_log.add_log_line(error_message)
            operation_log.complete(False)
        return False, error_message

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

def pull_images(config_path: str, operation_log=None) -> Tuple[bool, str]:
    """
    Pull images for a Docker Compose configuration

    Args:
        config_path (str): Path to Docker Compose file
        operation_log (DockerOperationLog, optional): Operation log object to record logs

    Returns:
        Tuple[bool, str]: Success status and output
    """
    try:
        # Get the directory containing the compose file
        config_dir = os.path.dirname(config_path)

        # Log the start of the operation
        if operation_log:
            operation_log.add_log_line(f"Starting docker compose pull for {config_path}")

        # Run docker-compose pull with real-time output
        process = subprocess.Popen(
            ['docker', 'compose', '-f', config_path, 'pull'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=config_dir,
            bufsize=1,
            universal_newlines=True
        )

        output = []
        for line in process.stdout:
            line = line.strip()
            output.append(line)
            if operation_log:
                operation_log.add_log_line(line)

        # Wait for the process to complete
        return_code = process.wait()

        # Check if the command was successful
        if return_code == 0:
            if operation_log:
                operation_log.add_log_line("Docker Compose pull completed successfully")
                operation_log.complete(True)
            return True, "\n".join(output)
        else:
            if operation_log:
                operation_log.add_log_line(f"Docker Compose pull failed with return code {return_code}")
                operation_log.complete(False)
            return False, "\n".join(output)
    except Exception as e:
        error_message = f"Error pulling images: {str(e)}"
        if operation_log:
            operation_log.add_log_line(error_message)
            operation_log.complete(False)
        return False, error_message

# Container operations

def start_container(container_id: str) -> Tuple[bool, str]:
    """
    Start a container

    Args:
        container_id (str): Container ID or name

    Returns:
        Tuple[bool, str]: Success status and output
    """
    try:
        result = subprocess.run(
            ['docker', 'start', container_id],
            capture_output=True,
            text=True,
            check=True
        )

        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, f"Error: {e.stderr}"
    except Exception as e:
        return False, f"Error starting container: {str(e)}"

def stop_container(container_id: str) -> Tuple[bool, str]:
    """
    Stop a container

    Args:
        container_id (str): Container ID or name

    Returns:
        Tuple[bool, str]: Success status and output
    """
    try:
        result = subprocess.run(
            ['docker', 'stop', container_id],
            capture_output=True,
            text=True,
            check=True
        )

        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, f"Error: {e.stderr}"
    except Exception as e:
        return False, f"Error stopping container: {str(e)}"

def restart_container(container_id: str) -> Tuple[bool, str]:
    """
    Restart a container

    Args:
        container_id (str): Container ID or name

    Returns:
        Tuple[bool, str]: Success status and output
    """
    try:
        result = subprocess.run(
            ['docker', 'restart', container_id],
            capture_output=True,
            text=True,
            check=True
        )

        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, f"Error: {e.stderr}"
    except Exception as e:
        return False, f"Error restarting container: {str(e)}"

def remove_container(container_id: str, force: bool = False) -> Tuple[bool, str]:
    """
    Remove a container

    Args:
        container_id (str): Container ID or name
        force (bool): Force removal of running container

    Returns:
        Tuple[bool, str]: Success status and output
    """
    try:
        cmd = ['docker', 'rm', container_id]
        if force:
            cmd.insert(2, '-f')

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )

        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, f"Error: {e.stderr}"
    except Exception as e:
        return False, f"Error removing container: {str(e)}"

def exec_container_command(container_id: str, command: str) -> Tuple[bool, str]:
    """
    Execute a command in a container

    Args:
        container_id (str): Container ID or name
        command (str): Command to execute

    Returns:
        Tuple[bool, str]: Success status and output
    """
    try:
        # Split the command into arguments
        cmd_args = command.split()

        # Build the docker exec command
        docker_cmd = ['docker', 'exec', container_id] + cmd_args

        result = subprocess.run(
            docker_cmd,
            capture_output=True,
            text=True,
            check=True
        )

        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, f"Error: {e.stderr}"
    except Exception as e:
        return False, f"Error executing command in container: {str(e)}"

def get_container_stats(container_id: str) -> Tuple[bool, Dict[str, Any]]:
    """
    Get stats for a container

    Args:
        container_id (str): Container ID or name

    Returns:
        Tuple[bool, Dict[str, Any]]: Success status and stats
    """
    try:
        result = subprocess.run(
            ['docker', 'stats', container_id, '--no-stream', '--format', '{{json .}}'],
            capture_output=True,
            text=True,
            check=True
        )

        if result.stdout.strip():
            stats = json.loads(result.stdout.strip())
            return True, stats
        else:
            return False, {}
    except subprocess.CalledProcessError as e:
        return False, {}
    except Exception as e:
        print(f"Error getting container stats: {str(e)}")
        return False, {}

def inspect_container(container_id: str) -> Tuple[bool, Dict[str, Any]]:
    """
    Inspect a container

    Args:
        container_id (str): Container ID or name

    Returns:
        Tuple[bool, Dict[str, Any]]: Success status and container details
    """
    try:
        result = subprocess.run(
            ['docker', 'inspect', container_id],
            capture_output=True,
            text=True,
            check=True
        )

        if result.stdout.strip():
            details = json.loads(result.stdout.strip())
            if details and isinstance(details, list):
                return True, details[0]
            return True, {}
        else:
            return False, {}
    except subprocess.CalledProcessError as e:
        return False, {}
    except Exception as e:
        print(f"Error inspecting container: {str(e)}")
        return False, {}

# Image operations

def pull_image(image_name: str, operation_log=None) -> Tuple[bool, str]:
    """
    Pull a Docker image

    Args:
        image_name (str): Image name (and tag)
        operation_log (DockerOperationLog, optional): Operation log object to record logs

    Returns:
        Tuple[bool, str]: Success status and output
    """
    try:
        # Log the start of the operation
        if operation_log:
            operation_log.add_log_line(f"Starting docker pull for {image_name}")

        # Run docker pull with real-time output
        process = subprocess.Popen(
            ['docker', 'pull', image_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )

        output = []
        for line in process.stdout:
            line = line.strip()
            output.append(line)
            if operation_log:
                operation_log.add_log_line(line)

        # Wait for the process to complete
        return_code = process.wait()

        # Check if the command was successful
        if return_code == 0:
            if operation_log:
                operation_log.add_log_line(f"Image {image_name} pulled successfully")
                operation_log.complete(True)
            return True, "\n".join(output)
        else:
            if operation_log:
                operation_log.add_log_line(f"Image pull failed with return code {return_code}")
                operation_log.complete(False)
            return False, "\n".join(output)
    except Exception as e:
        error_message = f"Error pulling image: {str(e)}"
        if operation_log:
            operation_log.add_log_line(error_message)
            operation_log.complete(False)
        return False, error_message

def remove_image(image_id: str, force: bool = False) -> Tuple[bool, str]:
    """
    Remove a Docker image

    Args:
        image_id (str): Image ID or name
        force (bool): Force removal of the image

    Returns:
        Tuple[bool, str]: Success status and output
    """
    try:
        cmd = ['docker', 'rmi', image_id]
        if force:
            cmd.insert(2, '-f')

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )

        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, f"Error: {e.stderr}"
    except Exception as e:
        return False, f"Error removing image: {str(e)}"

def build_image(dockerfile_path: str, tag: str) -> Tuple[bool, str]:
    """
    Build a Docker image

    Args:
        dockerfile_path (str): Path to the directory containing the Dockerfile
        tag (str): Tag for the image

    Returns:
        Tuple[bool, str]: Success status and output
    """
    try:
        result = subprocess.run(
            ['docker', 'build', '-t', tag, dockerfile_path],
            capture_output=True,
            text=True,
            check=True
        )

        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, f"Error: {e.stderr}"
    except Exception as e:
        return False, f"Error building image: {str(e)}"

def inspect_image(image_id: str) -> Tuple[bool, Dict[str, Any]]:
    """
    Inspect a Docker image

    Args:
        image_id (str): Image ID or name

    Returns:
        Tuple[bool, Dict[str, Any]]: Success status and image details
    """
    try:
        result = subprocess.run(
            ['docker', 'inspect', image_id],
            capture_output=True,
            text=True,
            check=True
        )

        if result.stdout.strip():
            details = json.loads(result.stdout.strip())
            if details and isinstance(details, list):
                return True, details[0]
            return True, {}
        else:
            return False, {}
    except subprocess.CalledProcessError as e:
        return False, {}
    except Exception as e:
        print(f"Error inspecting image: {str(e)}")
        return False, {}

def check_compose_status(config_path: str) -> str:
    """
    Check the status of a Docker Compose configuration

    Args:
        config_path (str): Path to Docker Compose file

    Returns:
        str: Status of the configuration ('up', 'down', 'partial', 'error')
    """
    try:
        # Get the directory containing the compose file
        config_dir = os.path.dirname(config_path)

        # Run docker-compose ps to get the status of the services
        result = subprocess.run(
            ['docker', 'compose', '-f', config_path, 'ps', '--format', 'json'],
            capture_output=True,
            text=True,
            cwd=config_dir
        )

        if result.returncode != 0:
            return 'error'

        # Parse the JSON output
        try:
            if not result.stdout.strip():
                return 'down'  # No services running

            services = []
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    services.append(json.loads(line))

            if not services:
                return 'down'

            # Check the status of each service
            up_count = 0
            for service in services:
                if 'State' in service and service['State'] == 'running':
                    up_count += 1

            if up_count == 0:
                return 'down'
            elif up_count == len(services):
                return 'up'
            else:
                return 'partial'
        except json.JSONDecodeError:
            # Fallback to text parsing if JSON parsing fails
            if 'running' in result.stdout:
                return 'up'
            elif not result.stdout.strip() or 'exited' in result.stdout:
                return 'down'
            else:
                return 'partial'
    except Exception as e:
        print(f"Error checking compose status: {str(e)}")
        return 'error'

# Volume operations

def get_volumes() -> List[Dict[str, Any]]:
    """
    Get list of Docker volumes

    Returns:
        List[Dict[str, Any]]: List of volume information
    """
    try:
        result = subprocess.run(
            ['docker', 'volume', 'ls', '--format', '{{json .}}'],
            capture_output=True,
            text=True,
            check=True
        )

        volumes = []
        for line in result.stdout.strip().split('\n'):
            if line:
                volume = json.loads(line)
                # Parse the creation time if available
                created = None
                if 'CreatedAt' in volume:
                    try:
                        created = date_parser.parse(volume.get('CreatedAt', ''))
                    except:
                        pass

                volumes.append({
                    'name': volume.get('Name', ''),
                    'driver': volume.get('Driver', ''),
                    'mountpoint': volume.get('Mountpoint', ''),
                    'created': created
                })

        return volumes
    except Exception as e:
        print(f"Error getting volumes: {str(e)}")
        return []

def create_volume(name: str, driver: str = 'local', labels: Dict[str, str] = None) -> Tuple[bool, str]:
    """
    Create a Docker volume

    Args:
        name (str): Volume name
        driver (str): Volume driver
        labels (Dict[str, str]): Volume labels

    Returns:
        Tuple[bool, str]: Success status and output
    """
    try:
        cmd = ['docker', 'volume', 'create', '--driver', driver]

        # Add labels if provided
        if labels:
            for key, value in labels.items():
                cmd.extend(['--label', f'{key}={value}'])

        # Add name
        cmd.append(name)

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )

        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, f"Error: {e.stderr}"
    except Exception as e:
        return False, f"Error creating volume: {str(e)}"

def remove_volume(name: str, force: bool = False) -> Tuple[bool, str]:
    """
    Remove a Docker volume

    Args:
        name (str): Volume name
        force (bool): Force removal of the volume

    Returns:
        Tuple[bool, str]: Success status and output
    """
    try:
        cmd = ['docker', 'volume', 'rm', name]
        if force:
            cmd.insert(3, '-f')

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )

        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, f"Error: {e.stderr}"
    except Exception as e:
        return False, f"Error removing volume: {str(e)}"

def inspect_volume(name: str) -> Tuple[bool, Dict[str, Any]]:
    """
    Inspect a Docker volume

    Args:
        name (str): Volume name

    Returns:
        Tuple[bool, Dict[str, Any]]: Success status and volume details
    """
    try:
        result = subprocess.run(
            ['docker', 'volume', 'inspect', name],
            capture_output=True,
            text=True,
            check=True
        )

        if result.stdout.strip():
            details = json.loads(result.stdout.strip())
            if details and isinstance(details, list):
                return True, details[0]
            return True, {}
        else:
            return False, {}
    except subprocess.CalledProcessError as e:
        return False, {}
    except Exception as e:
        print(f"Error inspecting volume: {str(e)}")
        return False, {}

# Network operations

def get_networks() -> List[Dict[str, Any]]:
    """
    Get list of Docker networks

    Returns:
        List[Dict[str, Any]]: List of network information
    """
    try:
        result = subprocess.run(
            ['docker', 'network', 'ls', '--format', '{{json .}}'],
            capture_output=True,
            text=True,
            check=True
        )

        networks = []
        for line in result.stdout.strip().split('\n'):
            if line:
                network = json.loads(line)
                # Parse the creation time if available
                created = None
                if 'CreatedAt' in network:
                    try:
                        created = date_parser.parse(network.get('CreatedAt', ''))
                    except:
                        pass

                networks.append({
                    'id': network.get('ID', ''),
                    'name': network.get('Name', ''),
                    'driver': network.get('Driver', ''),
                    'scope': network.get('Scope', ''),
                    'created': created
                })

        return networks
    except Exception as e:
        print(f"Error getting networks: {str(e)}")
        return []

def create_network(name: str, driver: str = 'bridge', subnet: str = None, gateway: str = None) -> Tuple[bool, str]:
    """
    Create a Docker network

    Args:
        name (str): Network name
        driver (str): Network driver
        subnet (str): Subnet in CIDR format
        gateway (str): Gateway IP address

    Returns:
        Tuple[bool, str]: Success status and output
    """
    try:
        cmd = ['docker', 'network', 'create', '--driver', driver]

        # Add subnet if provided
        if subnet:
            cmd.extend(['--subnet', subnet])

        # Add gateway if provided
        if gateway:
            cmd.extend(['--gateway', gateway])

        # Add name
        cmd.append(name)

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )

        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, f"Error: {e.stderr}"
    except Exception as e:
        return False, f"Error creating network: {str(e)}"

def remove_network(name: str) -> Tuple[bool, str]:
    """
    Remove a Docker network

    Args:
        name (str): Network name or ID

    Returns:
        Tuple[bool, str]: Success status and output
    """
    try:
        result = subprocess.run(
            ['docker', 'network', 'rm', name],
            capture_output=True,
            text=True,
            check=True
        )

        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, f"Error: {e.stderr}"
    except Exception as e:
        return False, f"Error removing network: {str(e)}"

def inspect_network(name: str) -> Tuple[bool, Dict[str, Any]]:
    """
    Inspect a Docker network

    Args:
        name (str): Network name or ID

    Returns:
        Tuple[bool, Dict[str, Any]]: Success status and network details
    """
    try:
        result = subprocess.run(
            ['docker', 'network', 'inspect', name],
            capture_output=True,
            text=True,
            check=True
        )

        if result.stdout.strip():
            details = json.loads(result.stdout.strip())
            if details and isinstance(details, list):
                return True, details[0]
            return True, {}
        else:
            return False, {}
    except subprocess.CalledProcessError as e:
        return False, {}
    except Exception as e:
        print(f"Error inspecting network: {str(e)}")
        return False, {}

def connect_container_to_network(container_id: str, network_id: str) -> Tuple[bool, str]:
    """
    Connect a container to a network

    Args:
        container_id (str): Container ID or name
        network_id (str): Network ID or name

    Returns:
        Tuple[bool, str]: Success status and output
    """
    try:
        result = subprocess.run(
            ['docker', 'network', 'connect', network_id, container_id],
            capture_output=True,
            text=True,
            check=True
        )

        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, f"Error: {e.stderr}"
    except Exception as e:
        return False, f"Error connecting container to network: {str(e)}"

def disconnect_container_from_network(container_id: str, network_id: str) -> Tuple[bool, str]:
    """
    Disconnect a container from a network

    Args:
        container_id (str): Container ID or name
        network_id (str): Network ID or name

    Returns:
        Tuple[bool, str]: Success status and output
    """
    try:
        result = subprocess.run(
            ['docker', 'network', 'disconnect', network_id, container_id],
            capture_output=True,
            text=True,
            check=True
        )

        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, f"Error: {e.stderr}"
    except Exception as e:
        return False, f"Error disconnecting container from network: {str(e)}"
