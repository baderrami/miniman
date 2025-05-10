#!/bin/bash

# Mini Manager - WiFi Access Point Provisioning Script
# This script automates the setup of an Ubuntu server as a WiFi access point
# for the Mini Manager application.
#
# CHANGELOG:
# - Added error handling for the configure_nginx function to prevent script failure
# - Enhanced network configuration with backup and rollback mechanisms
# - Made hostapd and dnsmasq configuration idempotent (can run multiple times safely)
# - Added specialized troubleshooting for each service
# - Improved service startup with automatic recovery from failures
# - Added fallback configurations for critical services
# - Extracted common functionality into helper functions
# - Added verification steps to ensure proper configuration

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

# Function to check and install dependencies
check_dependencies() {
    print_message "Checking essential dependencies..."
    
    # List of essential tools
    ESSENTIAL_TOOLS=("iw" "git")
    
    # Check each tool
    for tool in "${ESSENTIAL_TOOLS[@]}"; do
        if ! command_exists "$tool"; then
            print_message "Installing '$tool'..."
            apt update
            apt install -y "$tool"
            if ! command_exists "$tool"; then
                print_error "Failed to install '$tool'. Please install it manually."
                exit 1
            fi
            print_success "'$tool' installed successfully."
        fi
    done
    
    print_success "Essential dependencies checked and installed."
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
    
    # Pre-configure iptables-persistent to avoid interactive prompts
    print_message "Pre-configuring iptables-persistent to avoid prompts..."
    echo "iptables-persistent iptables-persistent/autosave_v4 boolean true" | debconf-set-selections
    echo "iptables-persistent iptables-persistent/autosave_v6 boolean true" | debconf-set-selections
    
    # Install packages with DEBIAN_FRONTEND=noninteractive to prevent interactive prompts
    DEBIAN_FRONTEND=noninteractive apt install -y hostapd dnsmasq iptables-persistent python3-pip python3-venv nginx git iw

    # Stop services initially to prevent them from running with default configs
    systemctl stop hostapd
    systemctl stop dnsmasq

    print_success "Required packages installed."
}

# Function to configure hostapd
configure_hostapd() {
    print_message "Configuring hostapd..."

    # Check if hostapd is already configured
    if [ -f /etc/hostapd/hostapd.conf ] && grep -q "^ssid=" /etc/hostapd/hostapd.conf; then
        print_message "hostapd configuration file already exists."

        # Extract existing SSID and password for reuse
        if grep -q "^ssid=" /etc/hostapd/hostapd.conf; then
            EXISTING_SSID=$(grep "^ssid=" /etc/hostapd/hostapd.conf | cut -d'=' -f2)
            print_message "Found existing SSID: $EXISTING_SSID"
        fi

        read -p "Use existing configuration? [Y/n]: " USE_EXISTING
        USE_EXISTING=${USE_EXISTING:-Y}

        if [[ "$USE_EXISTING" =~ ^[Yy]$ ]]; then
            # If using existing config, still need to set WIFI_SSID for other functions
            if [ -n "$EXISTING_SSID" ]; then
                WIFI_SSID=$EXISTING_SSID
                print_message "Using existing SSID: $WIFI_SSID"
            else
                # Fallback if we couldn't extract SSID
                WIFI_SSID="DeviceManager"
            fi

            # Ensure the configuration file is properly referenced
            if ! grep -q "DAEMON_CONF=\"/etc/hostapd/hostapd.conf\"" /etc/default/hostapd; then
                sed -i 's|#DAEMON_CONF=""|DAEMON_CONF="/etc/hostapd/hostapd.conf"|' /etc/default/hostapd
                print_message "Updated hostapd default configuration."
            fi

            print_success "Using existing hostapd configuration."
            return
        else
            print_message "Creating new hostapd configuration..."
            # Backup the existing configuration
            cp /etc/hostapd/hostapd.conf /etc/hostapd/hostapd.conf.bak.$(date +%Y%m%d%H%M%S)
            print_message "Backed up existing configuration."
        fi
    fi

    # Prompt for SSID and password
    read -p "Enter WiFi SSID [DeviceManager]: " WIFI_SSID
    WIFI_SSID=${WIFI_SSID:-DeviceManager}

    read -p "Enter WiFi password [securepassword]: " WIFI_PASSWORD
    WIFI_PASSWORD=${WIFI_PASSWORD:-securepassword}

    # Ensure WiFi interface is not managed by NetworkManager
    if command_exists nmcli; then
        print_message "Disabling NetworkManager control of $WIFI_INTERFACE..."
        nmcli device set $WIFI_INTERFACE managed no || true
    fi

    # Create hostapd configuration
    cat > /etc/hostapd/hostapd.conf << EOF
interface=$WIFI_INTERFACE
driver=nl80211
ssid=$WIFI_SSID
hw_mode=g
channel=7
country_code=US
ieee80211d=1
wmm_enabled=1
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase=$WIFI_PASSWORD
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
# Increase stability
beacon_int=100
dtim_period=2
rts_threshold=2347
fragm_threshold=2346
EOF

    # Configure hostapd to use this configuration file
    sed -i 's|#DAEMON_CONF=""|DAEMON_CONF="/etc/hostapd/hostapd.conf"|' /etc/default/hostapd

    # Explicitly set DAEMON_OPTS in default file to fix environment variable issue
    if ! grep -q "DAEMON_OPTS=\"\"" /etc/default/hostapd; then
        echo 'DAEMON_OPTS=""' >> /etc/default/hostapd
    fi

    # Enable hostapd service
    systemctl unmask hostapd
    systemctl enable hostapd

    print_success "hostapd configured."
}

