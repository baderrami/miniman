# Mini Manager
## Overview
Mini Manager is an automated solution for turning Linux devices into fully functional WiFi access points with a web-based management interface. The system provides network administrators with an intuitive way to configure and monitor network devices through a browser, all while maintaining a stable WiFi connection for client devices.
## Key Features
- **Automated WiFi Access Point Provisioning**: Transform any compatible Linux device into a WiFi hotspot
- **Web-Based Management Interface**: Control your device through an intuitive browser interface
- **Network Management Tools**: Configure interfaces, monitor network status, and diagnose issues
- **Offline Operation**: Fully functional without internet connectivity
- **System Reset Functionality**: Easily restore to factory defaults when needed
- **Local Resource Caching**: All required resources stored locally for reliability

## Hardware Requirements
- Linux device (physical or virtual) with:
    - WiFi interface that supports AP mode
    - Minimum 1GB RAM
    - Minimum 8GB storage
    - Internet connection during initial setup

## Getting Started
### Quick Installation
1. Download the provisioning script:
``` bash
wget https://github.com/baderrami/miniman/raw/main/provisioning_script.sh
```
1. Make the script executable:
``` bash
chmod +x provisioning_script.sh
```
1. Run the script as root:
``` bash
sudo ./provisioning_script.sh
```
1. Once complete, connect to the WiFi network "miniman" with password "123456789"
2. Access the web interface at [http://192.168.50.1](http://192.168.50.1)

### Default Credentials
- **WiFi Network**: miniman
- **WiFi Password**: 123456789
- **Web Interface Username**: admin
- **Web Interface Password**: admin

**Important**: Change the default passwords immediately after installation!
## Documentation
### Architecture
The Mini Manager follows a two-component architecture:
1. **WiFi Access Point Provisioning System**: Configures the device to function as a WiFi access point using hostapd, dnsmasq, and iptables
2. **Flask Web Application**: Provides the management interface through a responsive web application

For detailed information about the system design, component interaction, and implementation details, please refer to the [Architecture Document](architecture.md).
### Provisioning Manual
The [Provisioning Manual](provisioning_manual.md) provides comprehensive instructions for:
- System requirements and prerequisites
- Detailed installation steps
- Customization options
- Troubleshooting guidance
- Post-provisioning configuration
- Security considerations
- Maintenance procedures

## Usage Guide
### Network Management
1. Connect to the "miniman" WiFi network
2. Navigate to [http://192.168.50.1](http://192.168.50.1) in your browser
3. Log in with your credentials
4. Use the dashboard to monitor system status
5. Configure network interfaces through the Network menu
6. Adjust WiFi settings as needed

### System Management
The system provides several management functions:
- **Service Control**: Start, stop, or restart system services
- **Configuration Backup**: Export your settings for safekeeping
- **Configuration Restore**: Import previously saved settings
- **System Reset**: Restore to factory defaults

### Advanced Usage
Power users can customize the Mini Manager by:
1. Editing configuration files in and `/etc/hostapd/``/etc/dnsmasq.conf`
2. Modifying the web application in `/opt/miniman/`
3. Creating custom scripts for specialized functionality
4. Extending the application with additional Python modules

## Contributing
We welcome contributions to the Mini Manager project! Here's how you can help:
### Pull Requests
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup
To set up a development environment:
``` bash
# Clone the repository
git clone https://github.com/baderrami/miniman.git
cd miniman

# Create a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the development server (uses CDN for static resources)
export FLASK_CONFIG=development
python run.py

# Or run in production mode (uses local static resources)
export FLASK_CONFIG=production
python run.py
```

### Resource Loading Modes
Mini Manager supports two modes for loading static resources:

1. **Production Mode** (default): All static resources (CSS, JavaScript, fonts) are loaded locally from the server. This ensures the application works without internet connectivity, making it suitable for offline environments.

2. **Development Mode**: Static resources are loaded from Content Delivery Networks (CDNs). This mode is useful during development to ensure you're using the latest versions of libraries and to reduce local storage requirements.

To switch between modes:
```bash
# For development mode (using CDNs)
export FLASK_CONFIG=development
python run.py

# For production mode (using local resources)
export FLASK_CONFIG=production
python run.py
```

The application includes fallback mechanisms to load resources locally if CDNs are unavailable in development mode.
### Discussion
Have ideas or questions? Join the discussion on our [GitHub Discussions](https://github.com/baderrami/miniman/discussions) page. This is the perfect place to:
- Propose new features
- Discuss implementation approaches
- Share your use cases
- Get help with customization
- Connect with other users

## Troubleshooting
Common issues and their solutions:
### WiFi Access Point Issues
If the WiFi network isn't broadcasting:
``` bash
sudo systemctl status hostapd
sudo journalctl -u hostapd
```
### Web Interface Issues
If you can't access the web interface:
``` bash
sudo systemctl status nginx
sudo systemctl status miniman
sudo journalctl -u miniman
```
For additional troubleshooting guidance, refer to the [Provisioning Manual](provisioning_manual.md#troubleshooting).
## License
Mini Manager is released under the MIT License. See the [LICENSE](LICENSE) file for details.
``` 
MIT License

Copyright (c) 2023 Bader Rami

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
## Acknowledgments
- The Flask team for their excellent web framework
- The hostapd and dnsmasq projects for their reliable network services
- All contributors who have helped improve Mini Manager

**Project Home**: [https://github.com/baderrami/miniman](https://github.com/baderrami/miniman)
**Report Issues**: [https://github.com/baderrami/miniman/issues](https://github.com/baderrami/miniman/issues)
**Discussions**: [https://github.com/baderrami/miniman/discussions](https://github.com/baderrami/miniman/discussions)
