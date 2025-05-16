"""
Docker volume operations.

This module provides the VolumeManager class for managing Docker volumes.
"""

import json
from typing import Dict, List, Tuple, Any
from dateutil import parser as date_parser
from app.utils.docker.base import DockerBase


class VolumeManager(DockerBase):
    """Class for managing Docker volumes."""

    def get_volumes(self) -> List[Dict[str, Any]]:
        """
        Get list of Docker volumes.

        Returns:
            List[Dict[str, Any]]: List of volume information
        """
        try:
            success, output = self.run_command(
                ['docker', 'volume', 'ls', '--format', '{{json .}}'],
                capture_output=True,
                check=True
            )

            if not success:
                return []

            volumes = []
            for volume in self.parse_json_output(output):
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

    def create_volume(self, name: str, driver: str = 'local', labels: Dict[str, str] = None) -> Tuple[bool, str]:
        """
        Create a Docker volume.

        Args:
            name (str): Volume name
            driver (str): Volume driver
            labels (Dict[str, str]): Volume labels

        Returns:
            Tuple[bool, str]: Success status and output
        """
        cmd = ['docker', 'volume', 'create', '--driver', driver]

        # Add labels if provided
        if labels:
            for key, value in labels.items():
                cmd.extend(['--label', f'{key}={value}'])

        # Add name
        cmd.append(name)

        return self.run_command(
            cmd,
            capture_output=True,
            check=False
        )

    def remove_volume(self, name: str, force: bool = False) -> Tuple[bool, str]:
        """
        Remove a Docker volume.

        Args:
            name (str): Volume name
            force (bool): Force removal of the volume

        Returns:
            Tuple[bool, str]: Success status and output
        """
        cmd = ['docker', 'volume', 'rm', name]
        if force:
            cmd.insert(3, '-f')

        return self.run_command(
            cmd,
            capture_output=True,
            check=False
        )

    def inspect_volume(self, name: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Inspect a Docker volume.

        Args:
            name (str): Volume name

        Returns:
            Tuple[bool, Dict[str, Any]]: Success status and volume details
        """
        success, output = self.run_command(
            ['docker', 'volume', 'inspect', name],
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