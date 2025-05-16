"""
Base Docker functionality.

This module provides the base class for Docker operations.
"""

import subprocess
import json
import time
import logging
import functools
from typing import Dict, List, Tuple, Any, Optional, Callable, TypeVar, cast

# Configure logging
logger = logging.getLogger(__name__)

# Type variables for generic functions
T = TypeVar('T')


class DockerBase:
    """Base class for Docker operations."""

    def __init__(self):
        """Initialize the Docker base class."""
        self.ensure_docker_installed()
        self._last_health_check = 0
        self._docker_healthy = False
        # Perform initial health check
        self.check_docker_health()

    def ensure_docker_installed(self) -> bool:
        """
        Ensure Docker and Docker Compose are installed.

        Returns:
            bool: True if Docker and Docker Compose are installed, False otherwise
        """
        try:
            # Check Docker
            subprocess.run(
                ['docker', '--version'],
                capture_output=True,
                text=True,
                check=True
            )

            # Check Docker Compose
            subprocess.run(
                ['docker', 'compose', 'version'],
                capture_output=True,
                text=True,
                check=True
            )

            return True
        except Exception as e:
            print(f"Docker or Docker Compose not installed: {str(e)}")
            return False

    def install_docker(self) -> Tuple[bool, str]:
        """
        Install Docker and Docker Compose.

        Returns:
            Tuple[bool, str]: Success status and output message
        """
        try:
            # Update package index
            subprocess.run(['apt-get', 'update'], check=True)

            # Install prerequisites
            subprocess.run([
                'apt-get', 'install', '-y',
                'apt-transport-https', 'ca-certificates',
                'curl', 'gnupg', 'lsb-release'
            ], check=True)

            # Add Docker's official GPG key
            subprocess.run([
                'curl', '-fsSL', 'https://download.docker.com/linux/ubuntu/gpg',
                '-o', '/tmp/docker.gpg'
            ], check=True)
            subprocess.run([
                'gpg', '--dearmor', '-o', '/usr/share/keyrings/docker-archive-keyring.gpg',
                '/tmp/docker.gpg'
            ], check=True)

            # Set up the stable repository
            subprocess.run([
                'echo', 
                'deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] '
                'https://download.docker.com/linux/ubuntu '
                '$(lsb_release -cs) stable',
                '>', '/etc/apt/sources.list.d/docker.list'
            ], check=True)

            # Install Docker Engine
            subprocess.run(['apt-get', 'update'], check=True)
            subprocess.run(['apt-get', 'install', '-y', 'docker-ce', 'docker-ce-cli', 'containerd.io'], check=True)

            # Enable and start Docker service
            subprocess.run(['systemctl', 'enable', 'docker'], check=True)
            subprocess.run(['systemctl', 'start', 'docker'], check=True)

            return True, "Docker installed successfully"
        except Exception as e:
            return False, f"Error installing Docker: {str(e)}"

    def run_command(self, cmd: List[str], capture_output: bool = True, 
                    check: bool = False, cwd: Optional[str] = None) -> Tuple[bool, str]:
        """
        Run a Docker command.

        Args:
            cmd (List[str]): Command to run
            capture_output (bool): Whether to capture output
            check (bool): Whether to check return code
            cwd (Optional[str]): Working directory

        Returns:
            Tuple[bool, str]: Success status and output
        """
        try:
            result = subprocess.run(
                cmd,
                capture_output=capture_output,
                text=True,
                check=check,
                cwd=cwd
            )

            if capture_output:
                return result.returncode == 0, result.stdout
            return True, ""
        except subprocess.CalledProcessError as e:
            return False, f"Error: {e.stderr}"
        except Exception as e:
            return False, f"Error running command: {str(e)}"

    def run_command_with_streaming(self, cmd: List[str], logger=None, cwd: Optional[str] = None) -> Tuple[bool, str]:
        """
        Run a Docker command with real-time output streaming.

        Args:
            cmd (List[str]): Command to run
            logger: Deprecated parameter, kept for backward compatibility
            cwd (Optional[str]): Working directory

        Returns:
            Tuple[bool, str]: Success status and output
        """
        import select
        import time

        try:
            # Run command with real-time output
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=cwd,
                bufsize=1,
                universal_newlines=True
            )

            output = []

            # Flag to indicate if the process is still running
            is_running = True

            # Use select to read from stdout without blocking
            while is_running:
                # Check if process has terminated
                if process.poll() is not None:
                    is_running = False
                    break

                # Use select with a timeout to avoid blocking indefinitely
                ready_to_read, _, _ = select.select([process.stdout], [], [], 0.5)

                if ready_to_read:
                    line = process.stdout.readline()
                    if not line:  # EOF
                        is_running = False
                        break

                    line = line.strip()
                    output.append(line)

            # Wait for the process to complete
            return_code = process.wait()

            # Check if the command was successful
            if return_code == 0:
                return True, "\n".join(output)
            else:
                return False, "\n".join(output)
        except Exception as e:
            error_message = f"Error running command: {str(e)}"
            return False, error_message

    def parse_json_output(self, output: str) -> List[Dict[str, Any]]:
        """
        Parse JSON output from Docker commands.

        Args:
            output (str): Command output

        Returns:
            List[Dict[str, Any]]: Parsed JSON objects
        """
        results = []
        for line in output.strip().split('\n'):
            if line:
                try:
                    results.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        return results

    def check_docker_health(self, force: bool = False) -> bool:
        """
        Check if Docker daemon is healthy and responsive.

        This method caches the health status for 30 seconds to avoid excessive checks.

        Args:
            force (bool): Force a new health check even if cached result is available

        Returns:
            bool: True if Docker daemon is healthy, False otherwise
        """
        current_time = time.time()

        # Use cached result if available and not forced
        if not force and (current_time - self._last_health_check) < 30:
            return self._docker_healthy

        try:
            # Simple command to check if Docker daemon is responsive
            result = subprocess.run(
                ['docker', 'info'],
                capture_output=True,
                text=True,
                timeout=5  # Set a timeout to avoid hanging
            )

            # Update health status
            self._docker_healthy = result.returncode == 0
            self._last_health_check = current_time

            if self._docker_healthy:
                logger.debug("Docker daemon health check: Healthy")
            else:
                logger.warning(f"Docker daemon health check: Unhealthy - {result.stderr.strip()}")

            return self._docker_healthy

        except subprocess.TimeoutExpired:
            logger.error("Docker daemon health check: Timeout - daemon is not responding")
            self._docker_healthy = False
            self._last_health_check = current_time
            return False

        except Exception as e:
            logger.error(f"Docker daemon health check: Error - {str(e)}")
            self._docker_healthy = False
            self._last_health_check = current_time
            return False

    def with_docker_health_check(self, func):
        """
        Decorator to check Docker health before executing a function.

        Args:
            func: The function to wrap with health check

        Returns:
            Function: Wrapped function that checks Docker health first
        """
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not self.check_docker_health():
                logger.error(f"Docker operation '{func.__name__}' aborted: Docker daemon is not healthy")
                return False, "Docker daemon is not healthy or not responding"
            return func(*args, **kwargs)
        return wrapper

    def with_retry(self, max_retries: int = 3, delay: float = 1.0, 
                  backoff: float = 2.0, exceptions: tuple = (Exception,)):
        """
        Decorator to retry a function on failure with exponential backoff.

        Args:
            max_retries (int): Maximum number of retries
            delay (float): Initial delay between retries in seconds
            backoff (float): Backoff multiplier (e.g. 2 means delay doubles each retry)
            exceptions (tuple): Exceptions to catch and retry on

        Returns:
            Callable: Decorator function
        """
        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            @functools.wraps(func)
            def wrapper(*args, **kwargs) -> T:
                mtries, mdelay = max_retries, delay
                last_exception = None

                # Try the function up to max_retries times
                while mtries > 0:
                    try:
                        return func(*args, **kwargs)
                    except exceptions as e:
                        mtries -= 1
                        last_exception = e

                        if mtries <= 0:
                            logger.error(f"Function {func.__name__} failed after {max_retries} retries: {str(e)}")
                            break

                        logger.warning(f"Retrying {func.__name__} in {mdelay:.2f}s after error: {str(e)}")
                        time.sleep(mdelay)
                        mdelay *= backoff

                # If we get here, all retries failed
                if isinstance(last_exception, Exception):
                    logger.error(f"All retries failed for {func.__name__}: {str(last_exception)}")
                    # For Docker operations that return (bool, str) tuples
                    if hasattr(func, '__annotations__') and 'return' in func.__annotations__:
                        return_type = func.__annotations__['return']
                        if return_type == Tuple[bool, str]:
                            return cast(T, (False, f"Operation failed after {max_retries} retries: {str(last_exception)}"))

                    # Re-raise the last exception
                    raise last_exception

                # This should never happen, but just in case
                return cast(T, None)

            return wrapper
        return decorator
