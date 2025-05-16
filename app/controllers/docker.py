from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app import db
from app.models.docker import DockerComposeConfig, DockerContainer, DockerImage, DockerVolume, DockerNetwork, \
    DockerOperationLog
from app.utils import websocket_manager
from app.utils.docker import (
    ensure_docker_installed, install_docker, download_compose_file,
    check_for_updates, update_compose_file, run_compose, stop_compose,
    restart_compose, get_container_logs, get_containers, get_images,
    pull_images, start_container, stop_container, restart_container,
    remove_container, exec_container_command, get_container_stats,
    inspect_container, pull_image, remove_image, build_image,
    inspect_image, get_volumes, create_volume, remove_volume,
    inspect_volume, get_networks, create_network, remove_network,
    inspect_network, connect_container_to_network, disconnect_container_from_network, check_compose_status
)
from app.utils.docker.logger import create_logger
from app.controllers.auth import admin_required
import os
from datetime import datetime

# Create blueprint
docker_bp = Blueprint('docker', __name__)

# Register Docker-specific WebSocket event handlers
@websocket_manager.register_event_handler('stream_container_logs')
def handle_stream_container_logs(data):
    """
    Handle streaming container logs.

    Args:
        data (dict): Data containing container ID and room information
    """
    container_id = data.get('container_id')
    room = data.get('room')

    print(f"Received request to stream logs for container {container_id} in room {room}")

    if not container_id or not room:
        websocket_manager.emit_event('status', {'msg': 'Missing container_id or room'}, room)
        return

    # Send a message to indicate streaming is starting
    websocket_manager.emit_container_log(
        container_id=container_id,
        line=f'Starting log streaming for container {container_id}...',
        status='info',
        room=room
    )

    # Create a WebSocket logger for this container
    logger = create_logger(
        operation_type='stream_container_logs',
        container_id=container_id,
        use_websocket=True,
        room=room,
        use_db=False  # Don't create a DB log for streaming logs
    )

    # Import the container manager
    from app.utils.docker.container import ContainerManager

    # Create a container manager and stream logs
    container_manager = ContainerManager()

    # Define the streaming function
    def stream_logs_thread():
        try:
            print(f"Starting log streaming thread for container {container_id}")
            # Send an initial message to confirm the thread has started
            websocket_manager.emit_container_log(
                container_id=container_id,
                line='Log streaming thread started',
                status='info',
                room=room
            )

            # Stream the logs
            container_manager.stream_container_logs(container_id, logger)

            # If we get here, the streaming has completed normally
            print(f"Log streaming completed for container {container_id}")
            websocket_manager.emit_event('docker_log_complete', {
                'container_id': container_id,
                'success': True,
                'timestamp': datetime.utcnow().isoformat(),
                'status': 'completed'
            }, room)

        except Exception as e:
            print(f"Error streaming logs for container {container_id}: {str(e)}")
            websocket_manager.emit_container_log(
                container_id=container_id,
                line=f'Error streaming logs: {str(e)}',
                status='error',
                room=room
            )

            websocket_manager.emit_event('docker_log_complete', {
                'container_id': container_id,
                'success': False,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat(),
                'status': 'error'
            }, room)

    # Run in a background thread to avoid blocking
    websocket_manager.run_in_background(stream_logs_thread)
    print(f"Started log streaming thread for container {container_id}")

