#!/bin/bash
set -e

# === CONFIGURATION ===
SSID="miniman"
PASSPHRASE="123456789"
STATIC_IP="192.168.50.1/24"
HTTP_PORT=8000
APP_DIR="/opt/miniman"
GIT_REPO="https://github.com/baderrami/miniman.git"  # Set to empty to skip Git clone

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

# === Ensure required packages are installed ===
print_message "Installing required packages..."
apt update
apt install -y hostapd dnsmasq iptables \
    wireless-tools curl python3-pip python3-venv git nginx \
    apt-transport-https ca-certificates gnupg lsb-release

# Install Docker if not already installed
if ! command -v docker &> /dev/null; then
    print_message "Installing Docker..."
    # Add Docker's official GPG key
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

    # Set up the stable repository
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

    # Install Docker Engine
    apt update
    apt install -y docker-ce docker-ce-cli containerd.io

    # Enable and start Docker service
    systemctl enable docker
    systemctl start docker

    print_success "Docker installed successfully"
else
    print_message "Docker is already installed"
fi

# Install Docker Compose if not already installed
if ! command -v docker-compose &> /dev/null; then
    print_message "Installing Docker Compose..."
    apt install -y docker-compose-plugin
    print_success "Docker Compose installed successfully"
else
    print_message "Docker Compose is already installed"
fi

# Setup custom iptables persistence instead of using iptables-persistent package
print_message "Setting up custom iptables persistence..."
# Create rules directories
mkdir -p /etc/iptables

# Create systemd service for loading iptables rules at boot
IPTABLES_SERVICE="/etc/systemd/system/iptables-restore.service"
if [ ! -f "$IPTABLES_SERVICE" ]; then
  print_message "Creating iptables-restore service..."
  cat <<EOF >"$IPTABLES_SERVICE"
[Unit]
Description=Restore iptables rules
After=network.target

[Service]
Type=oneshot
ExecStart=/bin/sh -c "/sbin/iptables-restore < /etc/iptables/rules.v4 || true"
ExecStart=/bin/sh -c "/sbin/ip6tables-restore < /etc/iptables/rules.v6 || true"
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

  # Enable the service
  systemctl enable iptables-restore.service
fi

# Save current rules (creating the files if they don't exist)
iptables-save > /etc/iptables/rules.v4
ip6tables-save > /etc/iptables/rules.v6

# === Enable systemd-networkd ===
systemctl enable systemd-networkd
systemctl start systemd-networkd

# === Enable & unmask services ===
systemctl unmask hostapd
systemctl enable hostapd
systemctl unmask dnsmasq
systemctl enable dnsmasq

# === Configure wlan0 static IP if not already done ===
WLAN0_NETWORK_FILE="/etc/systemd/network/10-wlan0.network"
if ! grep -q "$STATIC_IP" "$WLAN0_NETWORK_FILE" 2>/dev/null; then
  print_message "Setting wlan0 static IP..."
  cat <<EOF >"$WLAN0_NETWORK_FILE"
[Match]
Name=wlan0

[Network]
Address=$STATIC_IP
DHCPServer=yes
EOF
fi

WLAN0_LINK_FILE="/etc/systemd/network/10-wlan0.link"
if [ ! -f "$WLAN0_LINK_FILE" ]; then
  print_message "Setting wlan0 link config..."
  cat <<EOF >"$WLAN0_LINK_FILE"
[Match]
Name=wlan0

[Link]
WakeOnLan=off
EOF
fi

# === Configure hostapd only if not already matching ===
HOSTAPD_CONF="/etc/hostapd/hostapd.conf"
if ! grep -q "ssid=$SSID" "$HOSTAPD_CONF" 2>/dev/null; then
  print_message "Writing hostapd config..."
  cat <<EOF >"$HOSTAPD_CONF"
ctrl_interface=/var/run/hostapd
macaddr_acl=0
auth_algs=1
country_code=US
require_ht=0
wmm_enabled=1

driver=nl80211
interface=wlan0
hw_mode=g
channel=6
ssid=$SSID
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase=$PASSPHRASE
wpa_key_mgmt=WPA-PSK
wpa_pairwise=CCMP
rsn_pairwise=CCMP
EOF
fi

