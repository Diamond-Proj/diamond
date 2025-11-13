"""
Container model
"""

from diamond_backend.app.database.db import db


class Container(db.Model):  # type: ignore[name-defined]
    container_task_id = db.Column(db.String)
    container_status = db.Column(db.String)
    identity_id = db.Column(db.String(255), db.ForeignKey("profile.identity_id"))
    base_image = db.Column(db.String)
    name = db.Column(db.String, primary_key=True)
    location = db.Column(db.String)
    description = db.Column(db.Text)
    dependencies = db.Column(db.Text)
    environment = db.Column(db.Text)
    commands = db.Column(db.Text)
    endpoint_id = db.Column(db.String)
    is_public = db.Column(db.Boolean, default=False)
    host = db.Column(db.Text)

    def __init__(
        self,
        container_task_id,
        container_status,
        identity_id,
        base_image,
        name,
        location,
        description,
        dependencies,
        environment,
        commands,
        endpoint_id,
        is_public=False,
        host=None,
    ):
        self.container_task_id = container_task_id
        self.container_status = container_status
        self.identity_id = identity_id
        self.base_image = base_image
        self.name = name
        self.location = location
        self.description = description
        self.dependencies = dependencies
        self.environment = environment
        self.commands = commands
        self.endpoint_id = endpoint_id
        self.is_public = is_public
        self.host = host

    def __repr__(self):
        return f"<Container {self.name}>"
