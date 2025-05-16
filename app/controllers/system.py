from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.controllers.auth import admin_required
from app.utils.system_utils import get_system_info, perform_system_reset, get_disk_usage
from app import db
from app.utils import websocket_manager

# Create blueprint
system_bp = Blueprint('system', __name__)

@system_bp.route('/system')
@login_required
def system():
    """Display system information page"""
    system_info = get_system_info()
    disk_usage = get_disk_usage()
    return render_template('system.html', system_info=system_info, disk_usage=disk_usage)

@system_bp.route('/system/reset', methods=['GET', 'POST'])
@login_required
@admin_required
def reset():
    """Handle system reset"""
    if request.method == 'POST':
        try:
            # Perform system reset
            perform_system_reset()

            # This point should not be reached as the system will reboot
            flash('System reset initiated. The device will reboot shortly.', 'success')
        except Exception as e:
            flash(f'Error resetting system: {str(e)}', 'danger')

        return redirect(url_for('system.system'))

    # For GET requests, redirect to the system page
    flash('System reset requires a POST request.', 'warning')
    return redirect(url_for('system.system'))

@system_bp.route('/system/info')
@login_required
def system_info():
    """API endpoint to get system information"""
    try:
        system_info = get_system_info()
        disk_usage = get_disk_usage()

        return jsonify({
            'system': system_info,
            'disk': disk_usage,
            'success': True
        })
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500

@system_bp.route('/system/logs')
@login_required
def system_logs():
    """Display system operation logs"""
    logs = SystemOperationLog.query.order_by(SystemOperationLog.start_time.desc()).all()
    return render_template('system/logs.html', logs=logs)

@websocket_manager.register_event_handler('stream_system_logs')
def handle_stream_system_logs(data):
    """
    Handle streaming system logs.

    Args:
        data (dict): Data containing room information
    """
    room = data.get('room')

    if not room:
        websocket_manager.emit_event('status', {'msg': 'Missing room'}, room)
        return

    # Send a message to indicate streaming is starting
    websocket_manager.emit_event('status', {'msg': 'Starting system log streaming...'}, room)

    # Define the streaming function
    def stream_logs_thread():
        try:
            # Get the latest logs
            logs = SystemOperationLog.query.order_by(SystemOperationLog.start_time.desc()).limit(50).all()

            # Send each log
            for log in logs:
                websocket_manager.emit_event('system_log', {
                    'id': log.id,
                    'operation_type': log.operation_type,
                    'operation_name': log.operation_name,
                    'status': log.status,
                    'details': log.details,
                    'start_time': log.start_time.isoformat() if log.start_time else None,
                    'end_time': log.end_time.isoformat() if log.end_time else None,
                    'user_id': log.user_id,
                    'result': log.result,
                    'error_message': log.error_message
                }, room)

            # Emit completion event
            websocket_manager.emit_event('system_logs_complete', {
                'success': True,
                'timestamp': db.func.now().isoformat(),
                'status': 'completed'
            }, room)

        except Exception as e:
            print(f"Error streaming system logs: {str(e)}")

            websocket_manager.emit_event('system_logs_complete', {
                'success': False,
                'error': str(e),
                'timestamp': db.func.now().isoformat(),
                'status': 'error'
            }, room)

    # Run in a background thread to avoid blocking
    websocket_manager.run_in_background(stream_logs_thread)
