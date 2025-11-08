# Gunicorn Configuration File
# For Patreon Web Viewer Production Deployment

import multiprocessing
import os

# Server Socket
bind = os.getenv('WEB_VIEWER_BIND', '127.0.0.1:5001')
backlog = 2048

# Worker Processes
workers = int(os.getenv('WEB_VIEWER_WORKERS', multiprocessing.cpu_count()))
worker_class = 'sync'  # sync, gevent, or eventlet
worker_connections = 1000
timeout = int(os.getenv('WEB_VIEWER_TIMEOUT', 120))
keepalive = 5

# Restart workers after this many requests (prevents memory leaks)
max_requests = 1000
max_requests_jitter = 50

# Logging
accesslog = '-'  # stdout
errorlog = '-'   # stderr
loglevel = os.getenv('WEB_VIEWER_LOG_LEVEL', 'info')
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process Naming
proc_name = 'patreon_web_viewer'

# Server Mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (if needed)
# keyfile = None
# certfile = None

# Preload application for better memory usage
preload_app = False  # Set to True if using Redis cache (shared between workers)

# Server Hooks
def on_starting(server):
    """Called just before the master process is initialized."""
    print("🚀 Starting Patreon Web Viewer with Gunicorn")

def on_reload(server):
    """Called to recycle workers during a reload via SIGHUP."""
    print("♻️  Reloading workers...")

def when_ready(server):
    """Called just after the server is started."""
    print(f"✅ Server ready! Listening on {bind}")
    print(f"   Workers: {workers}")
    print(f"   Timeout: {timeout}s")

def worker_int(worker):
    """Called just after a worker exited on SIGINT or SIGQUIT."""
    print(f"⚠️  Worker {worker.pid} interrupted")

def pre_fork(server, worker):
    """Called just before a worker is forked."""
    pass

def post_fork(server, worker):
    """Called just after a worker has been forked."""
    print(f"👷 Worker spawned (pid: {worker.pid})")

def pre_exec(server):
    """Called just before a new master process is forked."""
    print("🔄 Forking new master process...")

def worker_exit(server, worker):
    """Called just after a worker has been exited."""
    print(f"👋 Worker {worker.pid} exited")
