"""
Flow model
"""

from diamond_backend.app.database.db import db


class Flows(db.Model):  # type: ignore[name-defined]
    template = db.Column(db.String, primary_key=True)
    flow_id = db.Column(db.String)

    def __init__(self, template, flow_id):
        self.template = template
        self.flow_id = flow_id

    def __repr__(self):
        return f"<Flows {self.template}>"
