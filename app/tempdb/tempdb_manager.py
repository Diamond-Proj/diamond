from flask import Flask
import logging
from datetime import datetime, timedelta

from app.database.db import db
from app.tempdb.models.endpoints import Endpoints
from app.tempdb.models.users import Users

logging.basicConfig(level=logging.INFO, datefmt='%Y-%m-%dT%H:%M:%S',
                    format='%(asctime)-15s.%(msecs)03dZ %(levelname)-7s : %(name)s - %(message)s')
logger = logging.getLogger(__name__)

class TempDatabase:

    def __init__(self, app: Flask):
        self.app = app
        with self.app.app_context():
            db.create_all()

    def exists_user_id(self, user_id):
        user = Users.query.filter_by(user_id=user_id).first()
        return user is not None
    
    def get_all_users(self):
        users = Users.query.all()
        return users
    
    def remove_expired_users(self):
        Users.query.filter(Users.ttl < datetime.now()).delete()
        db.session.commit()

    def save_user_id(self, user_id):
        user = Users(
            user_id=user_id,
            endpoints_registered=False,
            ttl=datetime.now() + timedelta(minutes=30)
        )
        db.session.merge(user)
        db.session.commit()

    def delete_user_id(self, user_id):
        Users.query.filter_by(user_id=user_id).delete()
        db.session.commit()

    def user_endpoints_registered(self, user_id):
        user = Users.query.filter_by(user_id=user_id).first()
        return user.endpoints_registered

    def exists_endpoint(self, user_id, endpoint_uuid):
        endpoint = Endpoints.query.filter_by(user_id=user_id, endpoint_uuid=endpoint_uuid).first()
        return endpoint is not None

    def save_endpoint(self, user_id, endpoint_name, endpoint_host, endpoint_uuid):
        logger.info(f"Saving endpoint: {endpoint_name}, {endpoint_host}, {endpoint_uuid}")
        endpoint = Endpoints(
            user_id=user_id,
            endpoint_name=endpoint_name,
            endpoint_host=endpoint_host,
            endpoint_uuid=endpoint_uuid
        )
        db.session.merge(endpoint)
        db.session.commit()
    
    def get_endpoints(self, user_id):
        return Endpoints.query.filter_by(user_id=user_id).all()
    
    def delete_endpoints(self, user_id):
        Endpoints.query.filter_by(user_id=user_id).delete()
        db.session.commit()

    def save_partition(self, user_id, endpoint_uuid, partitions):
        endpoint = Endpoints.query.filter_by(user_id=user_id, endpoint_uuid=endpoint_uuid).first()
        if endpoint:
            endpoint.partitions = partitions
            db.session.commit()
        else:
            logger.error(f"Endpoint not found for user {user_id} and UUID {endpoint_uuid}")

    def get_partitions(self, user_id, endpoint_uuid):
        endpoint = Endpoints.query.filter_by(user_id=user_id, endpoint_uuid=endpoint_uuid).first()
        if endpoint:
            return endpoint.partitions
        else:
            logger.error(f"Endpoint not found for user {user_id} and UUID {endpoint_uuid}")
            return None
    
    def save_accounts(self, user_id, endpoint_uuid, accounts):
        endpoint = Endpoints.query.filter_by(user_id=user_id, endpoint_uuid=endpoint_uuid).first()
        if endpoint:
            endpoint.accounts = accounts
            db.session.commit()
        else:
            logger.error(f"Endpoint not found for user {user_id} and UUID {endpoint_uuid}")

    def get_accounts(self, user_id, endpoint_uuid):
        endpoint = Endpoints.query.filter_by(user_id=user_id, endpoint_uuid=endpoint_uuid).first()
        if endpoint:
            return endpoint.accounts
        else:
            logger.error(f"Endpoint not found for user {user_id} and UUID {endpoint_uuid}")
            return None
