from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.docker import DockerComposeConfig, DockerContainer
from app.utils.docker_utils import (
    ensure_docker_installed, install_docker, download_compose_file,
    check_for_updates, update_compose_file, run_compose, stop_compose,
    restart_compose, get_container_logs, get_containers, get_images,
    pull_images
)
from app.controllers.auth import admin_required
import os
from datetime import datetime

# Create blueprint
docker_bp = Blueprint('docker', __name__)

@docker_bp.route('/docker')
@login_required
def docker():
    """Display Docker management page"""
    configs = DockerComposeConfig.query.all()
    return render_template('docker/index.html', configs=configs)

@docker_bp.route('/docker/check-docker')
@login_required
@admin_required
def check_docker():
    """Check if Docker is installed"""
    is_installed = ensure_docker_installed()
    
    if is_installed:
        flash('Docker and Docker Compose are installed.', 'success')
    else:
        flash('Docker or Docker Compose are not installed.', 'warning')
    
    return redirect(url_for('docker.docker'))

@docker_bp.route('/docker/install-docker', methods=['POST'])
@login_required
@admin_required
def install_docker_route():
    """Install Docker and Docker Compose"""
    success, message = install_docker()
    
    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')
    
    return redirect(url_for('docker.docker'))

@docker_bp.route('/docker/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_config():
    """Add a new Docker Compose configuration"""
    if request.method == 'POST':
        name = request.form.get('name')
        source_url = request.form.get('source_url')
        description = request.form.get('description')
        
        if not name or not source_url:
            flash('Name and source URL are required.', 'danger')
            return redirect(url_for('docker.add_config'))
        
        # Check if configuration with this name already exists
        existing = DockerComposeConfig.query.filter_by(name=name).first()
        if existing:
            flash(f'Configuration with name "{name}" already exists.', 'danger')
            return redirect(url_for('docker.add_config'))
        
        # Download the compose file
        success, message, local_path = download_compose_file(source_url, name)
        
        if not success:
            flash(message, 'danger')
            return redirect(url_for('docker.add_config'))
        
        # Create the configuration
        config = DockerComposeConfig(
            name=name,
            source_url=source_url,
            description=description,
            local_path=local_path
        )
        
        db.session.add(config)
        db.session.commit()
        
        flash(f'Docker Compose configuration "{name}" added successfully.', 'success')
        return redirect(url_for('docker.docker'))
    
    return render_template('docker/add_config.html')

@docker_bp.route('/docker/view/<int:id>')
@login_required
def view_config(id):
    """View a Docker Compose configuration"""
    config = DockerComposeConfig.query.get_or_404(id)
    
    # Get containers for this configuration
    containers = []
    if config.local_path and os.path.exists(config.local_path):
        system_containers = get_containers()
        
        # Filter containers by configuration (this is a simplification)
        # In a real implementation, we would need a more robust way to associate containers with configs
        for container in system_containers:
            db_container = DockerContainer.query.filter_by(container_id=container['id']).first()
            
            if db_container and db_container.config_id == config.id:
                containers.append(container)
    
    return render_template('docker/view_config.html', config=config, containers=containers)

@docker_bp.route('/docker/check-updates/<int:id>', methods=['POST'])
@login_required
@admin_required
def check_updates(id):
    """Check for updates to a Docker Compose configuration"""
    config = DockerComposeConfig.query.get_or_404(id)
    
    if not config.local_path or not os.path.exists(config.local_path):
        flash('Configuration file not found.', 'danger')
        return redirect(url_for('docker.view_config', id=id))
    
    success, updates_available = check_for_updates(config.local_path, config.source_url)
    
    config.last_checked = datetime.utcnow()
    config.update_available = updates_available
    db.session.commit()
    
    if success:
        if updates_available:
            flash('Updates are available for this configuration.', 'info')
        else:
            flash('No updates available for this configuration.', 'success')
    else:
        flash('Error checking for updates.', 'danger')
    
    return redirect(url_for('docker.view_config', id=id))

@docker_bp.route('/docker/update/<int:id>', methods=['POST'])
@login_required
@admin_required
def update_config(id):
    """Update a Docker Compose configuration"""
    config = DockerComposeConfig.query.get_or_404(id)
    
    if not config.local_path or not os.path.exists(config.local_path):
        flash('Configuration file not found.', 'danger')
        return redirect(url_for('docker.view_config', id=id))
    
    success, message = update_compose_file(config.local_path, config.source_url)
    
    if success:
        config.last_updated = datetime.utcnow()
        config.update_available = False
        db.session.commit()
        flash(message, 'success')
    else:
        flash(message, 'danger')
    
    return redirect(url_for('docker.view_config', id=id))

@docker_bp.route('/docker/run/<int:id>', methods=['POST'])
@login_required
@admin_required
def run_config(id):
    """Run a Docker Compose configuration"""
    config = DockerComposeConfig.query.get_or_404(id)
    
    if not config.local_path or not os.path.exists(config.local_path):
        flash('Configuration file not found.', 'danger')
        return redirect(url_for('docker.view_config', id=id))
    
    success, output = run_compose(config.local_path)
    
    if success:
        config.is_active = True
        db.session.commit()
        
        # Update container information in database
        update_container_info(config.id)
        
        flash('Docker Compose started successfully.', 'success')
    else:
        flash(f'Error starting Docker Compose: {output}', 'danger')
    
    return redirect(url_for('docker.view_config', id=id))

@docker_bp.route('/docker/stop/<int:id>', methods=['POST'])
@login_required
@admin_required
def stop_config(id):
    """Stop a Docker Compose configuration"""
    config = DockerComposeConfig.query.get_or_404(id)
    
    if not config.local_path or not os.path.exists(config.local_path):
        flash('Configuration file not found.', 'danger')
        return redirect(url_for('docker.view_config', id=id))
    
    success, output = stop_compose(config.local_path)
    
    if success:
        config.is_active = False
        db.session.commit()
        
        # Remove container information from database
        DockerContainer.query.filter_by(config_id=config.id).delete()
        db.session.commit()
        
        flash('Docker Compose stopped successfully.', 'success')
    else:
        flash(f'Error stopping Docker Compose: {output}', 'danger')
    
    return redirect(url_for('docker.view_config', id=id))

@docker_bp.route('/docker/restart/<int:id>', methods=['POST'])
@login_required
@admin_required
def restart_config(id):
    """Restart a Docker Compose configuration"""
    config = DockerComposeConfig.query.get_or_404(id)
    
    if not config.local_path or not os.path.exists(config.local_path):
        flash('Configuration file not found.', 'danger')
        return redirect(url_for('docker.view_config', id=id))
    
    success, output = restart_compose(config.local_path)
    
    if success:
        # Update container information in database
        update_container_info(config.id)
        
        flash('Docker Compose restarted successfully.', 'success')
    else:
        flash(f'Error restarting Docker Compose: {output}', 'danger')
    
    return redirect(url_for('docker.view_config', id=id))

@docker_bp.route('/docker/logs/<int:id>/<container_id>')
@login_required
def container_logs(id, container_id):
    """View logs for a container"""
    config = DockerComposeConfig.query.get_or_404(id)
    container = DockerContainer.query.filter_by(container_id=container_id).first_or_404()
    
    success, logs = get_container_logs(container_id)
    
    return render_template('docker/logs.html', config=config, container=container, logs=logs, success=success)

@docker_bp.route('/docker/pull/<int:id>', methods=['POST'])
@login_required
@admin_required
def pull_config(id):
    """Pull images for a Docker Compose configuration"""
    config = DockerComposeConfig.query.get_or_404(id)
    
    if not config.local_path or not os.path.exists(config.local_path):
        flash('Configuration file not found.', 'danger')
        return redirect(url_for('docker.view_config', id=id))
    
    success, output = pull_images(config.local_path)
    
    if success:
        flash('Images pulled successfully.', 'success')
    else:
        flash(f'Error pulling images: {output}', 'danger')
    
    return redirect(url_for('docker.view_config', id=id))

@docker_bp.route('/docker/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_config(id):
    """Delete a Docker Compose configuration"""
    config = DockerComposeConfig.query.get_or_404(id)
    
    # Stop containers if active
    if config.is_active and config.local_path and os.path.exists(config.local_path):
        stop_compose(config.local_path)
    
    # Remove container information from database
    DockerContainer.query.filter_by(config_id=config.id).delete()
    
    # Remove configuration
    db.session.delete(config)
    db.session.commit()
    
    # Remove configuration directory
    if config.local_path:
        config_dir = os.path.dirname(config.local_path)
        if os.path.exists(config_dir):
            import shutil
            shutil.rmtree(config_dir)
    
    flash(f'Docker Compose configuration "{config.name}" deleted successfully.', 'success')
    return redirect(url_for('docker.docker'))

def update_container_info(config_id):
    """Update container information in database"""
    config = DockerComposeConfig.query.get(config_id)
    if not config:
        return
    
    # Get containers from system
    system_containers = get_containers()
    
    # Clear existing containers for this config
    DockerContainer.query.filter_by(config_id=config_id).delete()
    
    # Add new containers
    for container in system_containers:
        # This is a simplification - in a real implementation, we would need a more robust way
        # to associate containers with configs
        if config.name.lower() in container['name'].lower():
            db_container = DockerContainer(
                container_id=container['id'],
                name=container['name'],
                image=container['image'],
                status=container['status'],
                config_id=config_id,
                ports=container['ports']
            )
            db.session.add(db_container)
    
    db.session.commit()