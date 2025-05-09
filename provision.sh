#!/bin/bash

# Mini Manager - WiFi Access Point Provisioning Script
# This script automates the setup of an Ubuntu server as a WiFi access point
# for the Mini Manager application.

# Exit on any error
set -e

# ANSI color codes for better readability
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored messages
print_message() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if running as root
check_root() {
    if [ "$(id -u)" -ne 0 ]; then
        print_error "This script must be run as root"
        exit 1
    fi
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check Ubuntu version
check_ubuntu_version() {
    if ! command_exists lsb_release; then
        print_error "lsb_release command not found. Cannot determine Ubuntu version."
        exit 1
    fi

    UBUNTU_VERSION=$(lsb_release -rs)
    if (( $(echo "$UBUNTU_VERSION < 20.04" | bc -l) )); then
        print_error "This script requires Ubuntu 20.04 or newer. Found: $UBUNTU_VERSION"
        exit 1
    fi

    print_message "Ubuntu version $UBUNTU_VERSION detected."
}

# Function to check for WiFi interface
check_wifi_interface() {
    print_message "Checking for WiFi interfaces..."

    # Get list of wireless interfaces
    WIFI_INTERFACES=$(iw dev | grep Interface | awk '{print $2}')

    if [ -z "$WIFI_INTERFACES" ]; then
        print_error "No WiFi interfaces found. This script requires at least one WiFi interface."
        exit 1
    fi

    # If multiple interfaces, let user choose
    if [ "$(echo "$WIFI_INTERFACES" | wc -l)" -gt 1 ]; then
        print_message "Multiple WiFi interfaces found:"
        i=1
        for iface in $WIFI_INTERFACES; do
            echo "$i) $iface"
            i=$((i+1))
        done

        read -p "Select WiFi interface to use for AP [1]: " WIFI_CHOICE
        WIFI_CHOICE=${WIFI_CHOICE:-1}

        WIFI_INTERFACE=$(echo "$WIFI_INTERFACES" | sed -n "${WIFI_CHOICE}p")
    else
        WIFI_INTERFACE=$WIFI_INTERFACES
    fi

    print_message "Using WiFi interface: $WIFI_INTERFACE"
}

# Function to update system packages
update_system() {
    print_message "Updating system packages..."
    apt update
    apt upgrade -y
    print_success "System packages updated."
}

# Function to install required packages
install_packages() {
    print_message "Installing required packages..."
    apt install -y hostapd dnsmasq iptables-persistent python3-pip python3-venv nginx git

    # Stop services initially to prevent them from running with default configs
    systemctl stop hostapd
    systemctl stop dnsmasq

    print_success "Required packages installed."
}

# Function to configure hostapd
configure_hostapd() {
    print_message "Configuring hostapd..."

    # Prompt for SSID and password
    read -p "Enter WiFi SSID [DeviceManager]: " WIFI_SSID
    WIFI_SSID=${WIFI_SSID:-DeviceManager}

    read -p "Enter WiFi password [securepassword]: " WIFI_PASSWORD
    WIFI_PASSWORD=${WIFI_PASSWORD:-securepassword}

    # Create hostapd configuration
    cat > /etc/hostapd/hostapd.conf << EOF
interface=$WIFI_INTERFACE
driver=nl80211
ssid=$WIFI_SSID
hw_mode=g
channel=7
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase=$WIFI_PASSWORD
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
EOF

    # Configure hostapd to use this configuration file
    sed -i 's|#DAEMON_CONF=""|DAEMON_CONF="/etc/hostapd/hostapd.conf"|' /etc/default/hostapd

    # Enable hostapd service
    systemctl unmask hostapd
    systemctl enable hostapd

    print_success "hostapd configured."
}

# Function to configure dnsmasq
configure_dnsmasq() {
    print_message "Configuring dnsmasq..."

    # Backup original configuration
    if [ -f /etc/dnsmasq.conf ]; then
        cp /etc/dnsmasq.conf /etc/dnsmasq.conf.bak
    fi

    # Stop and disable systemd-resolved to avoid port conflicts
    print_message "Stopping systemd-resolved to avoid port conflicts..."

    # Check if systemd-resolved is running before attempting to stop it
    if systemctl is-active --quiet systemd-resolved; then
        systemctl stop systemd-resolved || print_warning "Failed to stop systemd-resolved, it might not be running"
    else
        print_message "systemd-resolved is not running, skipping stop"
    fi

    # Check if systemd-resolved is enabled before attempting to disable it
    if systemctl is-enabled --quiet systemd-resolved 2>/dev/null; then
        systemctl disable systemd-resolved || print_warning "Failed to disable systemd-resolved"
    else
        print_message "systemd-resolved is not enabled, skipping disable"
    fi

    # If resolv.conf is a symlink to systemd-resolved's version, replace it
    if [ -L /etc/resolv.conf ]; then
        rm /etc/resolv.conf
        echo "nameserver 8.8.8.8" > /etc/resolv.conf
        echo "nameserver 8.8.4.4" >> /etc/resolv.conf
        print_success "Created new resolv.conf with Google DNS servers"
    else
        # Ensure resolv.conf exists and has proper content
        if [ ! -f /etc/resolv.conf ] || ! grep -q "nameserver" /etc/resolv.conf; then
            echo "nameserver 8.8.8.8" > /etc/resolv.conf
            echo "nameserver 8.8.4.4" >> /etc/resolv.conf
            print_success "Created/updated resolv.conf with Google DNS servers"
        fi
    fi

    # Create dnsmasq configuration
    cat > /etc/dnsmasq.conf << EOF
# Listen only on WiFi interface
interface=$WIFI_INTERFACE
# Don't use /etc/resolv.conf
no-resolv
# Use Google DNS
server=8.8.8.8
server=8.8.4.4
# DHCP range
dhcp-range=192.168.4.2,192.168.4.20,255.255.255.0,24h
# Local domain
domain=local
# Address mapping
address=/device.local/192.168.4.1
# Logging
log-queries
log-dhcp
EOF

    # Enable dnsmasq service
    systemctl enable dnsmasq

    print_success "dnsmasq configured."
}

# Function to configure network interfaces
configure_network() {
    print_message "Configuring network interfaces..."

    # Backup original configuration
    if [ -f /etc/netplan/50-cloud-init.yaml ]; then
        cp /etc/netplan/50-cloud-init.yaml /etc/netplan/50-cloud-init.yaml.bak
    fi

    # Create netplan configuration for WiFi AP
    cat > /etc/netplan/60-wifi-ap.yaml << EOF
network:
  version: 2
  ethernets:
    $WIFI_INTERFACE:
      dhcp4: no
      addresses: [192.168.4.1/24]
EOF

    # Set proper permissions for netplan configuration file
    chmod 600 /etc/netplan/60-wifi-ap.yaml

    # Apply netplan configuration
    netplan apply

    print_success "Network interfaces configured."
}

# Function to enable IP forwarding
enable_ip_forwarding() {
    print_message "Enabling IP forwarding..."

    # Enable IP forwarding for current session
    echo 1 > /proc/sys/net/ipv4/ip_forward

    # Enable IP forwarding permanently
    if ! grep -q "net.ipv4.ip_forward=1" /etc/sysctl.conf; then
        echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf
    fi

    # Apply sysctl settings
    sysctl -p

    print_success "IP forwarding enabled."
}

# Function to configure iptables
configure_iptables() {
    print_message "Configuring iptables..."

    # Get the main internet-connected interface
    INTERNET_IFACE=$(ip route | grep default | awk '{print $5}')

    if [ -z "$INTERNET_IFACE" ]; then
        print_warning "Could not determine internet interface. NAT will not be configured."
        return
    fi

    # Configure NAT
    iptables -t nat -A POSTROUTING -o $INTERNET_IFACE -j MASQUERADE
    iptables -A FORWARD -i $INTERNET_IFACE -o $WIFI_INTERFACE -m state --state RELATED,ESTABLISHED -j ACCEPT
    iptables -A FORWARD -i $WIFI_INTERFACE -o $INTERNET_IFACE -j ACCEPT

    # Save iptables rules
    if command_exists netfilter-persistent; then
        netfilter-persistent save
    else
        print_warning "netfilter-persistent not found. iptables rules will not persist after reboot."
        print_warning "Consider installing iptables-persistent package."
    fi

    print_success "iptables configured."
}

# Function to create WiFi AP service
create_wifi_ap_service() {
    print_message "Creating WiFi AP service..."

    # Create systemd service file
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

    # Enable and start the service
    systemctl enable wifi-ap.service

    print_success "WiFi AP service created."
}

# Function to configure OverlayFS for system reset
configure_overlayfs() {
    print_message "Configuring OverlayFS for system reset..."

    # Create necessary directories
    mkdir -p /mnt/{lower,upper,work,merged}

    # Add to fstab for persistence
    if ! grep -q "overlay /mnt/merged" /etc/fstab; then
        echo "overlay /mnt/merged overlay lowerdir=/mnt/lower,upperdir=/mnt/upper,workdir=/mnt/work 0 0" >> /etc/fstab
    fi

    # Create reset script
    cat > /usr/local/bin/system-reset << EOF
#!/bin/bash
rm -rf /mnt/upper/*
rm -rf /mnt/work/*
sync
reboot
EOF

    # Make the script executable
    chmod +x /usr/local/bin/system-reset

    print_success "OverlayFS configured for system reset."
}

# Function to install and configure the Flask application
install_flask_app() {
    print_message "Installing Flask application..."

    # Check if the application directory already exists and is not empty
    if [ -d "/opt/device-manager" ] && [ "$(ls -A /opt/device-manager 2>/dev/null)" ]; then
        print_warning "Directory /opt/device-manager already exists and is not empty."
        read -p "What would you like to do? [s]kip, [b]ackup and replace, [p]ull updates if it's a git repo: " ACTION
        ACTION=${ACTION:-s}

        case $ACTION in
            s|S)
                print_message "Skipping repository cloning."
                if [ -d "/opt/device-manager/.git" ]; then
                    cd /opt/device-manager
                else
                    print_warning "Existing directory is not a git repository. Some features may not work correctly."
                    return
                fi
                ;;
            b|B)
                print_message "Backing up existing directory..."
                BACKUP_DIR="/opt/device-manager-backup-$(date +%Y%m%d%H%M%S)"
                mv /opt/device-manager $BACKUP_DIR
                print_success "Existing directory backed up to $BACKUP_DIR"
                mkdir -p /opt/device-manager
                ;;
            p|P)
                if [ -d "/opt/device-manager/.git" ]; then
                    print_message "Pulling latest changes..."
                    cd /opt/device-manager
                    git pull
                    if [ $? -ne 0 ]; then
                        print_error "Failed to pull updates. Repository may have local changes."
                        read -p "Force update? This will discard local changes [y/N]: " FORCE
                        if [[ "$FORCE" =~ ^[Yy]$ ]]; then
                            git fetch --all
                            git reset --hard origin/main || git reset --hard origin/master
                            print_success "Repository forcefully updated."
                        else
                            print_message "Continuing with existing repository state."
                        fi
                    else
                        print_success "Repository updated successfully."
                    fi
                else
                    print_error "Existing directory is not a git repository."
                    read -p "Backup and replace anyway? [y/N]: " REPLACE
                    if [[ "$REPLACE" =~ ^[Yy]$ ]]; then
                        BACKUP_DIR="/opt/device-manager-backup-$(date +%Y%m%d%H%M%S)"
                        mv /opt/device-manager $BACKUP_DIR
                        print_success "Existing directory backed up to $BACKUP_DIR"
                        mkdir -p /opt/device-manager
                    else
                        print_message "Skipping repository cloning."
                        return
                    fi
                fi
                ;;
            *)
                print_error "Invalid option. Skipping repository cloning."
                return
                ;;
        esac
    else
        # Create application directory if it doesn't exist
        mkdir -p /opt/device-manager
    fi

    # Clone the repository if needed (directory is empty or we chose to replace it)
    if [ ! "$(ls -A /opt/device-manager 2>/dev/null)" ]; then
        read -p "Enter Git repository URL for the application [skip]: " REPO_URL

        if [ -n "$REPO_URL" ]; then
            git clone $REPO_URL /opt/device-manager
            cd /opt/device-manager
        else
            print_warning "Repository URL not provided. Skipping application installation."
            print_warning "You will need to manually install the application later."
            return
        fi
    fi

    # Create virtual environment
    python3 -m venv venv
    source venv/bin/activate

    # Install dependencies
    if [ -f requirements.txt ]; then
        pip install -r requirements.txt
    else
        pip install flask flask-login flask-sqlalchemy flask-wtf gunicorn
    fi

    # Initialize database
    if [ -f run.py ]; then
        export FLASK_APP=run.py
        flask init-db
    fi

    # Deactivate virtual environment
    deactivate

    print_success "Flask application installed."
}

# Function to configure Nginx
configure_nginx() {
    print_message "Configuring Nginx..."

    # Create Nginx configuration file
    cat > /etc/nginx/sites-available/device-manager << EOF
server {
    listen 80;
    server_name device.local;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

    # Enable the site
    ln -sf /etc/nginx/sites-available/device-manager /etc/nginx/sites-enabled/

    # Test Nginx configuration
    nginx -t

    # Enable and restart Nginx
    systemctl enable nginx
    systemctl restart nginx

    print_success "Nginx configured."
}

# Function to create systemd service for the application
create_app_service() {
    print_message "Creating application service..."

    # Create service file
    cat > /etc/systemd/system/device-manager.service << EOF
[Unit]
Description=Device Manager Application
After=network.target

[Service]
# Change from www-data to root or the user who owns the application files
User=root
WorkingDirectory=/opt/device-manager
# Add these lines to specify a runtime directory
RuntimeDirectory=device-manager
RuntimeDirectoryMode=0755
ExecStart=/opt/device-manager/venv/bin/gunicorn -c gunicorn.conf.py run:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

    # Set proper permissions
    chown -R www-data:www-data /opt/device-manager

    # Enable the service
    systemctl enable device-manager.service

    print_success "Application service created."
}

# Function to start all services
start_services() {
    print_message "Starting services..."

    # Start hostapd
    print_message "Starting hostapd..."
    if systemctl is-active --quiet hostapd; then
        print_message "hostapd is already running, restarting to apply new configuration..."
        systemctl restart hostapd
    else
        systemctl start hostapd
    fi

    if ! systemctl is-active --quiet hostapd; then
        print_error "Failed to start hostapd. Check logs with: systemctl status hostapd"
        print_error "You may need to troubleshoot hostapd configuration."
        # Continue with other services despite this error
    else
        print_success "hostapd started successfully."
    fi

    # Start dnsmasq with error handling
    print_message "Starting dnsmasq..."
    if systemctl is-active --quiet dnsmasq; then
        print_message "dnsmasq is already running, restarting to apply new configuration..."
        systemctl restart dnsmasq
    else
        systemctl start dnsmasq
    fi

    if ! systemctl is-active --quiet dnsmasq; then
        print_error "Failed to start dnsmasq. Checking for common issues..."

        # Check if another service is using port 53
        if command_exists lsof; then
            PORT_53_PROCESS=$(lsof -i :53 2>/dev/null | grep -v "^COMMAND" | awk '{print $1}' | uniq)
            if [ -n "$PORT_53_PROCESS" ]; then
                print_error "Port 53 is already in use by: $PORT_53_PROCESS"
                print_message "Attempting to stop conflicting service..."
                systemctl stop $PORT_53_PROCESS 2>/dev/null
                systemctl disable $PORT_53_PROCESS 2>/dev/null

                # Try starting dnsmasq again
                print_message "Trying to start dnsmasq again..."
                systemctl start dnsmasq
                if ! systemctl is-active --quiet dnsmasq; then
                    print_error "Still unable to start dnsmasq. Check logs with: systemctl status dnsmasq"
                    print_error "You may need to manually resolve port conflicts."
                else
                    print_success "dnsmasq started successfully after resolving conflicts."
                fi
            else
                print_error "No process found using port 53. Check dnsmasq logs with: systemctl status dnsmasq"
                print_error "You may need to manually troubleshoot dnsmasq configuration."
            fi
        else
            print_error "lsof command not found. Cannot check for port conflicts."
            print_error "Check dnsmasq logs with: systemctl status dnsmasq"
        fi

        # Try to provide more specific error information
        DNSMASQ_STATUS=$(systemctl status dnsmasq 2>&1 | grep "Active:" | sed 's/^[ \t]*//')
        print_error "dnsmasq status: $DNSMASQ_STATUS"

        # Check if dnsmasq.conf has syntax errors
        if command_exists dnsmasq; then
            print_message "Checking dnsmasq configuration for errors..."
            dnsmasq --test 2>&1 | grep -i error
        fi
    else
        print_success "dnsmasq started successfully."
    fi

    # Start WiFi AP service
    print_message "Starting WiFi AP service..."
    if systemctl is-active --quiet wifi-ap.service; then
        print_message "WiFi AP service is already running, restarting to apply new configuration..."
        systemctl restart wifi-ap.service
    else
        systemctl start wifi-ap.service
    fi

    if ! systemctl is-active --quiet wifi-ap.service; then
        print_error "Failed to start WiFi AP service. Check logs with: systemctl status wifi-ap.service"
    else
        print_success "WiFi AP service started successfully."
    fi

    # Start device manager service
    print_message "Starting device manager service..."
    if systemctl is-active --quiet device-manager.service; then
        print_message "Device manager service is already running, restarting to apply new configuration..."
        systemctl restart device-manager.service
    else
        systemctl start device-manager.service
    fi

    if ! systemctl is-active --quiet device-manager.service; then
        print_error "Failed to start device manager service. Check logs with: systemctl status device-manager.service"
    else
        print_success "Device manager service started successfully."
    fi

    print_success "Services started."
}

# Function to display summary
display_summary() {
    print_message "Provisioning completed successfully!"
    echo ""
    echo "Summary:"
    echo "--------"
    echo "WiFi AP SSID: $WIFI_SSID"
    echo "WiFi Interface: $WIFI_INTERFACE"
    echo "IP Address: 192.168.4.1"
    echo ""
    echo "Web Interface: http://device.local or http://192.168.4.1"
    echo "Default Login: admin / admin"
    echo ""
    print_warning "IMPORTANT: Change the default admin password after first login!"
    echo ""
    echo "To reset the system to factory settings:"
    echo "  sudo /usr/local/bin/system-reset"
    echo ""
}

# Main function
main() {
    print_message "Starting Mini Manager WiFi AP provisioning..."

    # Check if running as root
    check_root

    # Check Ubuntu version
    check_ubuntu_version

    # Check for WiFi interface
    check_wifi_interface

    # Update system
    update_system

    # Install required packages
    install_packages

    # Configure hostapd
    configure_hostapd

    # Configure dnsmasq
    configure_dnsmasq

    # Configure network
    configure_network

    # Enable IP forwarding
    enable_ip_forwarding

    # Configure iptables
    configure_iptables

    # Create WiFi AP service
    create_wifi_ap_service

    # Configure OverlayFS
    configure_overlayfs

    # Install Flask application
    install_flask_app

    # Configure Nginx
    configure_nginx

    # Create application service
    create_app_service

    # Start services
    start_services

    # Display summary
    display_summary
}

# Run main function
main
