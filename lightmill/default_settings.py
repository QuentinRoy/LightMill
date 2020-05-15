__author__ = "Quentin Roy"

import os

DATABASE_URI = os.environ["LIGHTMILL_DB_URI"] or "experiments.db"
SERVER_PORT = 5000
