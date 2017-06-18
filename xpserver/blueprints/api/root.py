import os
from StringIO import StringIO
from flask.blueprints import Blueprint
from flask import jsonify, request
from experiment import props as experiment_props
from ..errors import UnknownElement
from .._utils import allow_origin, answer_options, inject_model, register_invalid_error
from ...touchstone import create_experiment, parse_experiment_id
from ...model import Experiment, db

blueprint = Blueprint('root', os.path.splitext(__name__)[0])


class CannotImportExperiment(Warning):
    status_code = 400

    def __init__(self, message, status_code=status_code, payload=None):
        Warning.__init__(self, message)
        self.message = message
        self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        return rv


blueprint.url_value_preprocessor(inject_model)
register_invalid_error(blueprint, CannotImportExperiment)
register_invalid_error(blueprint, UnknownElement)
allow_origin(blueprint)
answer_options(blueprint)


@blueprint.route('/experiments')
def experiments_list():
    experiments = dict(db.session.query(Experiment.id, Experiment.name).all())
    return jsonify(experiments)


@blueprint.route('/import', methods=['POST'])
def import_experiment():
    if request.method == 'POST':
        # retrieve the id of the experiment
        expe_id = parse_experiment_id(StringIO(request.data))
        print('Importing experiment {}...'.format(expe_id))
        # check if the experiment already exists
        if db.session.query(Experiment.query.filter_by(id=expe_id).exists()).scalar():
            raise CannotImportExperiment('Experiment already exists.')
        # create the experiment and commit the data
        experiment = create_experiment(StringIO(request.data))
        db.session.add(experiment)
        db.session.commit()
        print('Experiment imported.')
        return experiment_props(experiment)
