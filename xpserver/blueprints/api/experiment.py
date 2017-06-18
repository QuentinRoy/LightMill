import os
from StringIO import StringIO
from flask.blueprints import Blueprint
from flask import jsonify, request
from sqlalchemy import func
from run import run_info
from ..errors import UnknownElement
from .._utils import allow_origin, answer_options, inject_model, create_invalid_usage_response
from ...touchstone import create_experiment, parse_experiment_id
from ...model import Experiment, db, Block, Trial, Run

blueprint = Blueprint('experiment', os.path.splitext(__name__)[0])


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


blueprint.errorhandler(CannotImportExperiment)(create_invalid_usage_response)
blueprint.errorhandler(UnknownElement)(create_invalid_usage_response)
blueprint.url_value_preprocessor(inject_model)
blueprint.after_request(allow_origin)
blueprint.route('/*', methods=['OPTIONS'])(answer_options)


@blueprint.route('/list')
def experiments_list():
    experiments = dict(db.session.query(Experiment.id, Experiment.name).all())
    return jsonify(experiments)


@blueprint.route('/<experiment>')
def props(experiment):
    factors = {}
    for factor in experiment.factors:
        factor_dict = {
            'tag': factor.tag,
            'name': factor.name,
            'type': factor.type,
            'values': dict((value.id, value.name) for value in factor.values),
            'defaultValue': factor.default_value.id if factor.default_value else None
        }
        if factor.default_value:
            factor_dict['default_value'] = factor.default_value.id
        factors[factor.id] = factor_dict
    measures = {}
    for measure_id, measure in experiment.measures.items():
        measures[measure_id] = {
            'name': measure.name,
            'levels': measure.levels(),
            'type': measure.type
        }
    exp_data = {
        'id': experiment.id,
        'name': experiment.name,
        'description': experiment.description,
        'runs': [run.id for run in experiment.runs],
        'factors': factors,
        'measures': measures
    }
    return jsonify(exp_data)


@blueprint.route('/import', methods=['POST'])
def import_():
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
        return props(experiment)


@blueprint.route('/<experiment>/available_run')
def get_free_run(experiment):
    available_run = (experiment.runs
                     .outerjoin(Block, Trial)
                     .filter(Run.token.is_(None))
                     .having(func.count(Trial.completion_date) == 0)
                     .group_by(Run)).first()

    if available_run:
        return run_info(available_run)

    response = jsonify({
        'message': 'No available runs.',
        'type': 'NoAvailableRuns'
    })
    response.status_code = 410
    return response
