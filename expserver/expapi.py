from flask.blueprints import Blueprint

__author__ = 'Quentin Roy'

import os
from flask import jsonify, g
from model import Experiment, Run, Trial, Block
from time import time

exp_api = Blueprint('expe_api', os.path.splitext(__name__)[0])


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
    try:
        trial = Trial.query.get_by_number(values['trial'], values['block'], values['run'], values['experiment'])
        values['trial'] = trial
        values['experiment'] = trial.experiment
        values['block'] = trial.block
        values['run'] = trial.run
    except:
        raise UnknownElement("The trial does not exist.")


def _pull_block(values):
    try:
        block = Block.query.get_by_number(values['block'], values['run'], values['experiment'])
        values['experiment'] = block.experiment
        values['block'] = block
        values['run'] = block.run
    except:
        raise UnknownElement("The trial does not exist.")


def _pull_run(values):
    try:
        run = Run.query.get_by_id(values['run'], values['experiment'])
        values['run'] = run
        values['experiment'] = run.experiment
    except:
        raise UnknownElement("Either experiment " + values['experiment'] + " or run " + values['run'] +
                             " does not exist.")


def _pull_experiment(values):
    try:
        values['experiment'] = Experiment.query.get_by_id(values['experiment'])
    except:
        raise UnknownElement("Experiment " + values['experiment'] + " does not exist.")


@exp_api.url_value_preprocessor
def pull_objects(endpoint, values):
    """When a request contains a run_id value, or experiment_id value
     transform it directly into a project by checking the credentials
     are stored in session.
     If the project or the experiment does not exists, it raises an exception
    """
    if not values:
        return

    if 'experiment' in values:
        if not 'run' in values:
            _pull_experiment(values)
        elif not 'block' in values:
            _pull_run(values)
        elif not 'trial' in values:
            _pull_block(values)
        else:
            _pull_trial(values)


@exp_api.route('/experiments')
def experiments_list():
    experiments = dict((experiment.id, experiment.name) for experiment in Experiment.query.all())
    return jsonify(experiments)


@exp_api.route('/experiment/<experiment>')
def expe_props(experiment):
    start = time()
    exp_data = {
        'id': experiment.id,
        'name': experiment.name,
        'runs': [run.id for run in experiment.runs],
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
            'started': run.started()
        }
    runs_props['req_duration'] = time() - start
    return jsonify(runs_props)


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
    return jsonify({
        'num': trial.number,
        'block_num': trial.block.number,
        'experiment_id': experiment.id,
        'run_id': run.id,
        'values': dict((value.factor.id, value.id) for value in trial.iter_all_values())
    })


@exp_api.route('/trial/<experiment>/<run>/<int:block>/<int:trial>')
def trial_values(experiment, run, block, trial):
    return jsonify({
        'num': trial.number,
        'block_num': block.number,
        'experiment_id': experiment.id,
        'run_id': run.id,
        'values': dict((value.factor.id, value.id) for value in trial.iter_all_values())
    })


#
# @app.route('/<exp_id>/available_runs')
# def available_runs(exp_id):
#     exp = experiments[exp_id]
#     unstarted_runs = [run.id for run in exp.iter_runs() if not run.started()]
#     return json.dumps(unstarted_runs)
#
#
# @app.route('/<exp_id>/uncompleted_runs')
# def uncompleted_runs(exp_id):
#     exp = experiments[exp_id]
#     uncompleted_runs = [run.id for run in exp.iter_runs() if run.started() and not run.completed()]
#     return json.dumps(uncompleted_runs)
#
#
# @app.route('/<exp_id>/runs')
# def exp_runs(exp_id):
#     exp = experiments[exp_id]
#     status = OrderedDict((run.id, run.status()) for run in exp.iter_runs())
#     return json.dumps(status)
#
#
# @app.route('/<exp_id>')
# def experiment_props(exp_id):
#     exp = experiments[exp_id]
#     return json.dumps(exp.properties())
#
#
# @app.route('/<exp_id>/<run_id>')
# def run_status(exp_id, run_id):
#     exp = experiments[exp_id]
#     run = exp.get_run(run_id)
#     return json.dumps(run.properties())
#
#
# @app.route('/<exp_id>/<run_id>/current_trial')
# def current_trial(exp_id, run_id):
#     exp = experiments[exp_id]
#     trial = exp.get_run(run_id).current_trial()
#     return json.dumps(trial.properties())
#
#
# @app.route('/<exp_id>/<run_id>/current_block')
# def current_block(exp_id, run_id):
#     exp = experiments[exp_id]
#     block = exp.get_run(run_id).current_trial().block
#     return json.dumps(block.properties())
#
#
# @app.route('/<exp_id>/<run_id>/<int:block_num>')
# def block_props(exp_id, run_id, block_num):
#     exp = experiments[exp_id]
#     block = exp.get_run(run_id).get_block(block_num)
#     return json.dumps(block.properties())
#
#
# @app.route('/<exp_id>/<run_id>/<int:block_num>/<int:trial_num>')
# def trial_props(exp_id, run_id, block_num, trial_num):
#     exp = experiments[exp_id]
#     trial = exp.get_run(run_id).get_block(block_num).get_trial(trial_num)
#     return json.dumps(trial.properties())
