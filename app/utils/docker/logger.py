"""
Docker logging functionality.

This module provides classes for logging Docker operations, including WebSocket support.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Callable
from app.models.docker import DockerOperationLog


class DockerLogger:
    """Base class for Docker operation logging."""

    def __init__(self, operation_type: str, config_id: Optional[int] = None,
                 container_id: Optional[str] = None, image_name: Optional[str] = None):
        """
        Initialize the Docker logger.

        Args:
            operation_type (str): Type of operation being performed
            config_id (Optional[int]): ID of the Docker Compose configuration
            container_id (Optional[str]): ID of the container
            image_name (Optional[str]): Name of the image
        """
        self.operation_type = operation_type
        self.config_id = config_id
        self.container_id = container_id
        self.image_name = image_name
        self.log_lines = []
        self.started_at = datetime.utcnow()
        self.completed_at = None
        self.status = 'running'
        self.db_log = None

    def add_log_line(self, line: str) -> None:
        """
        Add a line to the log.

        Args:
            line (str): Log line to add
        """
        self.log_lines.append(line)
        if self.db_log:
            self.db_log.add_log_line(line)

    def complete(self, success: bool = True) -> None:
        """
        Mark the operation as completed.

        Args:
            success (bool): Whether the operation was successful
        """
        self.completed_at = datetime.utcnow()
        self.status = 'completed' if success else 'failed'
        if self.db_log:
            self.db_log.complete(success)

    def get_log_content(self) -> str:
        """
        Get the full log content.

        Returns:
            str: Full log content
        """
        return '\n'.join(self.log_lines)

    def create_db_log(self) -> None:
        """Create a database log entry."""
        self.db_log = DockerOperationLog(
            operation_type=self.operation_type,
            config_id=self.config_id,
            container_id=self.container_id,
            image_name=self.image_name,
            status='running'
        )
        from app import db
        db.session.add(self.db_log)
        db.session.commit()


class WebSocketLogger(DockerLogger):
    """Docker logger with WebSocket support for real-time logs."""

    def __init__(self, operation_type: str, config_id: Optional[int] = None,
                 container_id: Optional[str] = None, image_name: Optional[str] = None,
                 socket_io=None, room: Optional[str] = None):
        """
        Initialize the WebSocket logger.

        Args:
            operation_type (str): Type of operation being performed
            config_id (Optional[int]): ID of the Docker Compose configuration
            container_id (Optional[str]): ID of the container
            image_name (Optional[str]): Name of the image
            socket_io: Flask-SocketIO instance
            room (Optional[str]): Room to emit events to
        """
        super().__init__(operation_type, config_id, container_id, image_name)
        self.socket_io = socket_io
        self.room = room or 'docker_logs'
        self.log_id = None
        
        if self.db_log:
            self.log_id = self.db_log.id

    def add_log_line(self, line: str) -> None:
        """
        Add a line to the log and emit it via WebSocket.

        Args:
            line (str): Log line to add
        """
        super().add_log_line(line)
        
        if self.socket_io:
            self.socket_io.emit('docker_log', {
                'log_id': self.log_id,
                'operation_type': self.operation_type,
                'config_id': self.config_id,
                'container_id': self.container_id,
                'image_name': self.image_name,
                'line': line,
                'timestamp': datetime.utcnow().isoformat(),
                'status': self.status
            }, room=self.room)

    def complete(self, success: bool = True) -> None:
        """
        Mark the operation as completed and emit completion event.

        Args:
            success (bool): Whether the operation was successful
        """
        super().complete(success)
        
        if self.socket_io:
            self.socket_io.emit('docker_log_complete', {
                'log_id': self.log_id,
                'operation_type': self.operation_type,
                'config_id': self.config_id,
                'container_id': self.container_id,
                'image_name': self.image_name,
                'success': success,
                'timestamp': datetime.utcnow().isoformat(),
                'status': self.status
            }, room=self.room)


# Factory function to create the appropriate logger
def create_logger(operation_type: str, config_id: Optional[int] = None,
                  container_id: Optional[str] = None, image_name: Optional[str] = None,
                  use_websocket: bool = False, socket_io=None, room: Optional[str] = None,
                  use_db: bool = True) -> DockerLogger:
    """
    Create a Docker logger.

    Args:
        operation_type (str): Type of operation being performed
        config_id (Optional[int]): ID of the Docker Compose configuration
        container_id (Optional[str]): ID of the container
        image_name (Optional[str]): Name of the image
        use_websocket (bool): Whether to use WebSocket logging
        socket_io: Flask-SocketIO instance
        room (Optional[str]): Room to emit events to
        use_db (bool): Whether to create a database log entry

    Returns:
        DockerLogger: Docker logger instance
    """
    if use_websocket and socket_io:
        logger = WebSocketLogger(
            operation_type=operation_type,
            config_id=config_id,
            container_id=container_id,
            image_name=image_name,
            socket_io=socket_io,
            room=room
        )
    else:
        logger = DockerLogger(
            operation_type=operation_type,
            config_id=config_id,
            container_id=container_id,
            image_name=image_name
        )
    
    if use_db:
        logger.create_db_log()
    
    return logger