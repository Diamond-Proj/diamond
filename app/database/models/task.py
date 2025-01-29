"""
Task model
"""

from app.database.db import db
from sqlalchemy import func

class Task(db.Model):
    task_id = db.Column(db.String, primary_key=True)
    task_name = db.Column(db.String)
    identity_id = db.Column(db.String(255), db.ForeignKey('profile.identity_id'))
    task_status = db.Column(db.String)
    task_create_time = db.Column(db.TIMESTAMP, default=func.now())
    log_path = db.Column(db.String)

    def __init__(self, task_id, task_name, identity_id, task_status, task_create_time, log_path):
        self.task_id = task_id
        self.task_name = task_name
        self.identity_id = identity_id
        self.task_status = task_status
        self.task_create_time = task_create_time
        self.log_path = log_path

    def __repr__(self):
        return f"<Task {self.task_name}>"
    
    