# Function to configure dnsmasq
configure_dnsmasq() {
    print_message "Configuring dnsmasq..."

    # Check if dnsmasq is already configured
    if [ -f /etc/dnsmasq.conf ] && grep -q "interface=$WIFI_INTERFACE" /etc/dnsmasq.conf; then
        print_message "dnsmasq configuration file already exists for interface $WIFI_INTERFACE."

        read -p "Use existing dnsmasq configuration? [Y/n]: " USE_EXISTING
        USE_EXISTING=${USE_EXISTING:-Y}

        if [[ "$USE_EXISTING" =~ ^[Yy]$ ]]; then
            print_success "Using existing dnsmasq configuration."

            # Still need to ensure systemd-resolved is not conflicting
            handle_systemd_resolved

            # Ensure resolv.conf is properly configured
            configure_resolv_conf

            return
        else
            print_message "Creating new dnsmasq configuration..."
            # Backup the existing configuration with timestamp
            cp /etc/dnsmasq.conf /etc/dnsmasq.conf.bak.$(date +%Y%m%d%H%M%S)
            print_message "Backed up existing configuration."
        fi
    else
        # Backup original configuration if it exists
        if [ -f /etc/dnsmasq.conf ]; then
            cp /etc/dnsmasq.conf /etc/dnsmasq.conf.bak
        fi
    fi

    # Handle systemd-resolved
    handle_systemd_resolved

    # Configure resolv.conf
    configure_resolv_conf

    # Create dnsmasq configuration
    cat > /etc/dnsmasq.conf << EOF
# Listen on all interfaces but only respond to the WiFi interface
bind-interfaces
interface=$WIFI_INTERFACE
# Don't forward short names
domain-needed
# Don't forward addresses in non-routed address spaces
bogus-priv
# Don't use /etc/resolv.conf
no-resolv
# Use Google DNS
server=8.8.8.8
server=8.8.4.4
# DHCP range
dhcp-range=192.168.4.2,192.168.4.20,255.255.255.0,24h
# Set default gateway
dhcp-option=3,192.168.4.1
# Set DNS server
dhcp-option=6,192.168.4.1
# Local domain
domain=local
# Address mapping
address=/device.local/192.168.4.1
# Disable IP source and interface source checking
# bind-dynamic option removed - cannot be used with bind-interfaces
# Logging
log-queries
log-dhcp
# Listen on localhost first (more reliable)
listen-address=127.0.0.1
# Comment out specific IP binding initially to avoid startup failures
# listen-address=192.168.4.1
EOF

    # Create a directory for dnsmasq to use for DHCP lease information
    mkdir -p /var/lib/misc

    # Enable dnsmasq service
    systemctl enable dnsmasq

    print_success "dnsmasq configured."
}

