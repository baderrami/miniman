"""
Docker container operations.

This module provides the ContainerManager class for managing Docker containers.
"""

import json
import docker
from typing import Dict, List, Tuple, Any, Optional, Callable
from app.utils.docker.base import DockerBase


class ContainerManager(DockerBase):
    """Class for managing Docker containers."""

    def __init__(self):
        """Initialize the Container Manager."""
        super().__init__()
        self.client = docker.from_env()

    def get_containers(self, config_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get list of all containers.

        Args:
            config_id (int, optional): Filter by configuration ID

        Returns:
            List[Dict[str, Any]]: List of container information
        """
        try:
            # Get all containers (both running and stopped)
            all_containers = self.client.containers.list(all=True)

            containers = []
            for container in all_containers:
                # Get container ports
                ports = []
                for port, binding in container.ports.items():
                    if binding:
                        for bind in binding:
                            ports.append(f"{bind['HostIp']}:{bind['HostPort']}->{port}")
                    else:
                        ports.append(f"{port}")

                # Format ports as a string to match the expected format
                ports_str = ", ".join(ports)

                # Get container status
                status = container.status
                if status == "running":
                    # Add uptime information if available
                    if hasattr(container, 'attrs') and 'State' in container.attrs and 'StartedAt' in container.attrs['State']:
                        started_at = container.attrs['State']['StartedAt']
                        if started_at:
                            from datetime import datetime
                            import dateutil.parser
                            try:
                                start_time = dateutil.parser.parse(started_at)
                                now = datetime.now(start_time.tzinfo)
                                uptime = now - start_time
                                days = uptime.days
                                hours, remainder = divmod(uptime.seconds, 3600)
                                minutes, seconds = divmod(remainder, 60)

                                if days > 0:
                                    status = f"Up {days}d {hours}h {minutes}m"
                                elif hours > 0:
                                    status = f"Up {hours}h {minutes}m"
                                else:
                                    status = f"Up {minutes}m {seconds}s"
                            except Exception as e:
                                print(f"Error parsing container start time: {str(e)}")

                containers.append({
                    'id': container.id,
                    'name': container.name,
                    'image': container.image.tags[0] if container.image.tags else container.image.id,
                    'status': status,
                    'created': container.attrs['Created'] if hasattr(container, 'attrs') and 'Created' in container.attrs else '',
                    'ports': ports_str
                })

            return containers
        except docker.errors.APIError as e:
            print(f"Docker API error: {str(e)}")
            return []
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
        try:
            # Get the container
            container = self.client.containers.get(container_id)

            # Get container logs
            logs = container.logs(tail=tail, timestamps=True).decode('utf-8')

            return True, logs

        except docker.errors.NotFound:
            # Container not found
            return False, f"Container {container_id} not found"
        except docker.errors.APIError as e:
            # Docker API error
            return False, f"Docker API error: {str(e)}"
        except Exception as e:
            # Other errors
            return False, f"Error getting container logs: {str(e)}"

    def start_container(self, container_id: str) -> Tuple[bool, str]:
        """
        Start a container.

        Args:
            container_id (str): Container ID or name

        Returns:
            Tuple[bool, str]: Success status and output
        """
        try:
            # Get the container
            container = self.client.containers.get(container_id)

            # Start the container
            container.start()

            return True, f"Container {container_id} started successfully"

        except docker.errors.NotFound:
            # Container not found
            return False, f"Container {container_id} not found"
        except docker.errors.APIError as e:
            # Docker API error
            return False, f"Docker API error: {str(e)}"
        except Exception as e:
            # Other errors
            return False, f"Error starting container: {str(e)}"

    def stop_container(self, container_id: str) -> Tuple[bool, str]:
        """
        Stop a container.

        Args:
            container_id (str): Container ID or name

        Returns:
            Tuple[bool, str]: Success status and output
        """
        try:
            # Get the container
            container = self.client.containers.get(container_id)

            # Stop the container
            container.stop()

            return True, f"Container {container_id} stopped successfully"

        except docker.errors.NotFound:
            # Container not found
            return False, f"Container {container_id} not found"
        except docker.errors.APIError as e:
            # Docker API error
            return False, f"Docker API error: {str(e)}"
        except Exception as e:
            # Other errors
            return False, f"Error stopping container: {str(e)}"

    def restart_container(self, container_id: str) -> Tuple[bool, str]:
        """
        Restart a container.

        Args:
            container_id (str): Container ID or name

        Returns:
            Tuple[bool, str]: Success status and output
        """
        try:
            # Get the container
            container = self.client.containers.get(container_id)

            # Restart the container
            container.restart()

            return True, f"Container {container_id} restarted successfully"

        except docker.errors.NotFound:
            # Container not found
            return False, f"Container {container_id} not found"
        except docker.errors.APIError as e:
            # Docker API error
            return False, f"Docker API error: {str(e)}"
        except Exception as e:
            # Other errors
            return False, f"Error restarting container: {str(e)}"

    def remove_container(self, container_id: str, force: bool = False) -> Tuple[bool, str]:
        """
        Remove a container.

        Args:
            container_id (str): Container ID or name
            force (bool): Force removal of running container

        Returns:
            Tuple[bool, str]: Success status and output
        """
        try:
            # Get the container
            container = self.client.containers.get(container_id)

            # Remove the container
            container.remove(force=force)

            return True, f"Container {container_id} removed successfully"

        except docker.errors.NotFound:
            # Container not found
            return False, f"Container {container_id} not found"
        except docker.errors.APIError as e:
            # Docker API error
            return False, f"Docker API error: {str(e)}"
        except Exception as e:
            # Other errors
            return False, f"Error removing container: {str(e)}"

    def exec_container_command(self, container_id: str, command: str) -> Tuple[bool, str]:
        """
        Execute a command in a container.

        Args:
            container_id (str): Container ID or name
            command (str): Command to execute

        Returns:
            Tuple[bool, str]: Success status and output
        """
        try:
            # Get the container
            container = self.client.containers.get(container_id)

            # Execute the command
            exec_result = container.exec_run(command, stream=False)

            # Return the result
            return exec_result.exit_code == 0, exec_result.output.decode('utf-8')

        except docker.errors.NotFound:
            # Container not found
            return False, f"Container {container_id} not found"
        except docker.errors.APIError as e:
            # Docker API error
            return False, f"Docker API error: {str(e)}"
        except Exception as e:
            # Other errors
            return False, f"Error executing command: {str(e)}"

    def get_container_stats(self, container_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Get stats for a container.

        Args:
            container_id (str): Container ID or name

        Returns:
            Tuple[bool, Dict[str, Any]]: Success status and stats
        """
        try:
            # Get the container
            container = self.client.containers.get(container_id)

            # Get container stats
            stats = container.stats(stream=False)

            # Process stats to match the format expected by the frontend
            processed_stats = {
                'Name': container.name,
                'ID': container.id[:12],
                'CPUPerc': self._calculate_cpu_percentage(stats),
                'MemUsage': self._format_memory_usage(stats),
                'MemPerc': self._calculate_memory_percentage(stats),
                'NetIO': self._format_network_io(stats),
                'BlockIO': self._format_block_io(stats),
                'PIDs': stats.get('pids_stats', {}).get('current', 0)
            }

            return True, processed_stats

        except docker.errors.NotFound:
            # Container not found
            return False, {}
        except docker.errors.APIError as e:
            # Docker API error
            print(f"Docker API error: {str(e)}")
            return False, {}
        except Exception as e:
            # Other errors
            print(f"Error getting container stats: {str(e)}")
            return False, {}

    def _calculate_cpu_percentage(self, stats: Dict[str, Any]) -> str:
        """
        Calculate CPU percentage from stats.

        Args:
            stats (Dict[str, Any]): Container stats

        Returns:
            str: CPU percentage as string with % suffix
        """
        try:
            cpu_stats = stats.get('cpu_stats', {})
            precpu_stats = stats.get('precpu_stats', {})

            cpu_total_usage = cpu_stats.get('cpu_usage', {}).get('total_usage', 0)
            precpu_total_usage = precpu_stats.get('cpu_usage', {}).get('total_usage', 0)

            cpu_system_usage = cpu_stats.get('system_cpu_usage', 0)
            precpu_system_usage = precpu_stats.get('system_cpu_usage', 0)

            cpu_delta = cpu_total_usage - precpu_total_usage
            system_delta = cpu_system_usage - precpu_system_usage

            if system_delta > 0 and cpu_delta > 0:
                cpu_percent = (cpu_delta / system_delta) * len(cpu_stats.get('cpu_usage', {}).get('percpu_usage', [])) * 100
                return f"{cpu_percent:.2f}%"

            return "0.00%"
        except Exception as e:
            print(f"Error calculating CPU percentage: {str(e)}")
            return "0.00%"

    def _format_memory_usage(self, stats: Dict[str, Any]) -> str:
        """
        Format memory usage from stats.

        Args:
            stats (Dict[str, Any]): Container stats

        Returns:
            str: Memory usage as string in format "used / limit"
        """
        try:
            memory_stats = stats.get('memory_stats', {})
            usage = memory_stats.get('usage', 0)
            limit = memory_stats.get('limit', 0)

            # Convert to human-readable format
            used = self._human_readable_size(usage)
            total = self._human_readable_size(limit)

            return f"{used} / {total}"
        except Exception as e:
            print(f"Error formatting memory usage: {str(e)}")
            return "0B / 0B"

    def _calculate_memory_percentage(self, stats: Dict[str, Any]) -> str:
        """
        Calculate memory percentage from stats.

        Args:
            stats (Dict[str, Any]): Container stats

        Returns:
            str: Memory percentage as string with % suffix
        """
        try:
            memory_stats = stats.get('memory_stats', {})
            usage = memory_stats.get('usage', 0)
            limit = memory_stats.get('limit', 0)

            if limit > 0:
                mem_percent = (usage / limit) * 100
                return f"{mem_percent:.2f}%"

            return "0.00%"
        except Exception as e:
            print(f"Error calculating memory percentage: {str(e)}")
            return "0.00%"

    def _format_network_io(self, stats: Dict[str, Any]) -> str:
        """
        Format network I/O from stats.

        Args:
            stats (Dict[str, Any]): Container stats

        Returns:
            str: Network I/O as string in format "in / out"
        """
        try:
            networks = stats.get('networks', {})
            rx_bytes = sum(network.get('rx_bytes', 0) for network in networks.values())
            tx_bytes = sum(network.get('tx_bytes', 0) for network in networks.values())

            # Convert to human-readable format
            rx = self._human_readable_size(rx_bytes)
            tx = self._human_readable_size(tx_bytes)

            return f"{rx} / {tx}"
        except Exception as e:
            print(f"Error formatting network I/O: {str(e)}")
            return "0B / 0B"

    def _format_block_io(self, stats: Dict[str, Any]) -> str:
        """
        Format block I/O from stats.

        Args:
            stats (Dict[str, Any]): Container stats

        Returns:
            str: Block I/O as string in format "read / write"
        """
        try:
            blkio_stats = stats.get('blkio_stats', {})
            io_service_bytes_recursive = blkio_stats.get('io_service_bytes_recursive', [])

            read_bytes = 0
            write_bytes = 0

            for io_stat in io_service_bytes_recursive:
                if io_stat.get('op') == 'Read':
                    read_bytes += io_stat.get('value', 0)
                elif io_stat.get('op') == 'Write':
                    write_bytes += io_stat.get('value', 0)

            # Convert to human-readable format
            read = self._human_readable_size(read_bytes)
            write = self._human_readable_size(write_bytes)

            return f"{read} / {write}"
        except Exception as e:
            print(f"Error formatting block I/O: {str(e)}")
            return "0B / 0B"

    def _human_readable_size(self, size_bytes: int) -> str:
        """
        Convert bytes to human-readable format.

        Args:
            size_bytes (int): Size in bytes

        Returns:
            str: Human-readable size
        """
        if size_bytes == 0:
            return "0B"

        units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
        i = 0
        while size_bytes >= 1024 and i < len(units) - 1:
            size_bytes /= 1024
            i += 1

        return f"{size_bytes:.2f}{units[i]}"

    def inspect_container(self, container_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Inspect a container.

        Args:
            container_id (str): Container ID or name

        Returns:
            Tuple[bool, Dict[str, Any]]: Success status and container details
        """
        try:
            # Get the container
            container = self.client.containers.get(container_id)

            # Get container attributes
            container_attrs = container.attrs

            return True, container_attrs

        except docker.errors.NotFound:
            # Container not found
            return False, {}
        except docker.errors.APIError as e:
            # Docker API error
            print(f"Docker API error: {str(e)}")
            return False, {}
        except Exception as e:
            # Other errors
            print(f"Error inspecting container: {str(e)}")
            return False, {}

    def stream_container_logs(self, container_id: str, log_callback: Callable[[str], None]) -> None:
        """
        Stream logs from a container in real-time using the Docker Python SDK.

        Args:
            container_id (str): Container ID or name
            log_callback (Callable[[str], None]): Callback function to handle each log line
        """
        try:
            # Get the container
            container = self.client.containers.get(container_id)

            # Check if the container exists
            if not container:
                return

            # Get container state
            is_running = container.status == 'running'

            # If container is not running, show the logs without follow
            if not is_running:
                logs = container.logs(timestamps=True, stream=False).decode('utf-8')
                for line in logs.splitlines():
                    log_callback(line)
                return

            # Stream logs with timestamps
            for line in container.logs(timestamps=True, stream=True, follow=True):
                log_callback(line.decode('utf-8'))

        except docker.errors.NotFound:
            # Container not found
            return
        except docker.errors.APIError as e:
            # Docker API error
            print(f"Docker API error: {str(e)}")
        except Exception as e:
            # Other errors
            print(f"Error streaming logs: {str(e)}")
