"""
Dataset model
"""

from diamond_backend.app.database.db import db


class Dataset(db.Model):  # type: ignore[name-defined]
    id = db.Column(db.Integer, primary_key=True)
    identity_id = db.Column(db.String(255), db.ForeignKey("profile.identity_id"))
    collection_uuid = db.Column(db.String(36), nullable=False)  # Globus collection UUID
    globus_path = db.Column(db.String, nullable=False)  # Path within globus collection
    system_path = db.Column(db.String, nullable=False)  # actual path on machine
    public = db.Column(db.Boolean, default=False, nullable=False)
    machine_name = db.Column(
        db.String, nullable=False
    )  # human readable e.g. "Anvil@RCAC"
    dataset_name = db.Column(
        db.String(255), nullable=True
    )  # Human-readable dataset title
    dataset_metadata = db.Column(db.Text)  # JSON string for any other metadata

    def __init__(
        self,
        collection_uuid,
        globus_path,
        system_path,
        public,
        machine_name,
        dataset_metadata,
        identity_id,
        dataset_name=None,
    ):
        self.collection_uuid = collection_uuid
        self.globus_path = globus_path
        self.system_path = system_path
        self.public = public
        self.machine_name = machine_name
        self.dataset_name = dataset_name
        self.dataset_metadata = dataset_metadata
        self.identity_id = identity_id

    def __repr__(self):
        return f"<Dataset {self.collection_uuid}:{self.globus_path}>"
