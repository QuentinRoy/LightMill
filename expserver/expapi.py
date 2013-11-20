import warnings

__author__ = 'Quentin Roy'

from flask.blueprints import Blueprint
from flask.helpers import url_for, make_response
from sqlalchemy.orm.exc import NoResultFound
import os
import uuid
from flask import jsonify, redirect, request, render_template, abort
from model import Experiment, Run, Trial, Block, db, ExperimentProgressError
from model import Event, TrialMeasureValue, EventMeasureValue, MeasureLevelError
from time import time
from collections import OrderedDict
from sqlalchemy.exc import IntegrityError
import json
import thread
from threading import Lock
from sqlalchemy import event
from geventwebsocket.exceptions import WebSocketError

exp_api = Blueprint('exp_api', os.path.splitext(__name__)[0])


class UnknownElement(Exception):
    status_code = 400

    def __init__(self, message, status_code=status_code, payload=None):
        Exception.__init__(self)
        self.message = message
        self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        return rv


class WrongMeasureKey(Warning):
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

# comment this to allow invalid measure key
# warnings.simplefilter('error', WrongMeasureKey)


@exp_api.errorhandler(UnknownElement)
@exp_api.errorhandler(WrongMeasureKey)
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
        factor_dict = {
            'tag': factor.tag,
            'name': factor.name,
            'type': factor.type,
            'values': dict((value.id, value.name) for value in factor.values)
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
        'measures': measures,
        'req_duration': time() - start
    }
    return jsonify(exp_data)


@exp_api.route('/experiment/<experiment>/measures')
def sorted_measures(experiment):
    measures = {
        "trial_level": OrderedDict(),
        "event_level": OrderedDict()
    }
    for measure in sorted(experiment.measures.values(), key=lambda m: m.id):
        if measure.trial_level:
            measures['trial_level'][measure.id] = measure.name
        if measure.event_level:
            measures['event_level'][measure.id] = measure.name
    if request.is_xhr:
        return jsonify(measures)
    else:
        return render_template('measures.html', experiment=experiment, measures=measures)


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
    return jsonify(_trial_info(trial))


@exp_api.route('/block/<experiment>/<run>/<int:block>')
def block_props(experiment, run, block):
    props = {
        'number': block.number,
        'measure_block_number': block.measure_block_number(),
        'values': dict((value.factor.id, value.id) for value in block.values),
        'total': run.block_count()
    }
    return jsonify(props)


@exp_api.route('/trial/<experiment>/<run>/<int:block>/<int:trial>', methods=('POST', 'GET', 'OPTIONS'))
def trial_props(experiment, run, block, trial):
    if request.method == 'OPTIONS':
        resp = make_response()
        resp.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        return resp
    elif request.method == 'POST':
        data = request.get_json()
        token = data['token']
        if run.token is None:
            response = jsonify({
                'message': 'Run must be locked before writing.',
                'type': 'RunNotLocked'
            })
            response.status_code = 405
            return response
        elif token != run.token:
            response = jsonify({
                'message': 'Wrong token: {} for run {}'.format(token, run.id),
                'type': 'WrongToken'
            })
            response.status_code = 405
            return response
        measures = experiment.measures

        for measure_id, measure_value in _convert_measures(data['measures']):
            try:
                if measure_id != 'events':
                    trial.measure_values.append(TrialMeasureValue(measure_value, measures[measure_id]))
            except KeyError:
                msg = "Invalid trial measure key: '{}' (value: '{}')".format(measure_id, measure_value)
                warnings.warn(msg, WrongMeasureKey)
            except MeasureLevelError:
                msg = "Measure key '{}'(value: '{}') is not at the trial level.".format(measure_id, measure_value)
                warnings.warn(msg, WrongMeasureKey)
        event_num = 0
        for event_measures in data['measures']['events']:
            values = []
            for measure_id, measure_value in _convert_measures(event_measures):
                try:
                    if measure_value is not None:
                        values.append(EventMeasureValue(measure_value, measures[measure_id]))
                except KeyError:
                    msg = "Invalid event measure key: '{}' (value: '{}')".format(measure_id, measure_value)
                    warnings.warn(msg, WrongMeasureKey)

                except MeasureLevelError:
                    msg = "Measure key '{}' (value: '{}') is not at the event level.".format(measure_id, measure_value)
                    warnings.warn(msg, WrongMeasureKey)

            Event(values, event_num, trial)
            event_num += 1
        trial.set_completed()
        db.session.commit()

    return jsonify(_trial_info(trial))


def _convert_measures(measures):
    for measure_path, value in _get_measures_paths(measures):
        yield '.'.join(measure_path), value


def _get_measures_paths(measures):
    if isinstance(measures, dict):
        for path_head, path_tail in measures.iteritems():
            for path_tail, value in _get_measures_paths(path_tail):
                yield [path_head] + path_tail, value
    else:
        yield [], measures


