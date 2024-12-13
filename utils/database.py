"""Manage access to the database."""

import logging
import os
import sqlite3

from flask import g

# create and configure logger
logging.basicConfig(
    level=logging.INFO,
    datefmt="%Y-%m-%dT%H:%M:%S",
    format="%(asctime)-15s.%(msecs)03dZ %(levelname)-7s : %(name)s - %(message)s",
)
# create log object with current module name
log = logging.getLogger(__name__)


class Database:
    """Database access."""

    def __init__(self, app):
        """Constructor."""
        self.app = app

        @app.teardown_appcontext
        def close_connection(exception):
            """Close database connection when finished handling request."""
            db = getattr(g, "_database", None)

            if db is not None:
                db.close()

    def ensure_tables_exist(self):
        """Ensure all required tables are created."""
        db = self.get_db()
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS profile (
                    identity_id VARCHAR(255) PRIMARY KEY,
                    name VARCHAR(255),
                    email VARCHAR(255),
                    institution TEXT
			)
			"""
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS task (
                task_id TEXT PRIMARY KEY,
                identity_id VARCHAR(255),
                task_status TEXT,
                task_create_time TIMESTAMP,
                FOREIGN KEY (identity_id) REFERENCES profile(identity_id)
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS container (
                container_task_id TEXT PRIMARY KEY,
                identity_id VARCHAR(255),
                base_image TEXT,
                name TEXT,
                location TEXT,
                description TEXT,
                FOREIGN KEY (identity_id) REFERENCES profile(identity_id)
            )
            """
        )
        db.commit()

    def connect_to_db(self):
        """Open database and return a connection handle."""
        return sqlite3.connect(os.environ["DATABASE"])

    def get_db(self):
        """Return the app global db connection or create one."""
        db = getattr(g, "_database", None)

        if db is None:
            db = g._database = self.connect_to_db()
            db.row_factory = sqlite3.Row

        return db

    def query_db(self, query, args=(), one=False):
        """Query the database."""
        log.info(f"Querying database: {query}")
        cur = self.get_db().execute(query, args)

        rv = cur.fetchall()
        cur.close()

        return (rv[0] if rv else None) if one else rv

    def save_profile(self, identity_id=None, name=None, email=None, institution=None):
        """Persist user profile."""
        log.info(f"Saving profile: {name}, {email}, {institution}")
        db = self.get_db()
        # Ensure the data types are correct, convert if necessary

        identity_id = str(identity_id) if identity_id is not None else None
        name = str(name) if name is not None else None
        email = str(email) if email is not None else None
        institution = str(institution) if institution is not None else None

        db.execute(
            """INSERT INTO profile (identity_id, name, email, institution)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(identity_id) DO UPDATE SET
            name = excluded.name, email = excluded.email, institution = excluded.institution""",
            (identity_id, name, email, institution),
        )
        db.commit()

    def load_profile(self, identity_id):
        """Load user profile."""
        log.info(f"Loading profile: {identity_id}")
        return self.query_db(
            """select name, email, institution from profile
														 where identity_id = ?""",
            [identity_id],
            one=True,
        )
    
    def save_task(self, task_id = None, identity_id=None, task_status=None, task_create_time=None):
        """Persist task information."""
        log.info(f"Saving task: {task_id}, {identity_id}")
        db = self.get_db()

        identity_id = str(identity_id) if identity_id is not None else None
        task_id = str(task_id) if task_id is not None else None
        task_status = str(task_status) if task_status is not None else None
        task_create_time = str(task_create_time) if task_create_time is not None else None

        db.execute(
            """INSERT INTO task (identity_id, task_id, task_status, task_create_time)
            VALUES (?, ?, ?, ?)""",
            (identity_id, task_id, task_status, task_create_time),
        )
        db.commit()

    def load_tasks(self, identity_id):
        """Load task data for a specific profile."""
        log.info(f"Loading task data for identity_id: {identity_id}")
        return self.query_db(
            """SELECT task_id, task_status, task_create_time FROM task
            WHERE identity_id = ?""",
            [identity_id]
        )

    def delete_task(self, task_id):
        """Delete a task."""
        log.info(f"Deleting task: {task_id}")
        db = self.get_db()
        db.execute(
            """DELETE FROM task
            WHERE task_id = ?""",
            [task_id]
        )
        db.commit()


    def save_container(
        self,
        container_task_id = None,
        identity_id=None,
        base_image = None,
        name=None,
        location=None,
        description=None,
    ):
        """Persist container information."""
        log.info(f"Saving task: {container_task_id}, {identity_id}")
        db = self.get_db()

        identity_id = str(identity_id) if identity_id is not None else None
        container_task_id = str(container_task_id) if container_task_id is not None else None
        base_image = str(base_image) if base_image is not None else None
        name = str(name) if name is not None else None
        location = str(location) if location is not None else None
        description = str(description) if description is not None else None

        db.execute(
            """INSERT INTO container (identity_id, container_task_id, base_image, name, location, description)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (identity_id, container_task_id, base_image, name, location, description),
        )
        db.commit()

    def load_containers(self, identity_id):
        """Load container data for a specific profile."""
        log.info(f"Loading container data for identity_id: {identity_id}")
        return self.query_db(
            """SELECT container_task_id, base_image, name, location, description FROM container
            WHERE identity_id = ?""",
            [identity_id]
        )

    def delete_container(self, container_task_id):
        """Delete a container."""
        log.info(f"Deleting container: {container_task_id}")
        db = self.get_db()
        db.execute(
            """DELETE FROM container
            WHERE container_task_id = ?""",
            [container_task_id]
        )
        db.commit()
