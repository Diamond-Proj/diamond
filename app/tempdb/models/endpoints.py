from datetime import datetime
from app.database.db import db


TEMP_BIND_KEY = 'temp_db'

class Endpoints(db.Model):
    __bind_key__ = TEMP_BIND_KEY
    __tablename__ = 'endpoints' 
    
    user_id = db.Column(db.String(255), primary_key=True)
    endpoint_name = db.Column(db.String(255), nullable=False)
    endpoint_host = db.Column(db.String(255), nullable=False)
    endpoint_uuid = db.Column(db.String(255), primary_key=True)
    partitions = db.Column(db.JSON, nullable=True)
    accounts = db.Column(db.JSON, nullable=True)

    def __init__(
            self,
            user_id,
            endpoint_name,
            endpoint_host,
            endpoint_uuid,
            partitions=None,
            accounts=None,
        ):
        self.user_id = user_id
        self.endpoint_name = endpoint_name
        self.endpoint_host = endpoint_host
        self.endpoint_uuid = endpoint_uuid
        self.partitions = partitions or []
        self.accounts = accounts or []

    def __repr__(self):
        return f"<Endpoints {self.endpoint_name}>"
