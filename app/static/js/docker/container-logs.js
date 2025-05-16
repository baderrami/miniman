/**
 * Container logs functionality
 * 
 * @requires container-common.js - For socket, containerId, roomName, hasJoinedRoom, containerRunning, formatTimestamp
 */

document.addEventListener('DOMContentLoaded', function() {
    // Logs Tab Elements
    const logContainer = document.getElementById('log-container');
    const initialLogs = document.getElementById('initial-logs');
    const toggleStreamingBtn = document.getElementById('toggle-streaming');
    const clearLogsBtn = document.getElementById('clear-logs');
    const autoScrollCheckbox = document.getElementById('auto-scroll');

    let isStreaming = false;

    // Scroll to bottom of log container
    function scrollToBottom() {
        if (autoScrollCheckbox.checked) {
            logContainer.scrollTop = logContainer.scrollHeight;
        }
    }

    // Add a log line to the container
    function addLogLine(timestamp, text) {
        // Don't add empty lines
        if (!text || text.trim() === '') {
            return;
        }

        const lineElement = document.createElement('div');
        lineElement.className = 'log-line';

        if (timestamp) {
            const timestampSpan = document.createElement('span');
            timestampSpan.className = 'log-timestamp';
            timestampSpan.textContent = formatTimestamp(timestamp);
            lineElement.appendChild(timestampSpan);
        }

        // Process the text to ensure it's properly formatted
        // This helps with log lines that might contain special characters or HTML
        const textNode = document.createTextNode(text);
        lineElement.appendChild(textNode);

        logContainer.appendChild(lineElement);
        scrollToBottom();
    }

    // Clear all logs
    clearLogsBtn.addEventListener('click', function() {
        // Clear the log container but keep the structure
        const alertInfo = document.createElement('div');
        alertInfo.className = 'alert alert-info';
        alertInfo.textContent = 'Logs cleared. Start streaming to see new logs.';

        logContainer.innerHTML = '';
        logContainer.appendChild(alertInfo);

        console.log('Logs cleared');
    });

    // Function to start streaming logs
    function startStreaming() {
        console.log('Starting streaming logs...');
        console.log('Socket connected:', socket.connected);

        if (!hasJoinedRoom) {
            console.log('Not joined to room yet, joining now');
            socket.emit('join', { room: roomName });
            hasJoinedRoom = true;
        }

        // Keep initial logs but clear any previous streaming logs
        if (initialLogs) {
            // We don't remove initialLogs completely to maintain the structure
            // Get all log lines
            const allLogLines = logContainer.querySelectorAll('.log-line');
            // Remove only those that are not part of initialLogs
            allLogLines.forEach(el => {
                if (!initialLogs.contains(el)) {
                    el.remove();
                }
            });
        }

        // Add a log line indicating streaming is starting
        addLogLine(new Date().toISOString(), '--- Starting log streaming ---');

        console.log('Emitting stream_container_logs event with data:', {
            container_id: containerId,
            room: roomName
        });

        socket.emit('stream_container_logs', {
            container_id: containerId,
            room: roomName
        });

        console.log('Event emitted');

        isStreaming = true;
        toggleStreamingBtn.textContent = 'Stop Streaming';
        toggleStreamingBtn.classList.remove('btn-primary');
        toggleStreamingBtn.classList.add('btn-danger');
        console.log('Started streaming logs');
    }

    // Function to stop streaming logs
    function stopStreaming() {
        socket.emit('leave', { room: roomName });
        isStreaming = false;
        toggleStreamingBtn.textContent = 'Start Streaming';
        toggleStreamingBtn.classList.remove('btn-danger');
        toggleStreamingBtn.classList.add('btn-primary');
        console.log('Stopped streaming logs');

        // Add a log line indicating streaming has stopped
        addLogLine(new Date().toISOString(), '--- Log streaming stopped ---');
    }

    // Toggle streaming
    toggleStreamingBtn.addEventListener('click', function() {
        if (isStreaming) {
            stopStreaming();
        } else {
            startStreaming();
        }
    });

    // Socket event handlers for logs
    socket.on('docker_log', function(data) {
        console.log('Received docker_log event:', data);

        if (data.container_id === containerId) {
            console.log('Log is for current container');

            // Remove any alert messages when we start getting logs
            const alerts = logContainer.querySelectorAll('.alert');
            alerts.forEach(alert => alert.remove());

            // Add the log line with timestamp
            addLogLine(data.timestamp, data.line);
            console.log('Added log line to container');
        } else {
            console.log('Log is for different container:', data.container_id);
        }
    });

    socket.on('docker_log_complete', function(data) {
        console.log('Received docker_log_complete event:', data);

        if (data.container_id === containerId) {
            console.log('Completion is for current container');

            addLogLine(data.timestamp, `--- Log streaming ${data.success ? 'completed' : 'failed'} ---`);
            console.log('Log streaming ' + (data.success ? 'completed' : 'failed'));

            isStreaming = false;
            toggleStreamingBtn.textContent = 'Start Streaming';
            toggleStreamingBtn.classList.remove('btn-danger');
            toggleStreamingBtn.classList.add('btn-primary');
        } else {
            console.log('Completion is for different container:', data.container_id);
        }
    });

    // Listen for container status changes to control log streaming
    socket.on('container_status_change', function(data) {
        if (data.container_id === containerId) {
            // Add a log entry about the action with a clear separator
            const actionMessage = data.success 
                ? `------ Container ${data.action} action successful ------` 
                : `------ Container ${data.action} action failed: ${data.error || 'Unknown error'} ------`;
            addLogLine(data.timestamp, actionMessage);

            // If container was started or restarted and we're not streaming, start streaming
            if ((data.action === 'start' || data.action === 'restart') && data.success && !isStreaming) {
                // Delay slightly to allow the container to start up
                setTimeout(function() {
                    console.log('Auto-starting streaming after container start/restart');
                    startStreaming();
                }, 1500);
            }

            // If container was stopped and we're streaming, stop streaming
            if (data.action === 'stop' && data.success && isStreaming) {
                console.log('Auto-stopping streaming after container stop');
                stopStreaming();
            }
        }
    });

    // Auto-start streaming if container is running
    if (containerRunning) {
        // Delay slightly to ensure the page is fully loaded and WebSocket is connected
        setTimeout(function() {
            console.log('Auto-starting streaming for running container');
            console.log('Socket connected:', socket.connected);
            // Only start if not already streaming
            if (!isStreaming) {
                startStreaming();
            }
        }, 1500); // Increased delay to ensure WebSocket connection is established
    } else {
        console.log('Container not running, not auto-starting streaming');
    }

    // Set up a periodic check to restart streaming if it stopped unexpectedly
    // This ensures logs continue to update even if the WebSocket connection was interrupted
    setInterval(function() {
        if (containerRunning && !isStreaming && hasJoinedRoom) {
            console.log('Detected container running but not streaming, restarting stream');
            startStreaming();
        }
    }, 10000); // Check every 10 seconds
});
