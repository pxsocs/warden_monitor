import json
import logging
from flask import current_app
from flask_login import UserMixin
from utils import safe_filename
from datetime import datetime, date, timedelta

db = current_app.db

# Loaders -------------


@current_app.login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def load_GlobalData(data_name, value=False, string=False):
    if data_name is None:
        query = GlobalData.query.all()
        return query
    query = GlobalData.query.filter_by(data_name=data_name).first()
    if value is True:
        return query.data_value
    elif string is True:
        return query.data_string
    else:
        return query


def load_Node(name=None, url=None):
    if name is None and url is None:
        query = Nodes.query.all()
        return query
    if name is not None:
        query = Nodes.query.filter_by(name=name).first()
        return query
    if url is not None:
        query = Nodes.query.filter_by(url=url).first()
        return query


# Updaters ---------------------
def update_GlobalData(data_name,
                      data_value,
                      data_string=None,
                      expires_in_seconds=None):

    if expires_in_seconds is None:
        expires_at = None
    else:
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in_seconds)

    # Stringify data_value if possible for viewing in database file
    if data_string is None:
        try:
            data_string = str(data_value)
        except Exception:
            data_string = None

    data_dict = {
        'data_name': data_name,
        'data_value': data_value,
        'data_string': data_string,
        'expires_at': expires_at,
        'last_updated': datetime.utcnow()
    }
    # Try to load this data from the database
    data = load_GlobalData(data_name)
    # Does not exist, create it
    if data is None:
        # Create new data
        new_data = GlobalData(**data_dict)
        db.session.add(new_data)
    else:
        # Update data
        for element in data_dict:
            setattr(data, element, data_dict[element])

    db.session.commit()


#  Models -------------


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)

    def __repr__(self):
        return (self.username)


class Nodes(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), nullable=False)
    # Make sure to parse url before including / editing
    url = db.Column(db.String(250), nullable=False, unique=True)
    is_reachable = db.Column(db.Boolean, default=False)
    is_public = db.Column(db.Boolean, default=None)
    last_check = db.Column(db.DateTime, default=date.min)
    is_localhost = db.Column(db.Boolean, default=None)
    blockchain_tip_height = db.Column(db.Integer, default=0)
    node_tip_height = db.Column(db.Integer, default=0)
    mps_api_reachable = db.Column(db.Boolean, default=False)
    ping_time = db.Column(db.PickleType(), default=0)
    last_online = db.Column(db.DateTime, default=date.min)

    def is_onion(self):
        return (True if 'onion' in self.url else False)

    def is_at_tip(self):
        is_at_tip = False if self.node_tip_height != self.blockchain_tip_height else True
        return is_at_tip

    def as_dict(self):
        dict_return = {
            c.name: getattr(self, c.name)
            for c in self.__table__.columns
        }
        # Add methods to return dict
        dict_return['is_onion'] = self.is_onion()
        dict_return['is_at_tip'] = self.is_at_tip()
        return (dict_return)

    def __repr__(self):
        return (json.dumps(self.as_dict(), default=str))

        # return f'{self.id}, {self.name}, {self.url}'


# Table to save general data - can store variables for later use
class GlobalData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data_name = db.Column(db.String(150), nullable=False, unique=True)
    # This will save a pickle
    data_value = db.Column(db.PickleType(), default=None)
    # This can save a string just for refence of what the pickle is
    # This is helpful when monitoring the .db file where the pickle will
    # not show properly.
    data_string = db.Column(db.String(250), default=None)
    last_updated = db.Column(db.DateTime, default=date.min)
    expires_at = db.Column(db.DateTime, default=date.min)

    def is_expired(self):
        expired = True if self.expires_at > date.today() else False
        return expired

    def to_json(self):
        # returns a dictionary of the object
        return (json.dumps(vars(self), indent=4, default=str))

    def __repr__(self):
        # returns a dictionary of the object
        return (f'{self.data_name}, {self.data_value}')
