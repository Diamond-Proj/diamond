import logging
import os

from dotenv import dotenv_values, load_dotenv
from flask import Flask
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix

from .database.data_manager import Database

# Load environment variables first, before any other imports or app creation
load_dotenv(override=True)

# create and configure logger
logging.basicConfig(
    level=logging.INFO,
    datefmt="%Y-%m-%dT%H:%M:%S",
    format="%(asctime)-15s.%(msecs)03dZ %(levelname)-7s : %(name)s - %(message)s",
)
# create log object with current module name
log = logging.getLogger(__name__)

HOST = os.environ.get("HOST")
config = dotenv_values()
print("config: ", config)

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
CORS(
    app,
    supports_credentials=True,
    resources={r"/*": {"origins": HOST}},
)

app.config.from_mapping(config)

basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////' + os.path.join(basedir, app.config['DATABASE'])
with app.app_context():
    database = Database(app)
    database.ensure_tables_exist()

# Import routes after app is created to avoid circular imports
from . import routes
