# Mini Manager Architecture Design
## System Overview
The Mini Manager architecture consists of two main components working together to provide a comprehensive network management solution:
1. **WiFi Access Point Provisioning System**: Transforms a Linux device into a fully functional WiFi access point
2. **Flask Web Application**: Delivers a browser-based management interface accessible through the WiFi network

This design enables network administrators to manage devices through an intuitive web interface while providing a stable WiFi connection to client devices.
## Architecture Components
### 1. WiFi Access Point System
#### Hardware Requirements
- Linux device (physical or virtual) with:
    - WiFi interface that supports AP mode
    - At least one additional network interface for internet connectivity (optional)
    - Minimum 1GB RAM
    - Minimum 8GB storage

#### Software Components
- **hostapd**: Creates and manages the WiFi access point
- **dnsmasq**: Provides DHCP and DNS services to connected clients
- **iptables**: Manages network traffic routing and firewall rules
- **systemd-networkd**: Handles network interface configuration
- **Custom iptables persistence**: Ensures firewall rules survive system reboots

#### Network Configuration
- WiFi interface (wlan0) configured with static IP (192.168.50.1/24)
- DHCP server assigns IPs in range 192.168.50.10-100
- Traffic from port 80 redirected to the application port (8000)
- IP forwarding enabled for proper routing between interfaces
- DNS resolution configured to use external DNS servers (8.8.8.8, 8.8.4.4)
- Conflicts with systemd-resolved handled automatically

### 2. Flask Web Application
#### Software Stack
- **Backend**:
    - Python 3.x with Flask framework
    - SQLite database for configuration storage
    - Gunicorn as WSGI server
    - Flask extensions for authentication and database management

- **Frontend**:
    - Bootstrap 5.2.3 for responsive design
    - Chart.js 3.9.1 for data visualization
    - Bootstrap Icons for user interface elements
    - Custom CSS/JS for specific functionality
    - All static resources cached locally for offline operation

#### Core Components
1. **Authentication Module**
    - Secure login system with session management
    - Default admin account with configurable credentials
    - Role-based access control for different operations

2. **Network Management Module**
    - Interface display and configuration
    - WiFi settings management
    - IP configuration tools
    - Network diagnostics

3. **System Management Module**
    - Service status monitoring
    - System resource monitoring
    - Configuration backup and restore
    - System reset functionality

4. **API Layer**
    - RESTful endpoints for programmatic control
    - Status reporting interfaces
    - Configuration management endpoints

### 3. Integration Layer
- **Nginx** serves as a reverse proxy, routing requests from port 80 to the application
- **Systemd Services** ensure components start in the correct order and restart on failure
- **Custom Scripts** facilitate system reset and maintenance operations

## System Workflow
### Provisioning Process
1. The provisioning script installs and configures all required components
2. WiFi access point is established using hostapd with SSID "miniman"
3. Network services are configured to provide DHCP and DNS to clients
4. Flask application is installed within a Python virtual environment
5. Static resources are downloaded and configured for offline operation
6. Services are started and enabled for automatic startup

### Runtime Operation
1. Device broadcasts WiFi network "miniman"
2. Clients connect to the WiFi network
3. Clients receive IP addresses via DHCP
4. Users access the web interface at [http://192.168.50.1](http://192.168.50.1)
5. Authentication system verifies user credentials
6. Web interface provides access to all management functions

### System Reset Process
1. Administrator initiates reset via web interface or command line
2. Reset script stops all services
3. Configuration files are removed or restored to defaults
4. Application database is reset (if applicable)
5. System reboots to apply changes

## Directory Structure
``` 
/opt/miniman/                  # Application root directory
├── app/                       # Flask application
│   ├── __init__.py            # Application initialization
│   ├── auth/                  # Authentication module
│   ├── network/               # Network management module
│   ├── system/                # System management module
│   ├── static/                # Static resources
│   │   ├── css/               # CSS files including Bootstrap
│   │   ├── js/                # JavaScript files including Chart.js
│   │   ├── fonts/             # Font files for Bootstrap Icons
│   │   └── img/               # Image resources
│   └── templates/             # HTML templates
├── instance/                  # Instance-specific data (database)
├── venv/                      # Python virtual environment
├── requirements.txt           # Python dependencies
└── run.py                     # Application entry point

/etc/hostapd/                  # WiFi access point configuration
/etc/dnsmasq.conf              # DHCP and DNS configuration
/etc/systemd/network/          # Network interface configuration
/etc/iptables/                 # Firewall rules
/etc/nginx/sites-enabled/      # Web server configuration
/usr/local/bin/system-reset    # System reset script
```
## Security Architecture
### Network Security
- WPA2 encryption for WiFi network
- Separate control plane (web interface) from data plane (client traffic)
- Firewall rules to restrict access to management interface
- DNS and DHCP services bound only to local interfaces

### Application Security
- Authentication required for all management functions
- Session-based security with CSRF protection
- Input validation for all user-submitted data
- Privilege separation between web server and application processes
- Secure handling of sensitive configuration data

### System Security
- Regular operating system updates
- Minimal software footprint to reduce attack surface
- Service isolation through systemd configuration
- Restricted permissions on configuration files and scripts

## Resource Loading Modes
The Mini Manager supports two modes for loading static resources:

### Production Mode (Default)
Designed for offline operation with no internet connectivity:
1. All static resources (CSS, JavaScript, fonts, images) are loaded locally
2. Bootstrap and Chart.js libraries are stored on the device
3. Font files for Bootstrap Icons are downloaded during provisioning
4. Web interface remains fully functional without internet access

### Development Mode
Optimized for development environments with internet connectivity:
1. Static resources (Bootstrap, Chart.js, Bootstrap Icons) are loaded from CDNs
2. Custom resources (application-specific CSS/JS) are still loaded locally
3. Fallback mechanisms automatically load local resources if CDNs are unavailable
4. Reduces local storage requirements and ensures latest library versions

The mode is controlled through the `FLASK_CONFIG` environment variable, with `production` mode as the default for offline operation.

## Scalability Considerations
The architecture can be extended in several ways:
1. **Multi-device Management**: Extend the application to manage multiple remote devices
2. **Advanced Network Features**: Add VPN, firewall management, and traffic shaping
3. **Monitoring System**: Incorporate time-series data storage for performance metrics
4. **User Management**: Add multiple user accounts with different permission levels
5. **API Integration**: Develop integrations with other network management tools

## Implementation Details
### Service Management
- Systemd unit files ensure proper startup order
- Services are configured to restart automatically on failure
- Runtime directories are properly managed with appropriate permissions
- Tempfiles configuration handles temporary runtime data

### Database Management
- SQLite database stores configuration and user data
- Database initialization script creates schema on first run
- Database backup functionality for configuration persistence
- Database reset capability for factory restore

### Interface Management
- Web interface adapts to different screen sizes
- Clear visual indicators for system status
- Intuitive navigation for accessing different functions
- Real-time updates for critical status information

## Test and Verification
The system includes a comprehensive test procedure:
1. **Component Testing**: Verify each service is functioning correctly
2. **Integration Testing**: Ensure all components work together properly
3. **Network Testing**: Validate WiFi, DHCP, and DNS functionality
4. **Application Testing**: Verify all web interface features
5. **Offline Testing**: Confirm operation without internet connectivity
6. **Reset Testing**: Validate the system reset functionality

This architecture provides a complete solution for deploying and managing WiFi access points with an intuitive web interface, balancing functionality, security, and ease of use.
