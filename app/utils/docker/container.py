"""
Docker container operations.

This module provides the ContainerManager class for managing Docker containers.
"""

import json
from typing import Dict, List, Tuple, Any, Optional
from app.utils.docker.base import DockerBase


class ContainerManager(DockerBase):
    """Class for managing Docker containers."""

    def get_containers(self, config_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get list of running containers.

        Args:
            config_id (int, optional): Filter by configuration ID

        Returns:
            List[Dict[str, Any]]: List of container information
        """
        try:
            # Get all containers
            success, output = self.run_command(
                ['docker', 'ps', '-a', '--format', '{{json .}}'],
                capture_output=True,
                check=True
            )

            if not success:
                return []

            containers = []
            for container in self.parse_json_output(output):
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

    def get_container_logs(self, container_id: str, tail: int = 100) -> Tuple[bool, str]:
        """
        Get logs for a container.

        Args:
            container_id (str): Container ID or name
            tail (int): Number of lines to tail

        Returns:
            Tuple[bool, str]: Success status and logs
        """
        return self.run_command(
            ['docker', 'logs', '--tail', str(tail), container_id],
            capture_output=True,
            check=False
        )

    def start_container(self, container_id: str) -> Tuple[bool, str]:
        """
        Start a container.

        Args:
            container_id (str): Container ID or name

        Returns:
            Tuple[bool, str]: Success status and output
        """
        return self.run_command(
            ['docker', 'start', container_id],
            capture_output=True,
            check=False
        )

    def stop_container(self, container_id: str) -> Tuple[bool, str]:
        """
        Stop a container.

        Args:
            container_id (str): Container ID or name

        Returns:
            Tuple[bool, str]: Success status and output
        """
        return self.run_command(
            ['docker', 'stop', container_id],
            capture_output=True,
            check=False
        )

    def restart_container(self, container_id: str) -> Tuple[bool, str]:
        """
        Restart a container.

        Args:
            container_id (str): Container ID or name

        Returns:
            Tuple[bool, str]: Success status and output
        """
        return self.run_command(
            ['docker', 'restart', container_id],
            capture_output=True,
            check=False
        )

    def remove_container(self, container_id: str, force: bool = False) -> Tuple[bool, str]:
        """
        Remove a container.

        Args:
            container_id (str): Container ID or name
            force (bool): Force removal of running container

        Returns:
            Tuple[bool, str]: Success status and output
        """
        cmd = ['docker', 'rm', container_id]
        if force:
            cmd.insert(2, '-f')

        return self.run_command(
            cmd,
            capture_output=True,
            check=False
        )

    def exec_container_command(self, container_id: str, command: str) -> Tuple[bool, str]:
        """
        Execute a command in a container.

        Args:
            container_id (str): Container ID or name
            command (str): Command to execute

        Returns:
            Tuple[bool, str]: Success status and output
        """
        # Split the command into arguments
        cmd_args = command.split()

        # Build the docker exec command
        docker_cmd = ['docker', 'exec', container_id] + cmd_args

        return self.run_command(
            docker_cmd,
            capture_output=True,
            check=False
        )

    def get_container_stats(self, container_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Get stats for a container.

        Args:
            container_id (str): Container ID or name

        Returns:
            Tuple[bool, Dict[str, Any]]: Success status and stats
        """
        success, output = self.run_command(
            ['docker', 'stats', container_id, '--no-stream', '--format', '{{json .}}'],
            capture_output=True,
            check=False
        )

        if success and output.strip():
            try:
                stats = json.loads(output.strip())
                return True, stats
            except json.JSONDecodeError:
                pass

        return False, {}

    def inspect_container(self, container_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Inspect a container.

        Args:
            container_id (str): Container ID or name

        Returns:
            Tuple[bool, Dict[str, Any]]: Success status and container details
        """
        success, output = self.run_command(
            ['docker', 'inspect', container_id],
            capture_output=True,
            check=False
        )

        if success and output.strip():
            try:
                details = json.loads(output.strip())
                if details and isinstance(details, list):
                    return True, details[0]
            except json.JSONDecodeError:
                pass

        return False, {}

    def stream_container_logs(self, container_id: str, logger=None) -> None:
        """
        Stream logs from a container in real-time.

        Args:
            container_id (str): Container ID or name
            logger: Logger object to record logs
        """
        import time

        try:
            # First, check if the container exists and is running
            success, container_details = self.inspect_container(container_id)

            if not success:
                if logger:
                    logger.add_log_line(f"Error: Container {container_id} not found")
                    logger.complete(False)
                return

            # Get container state
            container_state = container_details.get('State', {})
            is_running = container_state.get('Running', False)

            if logger:
                logger.add_log_line(f"Container {container_id} state: {'Running' if is_running else 'Not running'}")

            # If container is not running, show the logs without follow
            if not is_running:
                if logger:
                    logger.add_log_line("Container is not running, showing existing logs")

                self.run_command_with_streaming(
                    ['docker', 'logs', '--timestamps', container_id],
                    logger=logger
                )

                if logger:
                    logger.add_log_line("End of logs (container not running)")
                    logger.complete(True)
                return

            # Get the container start time to only show logs since then
            started_at = container_state.get('StartedAt', '')

            # For running containers, stream logs with follow
            if logger:
                logger.add_log_line(f"Streaming logs for running container {container_id}")

            # Use --since to only show logs since the container started
            # Use --timestamps to include timestamps in the logs
            self.run_command_with_streaming(
                ['docker', 'logs', '--follow', '--timestamps', '--since', started_at, container_id],
                logger=logger
            )

        except Exception as e:
            if logger:
                logger.add_log_line(f"Error streaming logs: {str(e)}")
                logger.complete(False)
