__author__ = "Quentin Roy"

import os

DATABASE_URI = (
    os.environ["LIGHTMILL_DB_URI"]
    if "LIGHTMILL_DB_URI" in os.environ
    else "experiments.db"
)
SERVER_PORT = 5000
