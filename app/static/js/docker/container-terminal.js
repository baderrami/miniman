/**
 * Container terminal functionality
 * 
 * @requires container-common.js - For socket, containerId, roomName, hasJoinedRoom
 */

document.addEventListener('DOMContentLoaded', function() {
    // Terminal Tab Elements
    const terminal = document.getElementById('terminal-instance');
    const connectTerminalBtn = document.getElementById('connect-terminal');
    const disconnectTerminalBtn = document.getElementById('disconnect-terminal');

    // Initialize xterm.js
    const term = new Terminal({
        cursorBlink: true,
        theme: {
            background: '#000000',
            foreground: '#ffffff'
        }
    });

    const fitAddon = new FitAddon.FitAddon();
    term.loadAddon(fitAddon);

    // Open terminal when tab is shown
    document.getElementById('terminal-tab').addEventListener('shown.bs.tab', function (e) {
        if (!term.element) {
            term.open(terminal);
            fitAddon.fit();
            term.writeln('Terminal ready. Click "Connect" to start an interactive session.');
        }
    });

    // Handle terminal input
    let commandBuffer = '';
    term.onData(function (data) {
        // If Enter key is pressed, send the command
        if (data === '\r') {
            term.writeln('');

            // Send the command to the server
            console.log('Sending command to server:', commandBuffer);
            console.log('Socket connected:', socket.connected);

            socket.emit('terminal_exec', {
                container_id: containerId,
                command: commandBuffer,
                room: roomName
            });

            console.log('Command sent');

            // Clear the command buffer
            commandBuffer = '';
        } 
        // Handle backspace
        else if (data === '\x7f') {
            if (commandBuffer.length > 0) {
                commandBuffer = commandBuffer.slice(0, -1);
                term.write('\b \b'); // Erase the character on screen
            }
        }
        // Handle other input
        else {
            commandBuffer += data;
            term.write(data);
        }
    });

    // Connect to terminal
    connectTerminalBtn.addEventListener('click', function() {
        console.log('Connecting to terminal...');
        console.log('Socket connected:', socket.connected);

        if (!hasJoinedRoom) {
            console.log('Not joined to room yet, joining now');
            socket.emit('join', { room: roomName });
            hasJoinedRoom = true;
        }

        term.clear();
        term.writeln('Connected to container ' + containerId);
        term.writeln('Type commands and press Enter to execute them.');
        term.writeln('');
        term.write('$ ');

        console.log('Terminal connected to container:', containerId);
        console.log('Socket connected:', socket.connected);
        console.log('Socket ID:', socket.id);

        connectTerminalBtn.disabled = true;
        disconnectTerminalBtn.disabled = false;
    });

    // Disconnect from terminal
    disconnectTerminalBtn.addEventListener('click', function() {
        term.writeln('');
        term.writeln('Disconnected from container.');
        term.writeln('Click "Connect" to start a new session.');

        connectTerminalBtn.disabled = false;
        disconnectTerminalBtn.disabled = true;
    });

    // Handle terminal output
    socket.on('terminal_output', function(data) {
        console.log('Received terminal output:', data);

        if (data.container_id === containerId) {
            if (data.error) {
                console.log('Terminal error:', data.error);
                term.writeln('\r\nError: ' + data.error);
            } else {
                console.log('Terminal output:', data.output);
                term.writeln('\r\n' + data.output);
            }
            term.write('$ ');
        } else {
            console.log('Received output for different container:', data.container_id);
        }
    });
});
