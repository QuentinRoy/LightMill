__author__ = 'Quentin Roy'


from gevent import monkey
monkey.patch_all()

from flask import Flask
from expapi import exp_api
from model import db, Experiment
from touchstone import create_experiment, parse_experiment_id
import os
import default_settings
from geventwebsocket.handler import WebSocketHandler
from gevent.pywsgi import WSGIServer
from werkzeug import serving
from werkzeug.debug import DebuggedApplication

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
            print("Importing experiment {} from {}..".format(expe_id, touchstone_file))
            experiment = create_experiment(touchstone_file)
            db.session.add(experiment)
            db.session.commit()

# experiment initialization
if os.path.exists(default_settings.TOUCHSTONE_FILE):
    import_experiment(default_settings.TOUCHSTONE_FILE)


@serving.run_with_reloader
def runServer():
    app.debug = True
    dapp = DebuggedApplication(app, evalex=True, show_hidden_frames=True)
    http_server = WSGIServer(('', 5000), dapp, handler_class=WebSocketHandler)
    http_server.serve_forever()


if __name__ == '__main__':
    runServer()