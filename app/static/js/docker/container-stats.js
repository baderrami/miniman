/**
 * Container stats functionality
 * 
 * @requires container-common.js - For socket, containerId, roomName, hasJoinedRoom, containerRunning
 */

document.addEventListener('DOMContentLoaded', function() {
    // Stats Tab Elements
    const toggleStatsBtn = document.getElementById('toggle-stats');
    const statsIntervalSelect = document.getElementById('stats-interval');

    // Chart elements
    const cpuChart = document.getElementById('cpu-chart');
    const memoryChart = document.getElementById('memory-chart');
    const networkChart = document.getElementById('network-chart');
    const diskChart = document.getElementById('disk-chart');

    // Current stats elements
    const cpuCurrent = document.getElementById('cpu-current');
    const memoryCurrent = document.getElementById('memory-current');
    const networkCurrent = document.getElementById('network-current');
    const diskCurrent = document.getElementById('disk-current');

    let isMonitoring = false;
    let statsInterval = 2000; // Default to 2 seconds
    let statsIntervalId = null;

    // Initialize charts
    const charts = {
        cpu: new Chart(cpuChart, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'CPU Usage',
                    data: [],
                    borderColor: 'rgb(75, 192, 192)',
                    tension: 0.1,
                    fill: false
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        title: {
                            display: true,
                            text: 'Percentage'
                        }
                    }
                }
            }
        }),
        memory: new Chart(memoryChart, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Memory Usage',
                    data: [],
                    borderColor: 'rgb(153, 102, 255)',
                    tension: 0.1,
                    fill: false
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Usage'
                        }
                    }
                }
            }
        }),
        network: new Chart(networkChart, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Network In',
                    data: [],
                    borderColor: 'rgb(54, 162, 235)',
                    tension: 0.1,
                    fill: false
                }, {
                    label: 'Network Out',
                    data: [],
                    borderColor: 'rgb(255, 99, 132)',
                    tension: 0.1,
                    fill: false
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Bytes'
                        }
                    }
                }
            }
        }),
        disk: new Chart(diskChart, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Disk Read',
                    data: [],
                    borderColor: 'rgb(255, 159, 64)',
                    tension: 0.1,
                    fill: false
                }, {
                    label: 'Disk Write',
                    data: [],
                    borderColor: 'rgb(255, 205, 86)',
                    tension: 0.1,
                    fill: false
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Bytes'
                        }
                    }
                }
            }
        })
    };

    // Parse CPU percentage
    function parseCPUPercentage(cpuStr) {
        return parseFloat(cpuStr.replace('%', ''));
    }

    // Parse memory usage
    function parseMemoryUsage(memStr) {
        // Example: "1.5MiB / 8GiB"
        const parts = memStr.split('/');
        if (parts.length !== 2) return 0;

        const used = parts[0].trim();
        return used;
    }

    // Parse network I/O
    function parseNetworkIO(netStr) {
        // Example: "5.2kB / 3.4kB"
        const parts = netStr.split('/');
        if (parts.length !== 2) return [0, 0];

        const inBytes = parts[0].trim();
        const outBytes = parts[1].trim();
        return [inBytes, outBytes];
    }

    // Parse block I/O
    function parseBlockIO(blockStr) {
        // Example: "4.2MB / 2.1MB"
        const parts = blockStr.split('/');
        if (parts.length !== 2) return [0, 0];

        const readBytes = parts[0].trim();
        const writeBytes = parts[1].trim();
        return [readBytes, writeBytes];
    }

    // Update charts with new data
    function updateCharts(stats) {
        const timestamp = new Date().toLocaleTimeString();

        // Update CPU chart
        const cpuPercentage = parseCPUPercentage(stats.CPUPerc);
        charts.cpu.data.labels.push(timestamp);
        charts.cpu.data.datasets[0].data.push(cpuPercentage);
        if (charts.cpu.data.labels.length > 10) {
            charts.cpu.data.labels.shift();
            charts.cpu.data.datasets[0].data.shift();
        }
        charts.cpu.update();
        cpuCurrent.textContent = stats.CPUPerc;

        // Update Memory chart
        const memoryUsage = parseMemoryUsage(stats.MemUsage);
        charts.memory.data.labels.push(timestamp);
        charts.memory.data.datasets[0].data.push(memoryUsage);
        if (charts.memory.data.labels.length > 10) {
            charts.memory.data.labels.shift();
            charts.memory.data.datasets[0].data.shift();
        }
        charts.memory.update();
        memoryCurrent.textContent = stats.MemUsage;

        // Update Network chart
        const [netIn, netOut] = parseNetworkIO(stats.NetIO);
        charts.network.data.labels.push(timestamp);
        charts.network.data.datasets[0].data.push(netIn);
        charts.network.data.datasets[1].data.push(netOut);
        if (charts.network.data.labels.length > 10) {
            charts.network.data.labels.shift();
            charts.network.data.datasets[0].data.shift();
            charts.network.data.datasets[1].data.shift();
        }
        charts.network.update();
        networkCurrent.textContent = stats.NetIO;

        // Update Disk chart
        const [diskRead, diskWrite] = parseBlockIO(stats.BlockIO);
        charts.disk.data.labels.push(timestamp);
        charts.disk.data.datasets[0].data.push(diskRead);
        charts.disk.data.datasets[1].data.push(diskWrite);
        if (charts.disk.data.labels.length > 10) {
            charts.disk.data.labels.shift();
            charts.disk.data.datasets[0].data.shift();
            charts.disk.data.datasets[1].data.shift();
        }
        charts.disk.update();
        diskCurrent.textContent = stats.BlockIO;
    }

    // Start monitoring stats
    function startMonitoring() {
        if (!hasJoinedRoom) {
            socket.emit('join', { room: roomName });
            hasJoinedRoom = true;
        }

        // Get the selected interval
        statsInterval = parseInt(statsIntervalSelect.value);

        // Request stats from server
        socket.emit('stream_container_stats', {
            container_id: containerId,
            interval: statsInterval,
            room: roomName
        });

        isMonitoring = true;
        toggleStatsBtn.textContent = 'Stop Monitoring';
        toggleStatsBtn.classList.remove('btn-primary');
        toggleStatsBtn.classList.add('btn-danger');
        statsIntervalSelect.disabled = true;
    }

    // Stop monitoring stats
    function stopMonitoring() {
        socket.emit('leave', { room: roomName });

        isMonitoring = false;
        toggleStatsBtn.textContent = 'Start Monitoring';
        toggleStatsBtn.classList.remove('btn-danger');
        toggleStatsBtn.classList.add('btn-primary');
        statsIntervalSelect.disabled = false;
    }

    // Toggle stats monitoring
    toggleStatsBtn.addEventListener('click', function() {
        if (isMonitoring) {
            stopMonitoring();
        } else {
            startMonitoring();
        }
    });

    // Handle stats interval change
    statsIntervalSelect.addEventListener('change', function() {
        statsInterval = parseInt(this.value);

        // If monitoring is active, restart it with the new interval
        if (isMonitoring) {
            stopMonitoring();
            startMonitoring();
        }
    });

    // Open stats tab
    document.getElementById('stats-tab').addEventListener('shown.bs.tab', function (e) {
        // Resize charts to fit container
        Object.values(charts).forEach(chart => chart.resize());

        // Start monitoring if not already monitoring
        if (!isMonitoring && containerRunning) {
            startMonitoring();
        }
    });

    // Handle stats updates
    socket.on('container_stats', function(data) {
        if (data.container_id === containerId) {
            updateCharts(data.stats);
        }
    });

    // Handle stats completion
    socket.on('container_stats_complete', function(data) {
        if (data.container_id === containerId) {
            if (!data.success) {
                console.error('Stats streaming error:', data.error);
            }

            // Reset the monitoring state
            isMonitoring = false;
            toggleStatsBtn.textContent = 'Start Monitoring';
            toggleStatsBtn.classList.remove('btn-danger');
            toggleStatsBtn.classList.add('btn-primary');
            statsIntervalSelect.disabled = false;
        }
    });
});
