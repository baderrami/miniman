"""
Docker image operations.

This module provides the ImageManager class for managing Docker images.
"""

import json
from typing import Dict, List, Tuple, Any
from app.utils.docker.base import DockerBase


class ImageManager(DockerBase):
    """Class for managing Docker images."""

    def get_images(self) -> List[Dict[str, Any]]:
        """
        Get list of Docker images.

        Returns:
            List[Dict[str, Any]]: List of image information
        """
        try:
            success, output = self.run_command(
                ['docker', 'images', '--format', '{{json .}}'],
                capture_output=True,
                check=True
            )

            if not success:
                return []

            images = []
            for image in self.parse_json_output(output):
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

    def pull_image(self, image_name: str, logger=None) -> Tuple[bool, str]:
        """
        Pull a Docker image.

        Args:
            image_name (str): Image name (and tag)
            logger: Logger object to record logs

        Returns:
            Tuple[bool, str]: Success status and output
        """
        return self.run_command_with_streaming(
            ['docker', 'pull', image_name],
            logger=logger
        )

    def remove_image(self, image_id: str, force: bool = False) -> Tuple[bool, str]:
        """
        Remove a Docker image.

        Args:
            image_id (str): Image ID or name
            force (bool): Force removal of the image

        Returns:
            Tuple[bool, str]: Success status and output
        """
        cmd = ['docker', 'rmi', image_id]
        if force:
            cmd.insert(2, '-f')

        return self.run_command(
            cmd,
            capture_output=True,
            check=False
        )

    def build_image(self, dockerfile_path: str, tag: str, logger=None) -> Tuple[bool, str]:
        """
        Build a Docker image.

        Args:
            dockerfile_path (str): Path to the directory containing the Dockerfile
            tag (str): Tag for the image
            logger: Logger object to record logs

        Returns:
            Tuple[bool, str]: Success status and output
        """
        if logger:
            return self.run_command_with_streaming(
                ['docker', 'build', '-t', tag, dockerfile_path],
                logger=logger
            )
        else:
            return self.run_command(
                ['docker', 'build', '-t', tag, dockerfile_path],
                capture_output=True,
                check=False
            )

    def inspect_image(self, image_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Inspect a Docker image.

        Args:
            image_id (str): Image ID or name

        Returns:
            Tuple[bool, Dict[str, Any]]: Success status and image details
        """
        success, output = self.run_command(
            ['docker', 'inspect', image_id],
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