@docker_bp.route('/docker')
@login_required
def docker():
    """Display Docker management page"""
    configs = DockerComposeConfig.query.all()

    # Get counts for dashboard
    containers = get_containers()
    images = get_images()
    volumes = get_volumes()
    networks = get_networks()

    return render_template(
        'docker/index.html', 
        configs=configs,
        container_count=len(containers),
        image_count=len(images),
        volume_count=len(volumes),
        network_count=len(networks)
    )

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
            local_path=local_path,
            status='down'
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

    # Update the status of the configuration
    if config.local_path and os.path.exists(config.local_path):
        config.status = check_compose_status(config.local_path)
        db.session.commit()

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

    # Pass the DockerOperationLog model to the template for ordering
    from app.models.docker import DockerOperationLog
    return render_template('docker/view_config.html', config=config, containers=containers, DockerOperationLog=DockerOperationLog)

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

    # Create an operation log
    operation_log = DockerOperationLog(
        operation_type='run_compose',
        config_id=config.id,
        status='running'
    )
    db.session.add(operation_log)
    db.session.commit()

    # Create a WebSocket logger
    logger = create_logger(
        operation_type='run_compose',
        config_id=config.id,
        use_websocket=True,
        room=f'docker_config_{config.id}',
        use_db=False  # We already created the DB log
    )
    # Set the log_id from the DB log
    if hasattr(logger, 'log_id'):
        logger.log_id = operation_log.id

    # Update config status to indicate it's being deployed
    config.status = 'deploying'
    db.session.commit()

    # Run the compose command with logging
    success, output = run_compose(config.local_path, logger)

    if success:
        config.is_active = True
        # Check the actual status of the compose configuration
        config.status = check_compose_status(config.local_path)
        db.session.commit()

        # Update container information in database
        update_container_info(config.id)

        flash('Docker Compose started successfully.', 'success')
    else:
        config.status = 'error'
        db.session.commit()
        flash(f'Error starting Docker Compose: {output}', 'danger')

    # Redirect to the operation log page
    return redirect(url_for('docker.operation_log', id=operation_log.id))

@docker_bp.route('/docker/stop/<int:id>', methods=['POST'])
@login_required
@admin_required
def stop_config(id):
    """Stop a Docker Compose configuration"""
    config = DockerComposeConfig.query.get_or_404(id)

    if not config.local_path or not os.path.exists(config.local_path):
        flash('Configuration file not found.', 'danger')
        return redirect(url_for('docker.view_config', id=id))

    # Create an operation log
    operation_log = DockerOperationLog(
        operation_type='stop_compose',
        config_id=config.id,
        status='running'
    )
    db.session.add(operation_log)
    db.session.commit()

    # Create a WebSocket logger
    logger = create_logger(
        operation_type='stop_compose',
        config_id=config.id,
        use_websocket=True,
        room=f'docker_config_{config.id}',
        use_db=False  # We already created the DB log
    )
    # Set the log_id from the DB log
    if hasattr(logger, 'log_id'):
        logger.log_id = operation_log.id

    # Update config status to indicate it's being stopped
    config.status = 'stopping'
    db.session.commit()

    # Run the compose command with logging
    success, output = stop_compose(config.local_path, logger)

    if success:
        config.is_active = False
        config.status = 'down'
        db.session.commit()

        # Remove container information from database
        DockerContainer.query.filter_by(config_id=config.id).delete()
        db.session.commit()

        flash('Docker Compose stopped successfully.', 'success')
    else:
        # Check the actual status of the compose configuration
        config.status = check_compose_status(config.local_path)
        db.session.commit()
        flash(f'Error stopping Docker Compose: {output}', 'danger')

    # Redirect to the operation log page
    return redirect(url_for('docker.operation_log', id=operation_log.id))

