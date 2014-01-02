__author__ = 'Quentin Roy'

from flask import Flask
from expserver.model import Experiment, db, Measure
from os import path


def add_xp_measure(xp, measure_id, measure_type, trial_level, event_level, measure_name=None):
    m = Measure(id=measure_id, name=measure_name, type=measure_type, trial_level=trial_level, event_level=event_level)
    xp.measures[m.id] = m
    db.session.commit()


def update_measure(xp, id, type=None, trial_level=None, event_level=None, name=None):
    m = xp.measures[id]
    if trial_level is not None:
        m.trial_level = trial_level
    if event_level is not None:
        m.event_level = event_level
    if name is not None:
        m.name = name
    if type is not None:
        m.type = type
    db.session.commit()


def get_app(database):
    flask_app = Flask(__name__.split('.')[0])
    flask_app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///../experiments.db'
    db.init_app(flask_app)
    db.app = flask_app
    return flask_app


if __name__ == '__main__':
    database = path.abspath('../experiments.db')
    app = get_app(database)
    expe = Experiment.query.first()
    update_measure(expe, id='durations.execution', name="Execution Duration", event_level=False)