def _trial_info(trial):
    values = dict((value.factor.id, value.id) for value in trial.factor_values)
    block_values = dict((value.factor.id, value.id) for value in trial.block.factor_values)
    default_values = {}
    missing_values = []
    for factor in trial.experiment.factors:
        if factor.id not in values and factor.id not in block_values:
            if factor.default_value:
                default_values[factor.id] = factor.default_value.id
            else:
                missing_values.append(factor.id)


    return {
        'number': trial.number,
        'block_number': trial.block.number,
        'experiment_id': trial.experiment.id,
        'run_id': trial.run.id,
        'practice': trial.block.practice,
        'measure_block_number': trial.block.measure_block_number(),
        'values': values,
        'block_values': block_values,
        'default_values': default_values,
        'missing_values': missing_values,
        'total': trial.block.length(),
        'completion_date': trial.completion_date
    }


@exp_api.route('/trial/<experiment>/<run>/<int:block>/<int:trial>/events')
def events(experiment, run, block, trial):
    event_measures = sorted((measure for measure in experiment.measures.itervalues() if measure.event_level),
                            key=lambda x: x.id)
    return render_template('events.html',
                           trial=trial,
                           block=block,
                           event_measures=event_measures,
                           run=run,
                           experiment=experiment)


@exp_api.route('/run/<experiment>/<run>/results')
def run_results(experiment, run):
    factors = sorted(experiment.factors, key=lambda x: x.id)
    trial_measures = sorted((measure for measure in experiment.measures.itervalues() if measure.trial_level),
                            key=lambda x: x.id)

    if 'nojs' in request.args:
        return render_template('results_static.html',
                               trials=[
                                   _get_trial_measure_info(trial)
                                   for trial in run.trials.filter(Trial.completion_date != None)
                               ],
                               trial_measures=trial_measures,
                               factors=factors,
                               run=run,
                               experiment=experiment)
    else:
        return render_template('results_websocket.html',
                               config={
                                   'factors': OrderedDict((factor.id, factor.name) for factor in factors),
                                   'measures': OrderedDict((measure.id, measure.name) for measure in trial_measures),
                                   'run_id': run.id,
                                   'experiment_id': experiment.id,
                                   'websocket_url': url_for('exp_api.result_socket',
                                                            experiment=experiment.id,
                                                            run=run.id)
                               },
                               trial_measures=trial_measures,
                               factors=factors,
                               run=run,
                               experiment=experiment)


class _TrialCompletedAlert():
    def __init__(self):
        self._listeners = {}
        self._lock = Lock()

        event.listen(Trial.completion_date, 'set', self._listen)

    def _listen(self, target, value, oldvalue, initiator):
        exp_id, run_id = target.experiment.id, target.run.id
        if not exp_id in self._listeners or not run_id in self._listeners[exp_id]:
            return
        listeners = self._listeners[target.experiment.id][target.run.id]
        if listeners and value is not None:
            thread.start_new_thread(self._call_trial_completed_listeners,
                                    [listeners, target.number, target.block.number])

    def _call_trial_completed_listeners(self, listeners, trial_number, block_number):
        with self._lock:
            for listener in listeners:
                listener(trial_number, block_number)

    def append_listener(self, listener, experiment_id, run_id):
        if not experiment_id in self._listeners:
            self._listeners[experiment_id] = {}
        if not run_id in self._listeners[experiment_id]:
            self._listeners[experiment_id][run_id] = []
        self._listeners[experiment_id][run_id].append(listener)

    def remove_listener(self, listener, experiment_id, run_id):
        self._listeners[experiment_id][run_id].remove(listener)


_trial_completed_alert = _TrialCompletedAlert()


@exp_api.route('/run/<experiment>/<run>/result_socket')
def result_socket(experiment, run):
    if request.environ.get('wsgi.websocket'):

        ws = request.environ['wsgi.websocket']

        def send_trial(func_trial):
            trial_info = _get_trial_measure_info(func_trial)

            # convert the factors
            factors = trial_info['factors']
            for factor_id in factors:
                factors[factor_id] = factors[factor_id].id

            print('WebSocket send')
            func_message = json.dumps(trial_info)
            ws.send(func_message)

        def listener(trial_number, block_number):
            func_trial = Trial.query.get_by_number(trial_number, block_number, run.id, experiment.id)
            send_trial(func_trial)

        for trial in run.trials.filter(Trial.completion_date != None):
            send_trial(trial)

        _trial_completed_alert.append_listener(listener, experiment.id, run.id)

        while True:
            try:
                message = ws.receive()
                # we don't care about what you're saying.
                if message is None:
                    break
            except WebSocketError:
                break
            finally:
                _trial_completed_alert.remove_listener(listener, experiment.id, run.id)
        return ''
    else:
        abort(400, "Expected WebSocket request")


@exp_api.route('/test')
def test():
    return render_template('websock_test.html')


@exp_api.route('/api')
def api():
    if request.environ.get('wsgi.websocket'):
        ws = request.environ['wsgi.websocket']
        while True:
            message = ws.receive()
            ws.send(message)
    return


def _get_trial_measure_info(trial):
    return {
        'measures': _get_trial_measure(trial),
        'factors': dict((f_value.factor.id, f_value)
                        for f_value in trial.iter_all_factor_values()),
        'number': trial.number,
        'block_number': trial.block.number,
        'measure_block_number': trial.block.measure_block_number(),
        'practice': trial.block.practice
    }


def _get_trial_measure(trial):
    measure_values = dict()
    for measure_value in trial.measure_values:
        measure_values[measure_value.measure.id] = measure_value.value
    return measure_values