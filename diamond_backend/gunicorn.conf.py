import os

from dotenv import load_dotenv

# Load environment variables before Gunicorn configuration is processed
load_dotenv(override=True)

# Get the GUNICORN_CMD_ARGS from environment and parse it
cmd_args = os.getenv("GUNICORN_CMD_ARGS", "")
# Remove leading '--' and split on space + '--'
args_list = cmd_args.lstrip("-").split(" --")
args_dict = dict(arg.split("=") for arg in args_list if "=" in arg)

print("args_dict: ", args_dict)
# Set Gunicorn config variables
bind = args_dict.get("bind", "localhost:5328")
workers = int(args_dict.get("workers", 1))
threads = int(args_dict.get("threads", 100))
worker_class = args_dict.get("worker-class", "gthread")

print("bind: ", bind)
print("workers: ", workers)
print("threads: ", threads)
print("worker_class: ", worker_class)

# Add these for better debugging
accesslog = "-"
errorlog = "-"
loglevel = "debug"
