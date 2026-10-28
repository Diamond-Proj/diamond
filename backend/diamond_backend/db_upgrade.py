"""Apply pending database migrations; run before the server starts.

Databases created before migrations were added have the initial tables but
no alembic_version row, so `upgrade` would try to recreate them. Stamp those
at the initial revision first (see backend/README.md).
"""

import sqlalchemy as sa
from flask_migrate import stamp, upgrade

from diamond_backend.app import app
from diamond_backend.app.database.db import db

INITIAL_REVISION = "97c3d7c7b8d2"

with app.app_context():
    inspector = sa.inspect(db.engine)
    if not inspector.has_table("alembic_version") and inspector.has_table("profile"):
        stamp(revision=INITIAL_REVISION)
    upgrade()
