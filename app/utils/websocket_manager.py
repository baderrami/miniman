"""
Centralized WebSocket Management Module.

This module provides a centralized interface for WebSocket operations across the application.
It abstracts the underlying WebSocket implementation (Flask-SocketIO) and provides a clean API
for components to use.
"""

from typing import Dict, Any, Optional, Callable, List
from flask_socketio import emit, join_room, leave_room
from datetime import datetime
import functools
import threading

# Reference to the Flask-SocketIO instance
_socketio = None

def init_socketio(socketio_instance):
    """
    Initialize the WebSocket manager with a Flask-SocketIO instance.
    
    Args:
        socketio_instance: The Flask-SocketIO instance to use
    """
    global _socketio
    _socketio = socketio_instance
    
    # Register the basic event handlers
    register_default_handlers()

def register_default_handlers():
    """Register default WebSocket event handlers."""
    @_socketio.on('connect')
    def handle_connect():
        """Handle WebSocket connection."""
        print('Client connected')

    @_socketio.on('disconnect')
    def handle_disconnect():
        """Handle WebSocket disconnection."""
        print('Client disconnected')

    @_socketio.on('join')
    def handle_join(data):
        """
        Handle joining a room.
        
        Args:
            data (dict): Data containing room information
        """
        room = data.get('room')
        if room:
            join_room(room)
            emit('status', {'msg': f'Joined room: {room}'}, room=room)

    @_socketio.on('leave')
    def handle_leave(data):
        """
        Handle leaving a room.
        
        Args:
            data (dict): Data containing room information
        """
        room = data.get('room')
        if room:
            leave_room(room)
            emit('status', {'msg': f'Left room: {room}'}, room=room)

def emit_event(event_name: str, data: Dict[str, Any], room: Optional[str] = None):
    """
    Emit a WebSocket event.
    
    Args:
        event_name (str): Name of the event to emit
        data (Dict[str, Any]): Data to send with the event
        room (Optional[str]): Room to emit the event to, or None for all clients
    """
    if _socketio:
        _socketio.emit(event_name, data, room=room)

def run_in_background(func: Callable, *args, **kwargs):
    """
    Run a function in a background thread.
    
    Args:
        func (Callable): Function to run
        *args: Arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function
    
    Returns:
        threading.Thread: The thread running the function
    """
    thread = threading.Thread(target=func, args=args, kwargs=kwargs)
    thread.daemon = True
    thread.start()
    return thread

def register_event_handler(event_name: str):
    """
    Decorator to register a function as a WebSocket event handler.
    
    Args:
        event_name (str): Name of the event to handle
    
    Returns:
        Callable: Decorator function
    """
    def decorator(func):
        @_socketio.on(event_name)
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    return decorator

# Room management
def create_room_name(component: str, entity_type: str, entity_id: str) -> str:
    """
    Create a standardized room name for WebSocket communications.
    
    Args:
        component (str): Component name (e.g., 'docker', 'network')
        entity_type (str): Type of entity (e.g., 'container', 'config')
        entity_id (str): ID of the entity
    
    Returns:
        str: Standardized room name
    """
    return f"{component}_{entity_type}_{entity_id}"

# Logging helpers
def emit_log(component: str, log_type: str, data: Dict[str, Any], room: Optional[str] = None):
    """
    Emit a log event with standardized format.
    
    Args:
        component (str): Component generating the log (e.g., 'docker', 'network')
        log_type (str): Type of log (e.g., 'info', 'error', 'warning')
        data (Dict[str, Any]): Log data
        room (Optional[str]): Room to emit the log to, or None for all clients
    """
    log_data = {
        'component': component,
        'type': log_type,
        'timestamp': datetime.utcnow().isoformat(),
        **data
    }
    emit_event(f'{component}_log', log_data, room)

def emit_operation_complete(component: str, operation: str, success: bool, data: Dict[str, Any], room: Optional[str] = None):
    """
    Emit an operation complete event with standardized format.
    
    Args:
        component (str): Component that performed the operation (e.g., 'docker', 'network')
        operation (str): Type of operation (e.g., 'container_start', 'network_create')
        success (bool): Whether the operation was successful
        data (Dict[str, Any]): Operation data
        room (Optional[str]): Room to emit the event to, or None for all clients
    """
    complete_data = {
        'component': component,
        'operation': operation,
        'success': success,
        'timestamp': datetime.utcnow().isoformat(),
        **data
    }
    emit_event(f'{component}_operation_complete', complete_data, room)

# Docker-specific helpers
def emit_docker_log(log_data: Dict[str, Any], room: Optional[str] = None):
    """
    Emit a Docker log event.
    
    Args:
        log_data (Dict[str, Any]): Log data
        room (Optional[str]): Room to emit the log to, or None for all clients
    """
    emit_log('docker', 'log', log_data, room)

def emit_docker_operation_complete(operation: str, success: bool, data: Dict[str, Any], room: Optional[str] = None):
    """
    Emit a Docker operation complete event.
    
    Args:
        operation (str): Type of operation (e.g., 'container_start', 'image_pull')
        success (bool): Whether the operation was successful
        data (Dict[str, Any]): Operation data
        room (Optional[str]): Room to emit the event to, or None for all clients
    """
    emit_operation_complete('docker', operation, success, data, room)

# Container-specific helpers
def emit_container_log(container_id: str, line: str, status: str = 'info', room: Optional[str] = None):
    """
    Emit a container log event.
    
    Args:
        container_id (str): ID of the container
        line (str): Log line
        status (str): Status of the log (e.g., 'info', 'error')
        room (Optional[str]): Room to emit the log to, or None for all clients
    """
    log_data = {
        'container_id': container_id,
        'line': line,
        'status': status
    }
    emit_docker_log(log_data, room or create_room_name('docker', 'container', container_id))

def emit_container_status_change(container_id: str, status: str, action: str, success: bool, error: Optional[str] = None, room: Optional[str] = None):
    """
    Emit a container status change event.
    
    Args:
        container_id (str): ID of the container
        status (str): New status of the container
        action (str): Action that caused the status change
        success (bool): Whether the action was successful
        error (Optional[str]): Error message if the action failed
        room (Optional[str]): Room to emit the event to, or None for all clients
    """
    data = {
        'container_id': container_id,
        'status': status,
        'action': action,
        'success': success
    }
    if error:
        data['error'] = error
    
    emit_event('container_status_change', data, room or create_room_name('docker', 'container', container_id))