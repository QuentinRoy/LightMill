__author__ = 'Quentin Roy'

import os
from flask import Flask
from expapi import exp_api
from model import db, Experiment
from touchstone import create_experiment, parse_experiment_id
import default_settings

# app creation
app = Flask(__name__.split('.')[0])
app.config['SQLALCHEMY_DATABASE_URI'] = default_settings.SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = __debug__
app.register_blueprint(exp_api)
app.jinja_env.add_extension("jinja2htmlcompress.SelectiveHTMLCompress")

# database initialization
db.init_app(app)
db.app = app
db.create_all()


def import_experiment(touchstone_file):
    expe_id = parse_experiment_id(touchstone_file)
    with app.test_request_context():
        if not db.session.query(Experiment.query.filter_by(id=expe_id).exists()).scalar():
            print("Importing experiment {} from {}..".format(expe_id, touchstone_file))
            experiment = create_experiment(touchstone_file)
            db.session.add(experiment)
            db.session.commit()


if __name__ == '__main__':

    # experiment initialization
    if os.path.exists(default_settings.TOUCHSTONE_FILE):
        import_experiment(default_settings.TOUCHSTONE_FILE)

    app.debug = __debug__
    app.run(host='0.0.0.0')
