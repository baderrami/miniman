/**
 * Container file browser functionality
 * 
 * @requires container-common.js - For socket, containerId, roomName, hasJoinedRoom
 */

document.addEventListener('DOMContentLoaded', function() {
    // File Browser Tab Elements
    const fileBrowser = document.getElementById('file-browser');
    const fileContent = document.getElementById('file-content');
    const currentPath = document.getElementById('current-path');
    const currentFile = document.getElementById('current-file');
    const refreshFilesBtn = document.getElementById('refresh-files');
    const goUpBtn = document.getElementById('go-up');

    let currentDir = '/';

    // Refresh file list
    function refreshFiles() {
        if (!hasJoinedRoom) {
            socket.emit('join', { room: roomName });
            hasJoinedRoom = true;
        }

        // Clear the file browser
        fileBrowser.innerHTML = '<div class="alert alert-info m-3">Loading files...</div>';

        // Update the current path display
        currentPath.textContent = currentDir;

        // Request file list from server
        socket.emit('list_files', {
            container_id: containerId,
            path: currentDir,
            room: roomName
        });
    }

    // Navigate to a directory
    function navigateToDir(dir) {
        // If dir starts with /, it's an absolute path
        if (dir.startsWith('/')) {
            currentDir = dir;
        } 
        // If it's .., go up one level
        else if (dir === '..') {
            // Split the path by / and remove the last part
            const parts = currentDir.split('/').filter(p => p);
            parts.pop();
            currentDir = '/' + parts.join('/');
        }
        // Otherwise, it's a relative path
        else {
            // Make sure currentDir ends with /
            if (!currentDir.endsWith('/')) {
                currentDir += '/';
            }
            currentDir += dir;
        }

        // Make sure currentDir starts with /
        if (!currentDir.startsWith('/')) {
            currentDir = '/' + currentDir;
        }

        // Refresh the file list
        refreshFiles();
    }

    // View file content
    function viewFile(file) {
        // Make sure currentDir ends with /
        let filePath = currentDir;
        if (!filePath.endsWith('/')) {
            filePath += '/';
        }
        filePath += file;

        // Update the current file display
        currentFile.textContent = file;

        // Clear the file content
        fileContent.innerHTML = '<div class="alert alert-info">Loading file content...</div>';

        // Request file content from server
        socket.emit('read_file', {
            container_id: containerId,
            file_path: filePath,
            room: roomName
        });
    }

    // Refresh files button
    refreshFilesBtn.addEventListener('click', refreshFiles);

    // Go up button
    goUpBtn.addEventListener('click', function() {
        navigateToDir('..');
    });

    // Open file browser when tab is shown
    document.getElementById('files-tab').addEventListener('shown.bs.tab', function (e) {
        refreshFiles();
    });

    // Handle file list response
    socket.on('file_list', function(data) {
        if (data.container_id === containerId) {
            // Clear the file browser
            fileBrowser.innerHTML = '';

            if (!data.success) {
                fileBrowser.innerHTML = `<div class="alert alert-danger m-3">Error: ${data.error || 'Unknown error'}</div>`;
                return;
            }

            if (!data.files || data.files.length === 0) {
                fileBrowser.innerHTML = '<div class="alert alert-info m-3">No files found in this directory.</div>';
                return;
            }

            // Add .. (parent directory) if not at root
            if (currentDir !== '/') {
                const parentItem = document.createElement('a');
                parentItem.className = 'list-group-item dir-item';
                parentItem.innerHTML = '<i class="fas fa-folder"></i> ..';
                parentItem.addEventListener('click', function() {
                    navigateToDir('..');
                });
                fileBrowser.appendChild(parentItem);
            }

            // Add directories first
            data.files.filter(f => f.is_dir).forEach(function(file) {
                const fileItem = document.createElement('a');
                fileItem.className = 'list-group-item dir-item';
                fileItem.innerHTML = `<i class="fas fa-folder"></i> ${file.name}`;
                fileItem.addEventListener('click', function() {
                    navigateToDir(file.name);
                });
                fileBrowser.appendChild(fileItem);
            });

            // Then add files
            data.files.filter(f => !f.is_dir).forEach(function(file) {
                const fileItem = document.createElement('a');
                fileItem.className = 'list-group-item file-item';
                fileItem.innerHTML = `<i class="fas fa-file"></i> ${file.name} <span class="text-muted">(${file.size})</span>`;
                fileItem.addEventListener('click', function() {
                    viewFile(file.name);
                });
                fileBrowser.appendChild(fileItem);
            });
        }
    });

    // Handle file content response
    socket.on('file_content', function(data) {
        if (data.container_id === containerId) {
            if (!data.success) {
                fileContent.innerHTML = `<div class="alert alert-danger">Error: ${data.error || 'Unknown error'}</div>`;
                return;
            }

            // Display the file content
            fileContent.innerHTML = '';
            const pre = document.createElement('pre');
            pre.textContent = data.content;
            fileContent.appendChild(pre);
        }
    });
});