# === Point hostapd to config if not already ===
if ! grep -q "DAEMON_CONF=" /etc/default/hostapd; then
  echo 'DAEMON_CONF="/etc/hostapd/hostapd.conf"' >> /etc/default/hostapd
fi

# === Check for systemd-resolved conflict and handle it ===
print_message "Checking for DNS port conflicts..."
if lsof -i :53 | grep -q "systemd-r"; then
  print_message "Detected systemd-resolved using port 53, reconfiguring..."

  # Disable systemd-resolved service
  systemctl stop systemd-resolved
  systemctl disable systemd-resolved

  # Fix resolv.conf if it's a symlink to systemd-resolved
  if [ -L /etc/resolv.conf ]; then
    print_message "Fixing resolv.conf configuration..."
    rm -f /etc/resolv.conf
    echo "nameserver 8.8.8.8" > /etc/resolv.conf
    echo "nameserver 8.8.4.4" >> /etc/resolv.conf
  fi
fi

# === Configure dnsmasq (create custom if original exists) ===
DNSMASQ_CONF="/etc/dnsmasq.conf"
if [ -f "$DNSMASQ_CONF" ] && ! grep -q "interface=wlan0" "$DNSMASQ_CONF"; then
  print_message "Backing up existing dnsmasq.conf..."
  mv "$DNSMASQ_CONF" "$DNSMASQ_CONF.orig"
fi

if [ ! -f "$DNSMASQ_CONF" ]; then
  print_message "Writing dnsmasq config..."
  cat <<EOF >"$DNSMASQ_CONF"
# Only bind to the wireless interface
interface=wlan0
# Don't use /etc/resolv.conf
no-resolv
# Use Google's DNS servers
server=8.8.8.8
server=8.8.4.4
# Set the domain
domain=local
# Define the DHCP range
dhcp-range=192.168.50.10,192.168.50.100,12h
# Set the gateway address
dhcp-option=3,192.168.50.1
# Set DNS server address
dhcp-option=6,192.168.50.1
# Add custom domain name
address=/mini.man/192.168.50.1
EOF
fi

# === Enable IP forwarding (persistently) ===
SYSCTL_FILE="/etc/sysctl.conf"
if ! grep -q "net.ipv4.ip_forward=1" "$SYSCTL_FILE"; then
  print_message "Enabling IP forwarding..."
  echo "net.ipv4.ip_forward=1" >> "$SYSCTL_FILE"
  sysctl -w net.ipv4.ip_forward=1
fi

# === Add NAT rule if not already present ===
if ! iptables -t nat -C PREROUTING -i wlan0 -p tcp --dport 80 -j REDIRECT --to-port $HTTP_PORT 2>/dev/null; then
  print_message "Adding iptables NAT rule to redirect HTTP to port $HTTP_PORT"
  iptables -t nat -A PREROUTING -i wlan0 -p tcp --dport 80 -j REDIRECT --to-port $HTTP_PORT
  # Save the updated rules to make them persistent
  iptables-save > /etc/iptables/rules.v4
else
  print_message "iptables NAT rule already exists, skipping"
fi

# === Python App Installation ===
print_message "Setting up Python application..."

# Create application directory if it doesn't exist
if [ ! -d "$APP_DIR" ]; then
  mkdir -p "$APP_DIR"
fi

# Clone repository if provided and directory is empty
if [ -n "$GIT_REPO" ] && [ -z "$(ls -A $APP_DIR)" ]; then
  print_message "Cloning application repository..."
  GIT_TERMINAL_PROMPT=0 git clone --depth=1 --branch multi-env "$GIT_REPO" "$APP_DIR" || print_warning "Failed to clone repository. Continuing without application code."
elif [ -n "$GIT_REPO" ] && [ -d "$APP_DIR/.git" ]; then
  print_message "Updating existing repository..."
  cd "$APP_DIR"
  GIT_TERMINAL_PROMPT=0 git pull || print_warning "Failed to update repository. Continuing with existing code."
