import subprocess
import shlex
from typing import Tuple, List, Dict, Any

# Define allowed commands
ALLOWED_COMMANDS = {
    'ping': {
        'description': 'Test connectivity to a host',
        'format': 'ping [options] <host>',
        'example': 'ping -c 4 8.8.8.8',
        'args_required': True
    },
    'ifconfig': {
        'description': 'Display network interface configuration',
        'format': 'ifconfig [interface]',
        'example': 'ifconfig eth0',
        'args_required': False
    },
    'ip': {
        'description': 'Show / manipulate routing, devices, policy routing and tunnels',
        'format': 'ip [options] <object> <command>',
        'example': 'ip addr show',
        'args_required': True
    },
    'traceroute': {
        'description': 'Print the route packets trace to network host',
        'format': 'traceroute [options] <host>',
        'example': 'traceroute google.com',
        'args_required': True
    },
    'nslookup': {
        'description': 'Query DNS for domain name or IP address mapping',
        'format': 'nslookup <host>',
        'example': 'nslookup google.com',
        'args_required': True
    },
    'netstat': {
        'description': 'Print network connections, routing tables, interface statistics, etc.',
        'format': 'netstat [options]',
        'example': 'netstat -tuln',
        'args_required': False
    },
    'df': {
        'description': 'Report file system disk space usage',
        'format': 'df [options]',
        'example': 'df -h',
        'args_required': False
    },
    'free': {
        'description': 'Display amount of free and used memory in the system',
        'format': 'free [options]',
        'example': 'free -h',
        'args_required': False
    },
    'uptime': {
        'description': 'Tell how long the system has been running',
        'format': 'uptime',
        'example': 'uptime',
        'args_required': False
    }
}

def get_allowed_commands() -> Dict[str, Dict[str, Any]]:
    """
    Get the list of allowed commands
    
    Returns:
        Dict[str, Dict[str, Any]]: Dictionary of allowed commands with their descriptions
    """
    return ALLOWED_COMMANDS

def is_command_allowed(command: str) -> bool:
    """
    Check if a command is allowed
    
    Args:
        command (str): Command to check
        
    Returns:
        bool: True if command is allowed, False otherwise
    """
    return command in ALLOWED_COMMANDS

def validate_command_args(command: str, args: str) -> bool:
    """
    Validate command arguments
    
    Args:
        command (str): Command to validate
        args (str): Command arguments
        
    Returns:
        bool: True if arguments are valid, False otherwise
    """
    if command not in ALLOWED_COMMANDS:
        return False
    
    # Check if arguments are required but not provided
    if ALLOWED_COMMANDS[command]['args_required'] and not args.strip():
        return False
    
    # Additional validation could be added here
    # For example, checking for dangerous arguments or patterns
    
    return True

def execute_command(command: str, args: str = '') -> Tuple[str, int]:
    """
    Execute a command with arguments
    
    Args:
        command (str): Command to execute
        args (str): Command arguments
        
    Returns:
        Tuple[str, int]: Command output and exit code
    
    Raises:
        ValueError: If command is not allowed or arguments are invalid
    """
    # Check if command is allowed
    if not is_command_allowed(command):
        raise ValueError(f"Command '{command}' is not allowed")
    
    # Validate command arguments
    if not validate_command_args(command, args):
        raise ValueError(f"Invalid arguments for command '{command}'")
    
    # Prepare the command
    cmd = f"{command} {args}".strip()
    cmd_args = shlex.split(cmd)
    
    try:
        # Execute the command
        process = subprocess.run(
            cmd_args,
            capture_output=True,
            text=True,
            timeout=30  # Timeout after 30 seconds
        )
        
        # Return output and exit code
        return process.stdout + process.stderr, process.returncode
    except subprocess.TimeoutExpired:
        return "Command timed out after 30 seconds", 1
    except Exception as e:
        return f"Error executing command: {str(e)}", 1