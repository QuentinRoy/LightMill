from flask.blueprints import Blueprint
from flask.helpers import url_for
from sqlalchemy.orm.exc import NoResultFound

__author__ = 'Quentin Roy'

import os
from flask import jsonify, redirect
from model import Experiment, Run, Trial, Block
from time import time

exp_api = Blueprint('exp_api', os.path.splitext(__name__)[0])


class UnknownElement(Exception):
    status_code = 400

    def __init__(self, message, status_code=None, payload=None):
        Exception.__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        return rv


@exp_api.errorhandler(UnknownElement)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response


def _pull_trial(values):
    trial = Trial.query.get_by_number(values['trial'], values['block'], values['run'], values['experiment'])
    values['trial'] = trial
    values['experiment'] = trial.experiment
    values['block'] = trial.block
    values['run'] = trial.run


def _pull_block(values):
    block = Block.query.get_by_number(values['block'], values['run'], values['experiment'])
    values['experiment'] = block.experiment
    values['block'] = block
    values['run'] = block.run


def _pull_run(values):
    run = Run.query.get_by_id(values['run'], values['experiment'])
    values['run'] = run
    values['experiment'] = run.experiment


def _pull_experiment(values):
    values['experiment'] = Experiment.query.get_by_id(values['experiment'])


@exp_api.url_value_preprocessor
def pull_objects(endpoint, values):
    """When a request contains a run_id value, or experiment_id value
     transform it directly into a project by checking the credentials
     are stored in session.
     If the project or the experiment does not exists, it raises an exception
    """
    if not values:
        return
    try:
        if 'experiment' in values:
            if not 'run' in values:
                _pull_experiment(values)
            elif not 'block' in values:
                _pull_run(values)
            elif not 'trial' in values:
                _pull_block(values)
            else:
                _pull_trial(values)
    except NoResultFound:
        raise UnknownElement("Target not found.", payload={'request': values})


@exp_api.after_request
def allow_origin(response):
    """Makes all the api accessible from any origin"""
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response


@exp_api.route('/experiments')
def experiments_list():
    experiments = dict((experiment.id, experiment.name) for experiment in Experiment.query.all())
    return jsonify(experiments)


@exp_api.route('/')
def index():
    url = url_for('exp_api.experiments_list')
    return redirect(url)


@exp_api.route('/experiment/<experiment>')
def expe_props(experiment):
    start = time()
    exp_data = {
        'id': experiment.id,
        'name': experiment.name,
        'description': experiment.description,
        'runs': [run.id for run in experiment.runs],
        'req_duration': time() - start
    }
    return jsonify(exp_data)


@exp_api.route('/experiment/<experiment>/factors')
def factors(experiment):
    factors = {}
    for factor in experiment.factors:
        factors[factor.id] = {
            'tag': factor.tag,
            'name': factor.name,
            'type': factor.type,
            'values': dict((value.id, value.name) for value in factor.values)
        }
    return jsonify(factors)


@exp_api.route('/experiment/<experiment>/status')
def expe_runs(experiment):
    start = time()
    runs_props = {}
    for run in experiment.runs:
        runs_props[run.id] = {
            'completed': run.completed(),
            'started': run.started()
        }
    runs_props['req_duration'] = time() - start
    return jsonify(runs_props)


@exp_api.route('/experiment/<experiment>/next_run')
def get_free_run(experiment):
    started_runs = experiment.runs.join(Block, Trial).filter(Trial.completed == True).all()
    for run in experiment.runs:
        if run not in started_runs:
            return run.id


@exp_api.route('/run/<experiment>/<run>')
def run_props(experiment, run):
    start = time()
    return jsonify({
        'run_id': run.id,
        'experiment_id': run.experiment.id,
        'completed': run.completed(),
        'started': run.started(),
        'req_duration': time() - start
    })


@exp_api.route('/run/<experiment>/<run>/current_trial')
def run_current_trial(experiment, run):
    trial = run.current_trial()
    if trial:
        return jsonify({
            'num': trial.number,
            'block_num': trial.block.number,
            'experiment_id': experiment.id,
            'run_id': run.id,
            'values': dict((value.factor.id, value.id) for value in trial.iter_all_values())
        })
    else:
        response = jsonify({
            'message': 'The run is completed.'
        })
        response.status_code = 400
        return response


@exp_api.route('/trial/<experiment>/<run>/<int:block>/<int:trial>')
def trial_values(experiment, run, block, trial):
    return jsonify({
        'num': trial.number,
        'block_num': block.number,
        'experiment_id': experiment.id,
        'run_id': run.id,
        'values': dict((value.factor.id, value.id) for value in trial.iter_all_values())
    })