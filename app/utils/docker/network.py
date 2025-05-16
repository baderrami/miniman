"""
Docker network operations.

This module provides the NetworkManager class for managing Docker networks.
"""

import json
from typing import Dict, List, Tuple, Any
from dateutil import parser as date_parser
from app.utils.docker.base import DockerBase


class NetworkManager(DockerBase):
    """Class for managing Docker networks."""

    def get_networks(self) -> List[Dict[str, Any]]:
        """
        Get list of Docker networks.

        Returns:
            List[Dict[str, Any]]: List of network information
        """
        try:
            success, output = self.run_command(
                ['docker', 'network', 'ls', '--format', '{{json .}}'],
                capture_output=True,
                check=True
            )

            if not success:
                return []

            networks = []
            for network in self.parse_json_output(output):
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

    def create_network(self, name: str, driver: str = 'bridge', subnet: str = None, gateway: str = None) -> Tuple[bool, str]:
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
        cmd = ['docker', 'network', 'create', '--driver', driver]

        # Add subnet if provided
        if subnet:
            cmd.extend(['--subnet', subnet])

        # Add gateway if provided
        if gateway:
            cmd.extend(['--gateway', gateway])

        # Add name
        cmd.append(name)

        return self.run_command(
            cmd,
            capture_output=True,
            check=False
        )

    def remove_network(self, name: str) -> Tuple[bool, str]:
        """
        Remove a Docker network.

        Args:
            name (str): Network name or ID

        Returns:
            Tuple[bool, str]: Success status and output
        """
        return self.run_command(
            ['docker', 'network', 'rm', name],
            capture_output=True,
            check=False
        )

    def inspect_network(self, name: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Inspect a Docker network.

        Args:
            name (str): Network name or ID

        Returns:
            Tuple[bool, Dict[str, Any]]: Success status and network details
        """
        success, output = self.run_command(
            ['docker', 'network', 'inspect', name],
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

    def connect_container_to_network(self, container_id: str, network_id: str) -> Tuple[bool, str]:
        """
        Connect a container to a network.

        Args:
            container_id (str): Container ID or name
            network_id (str): Network ID or name

        Returns:
            Tuple[bool, str]: Success status and output
        """
        return self.run_command(
            ['docker', 'network', 'connect', network_id, container_id],
            capture_output=True,
            check=False
        )

    def disconnect_container_from_network(self, container_id: str, network_id: str) -> Tuple[bool, str]:
        """
        Disconnect a container from a network.

        Args:
            container_id (str): Container ID or name
            network_id (str): Network ID or name

        Returns:
            Tuple[bool, str]: Success status and output
        """
        return self.run_command(
            ['docker', 'network', 'disconnect', network_id, container_id],
            capture_output=True,
            check=False
        )