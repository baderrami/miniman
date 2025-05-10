```markdown
# Mini Manager Provisioning Manual

This manual provides comprehensive instructions for provisioning Linux servers as WiFi access points using the Mini Manager provisioning script.

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Installation](#installation)
4. [Script Functionality](#script-functionality)
5. [Customization Options](#customization-options)
6. [Troubleshooting](#troubleshooting)
7. [Post-Provisioning Steps](#post-provisioning-steps)
8. [Security Considerations](#security-considerations)
9. [Maintenance](#maintenance)

## Overview

The Mini Manager provisioning script (`provision_mini.sh`) automates the process of configuring a Linux server as a WiFi access point and deploying the Mini Manager application. This enables the server to function as a network management device with a web-based interface accessible through the WiFi network it creates.

Key features:
- Automatic WiFi access point configuration (SSID: miniman)
- DHCP server setup for connected clients
- Web-based management interface
- System reset functionality
- Network management capabilities

## Prerequisites

### Hardware Requirements

- Linux server (physical or virtual) with:
  - WiFi interface that supports AP mode
  - Minimum 1GB RAM
  - Minimum 8GB storage
  - Internet connection during setup (for package installation)

### Software Requirements

- Debian-based Linux distribution (Ubuntu, Raspberry Pi OS, etc.)
- Root access to the server
- Basic Linux command-line knowledge

### Required Packages

The script will automatically install these packages:
- hostapd
- dnsmasq
- iptables
- wireless-tools
- curl
- python3-pip
- python3-venv
- git
- nginx

## Installation

### 1. Download the Provisioning Script
```
bash
wget https://github.com/baderrami/miniman/raw/main/provision_mini.sh
```
Or copy the script to the server using SCP or another file transfer method.

### 2. Make the Script Executable
```
bash
chmod +x provision_mini.sh
```
### 3. Run the Script as Root
```
bash
sudo ./provision_mini.sh
```
### 4. Verify Installation

After the script completes, verify that:
- The WiFi access point is active and broadcasting with SSID "miniman"
- You can connect to the WiFi network using the password "123456789"
- The web interface is accessible at http://192.168.50.1

## Script Functionality

The provisioning script performs the following tasks:

### System Preparation
- Updates system packages
- Installs required packages (hostapd, dnsmasq, iptables, etc.)
- Sets up custom iptables persistence

### WiFi Access Point Setup
- Configures hostapd (WiFi access point daemon)
- Sets up SSID "miniman" and password "123456789"
- Configures the WiFi interface (wlan0) with a static IP (192.168.50.1/24)

### Network Services
- Configures dnsmasq for DHCP (range 192.168.50.10-100) and DNS services
- Enables IP forwarding for routing
- Sets up iptables rules to redirect HTTP traffic to the application port
- Handles systemd-resolved conflicts to ensure dnsmasq works properly

### Application Deployment
- Creates application directory at /opt/miniman
- Clones the Mini Manager repository (if provided)
- Sets up a Python virtual environment
- Installs required Python dependencies
- Initializes the application database
- Creates a systemd service for the application

### Web Server Configuration
- Configures Nginx as a reverse proxy
- Creates a systemd service for the application
- Sets appropriate permissions for web server access

### System Reset Functionality
- Creates a reset script at /usr/local/bin/system-reset

## Customization Options

### Configuration Variables

The script uses the following configuration variables that can be modified at the top of the script:
```
bash
SSID="miniman"
PASSPHRASE="123456789"
STATIC_IP="192.168.50.1/24"
HTTP_PORT=8000
APP_DIR="/opt/miniman"
GIT_REPO="https://github.com/baderrami/miniman.git"
```
### WiFi Configuration

To modify the WiFi settings:
1. Edit the script and change the `SSID` and `PASSPHRASE` variables
2. Run the script again

Alternatively, after installation:
1. Edit the hostapd configuration: `/etc/hostapd/hostapd.conf`
2. Restart hostapd: `sudo systemctl restart hostapd`

### Network Configuration

To modify the network settings:
1. Edit the script and change the `STATIC_IP` variable
2. Run the script again

Alternatively, after installation:
1. Edit the systemd-networkd configuration: `/etc/systemd/network/10-wlan0.network`
2. Edit the dnsmasq configuration: `/etc/dnsmasq.conf`
3. Restart services: `sudo systemctl restart systemd-networkd dnsmasq`

### Application Customization

To customize the application:
1. Edit the script and change the `APP_DIR` and `GIT_REPO` variables
2. Run the script again

## Troubleshooting

### WiFi Access Point Issues

If the WiFi access point is not working:

1. Check hostapd status:
   ```bash
   sudo systemctl status hostapd
   ```

2. View hostapd logs:
   ```bash
   sudo journalctl -u hostapd
   ```

3. Verify the WiFi interface is up:
   ```bash
   ip link show dev wlan0
   ```

4. Check hostapd configuration:
   ```bash
   sudo cat /etc/hostapd/hostapd.conf
   ```

### Network Issues

If clients cannot connect to the network:

1. Check dnsmasq status:
   ```bash
   sudo systemctl status dnsmasq
   ```

2. Verify IP configuration:
   ```bash
   ip addr show dev wlan0
   ```

3. Check if DHCP is working:
   ```bash
   sudo journalctl -u dnsmasq
   ```

#### Fixing dnsmasq Service Failures

If dnsmasq fails to start:

1. Check for port conflicts (dnsmasq uses port 53):
   ```bash
   sudo lsof -i :53
   ```

2. If systemd-resolved is using port 53, stop and disable it:
   ```bash
   sudo systemctl stop systemd-resolved
   sudo systemctl disable systemd-resolved
   ```

3. Fix resolv.conf if it's a symlink to systemd-resolved:
   ```bash
   sudo rm /etc/resolv.conf
   echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf
   echo "nameserver 8.8.4.4" | sudo tee -a /etc/resolv.conf
   ```

4. Restart dnsmasq:
   ```bash
   sudo systemctl restart dnsmasq
   ```

### Web Interface Issues

If the web interface is not accessible:

1. Check the application service status:
   ```bash
   sudo systemctl status miniman
   ```

2. Check application logs:
   ```bash
   sudo journalctl -u miniman
   ```

3. Verify Nginx configuration:
   ```bash
   sudo nginx -t
   sudo systemctl status nginx
   ```

### Rerunning the Script

The script is designed to be idempotent and can be run multiple times. When rerun, it will:

1. Detect existing configurations and update them as needed
2. Handle application directory with options to skip, backup and replace, or pull updates
3. Restart services to apply any new configurations

## Post-Provisioning Steps

After successful provisioning, complete these important steps:

### 1. Change Default Credentials

1. Connect to the WiFi network "miniman" with password "123456789"
2. Access the web interface at http://192.168.50.1
3. Log in with default credentials (admin/admin)
4. Change the default admin password

### 2. Configure Network Interfaces

If needed, configure additional network interfaces through the web interface.

### 3. Backup Configuration

Backup your configuration after initial setup:
```
bash
sudo cp /etc/hostapd/hostapd.conf /etc/hostapd/hostapd.conf.backup
sudo cp /etc/dnsmasq.conf /etc/dnsmasq.conf.backup
sudo cp /etc/systemd/network/10-wlan0.network /etc/systemd/network/10-wlan0.network.backup
```
## Security Considerations

### WiFi Security

- Change the default WiFi password to a strong, unique password
- Consider changing the default SSID
- For higher security, modify hostapd.conf to use stronger encryption settings

### Application Security

- Change the default admin password immediately
- Regularly update the system with security patches
- Consider enabling HTTPS for the web interface

### Network Security

- Restrict SSH access to trusted IP addresses
- Configure the firewall to allow only necessary services
- Regularly review system logs for suspicious activity

## Maintenance

### Regular Updates

Keep your system up to date:
```
bash
sudo apt update
sudo apt upgrade -y
```
### Monitoring

Monitor system health and performance:
```
bash
# Check system status
sudo systemctl status hostapd dnsmasq nginx miniman

# View logs
sudo journalctl -u hostapd
sudo journalctl -u dnsmasq
sudo journalctl -u miniman
```
### System Reset

If needed, you can reset the system to its initial state:
```
bash
sudo /usr/local/bin/system-reset
```
This will:
1. Stop all services
2. Remove configuration files
3. Reset the application database
4. Reboot the system

---

For additional support or to report issues, please visit the GitHub repository at https://github.com/baderrami/miniman.
```
