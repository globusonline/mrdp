from flask import Flask
import json

from portal.database import Database
from werkzeug.middleware.proxy_fix import ProxyFix

__author__ = 'Globus Team <info@globus.org>'

app = Flask(__name__)
app.wsgi_app = ProxyFix(
    app.wsgi_app, x_for=1, x_proto=1, x_host=1
)

app.config.from_pyfile('portal.conf')

database = Database(app)

with open(app.config['DATASETS']) as f:
    datasets = json.load(f)

import portal.views
