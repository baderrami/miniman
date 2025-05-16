# Real-time Container Logs Implementation

This document explains the implementation of real-time container logs in the MiniMan application using WebSockets.

## Overview

Previously, when viewing container logs or performing actions on containers, users had to manually reload the page to see updated logs. This created a poor user experience, especially when monitoring containers during startup, shutdown, or troubleshooting.

The new implementation uses WebSockets to stream container logs in real-time, allowing users to see log updates without refreshing the page. Additionally, container actions (start, stop, restart) now trigger automatic updates to the logs view.

## Implementation Details

### 1. WebSocket Event Handler for Container Logs

A new WebSocket event handler was added to stream container logs in real-time:

```python
@socketio.on('stream_container_logs')
def handle_stream_container_logs(data):
    """
    Handle streaming container logs.
    
    Args:
        data (dict): Data containing container ID and room information
    """
    container_id = data.get('container_id')
    room = data.get('room')
    
    # Join the room for this container's logs
    join_room(room)
    
    # Create a WebSocket logger
    logger = create_logger(
        operation_type='stream_container_logs',
        container_id=container_id,
        use_websocket=True,
        socket_io=socketio,
        room=room
    )
    
    # Stream logs in a background thread
    def stream_logs_thread():
        container_manager = ContainerManager()
        container_manager.stream_container_logs(container_id, logger)
    
    thread = threading.Thread(target=stream_logs_thread)
    thread.daemon = True
    thread.start()
```

This handler uses the existing `stream_container_logs` method from the `ContainerManager` class, which runs the `docker logs --follow` command to stream logs in real-time.

### 2. Container Action WebSocket Events

Container action routes (start, stop, restart) were updated to emit WebSocket events when actions are performed:

```python
# Emit WebSocket event for container status change
socketio.emit('container_status_change', {
    'container_id': container_id,
    'status': 'running',
    'action': 'start',
    'timestamp': datetime.utcnow().isoformat(),
    'success': True
}, room=f'container_logs_{container_id}')
```

These events notify clients about container status changes, allowing the UI to update in real-time.

### 3. Enhanced Container Logs UI

The container logs template was updated to:

1. Connect to WebSockets and join a room for the specific container
2. Display log messages in real-time as they arrive
3. Provide controls to start/stop streaming, clear logs, and toggle auto-scrolling
4. Automatically start streaming when the container is running
5. Update the container status badge when status changes
6. Automatically start/stop streaming based on container actions

```javascript
// Listen for Docker log events
socket.on('docker_log', function(data) {
    if (data.container_id === containerId) {
        addLogLine(data.timestamp, data.line);
    }
});

// Listen for container status changes
socket.on('container_status_change', function(data) {
    if (data.container_id === containerId) {
        // Update the container status badge
        if (data.status) {
            containerStatus.textContent = data.status === 'running' ? 'Up' : 'Stopped';
            containerStatus.className = 'badge ' + (data.status === 'running' ? 'bg-success' : 'bg-danger');
        }
        
        // Add a log entry about the action
        const actionMessage = data.success 
            ? `--- Container ${data.action} action successful ---` 
            : `--- Container ${data.action} action failed: ${data.error || 'Unknown error'} ---`;
        addLogLine(data.timestamp, actionMessage);
        
        // Automatically start/stop streaming based on container status
        if ((data.action === 'start' || data.action === 'restart') && data.success && !isStreaming) {
            setTimeout(function() { toggleStreamingBtn.click(); }, 1000);
        }
        
        if (data.action === 'stop' && data.success && isStreaming) {
            toggleStreamingBtn.click();
        }
    }
});
```

### 4. Improved Navigation Flow

Container action routes were updated to redirect back to the logs page if the action was initiated from there:

```python
# Check if we're coming from the container logs page
referrer = request.referrer
if referrer and 'logs' in referrer and container_id in referrer:
    # Extract the config ID from the referrer
    import re
    match = re.search(r'/docker/logs/(\d+)/', referrer)
    if match:
        config_id = match.group(1)
        return redirect(url_for('docker.container_logs', id=config_id, container_id=container_id))
```

This ensures that users stay on the logs page after performing container actions, providing a seamless experience.

## Benefits

1. **Real-time Visibility**: Users can see container logs as they are generated, without manual refreshing
2. **Improved Troubleshooting**: Makes it easier to debug container issues by seeing log output immediately
3. **Better User Experience**: Container actions automatically update the logs view, providing immediate feedback
4. **Reduced Server Load**: Eliminates the need for frequent page reloads, reducing server load
5. **Enhanced Interactivity**: Users can control streaming, clear logs, and toggle auto-scrolling

## Usage

No special actions are required to use the new functionality. When viewing container logs:

1. Logs for running containers will automatically start streaming
2. The "Start Streaming" button can be used to manually start/stop streaming
3. The "Clear" button can be used to clear the log display
4. The "Auto-scroll" checkbox controls whether the view automatically scrolls to new logs
5. Container actions (start, stop, restart) will automatically update the logs view

## Technical Notes

- The implementation uses Flask-SocketIO for WebSocket communication
- Container logs are streamed in a background thread to avoid blocking the main thread
- The UI automatically handles container status changes and updates accordingly
- The implementation is backward compatible with existing code