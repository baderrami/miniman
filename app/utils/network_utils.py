import subprocess
import re
import socket
import netifaces
import ipaddress
from typing import Dict, Any, Tuple, List, Optional

def get_interfaces() -> Dict[str, Dict[str, Any]]:
    """
    Get all network interfaces and their configurations
    
    Returns:
        Dict[str, Dict[str, Any]]: Dictionary of interfaces with their configurations
    """
    interfaces = {}
    
    try:
        # Get all interface names
        iface_names = netifaces.interfaces()
        
        for iface in iface_names:
            # Skip loopback interface
            if iface == 'lo':
                continue
                
            iface_info = {}
            addrs = netifaces.ifaddresses(iface)
            
            # Get IPv4 info if available
            if netifaces.AF_INET in addrs:
                inet_info = addrs[netifaces.AF_INET][0]
                iface_info['ip_address'] = inet_info.get('addr')
                iface_info['netmask'] = inet_info.get('netmask')
                
                # Determine if DHCP is used (this is a simplification)
                # In a real implementation, we would check DHCP client status
                iface_info['is_dhcp'] = not bool(inet_info.get('addr'))
            else:
                iface_info['ip_address'] = None
                iface_info['netmask'] = None
                iface_info['is_dhcp'] = True
            
            # Get gateway info
            gws = netifaces.gateways()
            if 'default' in gws and netifaces.AF_INET in gws['default']:
                gw_info = gws['default'][netifaces.AF_INET]
                if gw_info[1] == iface:
                    iface_info['gateway'] = gw_info[0]
                else:
                    iface_info['gateway'] = None
            else:
                iface_info['gateway'] = None
            
            # Get DNS servers (simplified - in real implementation we would parse /etc/resolv.conf)
            iface_info['dns_servers'] = "8.8.8.8,8.8.4.4"
            
            # Check if interface is active
            iface_info['is_active'] = is_interface_up(iface)
            
            interfaces[iface] = iface_info
            
        return interfaces
    except Exception as e:
        print(f"Error getting interfaces: {str(e)}")
        return {}

def is_interface_up(interface: str) -> bool:
    """
    Check if a network interface is up
    
    Args:
        interface (str): Interface name
        
    Returns:
        bool: True if interface is up, False otherwise
    """
    try:
        # Use subprocess to run ip link show
        result = subprocess.run(
            ['ip', 'link', 'show', interface],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Check if "UP" is in the output
        return "UP" in result.stdout
    except Exception:
        return False

def get_interface_status(interface: str) -> Dict[str, Any]:
    """
    Get detailed status of a network interface
    
    Args:
        interface (str): Interface name
        
    Returns:
        Dict[str, Any]: Interface status information
    """
    status = {
        'name': interface,
        'is_up': is_interface_up(interface),
        'ip_address': None,
        'netmask': None,
        'gateway': None,
        'mac_address': None,
        'rx_bytes': 0,
        'tx_bytes': 0,
        'rx_packets': 0,
        'tx_packets': 0,
        'errors': 0
    }
    
    try:
        # Get IP address info
        addrs = netifaces.ifaddresses(interface)
        if netifaces.AF_INET in addrs:
            inet_info = addrs[netifaces.AF_INET][0]
            status['ip_address'] = inet_info.get('addr')
            status['netmask'] = inet_info.get('netmask')
        
        # Get MAC address
        if netifaces.AF_LINK in addrs:
            link_info = addrs[netifaces.AF_LINK][0]
            status['mac_address'] = link_info.get('addr')
        
        # Get gateway
        gws = netifaces.gateways()
        if 'default' in gws and netifaces.AF_INET in gws['default']:
            gw_info = gws['default'][netifaces.AF_INET]
            if gw_info[1] == interface:
                status['gateway'] = gw_info[0]
        
        # Get statistics
        with open(f'/sys/class/net/{interface}/statistics/rx_bytes', 'r') as f:
            status['rx_bytes'] = int(f.read().strip())
        
        with open(f'/sys/class/net/{interface}/statistics/tx_bytes', 'r') as f:
            status['tx_bytes'] = int(f.read().strip())
        
        with open(f'/sys/class/net/{interface}/statistics/rx_packets', 'r') as f:
            status['rx_packets'] = int(f.read().strip())
        
        with open(f'/sys/class/net/{interface}/statistics/tx_packets', 'r') as f:
            status['tx_packets'] = int(f.read().strip())
        
        with open(f'/sys/class/net/{interface}/statistics/rx_errors', 'r') as f:
            rx_errors = int(f.read().strip())
        
        with open(f'/sys/class/net/{interface}/statistics/tx_errors', 'r') as f:
            tx_errors = int(f.read().strip())
        
        status['errors'] = rx_errors + tx_errors
        
        return status
    except Exception as e:
        print(f"Error getting interface status: {str(e)}")
        return status

def configure_interface(interface: str, is_dhcp: bool = True, ip_address: Optional[str] = None,
                       netmask: Optional[str] = None, gateway: Optional[str] = None,
                       dns_servers: Optional[str] = None, is_active: bool = True) -> bool:
    """
    Configure a network interface
    
    Args:
        interface (str): Interface name
        is_dhcp (bool): Whether to use DHCP
        ip_address (str, optional): Static IP address
        netmask (str, optional): Network mask
        gateway (str, optional): Default gateway
        dns_servers (str, optional): DNS servers (comma-separated)
        is_active (bool): Whether the interface should be active
        
    Returns:
        bool: True if configuration was successful, False otherwise
    """
    try:
        # Set interface up or down
        if is_active:
            subprocess.run(['ip', 'link', 'set', interface, 'up'], check=True)
        else:
            subprocess.run(['ip', 'link', 'set', interface, 'down'], check=True)
            return True  # If we're setting the interface down, we're done
        
        # Configure IP address
        if is_dhcp:
            # Use DHCP (this is simplified - in a real implementation we would use dhclient)
            subprocess.run(['dhclient', '-r', interface], check=True)
            subprocess.run(['dhclient', interface], check=True)
        else:
            # Use static IP
            if not ip_address or not netmask:
                raise ValueError("IP address and netmask are required for static configuration")
            
            # Convert netmask to CIDR notation
            netmask_cidr = ipaddress.IPv4Network(f'0.0.0.0/{netmask}').prefixlen
            
            # Remove any existing IP addresses
            subprocess.run(['ip', 'addr', 'flush', 'dev', interface], check=True)
            
            # Add new IP address
            subprocess.run(['ip', 'addr', 'add', f'{ip_address}/{netmask_cidr}', 'dev', interface], check=True)
            
            # Set default gateway if provided
            if gateway:
                # Remove existing default route
                try:
                    subprocess.run(['ip', 'route', 'del', 'default'], check=False)
                except:
                    pass
                
                # Add new default route
                subprocess.run(['ip', 'route', 'add', 'default', 'via', gateway], check=True)
            
            # Configure DNS servers if provided (simplified - in real implementation we would update /etc/resolv.conf)
            if dns_servers:
                with open('/etc/resolv.conf', 'w') as f:
                    for dns in dns_servers.split(','):
                        f.write(f"nameserver {dns.strip()}\n")
        
        return True
    except Exception as e:
        print(f"Error configuring interface: {str(e)}")
        return False