@docker_bp.route('/docker/restart/<int:id>', methods=['POST'])
@login_required
@admin_required
def restart_config(id):
    """Restart a Docker Compose configuration"""
    config = DockerComposeConfig.query.get_or_404(id)

    if not config.local_path or not os.path.exists(config.local_path):
        flash('Configuration file not found.', 'danger')
        return redirect(url_for('docker.view_config', id=id))

    # Create an operation log
    operation_log = DockerOperationLog(
        operation_type='restart_compose',
        config_id=config.id,
        status='running'
    )
    db.session.add(operation_log)
    db.session.commit()

    # Create a WebSocket logger
    logger = create_logger(
        operation_type='restart_compose',
        config_id=config.id,
        use_websocket=True,
        room=f'docker_config_{config.id}',
        use_db=False  # We already created the DB log
    )
    # Set the log_id from the DB log
    if hasattr(logger, 'log_id'):
        logger.log_id = operation_log.id

    # Update config status to indicate it's being restarted
    config.status = 'restarting'
    db.session.commit()

    # Run the compose command with logging
    success, output = restart_compose(config.local_path, logger)

    if success:
        # Check the actual status of the compose configuration
        config.status = check_compose_status(config.local_path)
        db.session.commit()

        # Update container information in database
        update_container_info(config.id)

        flash('Docker Compose restarted successfully.', 'success')
    else:
        # Check the actual status of the compose configuration
        config.status = check_compose_status(config.local_path)
        db.session.commit()
        flash(f'Error restarting Docker Compose: {output}', 'danger')

    # Redirect to the operation log page
    return redirect(url_for('docker.operation_log', id=operation_log.id))

@docker_bp.route('/docker/logs/<int:id>/<container_id>')
@login_required
def container_logs(id, container_id):
    """View logs for a container"""
    config = DockerComposeConfig.query.get_or_404(id)
    container = DockerContainer.query.filter_by(container_id=container_id).first_or_404()

    # Get initial logs
    success, logs = get_container_logs(container_id)

    # Create a room name for this container's logs
    room_name = f'container_logs_{container_id}'

    return render_template('docker/logs.html', 
                          config=config, 
                          container=container, 
                          logs=logs, 
                          success=success,
                          room_name=room_name)

@docker_bp.route('/docker/operation-log/<int:id>')
@login_required
def operation_log(id):
    """View operation log"""
    log = DockerOperationLog.query.get_or_404(id)

    # Get the associated config if available
    config = None
    if log.config_id:
        config = DockerComposeConfig.query.get(log.config_id)

    return render_template('docker/operation_log.html', log=log, config=config)

@docker_bp.route('/docker/pull/<int:id>', methods=['POST'])
@login_required
@admin_required
def pull_config(id):
    """Pull images for a Docker Compose configuration"""
    config = DockerComposeConfig.query.get_or_404(id)

    if not config.local_path or not os.path.exists(config.local_path):
        flash('Configuration file not found.', 'danger')
        return redirect(url_for('docker.view_config', id=id))

    # Create an operation log
    operation_log = DockerOperationLog(
        operation_type='pull_images',
        config_id=config.id,
        status='running'
    )
    db.session.add(operation_log)
    db.session.commit()

    # Create a WebSocket logger
    logger = create_logger(
        operation_type='pull_images',
        config_id=config.id,
        use_websocket=True,
        room=f'docker_config_{config.id}',
        use_db=False  # We already created the DB log
    )
    # Set the log_id from the DB log
    if hasattr(logger, 'log_id'):
        logger.log_id = operation_log.id

    # Run the compose command with logging
    success, output = pull_images(config.local_path, logger)

    if success:
        flash('Images pulled successfully.', 'success')
    else:
        flash(f'Error pulling images: {output}', 'danger')

    # Redirect to the operation log page
    return redirect(url_for('docker.operation_log', id=operation_log.id))

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

# Container management routes

@docker_bp.route('/docker/containers')
@login_required
def list_containers():
    """List all containers"""
    containers = get_containers()

    # Update database with container information
    update_all_containers_info(containers)

    return render_template('docker/containers.html', containers=containers)

@docker_bp.route('/docker/containers/<container_id>')
@login_required
def view_container(container_id):
    """View container details"""
    success, container_details = inspect_container(container_id)

    if not success:
        flash('Error retrieving container details.', 'danger')
        return redirect(url_for('docker.list_containers'))

    # Get initial logs
    success, logs = get_container_logs(container_id)

    # Get container stats
    stats_success, stats = get_container_stats(container_id)

    # Create a room name for this container's logs
    room_name = f'container_logs_{container_id}'

    return render_template(
        'docker/view_container.html', 
        container=container_details, 
        logs=logs, 
        stats=stats if stats_success else None,
        room_name=room_name
    )

