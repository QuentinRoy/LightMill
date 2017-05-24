__author__ = 'Quentin Roy'

import os

SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.abspath(os.path.join(os.path.dirname(__file__), '../experiments.db'))
TOUCHSTONE_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), '../experiment.xml'))
SERVER_PORT = 5000