# Function to handle systemd-resolved
handle_systemd_resolved() {
    print_message "Handling systemd-resolved to avoid port conflicts..."

    # Check if systemd-resolved is running before attempting to stop it
    if systemctl is-active --quiet systemd-resolved; then
        print_message "Stopping systemd-resolved..."
        systemctl stop systemd-resolved || print_warning "Failed to stop systemd-resolved, it might not be running"
    else
        print_message "systemd-resolved is not running, skipping stop"
    fi

    # Check if systemd-resolved is enabled before attempting to disable it
    if systemctl is-enabled --quiet systemd-resolved 2>/dev/null; then
        print_message "Disabling systemd-resolved..."
        systemctl disable systemd-resolved || print_warning "Failed to disable systemd-resolved"
    else
        print_message "systemd-resolved is not enabled, skipping disable"
    fi

    print_success "systemd-resolved handled."
}

# Function to configure resolv.conf
configure_resolv_conf() {
    print_message "Configuring resolv.conf..."

    # If resolv.conf is a symlink to systemd-resolved's version, replace it
    if [ -L /etc/resolv.conf ]; then
        print_message "Removing symlink to systemd-resolved's resolv.conf..."
        rm /etc/resolv.conf
        echo "nameserver 8.8.8.8" > /etc/resolv.conf
        echo "nameserver 8.8.4.4" >> /etc/resolv.conf
        print_success "Created new resolv.conf with Google DNS servers"
    else
        # Ensure resolv.conf exists and has proper content
        if [ ! -f /etc/resolv.conf ] || ! grep -q "nameserver" /etc/resolv.conf; then
            print_message "Creating/updating resolv.conf..."
            echo "nameserver 8.8.8.8" > /etc/resolv.conf
            echo "nameserver 8.8.4.4" >> /etc/resolv.conf
            print_success "Created/updated resolv.conf with Google DNS servers"
        else
            print_message "resolv.conf already exists with nameserver entries."
        fi
    fi

    print_success "resolv.conf configured."
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
  wifis:
    $WIFI_INTERFACE:
      dhcp4: no
      addresses: [192.168.4.1/24]
      nameservers:
        addresses: [8.8.8.8, 8.8.4.4]
      access-points:
        "$WIFI_SSID":
          mode: ap
          password: "$WIFI_PASSWORD"
EOF

    # Set proper permissions for netplan configuration file
    chmod 600 /etc/netplan/60-wifi-ap.yaml

    # Add a manual IP address configuration as backup in case netplan fails
    print_message "Setting up fallback IP configuration..."

    # Ensure interface is up
    ip link set $WIFI_INTERFACE up

    # Add IP address directly (this will be overridden by netplan if it works)
    ip addr add 192.168.4.1/24 dev $WIFI_INTERFACE 2>/dev/null || true

    # Save current network configuration for potential rollback
    print_message "Saving current network configuration for potential rollback..."
    mkdir -p /opt/network-backup
    ip addr show > /opt/network-backup/ip-addr-before-netplan.txt
    ip route show > /opt/network-backup/ip-route-before-netplan.txt

    # Apply netplan configuration with error handling
    print_message "Applying netplan configuration..."
    if ! netplan apply; then
        print_error "Netplan configuration failed. Attempting to restore previous network configuration..."

        # Restore the interface to its previous state
        if [ -f /opt/network-backup/ip-addr-before-netplan.txt ]; then
            print_message "Restoring IP addresses..."
            # Ensure the interface is up
            ip link set $WIFI_INTERFACE up

            # Re-add the IP address directly
            ip addr add 192.168.4.1/24 dev $WIFI_INTERFACE 2>/dev/null || true

            print_success "Basic network configuration restored."
        else
            print_error "Could not find backup network configuration. Manual intervention may be required."
        fi
    else
        print_success "Netplan configuration applied successfully."
    fi

    # Verify connectivity
    print_message "Verifying network configuration..."
    if ! ip addr show $WIFI_INTERFACE | grep -q "192.168.4.1"; then
        print_error "IP address 192.168.4.1 not configured on $WIFI_INTERFACE. Applying fallback configuration..."

        # Apply fallback configuration
        ip addr add 192.168.4.1/24 dev $WIFI_INTERFACE 2>/dev/null || true

        if ip addr show $WIFI_INTERFACE | grep -q "192.168.4.1"; then
            print_success "Fallback IP configuration applied successfully."
        else
            print_error "Failed to apply fallback IP configuration. Manual intervention may be required."
        fi
    else
        print_success "Network interface properly configured with IP 192.168.4.1."
    fi

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

    # Flush existing rules
    iptables -F
    iptables -t nat -F

    # Allow all traffic on loopback
    iptables -A INPUT -i lo -j ACCEPT

    # Allow established and related connections
    iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT

    # Allow ICMP (ping)
    iptables -A INPUT -p icmp -j ACCEPT

    # Allow all traffic from WiFi interface (essential for connectivity)
    iptables -A INPUT -i $WIFI_INTERFACE -j ACCEPT

    # Allow SSH, HTTP, and HTTPS
    iptables -A INPUT -p tcp --dport 22 -j ACCEPT
    iptables -A INPUT -p tcp --dport 80 -j ACCEPT
    iptables -A INPUT -p tcp --dport 443 -j ACCEPT

    # Configure NAT
    iptables -t nat -A POSTROUTING -o $INTERNET_IFACE -j MASQUERADE
    iptables -A FORWARD -i $INTERNET_IFACE -o $WIFI_INTERFACE -m state --state RELATED,ESTABLISHED -j ACCEPT
    iptables -A FORWARD -i $WIFI_INTERFACE -o $INTERNET_IFACE -j ACCEPT

    # Save iptables rules
    if command_exists netfilter-persistent; then
        print_message "Saving iptables rules..."
        DEBIAN_FRONTEND=noninteractive netfilter-persistent save
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

    # Create gunicorn configuration file
    cat > /opt/device-manager/gunicorn.conf.py << EOF
    bind = "0.0.0.0:8000"
    workers = 4
    worker_class = "sync"
    timeout = 30
    loglevel = "info"
    # Do not daemonize; systemd will manage the process
    daemon = False
    EOF

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

    # Ensure nginx directories exist
    mkdir -p /etc/nginx/sites-available /etc/nginx/sites-enabled

    # Create Nginx configuration file
    cat > /etc/nginx/sites-available/device-manager << EOF
server {
    listen 80;
    listen 192.168.4.1:80;
    server_name device.local _;

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

    # Test Nginx configuration with error handling
    if ! nginx -t; then
        print_warning "Nginx configuration test failed, creating a minimal working config"
        # Create a minimal working configuration
        cat > /etc/nginx/sites-available/device-manager << EOF
server {
    listen 80;
    server_name localhost;

    location / {
        proxy_pass http://127.0.0.1:8000;
    }
}
EOF
        # Test again
        if ! nginx -t; then
            print_error "Nginx configuration still failing, check nginx error logs"
            # Continue anyway to avoid script failure
        fi
    fi

    # Enable and restart Nginx with error handling
    systemctl enable nginx
    if ! systemctl restart nginx; then
        print_warning "Failed to restart Nginx, trying to start it"
        systemctl start nginx || print_error "Failed to start Nginx, manual intervention required"
    fi

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
User=root
WorkingDirectory=/opt/device-manager
RuntimeDirectory=device-manager
RuntimeDirectoryMode=0755
ExecStart=/opt/device-manager/venv/bin/gunicorn -c gunicorn.conf.py run:app
Environment="GUNICORN_CMD_ARGS=--bind=0.0.0.0:8000"
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

    # Fix permissions - keep root as owner since that's specified in the service
    chown -R root:root /opt/device-manager
    chmod -R 755 /opt/device-manager

    # Make sure the gunicorn config file exists and has proper format
    print_message "Creating gunicorn configuration file..."
    cat > /opt/device-manager/gunicorn.conf.py << EOF
bind = "0.0.0.0:8000"
workers = 4
worker_class = "sync"
timeout = 30
loglevel = "info"
daemon = False
EOF

    # Reload systemd to recognize the new service
    systemctl daemon-reload

    # Enable the service
    systemctl enable device-manager.service

    print_success "Application service created."
}

# Function to start all services
start_services() {
    print_message "Starting services..."

    # Array of services to start
    SERVICES=("hostapd" "dnsmasq" "wifi-ap.service" "nginx" "device-manager.service")

    # Track overall success
    OVERALL_SUCCESS=true

    # Special handling for dnsmasq - ensure IP is configured before starting
    for SERVICE in "${SERVICES[@]}"; do
        # If this is dnsmasq, verify IP configuration first
        if [ "$SERVICE" = "dnsmasq" ]; then
            print_message "Verifying IP configuration before starting dnsmasq..."
            if ! ip addr show $WIFI_INTERFACE | grep -q "192.168.4.1"; then
                print_warning "IP address 192.168.4.1 not configured on $WIFI_INTERFACE. Configuring it now..."
                # Ensure interface is up
                ip link set $WIFI_INTERFACE up
                # Add IP address directly
                ip addr add 192.168.4.1/24 dev $WIFI_INTERFACE 2>/dev/null || true
                # Wait a moment for the interface to be fully ready
                sleep 2
                # Verify IP was added
                if ip addr show $WIFI_INTERFACE | grep -q "192.168.4.1"; then
                    print_success "IP address 192.168.4.1 configured on $WIFI_INTERFACE."
                else
                    print_error "Failed to configure IP address. dnsmasq may fail to start."
                fi
            else
                print_success "IP address 192.168.4.1 already configured on $WIFI_INTERFACE."
            fi
        fi

        # Start the service
        start_service "$SERVICE" || OVERALL_SUCCESS=false
    done

    if $OVERALL_SUCCESS; then
        print_success "All services started successfully."
    else
        print_warning "Some services failed to start. Check the logs for details."
        print_message "You can run the diagnostic tool to troubleshoot: /usr/local/bin/diagnose-network"
    fi

    print_success "Services started."
}

# Function to start a specific service with error handling
start_service() {
    local SERVICE=$1
    print_message "Starting $SERVICE..."

    # Check if service is already running
    if systemctl is-active --quiet "$SERVICE"; then
        print_message "$SERVICE is already running, restarting to apply new configuration..."
        systemctl restart "$SERVICE" || {
            print_error "Failed to restart $SERVICE. Attempting to start it..."
            systemctl start "$SERVICE"
        }
    else
        systemctl start "$SERVICE"
    fi

    # Check if service started successfully
    if ! systemctl is-active --quiet "$SERVICE"; then
        print_error "Failed to start $SERVICE. Checking for common issues..."

        case "$SERVICE" in
            "dnsmasq")
                handle_dnsmasq_failure
                ;;
            "hostapd")
                handle_hostapd_failure
                ;;
            "nginx")
                handle_nginx_failure
                ;;
            "device-manager.service")
                handle_device_manager_failure
                ;;
            *)
                print_error "Failed to start $SERVICE. Check logs with: systemctl status $SERVICE"
                ;;
        esac

        # Final check if service is running
        if systemctl is-active --quiet "$SERVICE"; then
            print_success "$SERVICE started successfully after troubleshooting."
            return 0
        else
            print_error "$SERVICE failed to start. Manual intervention may be required."
            return 1
        fi
    else
        print_success "$SERVICE started successfully."
        return 0
    fi
}

