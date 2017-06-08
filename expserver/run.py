__author__ = 'Quentin Roy'

import os
from flask import Flask
from expapi import exp_api
from model import db, Experiment
from touchstone import create_experiment, parse_experiment_id
from queryyesno import query_yes_no
import default_settings


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
    app.register_blueprint(exp_api)
    app.jinja_env.add_extension("jinja2htmlcompress.SelectiveHTMLCompress")

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


if __name__ == '__main__':
    import argparse
    import sys

    parser = argparse.ArgumentParser(description='Experiment server.')

    parser.add_argument('-p', '--port',
                        type=int,
                        default=default_settings.SERVER_PORT,
                        help='Server port.')
    parser.add_argument('-e', '--experiment-design',
                        type=open,
                        help='Experiment design file to import on startup'
                             ' (if the experiment is not already imported)'
                             ' Supports touchsTone\'s XML export format.')
    parser.add_argument('-d', '--database',
                        default=default_settings.DATABASE_URI,
                        type=str,
                        help='Database file path'
                             ' (default: {}).'.format(default_settings.DATABASE_URI))
    parser.add_argument('-v', '--verbose',
                        action='store_true',
                        default=False,
                        help='Print out SQL requests.')
    parser.add_argument('--debug',
                        default=False,
                        action='store_true',
                        help='Server debug mode. Automatically reloads the server when its code'
                             ' changes, also provides error trace from the browser on failed'
                             ' requests.')
    parser.add_argument('--fixed-measures',
                        default=False,
                        action='store_true',
                        help='Prevent recording measures that are not defined in the experiment'
                             ' design. Pushing trial results containing unknown measures will'
                             ' result in an error.')
    parser.add_argument('--unprotected-runs',
                        default=False,
                        action='store_true',
                        help='Allow ongoing runs to be re-allocated (i.e. run locks are '
                             ' unprotected and always acquired when requested).'
                             ' This allows a run client to disconnect and reconnect (e.g. by'
                             ' refreshing a page) without unlocking its run.'
                             ' WARNING: this allows a client to "steal" the run of another.'
                             ' DO NOT USE IN PRODUCTION.')
    parser.add_argument('--volatile',
                        default=False,
                        action='store_true',
                        help='Do not keep any data. WARNING: This is only useful during'
                             ' development. DO NOT USE IN PRODUCTION. The data cannot be exported'
                             ' in any way.')

    args = parser.parse_args()

    if args.volatile or args.unprotected_runs:
        if not query_yes_no('WARNING: \'--unprotected-runs\' and \'--volatile\' are unfit for'
                            ' production and must not be used during an actual experiment.'
                            ' Continue ?',
                            default="no"):
            sys.exit(0)

    app = create_app(database_uri=args.database,
                     sql_echo=args.verbose,
                     debug=args.debug,
                     do_not_protect_runs=args.unprotected_runs,
                     add_missing_measures=not args.fixed_measures,
                     volatile=args.volatile)

    # Load experiment_design if provided.
    experiment_design = args.experiment_design
    if experiment_design:
        import_experiment(app, experiment_design)

    app.run(host='0.0.0.0', port=args.port)
