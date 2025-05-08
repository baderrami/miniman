from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.controllers.auth import admin_required
from app.utils.command_utils import execute_command, get_allowed_commands

# Create blueprint
commands_bp = Blueprint('commands', __name__)

@commands_bp.route('/commands')
@login_required
def commands():
    """Display command execution page"""
    allowed_commands = get_allowed_commands()
    return render_template('commands.html', commands=allowed_commands)

@commands_bp.route('/commands/execute', methods=['POST'])
@login_required
@admin_required
def execute():
    """Execute a command"""
    command = request.form.get('command')
    args = request.form.get('args', '')
    
    if not command:
        flash('No command specified.', 'danger')
        return redirect(url_for('commands.commands'))
    
    try:
        # Execute the command
        output, exit_code = execute_command(command, args)
        
        # Check if command was successful
        if exit_code == 0:
            flash('Command executed successfully.', 'success')
        else:
            flash(f'Command failed with exit code {exit_code}.', 'warning')
        
        # Return to commands page with output
        return render_template('commands.html', 
                              commands=get_allowed_commands(),
                              output=output,
                              last_command=f"{command} {args}".strip())
    except Exception as e:
        flash(f'Error executing command: {str(e)}', 'danger')
        return redirect(url_for('commands.commands'))

@commands_bp.route('/commands/api/execute', methods=['POST'])
@login_required
@admin_required
def api_execute():
    """API endpoint to execute a command and return JSON response"""
    data = request.get_json()
    
    if not data or 'command' not in data:
        return jsonify({'error': 'No command specified'}), 400
    
    command = data.get('command')
    args = data.get('args', '')
    
    try:
        # Execute the command
        output, exit_code = execute_command(command, args)
        
        # Return JSON response
        return jsonify({
            'command': f"{command} {args}".strip(),
            'output': output,
            'exit_code': exit_code,
            'success': exit_code == 0
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500