# Mini Manager Provisioning Manual

This manual provides comprehensive instructions for provisioning Ubuntu servers as WiFi access points using the Mini Manager provisioning script.

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

The Mini Manager provisioning script (`provision.sh`) automates the process of configuring an Ubuntu server as a WiFi access point and deploying the Mini Manager application. This enables the server to function as a network management device with a web-based interface accessible through the WiFi network it creates.

Key features:
- Automatic WiFi access point configuration
- DHCP server setup for connected clients
- Web-based management interface
- System reset functionality
- Network management capabilities

## Prerequisites

### Hardware Requirements

- Ubuntu server (physical or virtual) with:
  - WiFi interface that supports AP mode
  - Minimum 1GB RAM
  - Minimum 8GB storage
  - Internet connection during setup (for package installation)

### Software Requirements

- Ubuntu Server 20.04 LTS or newer
- Root access to the server
- Basic Linux command-line knowledge

### Required Packages

The script will automatically install these packages:
- hostapd
- dnsmasq
- iptables-persistent
- python3-pip
- python3-venv
- nginx
- git

## Installation

### 1. Download the Provisioning Script

```bash
wget https://raw.githubusercontent.com/yourusername/miniman/main/provision.sh
```

Or copy the script to the server using SCP or another file transfer method.

### 2. Make the Script Executable

```bash
chmod +x provision.sh
```

### 3. Run the Script as Root

```bash
sudo ./provision.sh
```

### 4. Follow the Interactive Prompts

The script will guide you through the setup process with interactive prompts:
- Select the WiFi interface to use for the access point
- Set the WiFi SSID (default: DeviceManager)
- Set the WiFi password (default: securepassword)
- Provide the Git repository URL for the application (optional)

### 5. Verify Installation

After the script completes, verify that:
- The WiFi access point is active and broadcasting
- You can connect to the WiFi network using the credentials you provided
- The web interface is accessible at http://device.local or http://192.168.4.1

### 6. Rerunning the Script

The provisioning script is designed to be idempotent, meaning it can be run multiple times without breaking the device or duplicating configurations. When rerun, the script will:

1. Check if components are already installed and skip installation steps if appropriate
2. Detect existing configurations and update them as needed
3. Restart services to apply any new configurations
4. Handle errors gracefully and provide helpful diagnostic information

#### Application Directory Handling

If you run the script again, it will detect if the application directory already exists and provide options:

```
[WARNING] Directory /opt/device-manager already exists and is not empty.
What would you like to do? [s]kip, [b]ackup and replace, [p]ull updates if it's a git repo:
```

Choose one of the following options:
- **s (skip)**: Skip the repository cloning step (default). Use this if you've made custom changes you want to keep.
- **b (backup and replace)**: Backup the existing directory to `/opt/device-manager-backup-[timestamp]` and clone a fresh copy.
- **p (pull updates)**: If the directory is a git repository, pull the latest changes. If the pull fails due to local changes, you'll be asked if you want to force update (which will discard local changes).

If the directory is not a git repository and you choose the pull option, you'll be asked if you want to backup and replace it instead.

#### Service Handling

When rerunning the script, it will check if services are already running:
- If a service is already running, it will be restarted to apply any new configurations
- If a service fails to start, the script will provide diagnostic information and continue with other services
- For dnsmasq specifically, the script will check for port conflicts and attempt to resolve them automatically

#### Configuration Files

The script handles existing configuration files in the following ways:
- Creates backups of original configuration files before modifying them
- Sets appropriate permissions for sensitive files like netplan configurations
- Updates configurations as needed while preserving custom settings where possible

## Script Functionality

The provisioning script performs the following tasks:

### System Preparation
- Checks if running as root
- Verifies Ubuntu version compatibility
- Detects available WiFi interfaces
- Updates system packages

### WiFi Access Point Setup
- Installs and configures hostapd (WiFi access point daemon)
- Sets up SSID and password for the WiFi network
- Configures the WiFi interface with a static IP (192.168.4.1)

### Network Services
- Configures dnsmasq for DHCP and DNS services
- Enables IP forwarding for routing between interfaces
- Sets up iptables rules for NAT (Network Address Translation)
- Creates a systemd service for the WiFi access point

### System Reset Functionality
- Configures OverlayFS for system reset capability
- Creates a reset script at /usr/local/bin/system-reset

### Application Deployment
- Installs the Mini Manager Flask application (if repository URL provided)
- Sets up a Python virtual environment
- Installs required Python dependencies
- Initializes the application database

### Web Server Configuration
- Configures Nginx as a reverse proxy
- Creates a systemd service for the application
- Sets appropriate permissions for web server access

## Customization Options

### WiFi Configuration

You can customize the WiFi settings during the interactive setup:
- SSID: The name of the WiFi network (default: DeviceManager)
- Password: The WiFi password (default: securepassword)
- Channel: Can be modified in the hostapd configuration file after installation

### Network Configuration

The default network configuration uses:
- IP address: 192.168.4.1
- DHCP range: 192.168.4.2 to 192.168.4.20

