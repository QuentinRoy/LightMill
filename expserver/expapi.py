from flask.blueprints import Blueprint

__author__ = 'Quentin Roy'

import os
import json
from model import Experiment

exp_api = Blueprint('expe_api', os.path.splitext(__name__)[0])


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
@exp_api.route('/experiments')
def experiments_list():
    experiments = dict((experiment.id, experiment.name) for experiment in Experiment.query.all())
    return json.dumps(experiments)
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
