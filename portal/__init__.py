from flask import Flask
import httplib2
import json

from portal.database import Database

__author__ = 'Globus Team <info@globus.org>'

httplib2.debuglevel = 4

app = Flask(__name__)
app.config.from_pyfile('portal.conf')

database = Database(app)

with open(app.config['DATASETS']) as f:
    datasets = json.load(f)

import portal.views