@docker_bp.route('/docker/containers/start/<container_id>', methods=['POST'])
@login_required
@admin_required
def start_container_route(container_id):
    """Start a container"""
    success, output = start_container(container_id)

    if success:
        # Update container status in database
        container = DockerContainer.query.filter_by(container_id=container_id).first()
        if container:
            container.status = 'running'
            db.session.commit()

        # Emit WebSocket event for container status change
        websocket_manager.emit_container_status_change(
            container_id=container_id,
            status='running',
            action='start',
            success=True
        )

        flash('Container started successfully.', 'success')
    else:
        # Emit WebSocket event for failed action
        websocket_manager.emit_container_status_change(
            container_id=container_id,
            status='error',
            action='start',
            success=False,
            error=output
        )

        flash(f'Error starting container: {output}', 'danger')

    # Check if we're coming from the container logs page
    referrer = request.referrer
    if referrer and 'logs' in referrer and container_id in referrer:
        # Extract the config ID from the referrer
        import re
        match = re.search(r'/docker/logs/(\d+)/', referrer)
        if match:
            config_id = match.group(1)
            return redirect(url_for('docker.container_logs', id=config_id, container_id=container_id))

    return redirect(url_for('docker.list_containers'))

@docker_bp.route('/docker/containers/stop/<container_id>', methods=['POST'])
@login_required
@admin_required
def stop_container_route(container_id):
    """Stop a container"""
    success, output = stop_container(container_id)

    if success:
        # Update container status in database
        container = DockerContainer.query.filter_by(container_id=container_id).first()
        if container:
            container.status = 'stopped'
            db.session.commit()

        # Emit WebSocket event for container status change
        websocket_manager.emit_container_status_change(
            container_id=container_id,
            status='stopped',
            action='stop',
            success=True
        )

        flash('Container stopped successfully.', 'success')
    else:
        # Emit WebSocket event for failed action
        websocket_manager.emit_container_status_change(
            container_id=container_id,
            status='error',
            action='stop',
            success=False,
            error=output
        )

        flash(f'Error stopping container: {output}', 'danger')

    # Check if we're coming from the container logs page
    referrer = request.referrer
    if referrer and 'logs' in referrer and container_id in referrer:
        # Extract the config ID from the referrer
        import re
        match = re.search(r'/docker/logs/(\d+)/', referrer)
        if match:
            config_id = match.group(1)
            return redirect(url_for('docker.container_logs', id=config_id, container_id=container_id))

    return redirect(url_for('docker.list_containers'))

@docker_bp.route('/docker/containers/restart/<container_id>', methods=['POST'])
@login_required
@admin_required
def restart_container_route(container_id):
    """Restart a container"""
    success, output = restart_container(container_id)

    if success:
        # Update container status in database
        container = DockerContainer.query.filter_by(container_id=container_id).first()
        if container:
            container.status = 'running'
            db.session.commit()

        # Emit WebSocket event for container status change
        websocket_manager.emit_container_status_change(
            container_id=container_id,
            status='running',
            action='restart',
            success=True
        )

        flash('Container restarted successfully.', 'success')
    else:
        # Emit WebSocket event for failed action
        websocket_manager.emit_container_status_change(
            container_id=container_id,
            status='error',
            action='restart',
            success=False,
            error=output
        )

        flash(f'Error restarting container: {output}', 'danger')

    # Check if we're coming from the container logs page
    referrer = request.referrer
    if referrer and 'logs' in referrer and container_id in referrer:
        # Extract the config ID from the referrer
        import re
        match = re.search(r'/docker/logs/(\d+)/', referrer)
        if match:
            config_id = match.group(1)
            return redirect(url_for('docker.container_logs', id=config_id, container_id=container_id))

    return redirect(url_for('docker.list_containers'))

