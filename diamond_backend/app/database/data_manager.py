"""Manage access to the database."""

import json
import logging  # some issue with importing logger from app
import typing as t

from flask import Flask

from diamond_backend.app.database.db import db
from diamond_backend.app.database.models.container import Container
from diamond_backend.app.database.models.dataset import Dataset
from diamond_backend.app.database.models.endpoints import Endpoints
from diamond_backend.app.database.models.profile import Profile  # noqa: F401
from diamond_backend.app.database.models.task import Task
from diamond_backend.app.errors import EndpointNotFound
from diamond_backend.app.utils.errors import TaskNotFoundError

logging.basicConfig(
    level=logging.INFO,
    datefmt="%Y-%m-%dT%H:%M:%S",
    format="%(asctime)-15s.%(msecs)03dZ %(levelname)-7s : %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


class Database:
    def __init__(self, app: Flask):
        """Constructor."""
        self.app = app
        db.init_app(app)
        # self.ensure_db_file_exists()

        @app.teardown_appcontext
        def close_connection(exception):
            if exception:
                db.session.rollback()
            db.session.remove()

    # def ensure_db_file_exists(self):
    #     """Create database file if it doesn't exist."""
    #     db_path = pathlib.Path(os.environ["DATABASE"])
    #     if not db_path.exists():
    #         log.info(f"Creating new database file at {db_path}")
    #         # Create parent directories if they don't exist
    #         db_path.parent.mkdir(parents=True, exist_ok=True)
    #         # Create an empty file
    #         db_path.touch()

    def ensure_tables_exist(self):
        with self.app.app_context():
            db.create_all()

    def save_profile(
        self,
        identity_id=None,
        name=None,
        email=None,
        institution=None,
        is_initialized=False,
    ):
        logger.info(f"Saving profile: {name}, {email}, {institution}")
        profile = Profile(
            identity_id=identity_id,
            name=name,
            email=email,
            institution=institution,
            is_initialized=is_initialized,
        )
        db.session.merge(profile)
        db.session.commit()

    def set_profile_initialization_state(
        self, identity_id=None, initialized: bool = True
    ):
        profile = Profile.query.filter_by(identity_id=identity_id).first()
        profile.is_initialized = initialized
        db.session.commit()

    def load_profile(self, identity_id):
        logger.debug(f"Loading profile: {identity_id}")
        return Profile.query.filter_by(identity_id=identity_id).first()

    def save_task(
        self,
        task_id=None,
        batch_job_id=None,
        task_name=None,
        identity_id=None,
        task_status=None,
        task_create_time=None,
        # TODO: Remove log_path
        log_path=None,
        stdout_path=None,
        stderr_path=None,
        compute_endpoint_id=None,
        checkpoint_path=None,
    ):
        logger.info(f"Saving task: {task_id}, {identity_id}")
        task = Task(
            task_id=task_id,
            batch_job_id=batch_job_id,
            task_name=task_name,
            identity_id=identity_id,
            task_status=task_status,
            task_create_time=task_create_time,
            log_path=log_path,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            compute_endpoint_id=compute_endpoint_id,
            checkpoint_path=checkpoint_path,
        )
        db.session.merge(task)
        db.session.commit()

    def update_task_status(self, task_id, task_status):
        logger.info(f"Updating task status: {task_id}, {task_status}")
        task = Task.query.filter_by(task_id=task_id).first()
        if task:
            task.task_status = task_status
            db.session.commit()
        else:
            # logger.error(f"Task {task_id} not found")
            raise TaskNotFoundError(task_id=task_id)

    def load_tasks(self, identity_id):
        logger.info(f"Loading task data for identity_id: {identity_id}")
        return Task.query.filter_by(identity_id=identity_id).all()

    def delete_task(self, task_id):
        logger.info(f"Deleting task: {task_id}")
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
        is_public=False,
        host=None,
    ):
        logger.info(f"Saving container: {container_task_id}, {identity_id}")
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
            is_public=is_public,
            host=host,
        )
        db.session.merge(container)
        db.session.commit()

    def update_container_status(self, container_task_id, container_status):
        logger.info(
            f"Updating container status: {container_task_id}, {container_status}"
        )
        container = Container.query.filter_by(
            container_task_id=container_task_id
        ).first()
        container.container_status = container_status
        db.session.commit()

    def get_container_path_by_name(self, container_name):
        logger.info(f"Getting container path by name: {container_name}")
        return Container.query.filter_by(name=container_name).first().location

    def load_containers(self, identity_id):
        logger.info(f"Loading container data for identity_id: {identity_id}")
        return Container.query.filter_by(identity_id=identity_id).all()

    def load_containers_by_endpoint(self, identity_id, endpoint_uuid):
        logger.info(
            f"Loading container data for identity_id: {identity_id} on endpoint: {endpoint_uuid}"
        )
        return Container.query.filter_by(
            identity_id=identity_id, endpoint_id=endpoint_uuid
        ).all()

    def load_public_containers_by_hosts(self, hosts, exclude_identity_id=None):
        logger.info(
            f"Loading public containers for hosts: {hosts}, excluding identity: {exclude_identity_id}"
        )
        if not hosts:
            return []

        return Container.query.filter(
            Container.is_public.is_(True),
            Container.host.in_(hosts),
        )

    def update_container_public_status(self, container_name, identity_id, is_public):
        logger.info(
            f"Updating container public status: {container_name}, identity_id: {identity_id}, is_public: {is_public}"
        )
        container = Container.query.filter_by(
            name=container_name, identity_id=identity_id
        ).first()
        if container:
            container.is_public = is_public
            db.session.commit()
        return container

    def get_container_by_name(self, container_name):
        logger.info(f"Fetching container by name: {container_name}")
        return Container.query.filter_by(name=container_name).first()

    def delete_container(self, container_task_id):
        logger.info(f"Deleting container: {container_task_id}")
        Container.query.filter_by(container_task_id=container_task_id).delete()
        db.session.commit()

    def exists_endpoint(self, identity_id, endpoint_uuid):
        endpoint = Endpoints.query.filter_by(
            identity_id=identity_id, endpoint_uuid=endpoint_uuid
        ).first()
        return endpoint is not None

    def save_endpoint(
        self,
        identity_id,
        endpoint_name,
        endpoint_host,
        endpoint_uuid,
        endpoint_status,
        is_managed: bool = False,
    ):
        logger.info(
            f"Saving endpoint: {endpoint_name}, {endpoint_host}, {endpoint_uuid}"
        )
        endpoint = Endpoints(
            identity_id=identity_id,
            endpoint_name=endpoint_name,
            endpoint_host=endpoint_host,
            endpoint_uuid=endpoint_uuid,
            endpoint_status=endpoint_status,
            is_managed=is_managed,
        )
        db.session.merge(endpoint)
        db.session.commit()

    def update_endpoint_managed_status(
        self, identity_id, endpoint_uuid, is_managed: bool = True
    ):
        endpoint = Endpoints.query.filter_by(
            identity_id=identity_id, endpoint_uuid=endpoint_uuid
        ).first()
        if endpoint:
            endpoint.is_managed = is_managed
            db.session.commit()
        else:
            raise EndpointNotFound(
                "Requested endpoint not found",
                identity_id=identity_id,
                endpoint_uuid=endpoint_uuid,
            )

    def get_endpoints(self, identity_id):
        return Endpoints.query.filter_by(identity_id=identity_id).all()

    def delete_endpoints(self, identity_id):
        Endpoints.query.filter_by(identity_id=identity_id).delete()
        db.session.commit()

    def get_endpoint_host(self, endpoint_uuid):
        endpoint = Endpoints.query.filter_by(endpoint_uuid=endpoint_uuid).first()
        if endpoint:
            return endpoint.endpoint_host
        else:
            logger.error(f"Endpoint {endpoint_uuid} not found")
            return None

    def get_endpoint_status(self, endpoint_uuid):
        endpoint = Endpoints.query.filter_by(endpoint_uuid=endpoint_uuid).first()
        if endpoint:
            return endpoint.endpoint_status
        else:
            logger.error(f"Endpoint {endpoint_uuid} not found")
            return None

    def update_endpoint_status(self, endpoint_uuid, endpoint_status):
        endpoint = Endpoints.query.filter_by(endpoint_uuid=endpoint_uuid).first()
        if endpoint:
            endpoint.endpoint_status = endpoint_status
            db.session.commit()
        else:
            logger.error(f"Endpoint {endpoint_uuid} not found")

    def save_partition(self, identity_id, endpoint_uuid, partitions):
        endpoint = Endpoints.query.filter_by(
            identity_id=identity_id, endpoint_uuid=endpoint_uuid
        ).first()
        if endpoint:
            endpoint.partitions = partitions
            db.session.commit()
        else:
            logger.error(
                f"Endpoint not found for user {identity_id} and UUID {endpoint_uuid}"
            )

    def get_partitions(self, identity_id, endpoint_uuid):
        endpoint = Endpoints.query.filter_by(
            identity_id=identity_id, endpoint_uuid=endpoint_uuid
        ).first()
        if endpoint:
            return endpoint.partitions
        else:
            logger.error(
                f"Endpoint not found for user {identity_id} and UUID {endpoint_uuid}"
            )
            return None

    def save_accounts(self, identity_id, endpoint_uuid, accounts):
        endpoint = Endpoints.query.filter_by(
            identity_id=identity_id, endpoint_uuid=endpoint_uuid
        ).first()
        if endpoint:
            endpoint.accounts = accounts
            db.session.commit()
        else:
            logger.error(
                f"Endpoint not found for user {identity_id} and UUID {endpoint_uuid}"
            )

    def get_accounts(self, identity_id, endpoint_uuid):
        endpoint = Endpoints.query.filter_by(
            identity_id=identity_id, endpoint_uuid=endpoint_uuid
        ).first()
        if endpoint:
            return endpoint.accounts
        else:
            logger.error(
                f"Endpoint not found for user {identity_id} and UUID {endpoint_uuid}"
            )
            return None

    def save_diamond_dir(self, identity_id, endpoint_uuid, diamond_dir):
        endpoint = Endpoints.query.filter_by(
            identity_id=identity_id, endpoint_uuid=endpoint_uuid
        ).first()
        if endpoint:
            endpoint.diamond_dir = diamond_dir
            db.session.commit()
        else:
            logger.error(
                f"Endpoint not found for user {identity_id} and UUID {endpoint_uuid}"
            )

    def get_diamond_dir(self, identity_id, endpoint_uuid):
        endpoint = Endpoints.query.filter_by(
            identity_id=identity_id, endpoint_uuid=endpoint_uuid
        ).first()
        if endpoint:
            return endpoint.diamond_dir
        else:
            logger.error(
                f"Endpoint not found for user {identity_id} and UUID {endpoint_uuid}"
            )
            return None

    def get_stats(self, identity_id) -> dict[str, t.Collection]:
        """Fetch stats for the dashboard"""
        user_endpoints = Endpoints.query.filter_by(identity_id=identity_id)
        user_tasks = Task.query.filter_by(identity_id=identity_id)
        user_images = Container.query.filter_by(identity_id=identity_id)

        recent_tasks = (
            Task.query.filter_by(identity_id=identity_id)
            .order_by(Task.task_create_time.desc())
            .limit(10)
            .all()
        )

        priv_datasets = Dataset.query.filter_by(identity_id=identity_id).filter_by(
            public=False
        )
        pub_datasets = Dataset.query.filter_by(public=True)
        task_summary: list[dict[str, t.Any]] = []
        for task in recent_tasks:
            summary = {
                "name": task.task_name,
                "task_id": task.task_id,
                "status": task.task_status,
                "create_time": task.task_create_time,
                # TODO: Fix the following once we update task table with last_update_time
                "last_update_time": task.task_create_time,
            }
            task_summary.append(summary)

        stats = {
            "endpoints": {
                "online": len(
                    [ep for ep in user_endpoints if ep.endpoint_status == "online"]
                ),
                "offline": len(
                    [ep for ep in user_endpoints if ep.endpoint_status == "offline"]
                ),
            },
            "tasks": {
                "completed": len(
                    [
                        t
                        for t in user_tasks
                        if str(t.task_status).upper() in ("COMPLETING", "COMPLETED")
                    ]
                ),
                "running": len(
                    [
                        t
                        for t in user_tasks
                        if str(t.task_status).upper()
                        in ("PENDING", "RUNNING", "SUBMITTED")
                    ]
                ),
                "failed": len(
                    [t for t in user_tasks if str(t.task_status).upper() in ("FAILED")]
                ),
            },
            "images": {
                "public": 0,
                "private": len(user_images.all()),
            },
            # Pending datasets PR merge
            "datasets": {
                "public": len(pub_datasets.all()),
                "private": len(priv_datasets.all()),
            },
            # Recent tasks will return a list of upto 10 tasks
            "recent_tasks": task_summary,
        }

        return stats

    def save_dataset(
        self,
        collection_uuid,
        globus_path,
        system_path,
        machine_name,
        dataset_metadata,
        identity_id,
        public=False,
        dataset_name=None,
    ):
        logger.info(
            f"Saving dataset: {collection_uuid}:{globus_path} for user {identity_id}"
        )

        if not isinstance(dataset_metadata, str):
            dataset_metadata = json.dumps(dataset_metadata)

        dataset = Dataset(
            collection_uuid=collection_uuid,
            globus_path=globus_path,
            system_path=system_path,
            public=public,
            machine_name=machine_name,
            dataset_metadata=dataset_metadata,
            identity_id=identity_id,
            dataset_name=dataset_name,
        )
        db.session.merge(dataset)
        db.session.commit()

    def get_datasets(self, identity_id) -> list[Dataset]:
        logger.info(f"Loading datasets for identity_id: {identity_id}")

        user_datasets = Dataset.query.filter_by(identity_id=identity_id).all()
        public_datasets = Dataset.query.filter_by(public=True).all()

        return user_datasets + public_datasets

    def get_dataset_by_id(self, dataset_id) -> Dataset:
        dataset = Dataset.query.filter_by(id=dataset_id).first()
        return dataset
