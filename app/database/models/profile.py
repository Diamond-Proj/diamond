"""
Profile model
"""

from app.database.db import db


class Profile(db.Model):
    identity_id = db.Column(db.String(255), primary_key=True)
    name = db.Column(db.String(255))
    email = db.Column(db.String(255))
    institution = db.Column(db.Text)

    def __init__(self, identity_id, name, email, institution):
        self.identity_id = identity_id
        self.name = name
        self.email = email
        self.institution = institution

    def __repr__(self):
        return f"<Profile {self.name}>"
