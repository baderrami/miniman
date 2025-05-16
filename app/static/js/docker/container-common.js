/**
 * Common functionality for container view
 */

/**
 * Socket.IO client library
 * @external io
 * @see {@link https://socket.io/docs/v4/client-api/}
 */

/**
 * Creates a new Socket.IO client instance
 * @function io
 * @param {string} url - The URL to connect to
 * @param {Object} options - Connection options
 * @returns {Socket} A new Socket.IO client instance
 */

/**
 * @typedef {Object} Socket
 * @property {function} on - Register an event handler
 * @property {function} emit - Emit an event
 * @property {string} id - Socket ID
 * @property {Object} nsp - Socket namespace
 * @property {boolean} connected - Whether socket is connected
 */

// Initialize Socket.IO with reconnection options
// Use window.location to ensure we connect to the same host and port as the page
/** @type {Socket} */
window.socket = io(window.location.origin, {
    reconnection: true,
    reconnectionAttempts: 10,
    reconnectionDelay: 1000,
    reconnectionDelayMax: 5000,
    timeout: 20000
});

// Global variables
window.containerId = document.getElementById('container-id').value;
window.roomName = document.getElementById('room-name').value;
const containerStatusRunning = document.getElementById('container-status-running');
const containerStatusStopped = document.getElementById('container-status-stopped');
const containerStatus = containerStatusRunning || containerStatusStopped;
window.containerRunning = containerStatus ? containerStatus.getAttribute('data-running') === 'true' : false;
window.hasJoinedRoom = false;

// Format timestamp
window.formatTimestamp = function(isoString) {
    const date = new Date(isoString);
    return date.toLocaleTimeString();
}

// Socket event handlers for connection
window.socket.on('connect', function() {
    console.log('Connected to WebSocket server');
    console.log('Socket ID:', window.socket.id);
    console.log('Socket namespace:', window.socket.nsp);
    console.log('Socket connected to:', window.location.origin);

    // Join the room for this container when connection is established
    window.socket.emit('join', { room: window.roomName });
    console.log('Joined room:', window.roomName);
    window.hasJoinedRoom = true;
});

window.socket.on('reconnect_attempt', function(attemptNumber) {
    console.log('Attempting to reconnect:', attemptNumber);
});

window.socket.on('reconnect', function(attemptNumber) {
    console.log('Reconnected after', attemptNumber, 'attempts');

    // Re-join the room after reconnection
    window.socket.emit('join', { room: window.roomName });
    window.hasJoinedRoom = true;
});

window.socket.on('reconnect_error', function(error) {
    console.error('Reconnection error:', error);
    console.error('Error details:', error.message);
    console.error('Connection URL:', window.location.origin);
});

window.socket.on('error', function(error) {
    console.error('Socket.IO error:', error);
    console.error('Error details:', error.message || error);
    console.error('Socket ID:', window.socket.id);
    console.error('Socket connected:', window.socket.connected);
});

window.socket.on('connect_error', function(error) {
    console.error('Socket.IO connection error:', error);
    console.error('Error details:', error.message);
    console.error('Connection URL:', window.location.origin);
});

window.socket.on('status', function(data) {
    console.log('Status:', data.msg);
});

// Listen for container status changes
window.socket.on('container_status_change', function(data) {
    console.log('Received container_status_change event:', data);

    if (data.container_id === window.containerId) {
        console.log('Status change is for current container');

        // Update the container status badge
        if (data.status) {
            // Show/hide the appropriate status badge based on container status
            if (data.status === 'running') {
                if (containerStatusRunning) {
                    containerStatusRunning.style.display = '';
                    if (containerStatusStopped) containerStatusStopped.style.display = 'none';
                }
            } else {
                if (containerStatusStopped) {
                    containerStatusStopped.style.display = '';
                    if (containerStatusRunning) containerStatusRunning.style.display = 'none';
                }
            }

            // Update the containerRunning variable to reflect current state
            window.containerRunning = data.status === 'running';
        }
    }
});

window.socket.on('disconnect', function(reason) {
    console.log('Disconnected from WebSocket server:', reason);
    window.hasJoinedRoom = false;
});
