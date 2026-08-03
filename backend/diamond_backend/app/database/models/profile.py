"""
Profile model
"""

from diamond_backend.app.database.db import db


class Profile(db.Model):  # type: ignore[name-defined]
    identity_id = db.Column(db.String(255), primary_key=True)
    name = db.Column(db.String(255))
    email = db.Column(db.String(255))
    institution = db.Column(db.Text)
    is_initialized = db.Column(db.Boolean)

    def __init__(self, identity_id, name, email, institution, is_initialized=False):
        self.identity_id = identity_id
        self.name = name
        self.email = email
        self.institution = institution
        self.is_initialized = is_initialized

    def __repr__(self):
        return f"<Profile {self.name}>"
