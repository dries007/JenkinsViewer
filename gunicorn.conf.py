import os
from multiprocessing import cpu_count


def max_workers():
    return cpu_count()


proc_name = 'JenkinsViewer'
bind = 'unix:/sock/web.sock'
max_requests = 1000
max_requests_jitter = 100
workers = max_workers()

# Required env var, avoid running as root.
user, group = map(int, os.environ["RUNAS"].split(':'))


def on_starting(server):
    # Make sure the socket folder is owned by the user that will write to it.
    # This is done here to allow tmpfs folders like /run to be used for mounting.
    # This makes it so docker doesn't need a persistent folder to keep the file permissions correct.
    os.chown("/sock", user, group)
