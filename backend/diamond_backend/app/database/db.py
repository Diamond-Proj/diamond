import os

from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
migrate = Migrate()

# backend/migrations, resolved absolutely so `flask db` works from any cwd
MIGRATIONS_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), os.pardir, os.pardir, os.pardir, "migrations"
    )
)
