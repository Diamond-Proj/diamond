"""Manage access to the database."""

import logging
import pathlib
import os
from flask_sqlalchemy import SQLAlchemy
from flask import Flask

from app.database.db import db
from app.database.models.container import Container
from app.database.models.profile import Profile
from app.database.models.task import Task

logging.basicConfig(
    level=logging.INFO,
    datefmt="%Y-%m-%dT%H:%M:%S",
    format="%(asctime)-15s.%(msecs)03dZ %(levelname)-7s : %(name)s - %(message)s",
)
log = logging.getLogger(__name__)


class Database:

    def __init__(self, app: Flask):
        """Constructor."""
        self.app = app
        db.init_app(app)
        self.ensure_db_file_exists()

        @app.teardown_appcontext
        def close_connection(exception):
            if exception:
                db.session.rollback()
            db.session.remove()

    def ensure_db_file_exists(self):
        """Create database file if it doesn't exist."""
        db_path = pathlib.Path(os.environ["DATABASE"])
        if not db_path.exists():
            log.info(f"Creating new database file at {db_path}")
            # Create parent directories if they don't exist
            db_path.parent.mkdir(parents=True, exist_ok=True)
            # Create an empty file
            db_path.touch()
    
    def ensure_tables_exist(self):
        with self.app.app_context():
            db.create_all()

    def save_profile(self, identity_id=None, name=None, email=None, institution=None):
        log.info(f"Saving profile: {name}, {email}, {institution}")
        profile = Profile(
            identity_id=identity_id, name=name, email=email, institution=institution
        )
        db.session.merge(profile)
        db.session.commit()

    def load_profile(self, identity_id):
        log.info(f"Loading profile: {identity_id}")
        return Profile.query.filter_by(identity_id=identity_id).first()

    def save_task(
        self,
        task_id=None,
        task_name=None,
        identity_id=None,
        task_status=None,
        task_create_time=None,
        log_path=None,
    ):
        log.info(f"Saving task: {task_id}, {identity_id}")
        task = Task(
            task_id=task_id,
            task_name=task_name,
            identity_id=identity_id,
            task_status=task_status,
            task_create_time=task_create_time,
            log_path=log_path,
        )
        db.session.merge(task)
        db.session.commit()

    def load_tasks(self, identity_id):
        log.info(f"Loading task data for identity_id: {identity_id}")
        return Task.query.filter_by(identity_id=identity_id).all()

    def delete_task(self, task_id):
        log.info(f"Deleting task: {task_id}")
        Task.query.filter_by(task_id=task_id).delete()
        db.session.commit()

    def save_container(
        self,
        container_task_id=None,
        container_status=None,
        identity_id=None,
        base_image=None,
        name=None,
        location=None,
        description=None,
        dependencies=None,
        environment=None,
        commands=None,
        endpoint_id=None,
    ):
        log.info(f"Saving container: {container_task_id}, {identity_id}")
        container = Container(
            container_task_id=container_task_id,
            container_status=container_status,
            identity_id=identity_id,
            base_image=base_image,
            name=name,
            location=location,
            description=description,
            dependencies=dependencies,
            environment=environment,
            commands=commands,
            endpoint_id=endpoint_id,
        )
        db.session.merge(container)
        db.session.commit()

    def update_container_status(self, container_task_id, container_status):
        log.info(f"Updating container status: {container_task_id}, {container_status}")
        container = Container.query.filter_by(container_task_id=container_task_id).first()
        container.container_status = container_status
        db.session.commit()

    def get_container_path_by_name(self, container_name):
        log.info(f"Getting container path by name: {container_name}")
        return Container.query.filter_by(name=container_name).first().location

    def load_containers(self, identity_id):
        log.info(f"Loading container data for identity_id: {identity_id}")
        return Container.query.filter_by(identity_id=identity_id).all()

    def delete_container(self, container_task_id):
        log.info(f"Deleting container: {container_task_id}")
        Container.query.filter_by(container_task_id=container_task_id).delete()
        db.session.commit()
        