elif [ -n "$GIT_REPO" ]; then
  print_warning "Directory $APP_DIR exists and is not empty."
  read -p "What would you like to do? [s]kip, [b]ackup and replace, [p]ull updates: " APP_DIR_ACTION
  APP_DIR_ACTION=${APP_DIR_ACTION:-s}

  case "$APP_DIR_ACTION" in
    b|B)
      print_message "Backing up existing directory..."
      mv "$APP_DIR" "${APP_DIR}-backup-$(date +%Y%m%d%H%M%S)"
      mkdir -p "$APP_DIR"
      GIT_TERMINAL_PROMPT=0 git clone --depth=1 --branch multi-env "$GIT_REPO" "$APP_DIR" || print_warning "Failed to clone repository. Continuing without application code."
      ;;
    p|P)
      if [ -d "$APP_DIR/.git" ]; then
        print_message "Pulling updates..."
        cd "$APP_DIR"
        GIT_TERMINAL_PROMPT=0 git pull || print_warning "Failed to pull updates. Continuing with existing code."
      else
        print_warning "Not a git repository. Cannot pull updates."
        read -p "Backup and replace instead? [y/N]: " BACKUP_REPLACE
        if [[ "$BACKUP_REPLACE" =~ ^[Yy]$ ]]; then
          mv "$APP_DIR" "${APP_DIR}-backup-$(date +%Y%m%d%H%M%S)"
          mkdir -p "$APP_DIR"
          GIT_TERMINAL_PROMPT=0 git clone --depth=1 --branch multi-env "$GIT_REPO" "$APP_DIR" || print_warning "Failed to clone repository. Continuing without application code."
        fi
      fi
      ;;
    *)
      print_message "Skipping repository clone/update."
      ;;
  esac
fi

# Setup Python virtual environment if it doesn't exist
if [ ! -d "$APP_DIR/venv" ]; then
  print_message "Creating Python virtual environment..."
  cd "$APP_DIR"
  python3 -m venv venv

  # Install requirements if requirements.txt exists
  if [ -f "$APP_DIR/requirements.txt" ]; then
    print_message "Installing Python dependencies..."
    source "$APP_DIR/venv/bin/activate"
    pip install -r requirements.txt
    deactivate
  fi
fi

# Ensure all static resources are available locally
print_message "Ensuring all static resources are available locally..."

# Create fonts directory if it doesn't exist
mkdir -p "$APP_DIR/app/static/fonts"

# Download Bootstrap Icons font files if they don't exist or are placeholders
if [ ! -f "$APP_DIR/app/static/fonts/bootstrap-icons.woff2" ] || [ ! -s "$APP_DIR/app/static/fonts/bootstrap-icons.woff2" ] || grep -q "placeholder" "$APP_DIR/app/static/fonts/bootstrap-icons.woff2"; then
  print_message "Downloading Bootstrap Icons font files..."
  curl -s -L -o "$APP_DIR/app/static/fonts/bootstrap-icons.woff2" "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/fonts/bootstrap-icons.woff2"
  curl -s -L -o "$APP_DIR/app/static/fonts/bootstrap-icons.woff" "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/fonts/bootstrap-icons.woff"

  # Update CSS to reference local font files if needed
  if ! grep -q "font-face" "$APP_DIR/app/static/css/bootstrap-icons.css"; then
    print_message "Updating bootstrap-icons.css to use local font files..."
    sed -i '1i @font-face {\n  font-family: "bootstrap-icons";\n  src: url("../fonts/bootstrap-icons.woff2") format("woff2"),\n       url("../fonts/bootstrap-icons.woff") format("woff");\n}\n' "$APP_DIR/app/static/css/bootstrap-icons.css"

    # Add font-family to the CSS selectors if not already present
    if ! grep -q "font-family: \"bootstrap-icons\"" "$APP_DIR/app/static/css/bootstrap-icons.css"; then
      sed -i 's/\.bi::before,/\.bi::before,/; s/{/{\n  font-family: "bootstrap-icons";/' "$APP_DIR/app/static/css/bootstrap-icons.css"
    fi
  fi
fi

# Download full versions of required static files
print_message "Downloading full versions of required static files..."

# Bootstrap CSS
print_message "Downloading Bootstrap CSS..."
curl -s -L -o "$APP_DIR/app/static/css/bootstrap.min.css" "https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/css/bootstrap.min.css"

