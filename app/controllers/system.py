from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.controllers.auth import admin_required
from app.utils.system_utils import get_system_info, perform_system_reset, get_disk_usage

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