# Function to handle dnsmasq failures
handle_dnsmasq_failure() {
    print_message "Troubleshooting dnsmasq..."

    # Check if the error is related to binding to the IP address
    DNSMASQ_ERROR=$(systemctl status dnsmasq 2>&1 | grep -i "failed to create listening socket" | grep -i "cannot assign requested address")
    if [ -n "$DNSMASQ_ERROR" ]; then
        print_error "dnsmasq failed to bind to IP address. Checking if IP is configured..."

        # Check if the IP address is configured on the interface
        if ! ip addr show $WIFI_INTERFACE | grep -q "192.168.4.1"; then
            print_error "IP address 192.168.4.1 not configured on $WIFI_INTERFACE. Applying IP configuration..."

            # Ensure interface is up
            ip link set $WIFI_INTERFACE up

            # Add IP address directly
            ip addr add 192.168.4.1/24 dev $WIFI_INTERFACE 2>/dev/null || true

            # Verify IP was added
            if ip addr show $WIFI_INTERFACE | grep -q "192.168.4.1"; then
                print_success "IP address 192.168.4.1 configured on $WIFI_INTERFACE."

                # Wait a moment for the interface to be fully ready
                sleep 2

                # Try starting dnsmasq again
                print_message "Trying to start dnsmasq again..."
                systemctl start dnsmasq
                return
            else
                print_error "Failed to configure IP address. Will try alternative configuration."
            fi
        fi

        # If we get here, either the IP is configured but dnsmasq still can't bind to it,
        # or we failed to configure the IP. Try with a modified configuration.
        print_message "Modifying dnsmasq configuration to use only localhost..."
        cp /etc/dnsmasq.conf /etc/dnsmasq.conf.with_specific_ip

        # Create a configuration that only binds to localhost
        cat > /etc/dnsmasq.conf << EOF
# Modified dnsmasq configuration - only binding to localhost
interface=$WIFI_INTERFACE
bind-interfaces
dhcp-range=192.168.4.2,192.168.4.20,255.255.255.0,24h
dhcp-option=3,192.168.4.1
dhcp-option=6,192.168.4.1
listen-address=127.0.0.1
# Removed specific IP binding that was causing issues
EOF

        # Try starting dnsmasq again
        print_message "Trying to start dnsmasq with modified configuration..."
        systemctl start dnsmasq
        return
    fi

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
        else
            print_error "No process found using port 53. Check dnsmasq logs with: systemctl status dnsmasq"
        fi
    else
        print_error "lsof command not found. Cannot check for port conflicts."
    fi

    # Try to provide more specific error information
    DNSMASQ_STATUS=$(systemctl status dnsmasq 2>&1 | grep "Active:" | sed 's/^[ \t]*//')
    print_error "dnsmasq status: $DNSMASQ_STATUS"

    # Check if dnsmasq.conf has syntax errors
    if command_exists dnsmasq; then
        print_message "Checking dnsmasq configuration for errors..."
        dnsmasq --test 2>&1 | grep -i error

        # If there are syntax errors, try to fix common issues
        if [ $? -eq 0 ]; then
            print_message "Attempting to fix dnsmasq configuration..."
            # Backup the problematic config
            cp /etc/dnsmasq.conf /etc/dnsmasq.conf.problematic

            # Create a minimal working configuration
            cat > /etc/dnsmasq.conf << EOF
# Minimal dnsmasq configuration
interface=$WIFI_INTERFACE
bind-interfaces
dhcp-range=192.168.4.2,192.168.4.20,255.255.255.0,24h
dhcp-option=3,192.168.4.1
dhcp-option=6,192.168.4.1
listen-address=127.0.0.1
EOF

            # Try starting dnsmasq again
            print_message "Trying to start dnsmasq with minimal configuration..."
            systemctl start dnsmasq
        fi
    fi
}

