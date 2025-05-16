# Docker Utilities Refactoring

This document explains the refactoring of the Docker utilities in the MiniMan application, including the improvements made and how to use the new WebSocket functionality for real-time Docker operations and logs.

## Overview

The original `docker_utils.py` file was a monolithic module with over 1,200 lines of code, containing functions for various Docker operations. This made it difficult to maintain, test, and extend. The refactoring breaks down this monolithic file into a more modular and maintainable structure, with separate classes for different types of Docker operations.

## Benefits of the Refactoring

1. **Improved Code Organization**: The code is now organized into logical modules based on functionality, making it easier to understand and navigate.
2. **Separation of Concerns**: Each class has a specific responsibility, following the Single Responsibility Principle.
3. **Better Testability**: Smaller, focused classes are easier to test in isolation.
4. **Enhanced Maintainability**: Changes to one aspect of Docker functionality won't affect others.
5. **Real-time Logging**: Added WebSocket support for real-time Docker operation logs.
6. **Backward Compatibility**: Existing code that uses the old functions will continue to work without changes.

## New Architecture

The refactored Docker utilities are organized as follows:

```
app/docker/
├── __init__.py          # Package initialization and re-exports
├── base.py              # Base Docker functionality
├── container.py         # Container operations
├── image.py             # Image operations
├── volume.py            # Volume operations
├── network.py           # Network operations
├── compose.py           # Docker Compose operations
├── logger.py            # Logging functionality with WebSocket support
└── compat.py            # Backward compatibility layer
```

### Class Hierarchy

- **DockerBase**: Base class with common Docker functionality
  - **ContainerManager**: Container operations
  - **ImageManager**: Image operations
  - **VolumeManager**: Volume operations
  - **NetworkManager**: Network operations
  - **ComposeManager**: Docker Compose operations

- **DockerLogger**: Base class for Docker operation logging
  - **WebSocketLogger**: Docker logger with WebSocket support

## WebSocket Integration for Real-time Logs

One of the major improvements is the addition of WebSocket support for real-time Docker operation logs. This allows users to see the output of Docker operations as they happen, rather than waiting for the operation to complete.

### How to Use WebSocket Logging

1. **Initialize Flask-SocketIO**:

```python
from flask import Flask
from flask_socketio import SocketIO

app = Flask(__name__)
socketio = SocketIO(app)
```

2. **Create a WebSocket Logger**:

```python
from app.utils.docker.logger import create_logger

logger = create_logger(
  operation_type='run_compose',
  config_id=1,
  use_websocket=True,
  socket_io=socketio,
  room='docker_logs'
)
```

3. **Use the Logger with Docker Operations**:

```python
from app.utils.docker.compose import ComposeManager

compose_manager = ComposeManager()
compose_manager.run_compose('/path/to/docker-compose.yml', logger=logger)
```

4. **Set Up Client-Side WebSocket Handling**:

```javascript
// Connect to the WebSocket server
const socket = io();

// Listen for Docker log events
socket.on('docker_log', function(data) {
    console.log(`[${data.timestamp}] ${data.line}`);
    // Update UI with the log line
    appendLogLine(data.line);
});

// Listen for operation completion
socket.on('docker_log_complete', function(data) {
    console.log(`Operation ${data.operation_type} completed with status: ${data.status}`);
    // Update UI to show completion
    showOperationComplete(data.success);
});
```

## Backward Compatibility

To ensure that existing code continues to work without changes, a compatibility layer is provided in `compat.py`. This module re-exports all the functions from the old `docker_utils.py` with the same signatures, but implements them using the new class-based architecture.

Example:

```python
# Old code using docker_utils.py
from app.utils.docker_utils import run_compose

# Will continue to work with the new architecture
run_compose('/path/to/docker-compose.yml', operation_log)
```

## Migrating to the New API

While the compatibility layer ensures that existing code will continue to work, it's recommended to migrate to the new class-based API for new code. This provides better organization and access to new features like WebSocket logging.

Example:

```python
# New code using the class-based API
from app.utils.docker.compose import ComposeManager
from app.utils.docker.logger import create_logger

# Create a logger with WebSocket support
logger = create_logger(
  operation_type='run_compose',
  config_id=1,
  use_websocket=True,
  socket_io=socketio
)

# Use the ComposeManager
compose_manager = ComposeManager()
compose_manager.run_compose('/path/to/docker-compose.yml', logger=logger)
```

## Conclusion

The refactoring of the Docker utilities improves code organization, maintainability, and testability, while adding new features like WebSocket support for real-time logs. The backward compatibility layer ensures that existing code will continue to work without changes, making this a safe and beneficial improvement to the codebase.