@docker_bp.route('/docker/containers/remove/<container_id>', methods=['POST'])
@login_required
@admin_required
def remove_container_route(container_id):
    """Remove a container"""
    force = request.form.get('force', 'false') == 'true'
    success, output = remove_container(container_id, force)

    if success:
        # Remove container from database
        container = DockerContainer.query.filter_by(container_id=container_id).first()
        if container:
            db.session.delete(container)
            db.session.commit()

        flash('Container removed successfully.', 'success')
    else:
        flash(f'Error removing container: {output}', 'danger')

    return redirect(url_for('docker.list_containers'))

@docker_bp.route('/docker/containers/exec/<container_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def exec_container(container_id):
    """Execute a command in a container"""
    if request.method == 'POST':
        command = request.form.get('command')

        if not command:
            flash('Command is required.', 'danger')
            return redirect(url_for('docker.exec_container', container_id=container_id))

        success, output = exec_container_command(container_id, command)

        return render_template(
            'docker/exec_result.html', 
            container_id=container_id, 
            command=command, 
            output=output, 
            success=success
        )

    return render_template('docker/exec.html', container_id=container_id)

def update_all_containers_info(containers=None):
    """Update all containers information in database"""
    if containers is None:
        containers = get_containers()

    # Get all container IDs from the database
    db_container_ids = [c.container_id for c in DockerContainer.query.all()]

    # Get all container IDs from the system
    system_container_ids = [c['id'] for c in containers]

    # Remove containers that no longer exist
    for container_id in db_container_ids:
        if container_id not in system_container_ids:
            DockerContainer.query.filter_by(container_id=container_id).delete()

    # Update or add containers
    for container in containers:
        db_container = DockerContainer.query.filter_by(container_id=container['id']).first()

        if db_container:
            # Update existing container
            db_container.name = container['name']
            db_container.image = container['image']
            db_container.status = container['status']
            db_container.ports = container['ports']
        else:
            # Add new container
            db_container = DockerContainer(
                container_id=container['id'],
                name=container['name'],
                image=container['image'],
                status=container['status'],
                ports=container['ports']
            )
            db.session.add(db_container)

    db.session.commit()

# Image management routes

@docker_bp.route('/docker/images')
@login_required
def list_images():
    """List all images"""
    images = get_images()

    # Update database with image information
    update_all_images_info(images)

    return render_template('docker/images.html', images=images)

@docker_bp.route('/docker/images/<image_id>')
@login_required
def view_image(image_id):
    """View image details"""
    success, image_details = inspect_image(image_id)

    if not success:
        flash('Error retrieving image details.', 'danger')
        return redirect(url_for('docker.list_images'))

    return render_template('docker/view_image.html', image=image_details)

@docker_bp.route('/docker/images/pull', methods=['GET', 'POST'])
@login_required
@admin_required
def pull_image_route():
    """Pull a Docker image"""
    if request.method == 'POST':
        image_name = request.form.get('image_name')

        if not image_name:
            flash('Image name is required.', 'danger')
            return redirect(url_for('docker.pull_image_route'))

        # Create an operation log
        operation_log = DockerOperationLog(
            operation_type='pull_image',
            image_name=image_name,
            status='running'
        )
        db.session.add(operation_log)
        db.session.commit()

        # Create a WebSocket logger
        logger = create_logger(
            operation_type='pull_image',
            image_name=image_name,
            use_websocket=True,
            room=f'docker_image_{image_name.replace(":", "_")}',
            use_db=False  # We already created the DB log
        )
        # Set the log_id from the DB log
        if hasattr(logger, 'log_id'):
            logger.log_id = operation_log.id

        # Run the pull command with logging
        success, output = pull_image(image_name, logger)

        if success:
            flash(f'Image {image_name} pulled successfully.', 'success')
            # Update images in database
            update_all_images_info()
        else:
            flash(f'Error pulling image: {output}', 'danger')

        # Redirect to the operation log page
        return redirect(url_for('docker.operation_log', id=operation_log.id))

    return render_template('docker/pull_image.html')

@docker_bp.route('/docker/images/remove/<image_id>', methods=['POST'])
@login_required
@admin_required
def remove_image_route(image_id):
    """Remove a Docker image"""
    force = request.form.get('force', 'false') == 'true'
    success, output = remove_image(image_id, force)

    if success:
        # Remove image from database
        image = DockerImage.query.filter_by(image_id=image_id).first()
        if image:
            db.session.delete(image)
            db.session.commit()

        flash('Image removed successfully.', 'success')
    else:
        flash(f'Error removing image: {output}', 'danger')

    return redirect(url_for('docker.list_images'))

@docker_bp.route('/docker/images/build', methods=['GET', 'POST'])
@login_required
@admin_required
def build_image_route():
    """Build a Docker image"""
    if request.method == 'POST':
        dockerfile_path = request.form.get('dockerfile_path')
        tag = request.form.get('tag')

        if not dockerfile_path or not tag:
            flash('Dockerfile path and tag are required.', 'danger')
            return redirect(url_for('docker.build_image_route'))

        # Create an operation log
        operation_log = DockerOperationLog(
            operation_type='build_image',
            image_name=tag,
            status='running'
        )
        db.session.add(operation_log)
        db.session.commit()

        # Create a WebSocket logger
        logger = create_logger(
            operation_type='build_image',
            image_name=tag,
            use_websocket=True,
            room=f'docker_image_{tag.replace(":", "_")}',
            use_db=False  # We already created the DB log
        )
        # Set the log_id from the DB log
        if hasattr(logger, 'log_id'):
            logger.log_id = operation_log.id

        # Run the build command with logging
        success, output = build_image(dockerfile_path, tag, logger)

        if success:
            flash(f'Image {tag} built successfully.', 'success')
            # Update images in database
            update_all_images_info()
        else:
            flash(f'Error building image: {output}', 'danger')

        return redirect(url_for('docker.list_images'))

    return render_template('docker/build_image.html')

def update_all_images_info(images=None):
    """Update all images information in database"""
    if images is None:
        images = get_images()

    # Get all image IDs from the database
    db_image_ids = [i.image_id for i in DockerImage.query.all()]

    # Get all image IDs from the system
    system_image_ids = [i['id'] for i in images]

    # Remove images that no longer exist
    for image_id in db_image_ids:
        if image_id not in system_image_ids:
            DockerImage.query.filter_by(image_id=image_id).delete()

    # Update or add images
    for image in images:
        db_image = DockerImage.query.filter_by(image_id=image['id']).first()

        # Parse the creation time if available
        created = None
        if 'created' in image:
            try:
                from dateutil import parser as date_parser
                created = date_parser.parse(image['created'])
            except:
                created = datetime.utcnow()
        else:
            created = datetime.utcnow()

        if db_image:
            # Update existing image
            db_image.repository = image['repository']
            db_image.tag = image['tag']
            db_image.size = image['size']
            db_image.created = created
        else:
            # Add new image
            db_image = DockerImage(
                image_id=image['id'],
                repository=image['repository'],
                tag=image['tag'],
                size=image['size'],
                created=created
            )
            db.session.add(db_image)

    db.session.commit()

# Volume management routes

@docker_bp.route('/docker/volumes')
@login_required
def list_volumes():
    """List all volumes"""
    volumes = get_volumes()

    # Update database with volume information
    update_all_volumes_info(volumes)

    return render_template('docker/volumes.html', volumes=volumes)

@docker_bp.route('/docker/volumes/<volume_name>')
@login_required
def view_volume(volume_name):
    """View volume details"""
    success, volume_details = inspect_volume(volume_name)

    if not success:
        flash('Error retrieving volume details.', 'danger')
        return redirect(url_for('docker.list_volumes'))

    return render_template('docker/view_volume.html', volume=volume_details)

@docker_bp.route('/docker/volumes/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_volume_route():
    """Create a Docker volume"""
    if request.method == 'POST':
        volume_name = request.form.get('volume_name')
        driver = request.form.get('driver', 'local')

        if not volume_name:
            flash('Volume name is required.', 'danger')
            return redirect(url_for('docker.create_volume_route'))

        # Parse labels if provided
        labels = {}
        labels_str = request.form.get('labels', '')
        if labels_str:
            try:
                for label in labels_str.split(','):
                    key, value = label.strip().split('=')
                    labels[key] = value
            except:
                flash('Invalid labels format. Use key=value,key2=value2', 'danger')
                return redirect(url_for('docker.create_volume_route'))

        success, output = create_volume(volume_name, driver, labels)

        if success:
            flash(f'Volume {volume_name} created successfully.', 'success')
            # Update volumes in database
            update_all_volumes_info()
        else:
            flash(f'Error creating volume: {output}', 'danger')

        return redirect(url_for('docker.list_volumes'))

    return render_template('docker/create_volume.html')

@docker_bp.route('/docker/volumes/remove/<volume_name>', methods=['POST'])
@login_required
@admin_required
def remove_volume_route(volume_name):
    """Remove a Docker volume"""
    force = request.form.get('force', 'false') == 'true'
    success, output = remove_volume(volume_name, force)

    if success:
        # Remove volume from database
        volume = DockerVolume.query.filter_by(volume_name=volume_name).first()
        if volume:
            db.session.delete(volume)
            db.session.commit()

        flash('Volume removed successfully.', 'success')
    else:
        flash(f'Error removing volume: {output}', 'danger')

    return redirect(url_for('docker.list_volumes'))

def update_all_volumes_info(volumes=None):
    """Update all volumes information in database"""
    if volumes is None:
        volumes = get_volumes()

    # Get all volume names from the database
    db_volume_names = [v.volume_name for v in DockerVolume.query.all()]

    # Get all volume names from the system
    system_volume_names = [v['name'] for v in volumes]

    # Remove volumes that no longer exist
    for volume_name in db_volume_names:
        if volume_name not in system_volume_names:
            DockerVolume.query.filter_by(volume_name=volume_name).delete()

    # Update or add volumes
    for volume in volumes:
        db_volume = DockerVolume.query.filter_by(volume_name=volume['name']).first()

        # Use current time if created time is not available
        created = volume.get('created') or datetime.utcnow()

        if db_volume:
            # Update existing volume
            db_volume.driver = volume['driver']
            db_volume.mountpoint = volume.get('mountpoint', '')
            db_volume.created = created
        else:
            # Add new volume
            db_volume = DockerVolume(
                volume_name=volume['name'],
                driver=volume['driver'],
                mountpoint=volume.get('mountpoint', ''),
                created=created
            )
            db.session.add(db_volume)

    db.session.commit()

# Network management routes

@docker_bp.route('/docker/networks')
@login_required
def list_networks():
    """List all networks"""
    networks = get_networks()

    # Update database with network information
    update_all_networks_info(networks)

    return render_template('docker/networks.html', networks=networks)

@docker_bp.route('/docker/networks/<network_id>')
@login_required
def view_network(network_id):
    """View network details"""
    success, network_details = inspect_network(network_id)

    if not success:
        flash('Error retrieving network details.', 'danger')
        return redirect(url_for('docker.list_networks'))

    return render_template('docker/view_network.html', network=network_details)

@docker_bp.route('/docker/networks/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_network_route():
    """Create a Docker network"""
    if request.method == 'POST':
        network_name = request.form.get('network_name')
        driver = request.form.get('driver', 'bridge')
        subnet = request.form.get('subnet')
        gateway = request.form.get('gateway')

        if not network_name:
            flash('Network name is required.', 'danger')
            return redirect(url_for('docker.create_network_route'))

        success, output = create_network(network_name, driver, subnet, gateway)

        if success:
            flash(f'Network {network_name} created successfully.', 'success')
            # Update networks in database
            update_all_networks_info()
        else:
            flash(f'Error creating network: {output}', 'danger')

        return redirect(url_for('docker.list_networks'))

    return render_template('docker/create_network.html')

@docker_bp.route('/docker/networks/remove/<network_id>', methods=['POST'])
@login_required
@admin_required
def remove_network_route(network_id):
    """Remove a Docker network"""
    success, output = remove_network(network_id)

    if success:
        # Remove network from database
        network = DockerNetwork.query.filter_by(network_id=network_id).first()
        if network:
            db.session.delete(network)
            db.session.commit()

        flash('Network removed successfully.', 'success')
    else:
        flash(f'Error removing network: {output}', 'danger')

    return redirect(url_for('docker.list_networks'))

@docker_bp.route('/docker/networks/connect', methods=['GET', 'POST'])
@login_required
@admin_required
def connect_container_to_network_route():
    """Connect a container to a network"""
    if request.method == 'POST':
        container_id = request.form.get('container_id')
        network_id = request.form.get('network_id')

        if not container_id or not network_id:
            flash('Container ID and Network ID are required.', 'danger')
            return redirect(url_for('docker.connect_container_to_network_route'))

        success, output = connect_container_to_network(container_id, network_id)

        if success:
            flash(f'Container connected to network successfully.', 'success')
        else:
            flash(f'Error connecting container to network: {output}', 'danger')

        return redirect(url_for('docker.list_networks'))

    # Get containers and networks for the form
    containers = get_containers()
    networks = get_networks()

    return render_template('docker/connect_container.html', containers=containers, networks=networks)

@docker_bp.route('/docker/networks/disconnect', methods=['GET', 'POST'])
@login_required
@admin_required
def disconnect_container_from_network_route():
    """Disconnect a container from a network"""
    if request.method == 'POST':
        container_id = request.form.get('container_id')
        network_id = request.form.get('network_id')

        if not container_id or not network_id:
            flash('Container ID and Network ID are required.', 'danger')
            return redirect(url_for('docker.disconnect_container_from_network_route'))

        success, output = disconnect_container_from_network(container_id, network_id)

        if success:
            flash(f'Container disconnected from network successfully.', 'success')
        else:
            flash(f'Error disconnecting container from network: {output}', 'danger')

        return redirect(url_for('docker.list_networks'))

    # Get containers and networks for the form
    containers = get_containers()
    networks = get_networks()

    return render_template('docker/disconnect_container.html', containers=containers, networks=networks)

def update_all_networks_info(networks=None):
    """Update all networks information in database"""
    if networks is None:
        networks = get_networks()

    # Get all network IDs from the database
    db_network_ids = [n.network_id for n in DockerNetwork.query.all()]

    # Get all network IDs from the system
    system_network_ids = [n['id'] for n in networks]

    # Remove networks that no longer exist
    for network_id in db_network_ids:
        if network_id not in system_network_ids:
            DockerNetwork.query.filter_by(network_id=network_id).delete()

    # Update or add networks
    for network in networks:
        db_network = DockerNetwork.query.filter_by(network_id=network['id']).first()

        # Use current time if created time is not available
        created = network.get('created') or datetime.utcnow()

        if db_network:
            # Update existing network
            db_network.name = network['name']
            db_network.driver = network['driver']
            db_network.scope = network['scope']
            db_network.created = created
        else:
            # Add new network
            db_network = DockerNetwork(
                network_id=network['id'],
                name=network['name'],
                driver=network['driver'],
                scope=network['scope'],
                created=created
            )
            db.session.add(db_network)

    db.session.commit()
