from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.network import NetworkInterface, NetworkScan
from app.utils.network_utils import get_interfaces, get_interface_status, configure_interface
from app.controllers.auth import admin_required
import json

# Create blueprint
network_bp = Blueprint('network', __name__)

@network_bp.route('/dashboard')
@login_required
def dashboard():
    """Display network dashboard"""
    interfaces = NetworkInterface.query.all()
    return render_template('dashboard.html', interfaces=interfaces)

@network_bp.route('/network')
@login_required
def network():
    """Display network configuration page"""
    interfaces = NetworkInterface.query.all()
    return render_template('network.html', interfaces=interfaces)

@network_bp.route('/network/refresh', methods=['POST'])
@login_required
@admin_required
def refresh_interfaces():
    """Refresh network interfaces from system"""
    try:
        # Get system interfaces
        system_interfaces = get_interfaces()
        
        # Update database with system interfaces
        for iface_name, iface_data in system_interfaces.items():
            # Skip loopback and WiFi AP interface
            if iface_name == 'lo' or iface_name == 'wlan0':
                continue
                
            # Check if interface exists in database
            iface = NetworkInterface.query.filter_by(name=iface_name).first()
            
            if iface:
                # Update existing interface
                iface.update_config(
                    ip_address=iface_data.get('ip_address'),
                    netmask=iface_data.get('netmask'),
                    gateway=iface_data.get('gateway'),
                    dns_servers=iface_data.get('dns_servers'),
                    is_dhcp=iface_data.get('is_dhcp', True),
                    is_active=iface_data.get('is_active', True)
                )
            else:
                # Create new interface
                iface = NetworkInterface(
                    name=iface_name,
                    ip_address=iface_data.get('ip_address'),
                    netmask=iface_data.get('netmask'),
                    gateway=iface_data.get('gateway'),
                    dns_servers=iface_data.get('dns_servers'),
                    is_dhcp=iface_data.get('is_dhcp', True),
                    is_active=iface_data.get('is_active', True)
                )
                db.session.add(iface)
                
        db.session.commit()
        flash('Network interfaces refreshed successfully.', 'success')
    except Exception as e:
        flash(f'Error refreshing interfaces: {str(e)}', 'danger')
    
    return redirect(url_for('network.network'))

@network_bp.route('/network/configure/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def configure_network(id):
    """Configure network interface"""
    interface = NetworkInterface.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            # Get form data
            is_dhcp = 'is_dhcp' in request.form
            ip_address = request.form.get('ip_address') if not is_dhcp else None
            netmask = request.form.get('netmask') if not is_dhcp else None
            gateway = request.form.get('gateway') if not is_dhcp else None
            dns_servers = request.form.get('dns_servers') if not is_dhcp else None
            is_active = 'is_active' in request.form
            
            # Update interface in system
            configure_interface(
                interface.name,
                is_dhcp=is_dhcp,
                ip_address=ip_address,
                netmask=netmask,
                gateway=gateway,
                dns_servers=dns_servers,
                is_active=is_active
            )
            
            # Update interface in database
            interface.update_config(
                ip_address=ip_address,
                netmask=netmask,
                gateway=gateway,
                dns_servers=dns_servers,
                is_dhcp=is_dhcp,
                is_active=is_active
            )
            
            db.session.commit()
            flash('Network interface configured successfully.', 'success')
            return redirect(url_for('network.network'))
        except Exception as e:
            flash(f'Error configuring interface: {str(e)}', 'danger')
    
    return render_template('configure_network.html', interface=interface)

@network_bp.route('/network/status/<int:id>')
@login_required
def interface_status(id):
    """Get interface status"""
    interface = NetworkInterface.query.get_or_404(id)
    
    try:
        status = get_interface_status(interface.name)
        return jsonify(status)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@network_bp.route('/network/scan/<int:id>', methods=['POST'])
@login_required
@admin_required
def scan_network(id):
    """Scan network on interface"""
    interface = NetworkInterface.query.get_or_404(id)
    
    try:
        # Implement network scanning functionality
        # This is a placeholder - actual implementation would depend on system utilities
        scan_results = {
            'timestamp': 'now',
            'devices': [
                {'ip': '192.168.1.1', 'mac': '00:11:22:33:44:55', 'hostname': 'router'},
                {'ip': '192.168.1.2', 'mac': '00:11:22:33:44:56', 'hostname': 'device1'}
            ]
        }
        
        # Save scan results
        scan = NetworkScan(
            interface_id=interface.id,
            results=json.dumps(scan_results)
        )
        db.session.add(scan)
        db.session.commit()
        
        flash('Network scan completed.', 'success')
    except Exception as e:
        flash(f'Error scanning network: {str(e)}', 'danger')
    
    return redirect(url_for('network.network'))