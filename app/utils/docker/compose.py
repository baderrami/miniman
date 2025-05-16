"""
Docker Compose operations.

This module provides the ComposeManager class for managing Docker Compose operations.
"""

import os
import json
import yaml
import shutil
import requests
import tempfile
from typing import Tuple, Optional
from app.utils.docker.base import DockerBase

# Base directory for storing Docker Compose files
import platform
import os.path

# Use platform-specific directory paths
if platform.system() == 'Darwin':  # macOS
    # Use user's home directory on macOS to avoid permission issues
    DOCKER_COMPOSE_DIR = os.path.join(os.path.expanduser('~'), '.miniman', 'docker-compose')
else:  # Linux or other systems
    # Try to use /opt/miniman if it's writable, otherwise fall back to home directory
    opt_dir = '/opt/miniman/docker-compose'
    try:
        # Check if we can write to /opt/miniman
        if not os.path.exists('/opt/miniman'):
            os.makedirs('/opt/miniman', exist_ok=True)
        # If we get here, we have permission to write to /opt/miniman
        DOCKER_COMPOSE_DIR = opt_dir
    except (IOError, PermissionError):
        # Fall back to user's home directory
        DOCKER_COMPOSE_DIR = os.path.join(os.path.expanduser('~'), '.miniman', 'docker-compose')


class ComposeManager(DockerBase):
    """Class for managing Docker Compose operations."""

    def __init__(self):
        """Initialize the Docker Compose manager."""
        super().__init__()
        os.makedirs(DOCKER_COMPOSE_DIR, exist_ok=True)

    def download_compose_file(self, url: str, name: str) -> Tuple[bool, str, Optional[str]]:
        """
        Download a Docker Compose file from a URL.

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

    def check_for_updates(self, config_path: str, source_url: str) -> Tuple[bool, bool]:
        """
        Check if updates are available for a Docker Compose configuration.

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

    def update_compose_file(self, config_path: str, source_url: str) -> Tuple[bool, str]:
        """
        Update a Docker Compose file from its source URL.

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
            if 'backup_path' in locals() and os.path.exists(backup_path):
                shutil.copy2(backup_path, config_path)

            return False, f"Error updating Docker Compose file: {str(e)}"

    def run_compose(self, config_path: str, logger=None) -> Tuple[bool, str]:
        """
        Run Docker Compose up.

        Args:
            config_path (str): Path to Docker Compose file
            logger: Deprecated parameter, kept for backward compatibility

        Returns:
            Tuple[bool, str]: Success status and output
        """
        # Get the directory containing the compose file
        config_dir = os.path.dirname(config_path)

        return self.run_command_with_streaming(
            ['docker', 'compose', '-f', config_path, 'up', '-d'],
            logger=None,
            cwd=config_dir
        )

    def stop_compose(self, config_path: str, logger=None) -> Tuple[bool, str]:
        """
        Stop Docker Compose.

        Args:
            config_path (str): Path to Docker Compose file
            logger: Deprecated parameter, kept for backward compatibility

        Returns:
            Tuple[bool, str]: Success status and output
        """
        # Get the directory containing the compose file
        config_dir = os.path.dirname(config_path)

        return self.run_command_with_streaming(
            ['docker', 'compose', '-f', config_path, 'down'],
            logger=None,
            cwd=config_dir
        )

    def restart_compose(self, config_path: str, logger=None) -> Tuple[bool, str]:
        """
        Restart Docker Compose.

        Args:
            config_path (str): Path to Docker Compose file
            logger: Deprecated parameter, kept for backward compatibility

        Returns:
            Tuple[bool, str]: Success status and output
        """
        # Get the directory containing the compose file
        config_dir = os.path.dirname(config_path)

        return self.run_command_with_streaming(
            ['docker', 'compose', '-f', config_path, 'restart'],
            logger=None,
            cwd=config_dir
        )

    def pull_images(self, config_path: str, logger=None) -> Tuple[bool, str]:
        """
        Pull images for a Docker Compose configuration.

        Args:
            config_path (str): Path to Docker Compose file
            logger: Deprecated parameter, kept for backward compatibility

        Returns:
            Tuple[bool, str]: Success status and output
        """
        # Get the directory containing the compose file
        config_dir = os.path.dirname(config_path)

        return self.run_command_with_streaming(
            ['docker', 'compose', '-f', config_path, 'pull'],
            logger=None,
            cwd=config_dir
        )

    def check_compose_status(self, config_path: str) -> str:
        """
        Check the status of a Docker Compose configuration.

        Args:
            config_path (str): Path to Docker Compose file

        Returns:
            str: Status of the configuration ('up', 'down', 'partial', 'error')
        """
        try:
            # Get the directory containing the compose file
            config_dir = os.path.dirname(config_path)

            # Run docker-compose ps to get the status of the services
            success, output = self.run_command(
                ['docker', 'compose', '-f', config_path, 'ps', '--format', 'json'],
                capture_output=True,
                check=False,
                cwd=config_dir
            )

            if not success:
                return 'error'

            # Parse the JSON output
            try:
                if not output.strip():
                    return 'down'  # No services running

                services = []
                for line in output.strip().split('\n'):
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
                if 'running' in output:
                    return 'up'
                elif not output.strip() or 'exited' in output:
                    return 'down'
                else:
                    return 'partial'
        except Exception as e:
            print(f"Error checking compose status: {str(e)}")
            return 'error'