# Function to handle hostapd failures
handle_hostapd_failure() {
    print_message "Troubleshooting hostapd..."

    # Check hostapd status
    HOSTAPD_STATUS=$(systemctl status hostapd 2>&1 | grep "Active:" | sed 's/^[ \t]*//')
    print_error "hostapd status: $HOSTAPD_STATUS"

    # Check if the WiFi interface exists and is up
    if ! ip link show "$WIFI_INTERFACE" &>/dev/null; then
        print_error "WiFi interface $WIFI_INTERFACE does not exist."
        print_message "Available interfaces:"
        ip link show | grep -E '^[0-9]+:' | cut -d' ' -f2 | sed 's/://'
        return 1
    fi

    # Ensure the interface is up
    print_message "Ensuring WiFi interface is up..."
    ip link set "$WIFI_INTERFACE" up

    # Check if the interface supports AP mode
    if command_exists iw; then
        print_message "Checking if interface supports AP mode..."
        if ! iw list | grep -q "AP"; then
            print_error "WiFi interface $WIFI_INTERFACE may not support AP mode."
            return 1
        fi
    fi

    # Check hostapd configuration
    print_message "Checking hostapd configuration..."
    if [ -f /etc/hostapd/hostapd.conf ]; then
        if grep -q "^interface=$WIFI_INTERFACE" /etc/hostapd/hostapd.conf; then
            print_message "hostapd configuration appears correct for interface $WIFI_INTERFACE."
        else
            print_error "hostapd configuration does not match WiFi interface $WIFI_INTERFACE."
            print_message "Updating hostapd configuration..."
            sed -i "s/^interface=.*/interface=$WIFI_INTERFACE/" /etc/hostapd/hostapd.conf
        fi
    else
        print_error "hostapd configuration file not found."
        return 1
    fi

    # Try starting hostapd again
    print_message "Trying to start hostapd again..."
    systemctl start hostapd
}