To modify these settings after installation:
1. Edit the dnsmasq configuration: `/etc/dnsmasq.conf`
2. Edit the netplan configuration: `/etc/netplan/60-wifi-ap.yaml`
3. Apply changes: `sudo netplan apply`
4. Restart services: `sudo systemctl restart dnsmasq hostapd`

### Application Customization

To customize the application after installation:
1. Navigate to the application directory: `cd /opt/device-manager`
2. Modify the configuration files as needed
3. Restart the application: `sudo systemctl restart device-manager`

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
   ip link show dev <wifi_interface>
   ```

4. Check if the WiFi interface supports AP mode:
   ```bash
   iw list | grep "Supported interface modes" -A 10
   ```

### Network Issues

If clients cannot connect to the network:

1. Check dnsmasq status:
   ```bash
   sudo systemctl status dnsmasq
   ```

2. Verify IP configuration:
   ```bash
   ip addr show dev <wifi_interface>
   ```

3. Check if DHCP is working:
   ```bash
   sudo journalctl -u dnsmasq
   ```

#### Fixing dnsmasq Service Failures

If dnsmasq fails to start with an error like "Job for dnsmasq.service failed because the control process exited with error code":

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

4. Check dnsmasq configuration for errors:
   ```bash
   sudo dnsmasq --test
   ```

5. Check dnsmasq status for specific error messages:
   ```bash
   sudo systemctl status dnsmasq
   ```

6. Try starting dnsmasq again:
   ```bash
   sudo systemctl start dnsmasq
   ```

7. If the issue persists, try restarting the system and running the script again. The script has been enhanced to handle cases where services are already running or fail to start.

#### Fixing Netplan Configuration Permissions

If you see a warning like "Permissions for /etc/netplan/60-wifi-ap.yaml are too open. Netplan configuration should NOT be accessible by others":

1. Fix the permissions for the netplan configuration file:
   ```bash
   sudo chmod 600 /etc/netplan/60-wifi-ap.yaml
   ```

2. Apply the netplan configuration:
   ```bash
   sudo netplan apply
   ```

The latest version of the provisioning script automatically sets the correct permissions for the netplan configuration file.

### Web Interface Issues

If the web interface is not accessible:

1. Check the application service status:
   ```bash
   sudo systemctl status device-manager
   ```

2. Verify Nginx configuration:
   ```bash
   sudo nginx -t
   sudo systemctl status nginx
   ```

3. Check application logs:
   ```bash
   sudo journalctl -u device-manager
   ```

### Common Error Messages

1. "No WiFi interfaces found":
   - Ensure your server has a WiFi interface
   - Check if the WiFi drivers are properly installed

2. "hostapd.service failed to start":
   - Verify the WiFi interface supports AP mode
   - Check for conflicting services using the WiFi interface

3. "Cannot bind to address 192.168.4.1":
   - Another service might be using this IP address
   - Check for IP conflicts with `ip addr show`

## Post-Provisioning Steps

After successful provisioning, complete these important steps:

### 1. Change Default Credentials

1. Connect to the WiFi network
2. Access the web interface at http://device.local or http://192.168.4.1
3. Log in with default credentials (admin/admin)
4. Navigate to the Users section
5. Change the default admin password

### 2. Configure Network Interfaces

1. In the web interface, go to the Network section
2. Configure additional network interfaces as needed
3. Set up internet sharing if required

### 3. Backup Configuration

It's recommended to backup your configuration after initial setup:

```bash
sudo cp /etc/hostapd/hostapd.conf /etc/hostapd/hostapd.conf.backup
sudo cp /etc/dnsmasq.conf /etc/dnsmasq.conf.backup
sudo cp /etc/netplan/60-wifi-ap.yaml /etc/netplan/60-wifi-ap.yaml.backup
```

### 4. Test System Reset Functionality

To verify the system reset functionality works correctly:
1. Make some configuration changes
2. Run the reset script: `sudo /usr/local/bin/system-reset`
3. After reboot, verify the system returns to its initial state

## Security Considerations

### WiFi Security

- Change the default WiFi password to a strong, unique password
- Consider changing the default SSID
- For higher security, modify hostapd.conf to use WPA2-Enterprise

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

```bash
sudo apt update
sudo apt upgrade -y
```

### Monitoring

Monitor system health and performance:

```bash
# Check system status
sudo systemctl status hostapd dnsmasq nginx device-manager

# View logs
sudo journalctl -u hostapd
sudo journalctl -u dnsmasq
sudo journalctl -u device-manager
```

### Backup and Recovery

Regularly backup important configuration files:

```bash
# Create a backup directory
sudo mkdir -p /opt/backups/$(date +%Y%m%d)

# Backup configuration files
sudo cp -r /etc/hostapd /etc/dnsmasq.conf /etc/netplan /opt/device-manager /opt/backups/$(date +%Y%m%d)/
```

To restore from backup:

```bash
# Restore configuration files
sudo cp -r /opt/backups/YYYYMMDD/hostapd /etc/
sudo cp /opt/backups/YYYYMMDD/dnsmasq.conf /etc/
sudo cp -r /opt/backups/YYYYMMDD/netplan /etc/
```

---

For additional support or to report issues, please visit the project repository or contact the system administrator.
