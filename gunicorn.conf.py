# Gunicorn configuration file for production deployment

# Server socket
bind = '0.0.0.0:8000'

# Worker processes
workers = 4  # Recommended: 2-4 x $(NUM_CORES)
worker_class = 'sync'
worker_connections = 1000
timeout = 30
keepalive = 2

# Server mechanics
daemon = False
pidfile = '/var/run/gunicorn.pid'
umask = 0o007
user = None
group = None
tmp_upload_dir = None

# Logging
errorlog = '-'
loglevel = 'info'
accesslog = '-'
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Process naming
proc_name = 'device-manager'

# Server hooks
def on_starting(server):
    """
    Called just before the master process is initialized.
    """
    pass

def on_reload(server):
    """
    Called before a worker is reloaded.
    """
    pass

def when_ready(server):
    """
    Called just after the server is started.
    """
    print("Gunicorn server is ready. Application startup complete.")

def worker_int(worker):
    """
    Called just after a worker exited on SIGINT or SIGQUIT.
    """
    pass

def worker_abort(worker):
    """
    Called when a worker received the SIGABRT signal.
    """
    pass

def post_fork(server, worker):
    """
    Called just after a worker has been forked.
    """
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def pre_fork(server, worker):
    """
    Called just prior to forking the worker subprocess.
    """
    pass

def pre_exec(server):
    """
    Called just prior to forking off a secondary master process during things like config reloading.
    """
    pass