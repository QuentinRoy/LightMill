import os
import uuid
import json
from flask import jsonify, request, current_app as app, Response
from flask.blueprints import Blueprint
from trial import trial_info
from block import generate_block_trials_info
from ...model import db
from .._utils import allow_origin, inject_model, answer_options, create_invalid_usage_response
from ..errors import UnknownElement


blueprint = Blueprint('run', os.path.splitext(__name__)[0])
blueprint.errorhandler(UnknownElement)(create_invalid_usage_response)
blueprint.url_value_preprocessor(inject_model)
blueprint.after_request(allow_origin)
blueprint.route('/*', methods=['OPTIONS'])(answer_options)


@blueprint.route('/<experiment>/<run>')
def run_info(run, experiment=None):
    return jsonify({
        'id': run.id,
        'experimentId': run.experiment.id,
        'completed': run.completed(),
        'started': run.started(),
        'trialCount': run.trial_count(),
        'blockCount': run.block_count(),
        'locked': run.locked
    })


@blueprint.route('/<experiment>/<run>/current_trial')
def run_current_trial(run, experiment=None):
    trial = run.current_trial()
    if not trial:
        response = jsonify({
            'message': 'Run is completed.',
            'type': 'RunCompleted'
        })
        response.status_code = 410
        return response
    return trial_info(trial)


@blueprint.route('/<experiment>/<run>/next_trial')
def run_next_trial(experiment, run):
    current_trial = run.current_trial()
    if not current_trial:
        response = jsonify({
            'message': 'Run is completed.',
            'type': 'RunCompleted'
        })
        response.status_code = 410
        return response
    next_trial = current_trial.next()
    if not next_trial:
        response = jsonify({
            'message': 'Current trial is last.',
            'type': 'RunCompleted'
        })
        response.status_code = 410
        return response
    return trial_info(next_trial)


@blueprint.route('/<experiment>/<run>/lock')
def lock_run(experiment, run):
    token = None
    if run.locked and not ('UNPROTECTED_RUNS' in app.config and app.config['UNPROTECTED_RUNS']):
        response = jsonify({
            'message': 'Run {} of {} is already locked.'.format(run.id, experiment.id),
            'type': 'RunAlreadyLocked'
        })
        response.status_code = 405
        return response

    token = str(uuid.uuid4())
    run.token = token
    db.session.commit()
    print("Run {} locked.".format(repr(run)))
    return jsonify({
        'token': token,
        'runId': run.id,
        'experimentId': experiment.id,
    })


@blueprint.route('/<experiment>/<run>/unlock', methods=['POST'])
def unlock_run(experiment, run):
    if not run.locked:
        response = jsonify({
            'message': 'Run {} of {} is not locked.'.format(run.id, experiment.id),
            'type': 'RunNotLocked'
        })
        response.status_code = 405
        return response
    elif not request.is_json:
        response = jsonify({
            'message': 'Incorrect request type.',
            'type': 'Incorrect Request Type'
        })
        response.status_code = 405
        return response
    elif request.get_json().get('token', None) != run.token:
        response = jsonify({
            'message': 'Wrong token: {} for run {}'.format(request.data.get('token', None), run.id),
            'type': 'WrongToken'
        })
        response.status_code = 405
        return response
    else:
        run.token = None
        db.session.commit()
        return run_info(experiment, run)


@blueprint.route('/<experiment>/<run>/plan')
def run_plan(experiment, run):
    exp_values = list(factor.default_value
                      for factor
                      in run.experiment.factors
                      if factor.default_value)
    measured_block_num = 0
    blocks = []
    for block in run.blocks:
        block_info = {
            'number': block.number,
            'factorValues': dict((value.factor.id, value.id) for value in block.factor_values),
            'trials': list(generate_block_trials_info(block,
                                                      exp_values=exp_values,
                                                      short=True,
                                                      measures=False)),
            'practice': block.practice
        }
        if not block.practice:
            block_info.update({
                'measuredBlockNumber': measured_block_num
            })
            measured_block_num += 1
        blocks.append(block_info)
    return Response(json.dumps(blocks), mimetype='application/json')


def generate_run_trials_info(run, completed_only=False):
    exp_values = list(factor.default_value
                      for factor
                      in run.experiment.factors
                      if factor.default_value)
    measured_block_num = 0
    for block in run.blocks:
        is_block_started = False
        for trial in generate_block_trials_info(block,
                                                completed_only=completed_only,
                                                exp_values=exp_values,
                                                measured_block_num=(None
                                                                    if block.practice
                                                                    else measured_block_num)):
            yield trial
            is_block_started = True
        else:
            if completed_only and not is_block_started:
                break
        if not block.practice:
            measured_block_num += 1