# Bootstrap JS
print_message "Downloading Bootstrap JS..."
curl -s -L -o "$APP_DIR/app/static/js/bootstrap.bundle.min.js" "https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/js/bootstrap.bundle.min.js"

# Chart.js
print_message "Downloading Chart.js..."
curl -s -L -o "$APP_DIR/app/static/js/chart.min.js" "https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js"

# Ensure all required static files exist and have content
REQUIRED_FILES=(
  "css/bootstrap.min.css"
  "js/bootstrap.bundle.min.js"
  "js/chart.min.js"
  "fonts/bootstrap-icons.woff"
  "fonts/bootstrap-icons.woff2"
)

for file in "${REQUIRED_FILES[@]}"; do
  if [ ! -f "$APP_DIR/app/static/$file" ] || [ ! -s "$APP_DIR/app/static/$file" ]; then
    print_error "Missing or empty required static file: $file"
  else
    print_success "Verified static file: $file"
  fi
done

# Initialize database
if [ -f "$APP_DIR/run.py" ]; then
  print_message "Initializing database..."
  cd "$APP_DIR"
  source venv/bin/activate
  export FLASK_APP=run.py
  flask init-db || print_warning "Database initialization failed or already initialized."
  deactivate
fi

# Configure systemd service for the application
APP_SERVICE="/etc/systemd/system/miniman.service"
# Always recreate the service file to ensure it has the correct paths
print_message "Creating application service..."

# Create runtime directory for gunicorn with proper permissions
print_message "Creating runtime directory for gunicorn..."
mkdir -p /var/run/miniman
chown www-data:www-data /var/run/miniman
chmod 755 /var/run/miniman

# Create service file with expanded variables
cat <<EOF >"$APP_SERVICE"
[Unit]
Description=Mini Manager Application
After=network.target

[Service]
User=www-data
WorkingDirectory=/opt/miniman
RuntimeDirectory=miniman
# Add runtime directory settings to avoid permission issues
ExecStart=/opt/miniman/venv/bin/gunicorn -w 4 -b 0.0.0.0:8000 --pid /var/run/miniman/gunicorn.pid --worker-tmp-dir /var/run/miniman "run:app"
Restart=always
RestartSec=5
# Set environment variables for the application
# FLASK_CONFIG must be one of the configurations defined in app/config.py
# Valid values are 'development', 'production', or 'default'
Environment="PYTHONUNBUFFERED=1"
Environment="PYTHONIOENCODING=UTF-8"
Environment="FLASK_CONFIG=production"

[Install]
WantedBy=multi-user.target
EOF

# Check if gunicorn is installed, install if not
if ! "$APP_DIR/venv/bin/pip" list | grep -q "gunicorn"; then
  print_message "Installing gunicorn..."
  source "$APP_DIR/venv/bin/activate"
  pip install gunicorn
  deactivate
fi

# Set proper permissions for the application directory
print_message "Setting proper permissions for application directory..."
chown -R www-data:www-data "$APP_DIR"
chmod -R 755 "$APP_DIR"

# Ensure instance directory exists with proper permissions
mkdir -p "$APP_DIR/instance"
chown -R www-data:www-data "$APP_DIR/instance"
chmod -R 755 "$APP_DIR/instance"

# Enable and start the service
systemctl enable miniman.service
systemctl start miniman.service || print_warning "Failed to start application service."

# Configure Nginx (optional, as we're using direct Gunicorn binding)
NGINX_CONF="/etc/nginx/sites-available/miniman"
if [ ! -f "$NGINX_CONF" ]; then
  print_message "Setting up Nginx configuration..."

  # First remove the default site if it exists to avoid conflicts
  if [ -f "/etc/nginx/sites-enabled/default" ]; then
    print_message "Removing default Nginx site to avoid conflicts..."
    rm -f /etc/nginx/sites-enabled/default
  fi

  cat <<EOF >"$NGINX_CONF"
