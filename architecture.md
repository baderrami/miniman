
# Full-Stack Flask Mini Manager Architecture Design

## System Overview

The proposed architecture for the full-stack Flask mini manager consists of two main components:

1. **WiFi Access Point Provisioning System**: Configures the device to function as a WiFi access point
2. **Flask Management Application**: Provides the web interface for network management and system operations

## Architecture Components

### 1. WiFi Access Point Provisioning

#### Hardware Requirements
- Ubuntu server with WiFi interface (e.g., wlan0)
- Secondary network interfaces for LAN connectivity (e.g., eth0, eth1)

#### Software Components
- **hostapd**: For creating and managing the WiFi access point
- **dnsmasq**: For DHCP and DNS services
- **iptables**: For network routing and firewall configuration
- **systemd**: For service management and startup configuration

#### Configuration Flow
1. Configure hostapd to create a WiFi access point on the WiFi interface
2. Set up dnsmasq to provide DHCP services to connected clients
3. Configure iptables for proper routing between interfaces
4. Create systemd services to ensure these services start on boot
5. Implement network isolation to protect the WiFi interface from management changes

### 2. Flask Management Application

#### Software Stack
- **Backend**:
    - Flask web framework
    - Flask-Login for authentication
    - SQLAlchemy for user database
    - Flask-WTF for form handling
    - Gunicorn as WSGI server
    - Nginx as reverse proxy

- **Frontend**:
    - HTML/CSS/JavaScript
    - Bootstrap for responsive design
    - AJAX for asynchronous requests

#### Application Components

1. **Authentication Module**
    - Login page
    - User management
    - Session handling
    - Security middleware

2. **Network Management Module**
    - Interface listing and status display
    - Configuration forms for LAN interfaces
    - Network diagnostics tools
    - Interface up/down controls
    - IP configuration management

3. **Command Execution Module**
    - Predefined bash command execution
    - Command output display
    - Execution history
    - Permission-based command restrictions

4. **System Reset Module**
    - OverlayFS management
    - System reset confirmation
    - Reset progress monitoring
    - Post-reset verification

#### Security Considerations
- HTTPS for all web traffic
- Rate limiting for login attempts
- Input validation for all form submissions
- Restricted bash command execution (whitelist approach)
- Privilege separation for system commands

## Implementation Plan

### 1. WiFi Access Point Setup

```bash
# Install required packages
apt-get update
apt-get install -y hostapd dnsmasq iptables-persistent

# Configure hostapd
cat > /etc/hostapd/hostapd.conf << EOF
interface=wlan0
driver=nl80211
ssid=DeviceManager
hw_mode=g
channel=7
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase=securepassword
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
EOF

# Configure dnsmasq
cat > /etc/dnsmasq.conf << EOF
interface=wlan0
dhcp-range=192.168.4.2,192.168.4.20,255.255.255.0,24h
domain=local
address=/device.local/192.168.4.1
EOF

# Configure network interfaces
cat > /etc/network/interfaces.d/wlan0 << EOF
auto wlan0
iface wlan0 inet static
    address 192.168.4.1
    netmask 255.255.255.0
EOF

# Enable IP forwarding
echo 1 > /proc/sys/net/ipv4/ip_forward

# Create systemd service for WiFi AP
cat > /etc/systemd/system/wifi-ap.service << EOF
[Unit]
Description=WiFi Access Point Service
After=network.target

[Service]
ExecStart=/usr/sbin/hostapd /etc/hostapd/hostapd.conf
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl enable wifi-ap.service
```

### 2. Flask Application Setup

```bash
# Install required packages
apt-get install -y python3-pip python3-venv nginx

# Create virtual environment
mkdir -p /opt/device-manager
cd /opt/device-manager
python3 -m venv venv
source venv/bin/activate

# Install Python packages
pip install flask flask-login flask-sqlalchemy flask-wtf gunicorn

# Create application structure
mkdir -p app/{static,templates,models,controllers}
```

### 3. OverlayFS Setup for System Reset

```bash
# Install required packages
apt-get install -y overlayfs-tools

# Configure overlayfs mount points
mkdir -p /mnt/{lower,upper,work,merged}

# Add to fstab for persistence
echo "overlay /mnt/merged overlay lowerdir=/mnt/lower,upperdir=/mnt/upper,workdir=/mnt/work 0 0" >> /etc/fstab

# Create reset script
cat > /usr/local/bin/system-reset << EOF
#!/bin/bash
rm -rf /mnt/upper/*
rm -rf /mnt/work/*
sync
reboot
EOF
chmod +x /usr/local/bin/system-reset
```

## Application Structure

```
/opt/device-manager/
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py
│   │   └── network.py
│   ├── controllers/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── network.py
│   │   ├── commands.py
│   │   └── system.py
│   ├── static/
│   │   ├── css/
│   │   ├── js/
│   │   └── img/
│   ├── templates/
│   │   ├── base.html
│   │   ├── login.html
│   │   ├── dashboard.html
│   │   ├── network.html
│   │   ├── commands.html
│   │   └── system.html
│   └── utils/
│       ├── __init__.py
│       ├── network_utils.py
│       ├── command_utils.py
│       └── system_utils.py
├── run.py
├── requirements.txt
└── gunicorn.conf.py
```

## Deployment Process

1. Set up the WiFi access point provisioning system
2. Install and configure the Flask application
3. Set up Nginx as a reverse proxy
4. Configure the OverlayFS system
5. Create systemd services for automatic startup
6. Implement security hardening
7. Test the complete system

## Security Considerations

- Regularly update all system packages
- Use strong passwords for WiFi and application access
- Implement proper input validation
- Restrict bash command execution to predefined commands only
- Use HTTPS for all web traffic
- Implement proper user authentication and authorization
- Regularly backup configuration

This architecture provides a comprehensive solution for managing Ubuntu servers with WiFi interfaces, allowing secure access and management through a web interface while maintaining the stability of the WiFi access point.