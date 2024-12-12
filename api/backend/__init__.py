import json
import logging
import os

import dotenv
from dotenv import dotenv_values, load_dotenv
from flask import Flask
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix

from api.backend.utils.database import Database

# create and configure logger
logging.basicConfig(
    level=logging.INFO,
    datefmt="%Y-%m-%dT%H:%M:%S",
    format="%(asctime)-15s.%(msecs)03dZ %(levelname)-7s : %(name)s - %(message)s",
)
# create log object with current module name
log = logging.getLogger(__name__)


load_dotenv(override=True)

# logging.info('env: ',dotenv.dotenv_values().keys())
# logging.info("Loading configuration from .env file", os.environ['USER_SCOPES'])

HOST = os.environ.get("HOST")

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
CORS(
    app,
    supports_credentials=True,
    resources={r"/*": {"origins": HOST}},
)
config = dotenv_values()
app.config.from_mapping(config)
# app.secret_key = os.environ.get('SECRET_KEY', 'DEFAULT_SECRET_KEY')

with app.app_context():
    database = Database(app)
    database.ensure_tables_exist()
