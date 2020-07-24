import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from pathlib import Path

app = Flask(__name__)

# Create required directory(s)
Path(os.environ.get('APPDATA')).mkdir(parents=True, exist_ok=True)
Path(os.environ.get('FILE_METADATA_JSON')).mkdir(parents=True, exist_ok=True)
Path(os.environ.get('IN_PROGRESS_DOWNLOADS')).mkdir(parents=True, exist_ok=True)

app.config['OCELOT_VERSION'] = os.environ.get('OCELOT_VERSION')
app.config['LOCAL_DATA'] = os.environ.get('LOCAL_DATA')
app.config['FILE_METADATA_JSON'] = os.environ.get('FILE_METADATA_JSON')

# Create file protocol path to OpacityDrive based on user's host machine
opacity_dir = os.environ.get('OPACITY_DRIVE_DIR_NAME').replace('"', '')
temp_dir = os.environ.get('USER_HOME_PATH').replace('"', '')
path_file_protocol = temp_dir.replace('\\', '/')
path_file_protocol = f"file://{path_file_protocol}" if temp_dir[0] == '/' else f"file:///{path_file_protocol}"
app.config['FILE_PROTOCOL_OPACITYDRIVE_PATH'] = f'{path_file_protocol}/{opacity_dir}'
app.config['FILE_EXPLORER_OPACITYDRIVE_PATH'] =  f"{temp_dir}/{opacity_dir}" if temp_dir[0] == '/' else f"{temp_dir}\\{opacity_dir}"

# SQL Alchemy
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.environ.get('APPDATA')}/opacity.sqlite"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
from .db_models import Account
# Will create tables if don't exist, otherwise ignored
db.create_all()

from app import routes