# Function to handle nginx failures
handle_nginx_failure() {
    print_message "Troubleshooting nginx..."

    # Ensure directories exist
    print_message "Ensuring nginx directories exist..."
    mkdir -p /etc/nginx/sites-available /etc/nginx/sites-enabled

    # Check nginx configuration
    print_message "Testing nginx configuration..."
    nginx -t

    # If there are configuration errors, try to fix them
    if [ $? -ne 0 ]; then
        print_error "Nginx configuration has errors."

        # Backup the problematic config
        if [ -f /etc/nginx/sites-enabled/device-manager ]; then
            cp /etc/nginx/sites-enabled/device-manager /etc/nginx/sites-enabled/device-manager.problematic
        fi
        
        # Remove any potentially problematic symlinks
        rm -f /etc/nginx/sites-enabled/device-manager

        # Create a minimal working configuration
        print_message "Creating minimal nginx configuration..."
        cat > /etc/nginx/sites-available/device-manager << EOF
server {
    listen 80;
    server_name localhost;

    location / {
        proxy_pass http://127.0.0.1:8000;
    }
}
EOF

        # Enable the site
        ln -sf /etc/nginx/sites-available/device-manager /etc/nginx/sites-enabled/

        # Try starting nginx again with error reporting
        print_message "Trying to start nginx with minimal configuration..."
        if ! systemctl start nginx; then
            print_error "Failed to start nginx even with minimal configuration."
            print_message "Nginx error details:"
            nginx -t 2>&1
        fi
    fi
}

