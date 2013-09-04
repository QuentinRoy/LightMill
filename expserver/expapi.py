from sqlalchemy.exc import IntegrityError

__author__ = 'Quentin Roy'

from flask.blueprints import Blueprint
from flask.helpers import url_for
from sqlalchemy.orm.exc import NoResultFound
import os
import uuid
from flask import jsonify, redirect, request
from model import Experiment, Run, Trial, Block, db, ExperimentProgressError
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
    error_dict = error.to_dict()
    error_dict['type'] = error.__class__.__name__
    response = jsonify(error_dict)
    response.status_code = error.status_code
    return response


@exp_api.errorhandler(ExperimentProgressError)
def handle_invalid_usage(error):
    response = jsonify({
        'message': error.args[0],
        'type': error.__class__.__name__
    })
    response.status_code = 405
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
    factors = {}
    for factor in experiment.factors:
        factors[factor.id] = {
            'tag': factor.tag,
            'name': factor.name,
            'type': factor.type,
            'values': dict((value.id, value.name) for value in factor.values)
        }
    measures = {}
    for measure in experiment.measures:
        measures[measure.id] = {
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
        'measures': measures,
        'req_duration': time() - start
    }
    return jsonify(exp_data)


@exp_api.route('/experiment/<experiment>/status')
def expe_runs(experiment):
    start = time()
    runs_props = {}
    for run in experiment.runs:
        runs_props[run.id] = {
            'completed': run.completed(),
            'started': run.started(),
            'locked': run.locked
        }
    runs_props['req_duration'] = time() - start
    return jsonify(runs_props)


@exp_api.route('/experiment/<experiment>/next_run')
def get_free_run(experiment):
    started_runs = experiment.runs.join(Block, Trial).filter(Trial.completion_date != None).all()
    target_run = None
    for run in experiment.runs:
        if run not in started_runs:
            target_run = run
            break
    if target_run:
        return jsonify(run_info(run))
    else:
        response = jsonify({
            'message': 'The experiment is completed.',
            'type': 'ExperimentAlreadyCompleted'
        })
        response.status_code = 410
        return response


@exp_api.route('/run/<experiment>/<run>')
def run_props(experiment, run):
    return jsonify(run_info(run))


@exp_api.route('/run/<experiment>/<run>/lock')
def lock_run(experiment, run):
    token = None
    if run.locked:
        response = jsonify({
            'message': 'Run {} of {} is already locked.'.format(run.id, experiment.id),
            'type': 'RunAlreadyLocked'
        })
        response.status_code = 405
        return response

    while token is None:
        try:
            token = str(uuid.uuid4())
            run.token = token
            db.session.commit()
        except IntegrityError:
            # that should never happen but... Who knows?
            token = None
    print("Run {} locked.".format(repr(run)))
    return jsonify({
        'token': token,
        'run_id': run.id,
        'experiment_id': experiment.id,
    })


@exp_api.route('/run/<experiment>/<run>/unlock', methods=['POST'])
def unlock_run(experiment, run):
    if not run.locked:
        response = jsonify({
            'message': 'Run {} of {} is not locked.'.format(run.id, experiment.id),
            'type': 'RunNotLocked'
        })
        response.status_code = 405
        return response
    elif request.form.get('token', None) != run.token:
        response = jsonify({
            'message': 'Wrong token: {} for run {}'.format(request.data.get('token', None), run.id),
            'type': 'WrongToken'
        })
        response.status_code = 405
        return response
    else:
        return force_unlock_run(experiment, run)


@exp_api.route('/run/<experiment>/<run>/force_unlock')
def force_unlock_run(experiment, run):
    run.token = None
    db.session.commit()
    print("Run {} unlocked.".format(repr(run)))
    return jsonify(run_info(run))


def run_info(run):
    return {
        'id': run.id,
        'experiment_id': run.experiment.id,
        'completed': run.completed(),
        'started': run.started(),
        'trial_count': run.trial_count(),
        'block_count': run.block_count(),
        'locked': run.locked
    }


@exp_api.route('/run/<experiment>/<run>/current_trial')
def run_current_trial(experiment, run):
    trial = run.current_trial()
    if not trial:
        response = jsonify({
            'message': 'Run is completed.',
            'type': 'RunCompleted'
        })
        response.status_code = 410
        return response
    return jsonify(trial_info(trial))


@exp_api.route('/block/<experiment>/<run>/<int:block>')
def block_props(experiment, run, block):
    props = {
        'number': block.number,
        'measure_block_number': block.measure_block_number(),
        'values': dict((value.factor.id, value.id) for value in block.values),
        'total': run.block_count()
    }
    return jsonify(props)


@exp_api.route('/trial/<experiment>/<run>/<int:block>/<int:trial>', methods=('POST', 'GET'))
def trial_props(experiment, run, block, trial):
    if request.method == 'POST':
        request_token = request.form.get('token', None)
        if run.token is None:
            response = jsonify({
                'message': 'Run must be locked before writing.',
                'type': 'RunNotLocked'
            })
            response.status_code = 405
            return response
        elif request_token != run.token:
            response = jsonify({
                'message': 'Wrong token: {} for run {}'.format(request_token, run.id),
                'type': 'WrongToken'
            })
            response.status_code = 405
            return response
            # print(request.form)
        trial.set_completed()
        db.session.commit()
    return jsonify(trial_info(trial))


def trial_info(trial):
    return {
        'number': trial.number,
        'block_number': trial.block.number,
        'experiment_id': trial.experiment.id,
        'run_id': trial.run.id,
        'practice': trial.block.practice,
        'measure_block_number': trial.block.measure_block_number(),
        'values': dict((value.factor.id, value.id) for value in trial.factor_values),
        'block_values': dict((value.factor.id, value.id) for value in trial.block.factor_values),
        'total': trial.block.length(),
        'completion_date': trial.completion_date
    }
