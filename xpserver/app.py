__author__ = 'Quentin Roy'

import os
from flask import Flask
from blueprints.web import web_blueprint
from blueprints.api import experiment_blueprint, run_blueprint, block_blueprint, trial_blueprint
from blueprints.api import root_blueprint as api_root_blueprint
from model import db, Experiment
from touchstone import create_experiment, parse_experiment_id


def create_app(database_uri,
               sql_echo=False,
               debug=False,
               do_not_protect_runs=False,
               add_missing_measures=True,
               volatile=False):
    # app creation
    app = Flask(__name__.split('.')[0])
    app.config['SQLALCHEMY_DATABASE_URI'] = ('sqlite://' if volatile
                                             else 'sqlite:///' + os.path.abspath(database_uri))
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ECHO'] = sql_echo
    app.config['UNPROTECTED_RUNS'] = do_not_protect_runs
    app.config['ADD_MISSING_MEASURES'] = add_missing_measures
    # FIXME: This depends on the current package and how it is run. Breaks easily.
    app.jinja_env.add_extension("xpserver.jinja2htmlcompress.SelectiveHTMLCompress")

    app.register_blueprint(web_blueprint)
    app.register_blueprint(api_root_blueprint, url_prefix='/api')
    app.register_blueprint(experiment_blueprint, url_prefix='/api/experiment')
    app.register_blueprint(run_blueprint, url_prefix='/api/run')
    app.register_blueprint(block_blueprint, url_prefix='/api/block')
    app.register_blueprint(trial_blueprint, url_prefix='/api/trial')

    # database initialization
    db.init_app(app)
    db.app = app
    db.create_all()

    app.debug = debug

    return app


def import_experiment(app, touchstone_file):
    expe_id = parse_experiment_id(touchstone_file)
    with app.test_request_context():
        if not db.session.query(Experiment.query.filter_by(id=expe_id).exists()).scalar():
            print("Importing experiment {} from {}..".format(expe_id, touchstone_file))
            experiment = create_experiment(touchstone_file)
            db.session.add(experiment)
            db.session.commit()
