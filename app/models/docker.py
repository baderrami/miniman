from app import db
from datetime import datetime
import json

class DockerComposeConfig(db.Model):
    """Docker Compose configuration model"""
    __tablename__ = 'docker_compose_configs'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, index=True)
    description = db.Column(db.Text, nullable=True)
    source_url = db.Column(db.String(255), nullable=False)
    local_path = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(64), default='down')  # 'up', 'down', 'partial', 'error'
    last_checked = db.Column(db.DateTime, default=datetime.utcnow)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    update_available = db.Column(db.Boolean, default=False)

    def __init__(self, name, source_url, description=None, local_path=None, is_active=False, status='down'):
        self.name = name
        self.source_url = source_url
        self.description = description
        self.local_path = local_path
        self.is_active = is_active
        self.status = status
        self.last_checked = datetime.utcnow()
        self.last_updated = datetime.utcnow()
        self.update_available = False

    def __repr__(self):
        return f'<DockerComposeConfig {self.name}>'

class DockerContainer(db.Model):
    """Docker container model"""
    __tablename__ = 'docker_containers'

    id = db.Column(db.Integer, primary_key=True)
    container_id = db.Column(db.String(64), unique=True, index=True)
    name = db.Column(db.String(64), nullable=False)
    image = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(64), nullable=False)
    config_id = db.Column(db.Integer, db.ForeignKey('docker_compose_configs.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    ports = db.Column(db.Text, nullable=True)  # JSON string of port mappings

    config = db.relationship('DockerComposeConfig', backref=db.backref('containers', lazy='dynamic'))

    def __init__(self, container_id, name, image, status, config_id=None, ports=None):
        self.container_id = container_id
        self.name = name
        self.image = image
        self.status = status
        self.config_id = config_id
        self.created_at = datetime.utcnow()
        self.ports = json.dumps(ports) if ports else None

    def get_ports(self):
        """Get ports as a dictionary"""
        if self.ports:
            try:
                return json.loads(self.ports)
            except json.JSONDecodeError as e:
                print(f"Error parsing ports JSON for container {self.container_id}: {e}")
                return {}
        return {}

    def __repr__(self):
        return f'<DockerContainer {self.name}>'

class DockerImage(db.Model):
    """Docker image model"""
    __tablename__ = 'docker_images'

    id = db.Column(db.Integer, primary_key=True)
    image_id = db.Column(db.String(64), unique=True, index=True)
    repository = db.Column(db.String(255))
    tag = db.Column(db.String(64))
    size = db.Column(db.String(64))
    created = db.Column(db.DateTime)

    def __init__(self, image_id, repository, tag, size, created):
        self.image_id = image_id
        self.repository = repository
        self.tag = tag
        self.size = size
        self.created = created

    def __repr__(self):
        return f'<DockerImage {self.repository}:{self.tag}>'

class DockerVolume(db.Model):
    """Docker volume model"""
    __tablename__ = 'docker_volumes'

    id = db.Column(db.Integer, primary_key=True)
    volume_name = db.Column(db.String(64), unique=True, index=True)
    driver = db.Column(db.String(64))
    mountpoint = db.Column(db.String(255))
    created = db.Column(db.DateTime)

    def __init__(self, volume_name, driver, mountpoint, created):
        self.volume_name = volume_name
        self.driver = driver
        self.mountpoint = mountpoint
        self.created = created

    def __repr__(self):
        return f'<DockerVolume {self.volume_name}>'

class DockerNetwork(db.Model):
    """Docker network model"""
    __tablename__ = 'docker_networks'

    id = db.Column(db.Integer, primary_key=True)
    network_id = db.Column(db.String(64), unique=True, index=True)
    name = db.Column(db.String(64))
    driver = db.Column(db.String(64))
    scope = db.Column(db.String(64))
    created = db.Column(db.DateTime)

    def __init__(self, network_id, name, driver, scope, created):
        self.network_id = network_id
        self.name = name
        self.driver = driver
        self.scope = scope
        self.created = created

    def __repr__(self):
        return f'<DockerNetwork {self.name}>'
