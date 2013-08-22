__author__ = 'Quentin Roy'

from flask import Flask
from expapi import exp_api
from model import db, Experiment
import touchstone

def create_db(app, touchstone_file):
    with app.test_request_context():
        db.create_all()
        touchstone_files = (touchstone_file, ) if isinstance(touchstone_file, basestring) else touchstone_file
        for ts_file in touchstone_files:
            experiment_id = touchstone.parse_experiment_id(ts_file)
            if Experiment.query.filter_by(id=experiment_id).count() < 1:
                experiment = touchstone.create_experiment(ts_file)
                db.session.add(experiment)
        db.session.commit()


def load_experiment(db_uri_or_app, touchstone_file):
    app = create_app(db_uri_or_app) if isinstance(db_uri_or_app, basestring) else db_uri_or_app
    with app.test_request_context():
        experiment = touchstone.create_experiment(touchstone_file)
        db.session.add(experiment)
        db.session.commit()


def create_app(db_uri):
    app = Flask(__name__.split('.')[0])
    app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
    app.register_blueprint(exp_api)
    db.init_app(app)
    return app


if __name__ == '__main__':
    from default_settings import SQLALCHEMY_DATABASE_URI, TOUCHSTONE_FILE

    app = create_app(SQLALCHEMY_DATABASE_URI)
    create_db(app, TOUCHSTONE_FILE)
    app.run(host="0.0.0.0", debug=True)