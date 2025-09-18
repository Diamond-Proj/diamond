from diamond_backend.app.database.db import db


class Endpoints(db.Model):
    identity_id = db.Column(db.String(255), primary_key=True)
    endpoint_name = db.Column(db.String(255), nullable=False)
    endpoint_host = db.Column(db.String(255), nullable=False)
    endpoint_uuid = db.Column(db.String(255), primary_key=True)
    endpoint_status = db.Column(db.String(255), nullable=False)
    partitions = db.Column(db.JSON, nullable=True)
    accounts = db.Column(db.JSON, nullable=True)
    diamond_dir = db.Column(db.String(255), nullable=True)

    def __init__(
        self,
        identity_id,
        endpoint_name,
        endpoint_host,
        endpoint_uuid,
        endpoint_status,
        partitions=None,
        accounts=None,
        diamond_dir=None,
    ):
        self.identity_id = identity_id
        self.endpoint_name = endpoint_name
        self.endpoint_host = endpoint_host
        self.endpoint_uuid = endpoint_uuid
        self.endpoint_status = endpoint_status
        self.partitions = partitions or []
        self.accounts = accounts or []
        self.diamond_dir = diamond_dir or ""

    def __repr__(self):
        return f"<Endpoints {self.endpoint_name}>"
