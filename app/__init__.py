import logger
import os
from datetime import datetime

from dotenv import dotenv_values, load_dotenv
from flask import Flask
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix

from .database.data_manager import Database
from .tempdb.tempdb_manager import TempDatabase


# Load environment variables first, before any other imports or app creation
load_dotenv()

log_dir= os.environ.get("DIAMOND_BACKEND_LOG_PATH", "/tmp")
log_name = os.environ.get("DIAMOND_BACKEND_LOG_NAME", "diamond-admin-backend")
if not os.access(log_dir, os.W_OK):
    logger = logger.Logger(name=log_name)
    logger.warning(f"Directory {log_dir} is not writable. Only logging to console.")
else:
    log_path = f"{log_dir}/{log_name}_{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.log"
    logger = logger.Logger(name=log_name, path=log_path)
    logger.info(f"Logging to {log_path}")

NEXT_URL = os.environ.get("NEXT_URL", "http://localhost:3000")  # Frontend URL
# Always allow localhost for development, and add production URL if different
allowed_origins = ["http://localhost:3000"]

if NEXT_URL != "http://localhost:3000":
    allowed_origins.append(NEXT_URL)

# print("Allowed Origins: ", allowed_origins)

is_production = os.environ.get("FLASK_ENV") == "production"

# Load configuration based on environment
if is_production:
    config = dict(os.environ)  # Only OS environment variables in production
else:
    config = dotenv_values()  # Only .env file variables in local development

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

CORS(
    app,
    supports_credentials=True,
    resources={r"/*": {"origins": allowed_origins}},
)

app.config.from_mapping(config)

app.config['SQLALCHEMY_BINDS'] = {
    # 'temp_db': 'sqlite:///:memory:'
    'temp_db': 'sqlite:////Users/haotianxie/work/diamond-admin-backend/data/app.db'
}

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))

# print("sql url: ", app.config["SQLALCHEMY_DATABASE_URI"])

with app.app_context():
    database = Database(app)
    temp_database = TempDatabase(app)


# Import routes after app is created to avoid circular imports
from . import routes
