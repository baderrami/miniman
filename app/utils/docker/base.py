"""
Base Docker functionality.

This module provides the base class for Docker operations.
"""

import subprocess
import json
from typing import Dict, List, Tuple, Any, Optional


class DockerBase:
    """Base class for Docker operations."""

    def __init__(self):
        """Initialize the Docker base class."""
        self.ensure_docker_installed()

    def ensure_docker_installed(self) -> bool:
        """
        Ensure Docker and Docker Compose are installed.

        Returns:
            bool: True if Docker and Docker Compose are installed, False otherwise
        """
        try:
            # Check Docker
            subprocess.run(
                ['docker', '--version'],
                capture_output=True,
                text=True,
                check=True
            )

            # Check Docker Compose
            subprocess.run(
                ['docker', 'compose', 'version'],
                capture_output=True,
                text=True,
                check=True
            )

            return True
        except Exception as e:
            print(f"Docker or Docker Compose not installed: {str(e)}")
            return False

    def install_docker(self) -> Tuple[bool, str]:
        """
        Install Docker and Docker Compose.

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

    def run_command(self, cmd: List[str], capture_output: bool = True, 
                    check: bool = False, cwd: Optional[str] = None) -> Tuple[bool, str]:
        """
        Run a Docker command.

        Args:
            cmd (List[str]): Command to run
            capture_output (bool): Whether to capture output
            check (bool): Whether to check return code
            cwd (Optional[str]): Working directory

        Returns:
            Tuple[bool, str]: Success status and output
        """
        try:
            result = subprocess.run(
                cmd,
                capture_output=capture_output,
                text=True,
                check=check,
                cwd=cwd
            )

            if capture_output:
                return result.returncode == 0, result.stdout
            return True, ""
        except subprocess.CalledProcessError as e:
            return False, f"Error: {e.stderr}"
        except Exception as e:
            return False, f"Error running command: {str(e)}"

    def run_command_with_streaming(self, cmd: List[str], logger=None, cwd: Optional[str] = None) -> Tuple[bool, str]:
        """
        Run a Docker command with real-time output streaming.

        Args:
            cmd (List[str]): Command to run
            logger: Logger object to record logs
            cwd (Optional[str]): Working directory

        Returns:
            Tuple[bool, str]: Success status and output
        """
        try:
            # Log the start of the operation
            if logger:
                logger.add_log_line(f"Starting command: {' '.join(cmd)}")

            # Run command with real-time output
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=cwd,
                bufsize=1,
                universal_newlines=True
            )

            output = []
            for line in process.stdout:
                line = line.strip()
                output.append(line)
                if logger:
                    logger.add_log_line(line)

            # Wait for the process to complete
            return_code = process.wait()

            # Check if the command was successful
            if return_code == 0:
                if logger:
                    logger.add_log_line("Command completed successfully")
                    logger.complete(True)
                return True, "\n".join(output)
            else:
                if logger:
                    logger.add_log_line(f"Command failed with return code {return_code}")
                    logger.complete(False)
                return False, "\n".join(output)
        except Exception as e:
            error_message = f"Error running command: {str(e)}"
            if logger:
                logger.add_log_line(error_message)
                logger.complete(False)
            return False, error_message

    def parse_json_output(self, output: str) -> List[Dict[str, Any]]:
        """
        Parse JSON output from Docker commands.

        Args:
            output (str): Command output

        Returns:
            List[Dict[str, Any]]: Parsed JSON objects
        """
        results = []
        for line in output.strip().split('\n'):
            if line:
                try:
                    results.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        return results