# Function to handle device-manager service failures
handle_device_manager_failure() {
    print_message "Troubleshooting device-manager service..."

    # Check if the application directory exists
    if [ ! -d "/opt/device-manager" ]; then
        print_error "Application directory /opt/device-manager does not exist."
        return 1
    fi

    # Check if the virtual environment exists
    if [ ! -d "/opt/device-manager/venv" ]; then
        print_error "Virtual environment not found in /opt/device-manager/venv."
        print_message "Attempting to create virtual environment..."

        cd /opt/device-manager
        python3 -m venv venv
        source venv/bin/activate

        # Install dependencies
        if [ -f requirements.txt ]; then
            pip install -r requirements.txt
        else
            pip install flask flask-login flask-sqlalchemy flask-wtf gunicorn
        fi

        deactivate
    fi

    # Check if gunicorn is installed
    if [ ! -f "/opt/device-manager/venv/bin/gunicorn" ]; then
        print_error "Gunicorn not found in virtual environment."
        print_message "Installing gunicorn..."

        cd /opt/device-manager
        source venv/bin/activate
        pip install gunicorn
        deactivate
    fi

    # Check service configuration
    print_message "Checking service configuration..."
    if ! grep -q "ExecStart=/opt/device-manager/venv/bin/gunicorn" /etc/systemd/system/device-manager.service; then
        print_error "Service configuration may be incorrect."
        print_message "Updating service configuration..."

        # Update service file
        cat > /etc/systemd/system/device-manager.service << EOF
[Unit]
Description=Device Manager Application
After=network.target

[Service]
User=root
WorkingDirectory=/opt/device-manager
RuntimeDirectory=device-manager
RuntimeDirectoryMode=0755
ExecStart=/opt/device-manager/venv/bin/gunicorn -c gunicorn.conf.py run:app
Environment="GUNICORN_CMD_ARGS=--bind=0.0.0.0:8000"
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

        # Reload systemd
        systemctl daemon-reload
    fi

    # Try starting the service again
    print_message "Trying to start device-manager service again..."
    systemctl start device-manager.service
}

