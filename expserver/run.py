__author__ = 'Quentin Roy'

from flask import Flask
from expapi import exp_api
from model import db, Experiment
from touchstone import create_experiment, parse_experiment_id
import os
import default_settings

# app creation
app = Flask(__name__.split('.')[0])
app.config['SQLALCHEMY_DATABASE_URI'] = default_settings.SQLALCHEMY_DATABASE_URI
app.register_blueprint(exp_api)

# database initialization
db.init_app(app)
db.app = app
db.create_all()

def import_experiment(touchstone_file):
    expe_id = parse_experiment_id(touchstone_file)
    with app.test_request_context():
        if not db.session.query(Experiment.query.filter_by(id=expe_id).exists()).scalar():
            print("Importing experiment {}..".format(expe_id))
            experiment = create_experiment(touchstone_file)
            db.session.add(experiment)
            db.session.commit()

# experiment initialization
if os.path.exists(default_settings.TOUCHSTONE_FILE):
    import_experiment(default_settings.TOUCHSTONE_FILE)


def main():
    app.run(host="0.0.0.0", debug=True)


if __name__ == '__main__':
    main()