server {
    listen 80 default_server;
    server_name miniman.local mini.man 192.168.50.1;

    # Increase timeouts for slow connections
    proxy_connect_timeout 300s;
    proxy_send_timeout 300s;
    proxy_read_timeout 300s;

    location / {
        proxy_pass http://127.0.0.1:$HTTP_PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # Ensure this path exactly matches your application's static files structure
    location /static/ {
        alias /opt/miniman/app/static/;
        expires 30d;
        add_header Cache-Control "public, max-age=2592000";
        access_log off;
    }
}
EOF

  # Enable the site
  if [ ! -f "/etc/nginx/sites-enabled/miniman" ]; then
    ln -s "$NGINX_CONF" "/etc/nginx/sites-enabled/"
  fi

  # Test and restart Nginx
  nginx -t && systemctl restart nginx || print_warning "Nginx configuration test failed."
fi

# === Restart network & services ===
print_message "Restarting services..."
systemctl restart systemd-networkd || print_warning "Failed to restart systemd-networkd, continuing..."
systemctl restart hostapd || print_warning "Failed to restart hostapd, continuing..."

# Check one more time for port 53 conflicts
if lsof -i :53 | grep -v dnsmasq; then
  print_error "Port 53 is still in use by another process. Attempting to force restart dnsmasq..."
  # Try to kill any process using port 53
  lsof -i :53 | awk 'NR>1 {print $2}' | xargs -r kill -9
  sleep 2
fi

# Restart dnsmasq with error handling
if ! systemctl restart dnsmasq; then
  print_error "Failed to start dnsmasq. This may affect DHCP functionality."
  print_warning "You may need to manually configure DNS and DHCP after setup."
else
  print_success "dnsmasq started successfully."
fi

# === System Reset Functionality ===
RESET_SCRIPT="/usr/local/bin/system-reset"
if [ ! -f "$RESET_SCRIPT" ]; then
  print_message "Creating system reset functionality..."

  # Create the reset script
  cat <<EOF >"$RESET_SCRIPT"
#!/bin/bash
echo "Resetting system to factory defaults..."
systemctl stop miniman
systemctl stop nginx
systemctl stop hostapd
systemctl stop dnsmasq

# Remove configuration files
rm -f /etc/hostapd/hostapd.conf
rm -f /etc/dnsmasq.conf
rm -f /etc/systemd/network/10-wlan0.network
rm -f /etc/systemd/network/10-wlan0.link

# Reset database (if applicable)
if [ -d "$APP_DIR" ]; then
  cd "$APP_DIR"
  if [ -f "instance/app.db" ]; then
    rm -f instance/app.db
  fi
fi

echo "System reset complete. Rebooting..."
reboot
EOF

  # Make the script executable
  chmod +x "$RESET_SCRIPT"
  print_success "System reset functionality created at $RESET_SCRIPT"
fi

# === Final Checks and Fixes ===
print_message "Performing final checks and fixes..."

# Note: The miniman.service file uses full paths instead of variables
# because systemd does not expand shell variables in service files.
# This prevents the 'status=203/EXEC' error that occurs when systemd
# cannot find the executable specified in ExecStart.
#
# The service file is always recreated during provisioning to ensure
# it has the correct hardcoded paths, even if it already exists.

# Check if miniman service is running correctly
if ! systemctl is-active --quiet miniman.service; then
  print_warning "miniman service is not running correctly. Attempting to fix common issues..."

  # Create a systemd tempfiles configuration for miniman
  cat <<EOF >/etc/tmpfiles.d/miniman.conf
d /var/run/miniman 0755 www-data www-data -
EOF

  # Apply tempfiles configuration
  systemd-tmpfiles --create

  # Restart the service
  systemctl restart miniman.service

  print_message "If the service still fails, check logs with: journalctl -u miniman.service"
fi

# Restart nginx to apply all configuration changes
systemctl restart nginx || print_warning "Failed to restart nginx"

# === Final Output ===
print_success "
✅ Mini Manager setup complete!
   - SSID: $SSID
   - IP: $STATIC_IP (subnet mask 255.255.255.0)
   - Web application running on port $HTTP_PORT
   - HTTP traffic on port 80 is redirected to port $HTTP_PORT

👉 Connect to the WiFi network '$SSID' with password '$PASSPHRASE'
   Then access the web interface at http://192.168.50.1 or http://mini.man

📝 Default credentials:
   - Username: admin
   - Password: admin (change immediately after first login)

🔄 To reset the system to factory defaults, run: sudo $RESET_SCRIPT
"
