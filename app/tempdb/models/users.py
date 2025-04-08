from app.database.db import db


TEMP_BIND_KEY = 'temp_db'

class Users(db.Model):
    __bind_key__ = TEMP_BIND_KEY
    __tablename__ = 'users'
    
    user_id = db.Column(db.String(255), primary_key=True)
    endpoints_registered = db.Column(db.Boolean, default=False)
    ttl = db.Column(db.DateTime)

    def __init__(self, user_id, endpoints_registered, ttl):
        self.user_id = user_id
        self.endpoints_registered = endpoints_registered
        self.ttl = ttl

    def __repr__(self):
        return f"<Users {self.user_id}>"
