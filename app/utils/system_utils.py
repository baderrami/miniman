import os
import subprocess
import platform
import psutil
import shutil
from typing import Dict, Any, List, Tuple


def get_system_info() -> Dict[str, Any]:
    """
    Get system information

    Returns:
        Dict[str, Any]: System information
    """
    info = {
        'hostname': platform.node(),
        'platform': platform.system(),
        'platform_version': platform.version(),
        'architecture': platform.machine(),
        'processor': platform.processor(),
        'python_version': platform.python_version(),
        'uptime': get_uptime(),
        'memory': get_memory_info(),
        'cpu_usage': psutil.cpu_percent(interval=1),
        'load_average': get_load_average()
    }

    return info


def get_uptime() -> str:
    """
    Get system uptime

    Returns:
        str: Uptime in human-readable format
    """
    try:
        uptime_seconds = float(open('/proc/uptime').read().split()[0])

        # Convert to days, hours, minutes, seconds
        days, remainder = divmod(uptime_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)

        if days > 0:
            return f"{int(days)}d {int(hours)}h {int(minutes)}m"
        elif hours > 0:
            return f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
        elif minutes > 0:
            return f"{int(minutes)}m {int(seconds)}s"
        else:
            return f"{int(seconds)}s"
    except Exception as e:
        print(f"Error getting uptime: {str(e)}")
        return "Unknown"


def get_memory_info() -> Dict[str, Any]:
    """
    Get memory information

    Returns:
        Dict[str, Any]: Memory information
    """
    mem = psutil.virtual_memory()

    return {
        'total': format_bytes(mem.total),
        'available': format_bytes(mem.available),
        'used': format_bytes(mem.used),
        'percent': mem.percent
    }


def get_load_average() -> List[float]:
    """
    Get system load average

    Returns:
        List[float]: Load average for 1, 5, and 15 minutes
    """
    try:
        return os.getloadavg()
    except Exception as e:
        print(f"Error getting load average: {str(e)}")
        return [0.0, 0.0, 0.0]


def get_disk_usage() -> Dict[str, Dict[str, Any]]:
    """
    Get disk usage information

    Returns:
        Dict[str, Dict[str, Any]]: Disk usage information
    """
    disk_info = {}

    for partition in psutil.disk_partitions():
        try:
            usage = psutil.disk_usage(partition.mountpoint)

            disk_info[partition.mountpoint] = {
                'device': partition.device,
                'fstype': partition.fstype,
                'total': format_bytes(usage.total),
                'used': format_bytes(usage.used),
                'free': format_bytes(usage.free),
                'percent': usage.percent
            }
        except Exception as e:
            print(f"Error getting disk usage for {partition.mountpoint}: {str(e)}")

    return disk_info


def format_bytes(bytes: int) -> str:
    """
    Format bytes to human-readable format

    Args:
        bytes (int): Bytes to format

    Returns:
        str: Formatted string
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes < 1024:
            return f"{bytes:.2f} {unit}"
        bytes /= 1024

    return f"{bytes:.2f} PB"


def perform_system_reset() -> None:
    """
    Perform system reset by clearing overlay filesystem and rebooting

    Raises:
        Exception: If reset fails
    """
    try:
        # Execute the system-reset script
        subprocess.run(['/usr/local/bin/system-reset'], check=True)
    except Exception as e:
        raise Exception(f"Failed to reset system: {str(e)}")