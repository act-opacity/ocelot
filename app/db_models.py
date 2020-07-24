from app import db

class Account(db.Model):
    __tablename__ = 'account'
    id = db.Column(db.Integer, primary_key=True)
    handle_name = db.Column(db.String(255), nullable=False)
    handle = db.Column(db.String(255), nullable=False)
    creation_date = db.Column(db.String(32), nullable=False)
    expiration_date = db.Column(db.String(32), nullable=False)
    # months remaining in subscription
    months_in_subscription = db.Column(db.Integer, nullable=False)
    storage_capacity = db.Column(db.Integer, nullable=False)
    # In Gigabytes
    storage_used = db.Column(db.String(32), nullable=False)

    def __repr__(self):
        return '<Handle Name %r>' % self.handle_name