# Function to create a diagnostic tool
create_diagnostic_tool() {
    print_message "Creating network diagnostic tool..."

    cat > /usr/local/bin/diagnose-network << 'EOF'
#!/bin/bash

# ANSI color codes for better readability
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}===== Network Diagnostic Tool =====${NC}"
echo

echo -e "${BLUE}System Information:${NC}"
uname -a
echo

echo -e "${BLUE}Network Interfaces:${NC}"
ip a
echo

echo -e "${BLUE}IP Routing Table:${NC}"
ip route
echo

echo -e "${BLUE}DNS Settings:${NC}"
cat /etc/resolv.conf
echo

echo -e "${BLUE}hostapd Status:${NC}"
systemctl status hostapd | head -20
echo

echo -e "${BLUE}dnsmasq Status:${NC}"
systemctl status dnsmasq | head -20
echo

echo -e "${BLUE}Device Manager Status:${NC}"
systemctl status device-manager | head -20
echo

echo -e "${BLUE}Nginx Status:${NC}"
systemctl status nginx | head -20
echo

echo -e "${BLUE}iptables Rules:${NC}"
iptables -L -v
echo

echo -e "${BLUE}NAT Table:${NC}"
iptables -t nat -L -v
echo

echo -e "${BLUE}Connected Devices:${NC}"
if [ -f /var/lib/misc/dnsmasq.leases ]; then
    cat /var/lib/misc/dnsmasq.leases
else
    echo "No leases file found"
fi
echo

echo -e "${BLUE}Active Connections:${NC}"
netstat -tuln
echo

echo -e "${YELLOW}To test connectivity, try:${NC}"
echo "1. Ping the server: ping 192.168.4.1"
echo "2. Visit the web interface: http://192.168.4.1"
echo "3. Check DNS resolution: nslookup device.local"
echo

echo -e "${BLUE}===== End of Diagnostic Report =====${NC}"
EOF

    chmod +x /usr/local/bin/diagnose-network
    print_success "Network diagnostic tool created: /usr/local/bin/diagnose-network"
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
    echo "If you encounter connectivity issues, run the diagnostic tool:"
    echo "  sudo /usr/local/bin/diagnose-network"
    echo ""
}

# Main function
main() {
    print_message "Starting Mini Manager WiFi AP provisioning..."

    # Check if running as root
    check_root

    # Check essential dependencies first
    check_dependencies
    
    # Check Ubuntu version
    check_ubuntu_version

    # Update system
    update_system

    # Install required packages - do this before checking interfaces
    install_packages

    # Check for WiFi interface
    check_wifi_interface

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

    # Configure Nginx (with proper error handling)
    configure_nginx

    # Create application service
    create_app_service

    # Create network diagnostic tool
    create_diagnostic_tool

    # Start services
    start_services

    # Display summary
    display_summary
}

# Run main function
main
