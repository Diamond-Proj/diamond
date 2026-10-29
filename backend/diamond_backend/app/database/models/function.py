"""
Function model
"""

from diamond_backend.app.database.db import db


class Functions(db.Model):  # type: ignore[name-defined]
    name = db.Column(db.String, primary_key=True)
    function_id = db.Column(db.String)

    def __init__(self, name, function_id):
        self.name = name
        self.function_id = function_id

    def __repr__(self):
        return f"<Functions {self.name}>"
