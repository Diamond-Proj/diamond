import os
from datetime import datetime

import logger
from dotenv import dotenv_values, load_dotenv
from flask import Flask
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix

from diamond_backend.app.database.data_manager import Database

# Load environment variables first, before any other imports or app creation
load_dotenv()

log_dir = os.environ.get("DIAMOND_BACKEND_LOG_PATH", "/tmp")
log_name = os.environ.get("DIAMOND_BACKEND_LOG_NAME", "diamond-admin-backend")
if not os.access(log_dir, os.W_OK):
    logger = logger.Logger(name=log_name)
    logger.warning(f"Directory {log_dir} is not writable. Only logging to console.")
else:
    log_path = (
        f"{log_dir}/{log_name}_{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.log"
    )
    logger = logger.Logger(name=log_name, path=log_path)
    logger.info(f"Logging to {log_path}")

NEXT_URL = os.environ.get("NEXT_URL", "http://localhost:3000")  # Frontend URL
# Always allow localhost for development, and add production URL if different
allowed_origins = ["http://localhost:3000"]

if NEXT_URL != "http://localhost:3000":
    allowed_origins.append(NEXT_URL)

# print("Allowed Origins: ", allowed_origins)

env_kind = os.environ.get("FLASK_ENV")

# Load configuration based on environment
if env_kind == "production":
    config = dict(os.environ)  # Only OS environment variables in production
elif env_kind == "development":
    # Load from .env file for local development
    config = dotenv_values()  # type: ignore[assignment]
elif env_kind == "pytest":
    config = dict(os.environ)  # os.environ pull from tox.ini for pytests
else:
    raise Exception(f"Environment:{env_kind} is not supported")

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)  # type: ignore[method-assign]

CORS(
    app,
    supports_credentials=True,
    resources={r"/*": {"origins": allowed_origins}},
)

app.config.from_mapping(config)

# Ensure SQLAlchemy uses pre-ping and reasonable pool recycle to avoid stale connections.
engine_options = app.config.setdefault("SQLALCHEMY_ENGINE_OPTIONS", {})
engine_options.setdefault("pool_pre_ping", True)
engine_options.setdefault("pool_recycle", 300)

basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))

# print("sql url: ", app.config["SQLALCHEMY_DATABASE_URI"])

with app.app_context():
    g_database = Database(app)


# Import routes after app is created to avoid circular imports
def register_routes():
    from diamond_backend.app import base_routes as base_routes
    from diamond_backend.app import containers as containers
    from diamond_backend.app import datasets as datasets
    from diamond_backend.app import endpoints as endpoints
    from diamond_backend.app import images as images
    from diamond_backend.app import tasks as tasks
    from diamond_backend.app import transfers as transfers


register_routes()
