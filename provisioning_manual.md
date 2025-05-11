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
The Mini Manager provisioning script () automates the process of configuring a Linux server as a WiFi access point and deploying the Mini Manager application. This enables the server to function as a network management device with a web-based interface accessible through the WiFi network it creates. `provisioning_script.sh`
Key features:
- Automatic WiFi access point configuration (SSID: miniman)
- DHCP server setup for connected clients
- Web-based management interface
- System reset functionality
- Network management capabilities
- Offline-ready with local static resources

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
``` bash
wget https://github.com/baderrami/miniman/raw/main/provisioning_script.sh
```
Or copy the script to the server using SCP or another file transfer method.
### 2. Make the Script Executable
``` bash
chmod +x provisioning_script.sh
```
### 3. Run the Script as Root
``` bash
sudo ./provisioning_script.sh
```
### 4. Verify Installation
After the script completes, verify that:
- The WiFi access point is active and broadcasting with SSID "miniman"
- You can connect to the WiFi network using the password "123456789"
- The web interface is accessible at [http://192.168.50.1](http://192.168.50.1) or [http://mini.man](http://mini.man)

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
- Sets appropriate link parameters including disabling WakeOnLan

### Network Services
- Configures dnsmasq for DHCP (range 192.168.50.10-100) and DNS services
- Enables IP forwarding for routing
- Sets up iptables rules to redirect HTTP traffic to the application port
- Handles systemd-resolved conflicts to ensure dnsmasq works properly
- Configures DNS to use Google's DNS servers (8.8.8.8, 8.8.4.4)

### Application Deployment
- Creates application directory at /opt/miniman
- Clones the Mini Manager repository (if provided)
- Sets up a Python virtual environment
- Installs required Python dependencies
- Downloads and configures required static resources (Bootstrap, Chart.js, icons)
- Initializes the application database
- Creates a systemd service for the application

### Web Server Configuration
- Configures Nginx as a reverse proxy
- Sets up timeouts for slow connections
- Configures caching for static resources
- Sets appropriate permissions for web server access
- Removes default nginx configuration to prevent conflicts

### System Reset Functionality
- Creates a reset script at /usr/local/bin/system-reset
- Provides functionality to restore the system to factory defaults

## Customization Options
### Configuration Variables
The script uses the following configuration variables that can be modified at the top of the script:
``` bash
SSID="miniman"
PASSPHRASE="123456789"
STATIC_IP="192.168.50.1/24"
HTTP_PORT=8000
APP_DIR="/opt/miniman"
GIT_REPO="https://github.com/baderrami/miniman.git"  # Set to empty to skip Git clone
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

### Custom Domain Configuration
The Mini Manager is configured with a custom domain name `mini.man` that resolves to the device's IP address (192.168.50.1). This allows users to access the web interface by typing `http://mini.man` in their browser instead of the IP address.

This is implemented through:
1. A DNS entry in dnsmasq configuration: `address=/mini.man/192.168.50.1`
2. The Nginx server configuration includes `mini.man` in the `server_name` directive

To modify or add additional custom domains:
1. Edit the dnsmasq configuration: `/etc/dnsmasq.conf`
2. Add a line in the format: `address=/your.domain/192.168.50.1`
3. Edit the Nginx configuration: `/etc/nginx/sites-available/miniman`
4. Add your domain to the `server_name` directive
5. Restart services: `sudo systemctl restart dnsmasq nginx`

### Application Customization
To customize the application:
1. Edit the script and change the `APP_DIR` and `GIT_REPO` variables
2. Run the script again

When the script detects an existing application directory, it provides options to:
- Skip repository update
- Backup the existing directory and replace it
- Pull the latest updates if it's a git repository

## Troubleshooting
### WiFi Access Point Issues
If the WiFi access point is not working:
1. Check hostapd status:
``` bash
   sudo systemctl status hostapd
```
1. View hostapd logs:
``` bash
   sudo journalctl -u hostapd
```
1. Verify the WiFi interface is up:
``` bash
   ip link show dev wlan0
```
1. Check hostapd configuration:
``` bash
   sudo cat /etc/hostapd/hostapd.conf
```
### Network Issues
If clients cannot connect to the network:
1. Check dnsmasq status:
``` bash
   sudo systemctl status dnsmasq
```
1. Verify IP configuration:
``` bash
   ip addr show dev wlan0
```
1. Check if DHCP is working:
``` bash
   sudo journalctl -u dnsmasq
```
#### Fixing dnsmasq Service Failures
If dnsmasq fails to start:
1. Check for port conflicts (dnsmasq uses port 53):
``` bash
   sudo lsof -i :53
```
1. If systemd-resolved is using port 53, stop and disable it:
``` bash
   sudo systemctl stop systemd-resolved
   sudo systemctl disable systemd-resolved
```
1. Fix resolv.conf if it's a symlink to systemd-resolved:
``` bash
   sudo rm /etc/resolv.conf
   echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf
   echo "nameserver 8.8.4.4" | sudo tee -a /etc/resolv.conf
```
1. Restart dnsmasq:
``` bash
   sudo systemctl restart dnsmasq
```
1. If port 53 is still in use, the script includes an emergency process termination:
``` bash
   sudo lsof -i :53 | awk 'NR>1 {print $2}' | xargs -r kill -9
```
### Web Interface Issues
If the web interface is not accessible:
1. Check the application service status:
``` bash
   sudo systemctl status miniman
```
1. Check application logs:
``` bash
   sudo journalctl -u miniman
```
1. Verify Nginx configuration:
``` bash
   sudo nginx -t
   sudo systemctl status nginx
```
1. Check runtime directory permissions:
``` bash
   ls -la /var/run/miniman
```
1. Verify gunicorn is installed in the virtual environment:
``` bash
   sudo /opt/miniman/venv/bin/pip list | grep gunicorn
```
### Fixing Runtime Directory Issues
If the miniman service fails due to runtime directory issues:
1. Create a systemd tempfiles configuration:
``` bash
   echo 'd /var/run/miniman 0755 www-data www-data -' | sudo tee /etc/tmpfiles.d/miniman.conf
```
1. Apply the configuration:
``` bash
   sudo systemd-tmpfiles --create
```
1. Restart the service:
``` bash
   sudo systemctl restart miniman
```
### Rerunning the Script
The script is designed to be idempotent and can be run multiple times. When rerun, it will:
1. Detect existing configurations and update them as needed
2. Handle application directory with options to skip, backup and replace, or pull updates
3. Verify all required static files and download missing ones
4. Restart services to apply any new configurations

## Post-Provisioning Steps
After successful provisioning, complete these important steps:
### 1. Change Default Credentials
1. Connect to the WiFi network "miniman" with password "123456789"
2. Access the web interface at [http://192.168.50.1](http://192.168.50.1) or [http://mini.man](http://mini.man)
3. Log in with default credentials (admin/admin)
4. Change the default admin password immediately

### 2. Configure Network Interfaces
If needed, configure additional network interfaces through the web interface.
### 3. Backup Configuration
Backup your configuration after initial setup:
``` bash
sudo cp /etc/hostapd/hostapd.conf /etc/hostapd/hostapd.conf.backup
sudo cp /etc/dnsmasq.conf /etc/dnsmasq.conf.backup
sudo cp /etc/systemd/network/10-wlan0.network /etc/systemd/network/10-wlan0.network.backup
```
### 4. Verify Offline Operation
Test that the interface works properly without internet connectivity:
1. Disconnect the device from the internet
2. Restart the device
3. Connect to the WiFi network
4. Verify all web interface features function correctly

## Security Considerations
### WiFi Security
- Change the default WiFi password to a strong, unique password
- Consider changing the default SSID
- For higher security, modify hostapd.conf to use stronger encryption settings

### Application Security
- Change the default admin password immediately
- Regularly update the system with security patches
- Consider enabling HTTPS for the web interface by configuring Nginx with SSL certificates

### Network Security
- Restrict SSH access to trusted IP addresses
- Configure the firewall to allow only necessary services
- Regularly review system logs for suspicious activity
- Consider implementing MAC address filtering in hostapd.conf for additional security

## Maintenance
### Regular Updates
Keep your system up to date:
``` bash
sudo apt update
sudo apt upgrade -y
```
To update the Mini Manager application:
``` bash
cd /opt/miniman
sudo git pull
```
### Monitoring
Monitor system health and performance:
``` bash
# Check system status
sudo systemctl status hostapd dnsmasq nginx miniman

# View logs
sudo journalctl -u hostapd
sudo journalctl -u dnsmasq
sudo journalctl -u miniman
```
### Resource Loading Modes
Mini Manager supports two modes for loading static resources:

#### Production Mode (Default)
In production mode, all static resources are loaded locally from the server. This ensures the application works without internet connectivity, making it suitable for offline environments.

To run in production mode:
``` bash
export FLASK_CONFIG=production
sudo systemctl restart miniman
```

Or modify the systemd service file to include the environment variable:
``` bash
sudo systemctl edit miniman
```

Add the following:
```
[Service]
Environment="FLASK_CONFIG=production"
```

#### Development Mode
In development mode, static resources are loaded from Content Delivery Networks (CDNs). This is useful during development to ensure you're using the latest versions of libraries and to reduce local storage requirements.

To run in development mode:
``` bash
export FLASK_CONFIG=development
sudo systemctl restart miniman
```

Or modify the systemd service file to include the environment variable:
``` bash
sudo systemctl edit miniman
```

Add the following:
```
[Service]
Environment="FLASK_CONFIG=development"
```

### Static Resource Management
If you need to update the local static resources:
``` bash
# Update Bootstrap
sudo curl -s -L -o "/opt/miniman/app/static/css/bootstrap.min.css" "https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/css/bootstrap.min.css"
sudo curl -s -L -o "/opt/miniman/app/static/js/bootstrap.bundle.min.js" "https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/js/bootstrap.bundle.min.js"

# Update Chart.js
sudo curl -s -L -o "/opt/miniman/app/static/js/chart.min.js" "https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js"
```

Note: When running in development mode, these local resources are only used as fallbacks if CDN resources are unavailable.
### System Reset
If needed, you can reset the system to its initial state:
``` bash
sudo /usr/local/bin/system-reset
```
This will:
1. Stop all services (miniman, nginx, hostapd, dnsmasq)
2. Remove configuration files (hostapd.conf, dnsmasq.conf, network settings)
3. Reset the application database (if applicable)
4. Reboot the system

For additional support or to report issues, please visit the GitHub repository at [https://github.com/baderrami/miniman](https://github.com/baderrami/miniman).
