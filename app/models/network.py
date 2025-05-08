from app import db
from datetime import datetime

class NetworkInterface(db.Model):
    """Network interface model"""
    __tablename__ = 'network_interfaces'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, index=True)
    ip_address = db.Column(db.String(15), nullable=True)
    netmask = db.Column(db.String(15), nullable=True)
    gateway = db.Column(db.String(15), nullable=True)
    dns_servers = db.Column(db.String(255), nullable=True)
    is_dhcp = db.Column(db.Boolean, default=True)
    is_active = db.Column(db.Boolean, default=True)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __init__(self, name, ip_address=None, netmask=None, gateway=None, 
                 dns_servers=None, is_dhcp=True, is_active=True):
        self.name = name
        self.ip_address = ip_address
        self.netmask = netmask
        self.gateway = gateway
        self.dns_servers = dns_servers
        self.is_dhcp = is_dhcp
        self.is_active = is_active
        self.last_updated = datetime.utcnow()
    
    def update_config(self, ip_address=None, netmask=None, gateway=None, 
                      dns_servers=None, is_dhcp=None, is_active=None):
        """Update network interface configuration"""
        if ip_address is not None:
            self.ip_address = ip_address
        if netmask is not None:
            self.netmask = netmask
        if gateway is not None:
            self.gateway = gateway
        if dns_servers is not None:
            self.dns_servers = dns_servers
        if is_dhcp is not None:
            self.is_dhcp = is_dhcp
        if is_active is not None:
            self.is_active = is_active
        self.last_updated = datetime.utcnow()
    
    def __repr__(self):
        return f'<NetworkInterface {self.name}>'

class NetworkScan(db.Model):
    """Network scan results model"""
    __tablename__ = 'network_scans'
    
    id = db.Column(db.Integer, primary_key=True)
    scan_time = db.Column(db.DateTime, default=datetime.utcnow)
    interface_id = db.Column(db.Integer, db.ForeignKey('network_interfaces.id'))
    results = db.Column(db.Text)
    
    interface = db.relationship('NetworkInterface', backref=db.backref('scans', lazy='dynamic'))
    
    def __init__(self, interface_id, results):
        self.interface_id = interface_id
        self.results = results
        self.scan_time = datetime.utcnow()
    
    def __repr__(self):
        return f'<NetworkScan {self.id} on interface {self.interface_id}>'