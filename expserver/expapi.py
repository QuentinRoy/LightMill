__author__ = 'Quentin Roy'

import os
import uuid
import time
import json
import warnings
import itertools
from collections import OrderedDict
from StringIO import StringIO
from flask import jsonify, redirect, request, render_template, Response
from flask import current_app as app
from flask.blueprints import Blueprint
from flask.helpers import url_for, make_response
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy import func, and_
from sqlalchemy.sql.expression import literal_column
from model import Experiment, Run, Trial, Block, db, ExperimentProgressError
from model import Event, TrialMeasureValue, EventMeasureValue, trial_factor_values
from model import Measure, MeasureLevelError, FactorValue, Factor
from touchstone import create_experiment, parse_experiment_id


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
def handle_experiment_error(error):
    response = jsonify({
        'message': error.args[0],
        'type': error.__class__.__name__
    })
    response.status_code = 405
    return response


def _pull_trial(values):
    trial = Trial.query.get_by_number(
        values['trial'],
        values['block'],
        values['run'],
        values['experiment']
    )
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
            if 'run' not in values:
                _pull_experiment(values)
            elif 'block' not in values:
                _pull_run(values)
            elif 'trial' not in values:
                _pull_block(values)
            else:
                _pull_trial(values)
    except NoResultFound:
        raise UnknownElement("Target not found.", payload={'request': values})


@exp_api.after_request
def allow_origin(response):
    """Makes all the api accessible from any origin"""
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'X-Requested-With, Content-Type')
    return response


# allows any OPTIONS call
@exp_api.route('/*', methods=['OPTIONS'])
def options():
    resp = make_response()
    return resp


@exp_api.route('/experiments')
def experiments_list():
    json_requested = (
        'json' in request.args and request.args['json'].lower() == 'true'
    ) or request.is_xhr
    if json_requested:
        experiments = dict(
            (experiment.id, experiment.name) for experiment in Experiment.query.all()
        )
        return jsonify(experiments)
    else:
        return render_template('experiments_list.html',
                               experiments=Experiment.query.all())


@exp_api.route('/')
def index():
    url = url_for('exp_api.experiments_list')
    return redirect(url)


@exp_api.route('/experiment/<experiment>')
def expe_props(experiment):
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


@exp_api.route('/experiment/<experiment>/measures')
def sorted_measures(experiment):
    measures = {
        "trialLevel": OrderedDict(),
        "eventLevel": OrderedDict()
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
    json_requested = ('json' in request.args and
                      request.args['json'].lower() == 'true' or
                      request.is_xhr)
    if json_requested:
        runs_props = [{
            'id': run.id,
            'completed': run.completed(),
            'started': run.started(),
            'locked': run.locked
        } for run in experiment.runs]
        return jsonify({
            'runs': runs_props
        })
    else:
        run_statuses = (db.session.query(Run,
                                         func.count(Trial.completion_date),
                                         func.count(Trial.number))
                        .outerjoin(Block, Trial)
                        .group_by(Run.id)).all()
        return render_template('xp_status.html',
                               run_statuses=run_statuses,
                               experiment=experiment,
                               completed_nb=len(filter(lambda e: e[1] == e[2], run_statuses)),
                               total_nb=len(run_statuses))


@exp_api.route('/experiment/<experiment>.csv')
def generate_trial_csv(experiment):
    def generate():
        # Create a big request that selects factors and measures and if they have id
        # conflicts. Returns the ids in alpha order, factors first.
        factor_query = db.session.query(Factor.id.label('id'),
                                        func.count(Measure.id)) \
            .join(Experiment) \
            .filter(Factor.experiment == experiment) \
            .outerjoin(Measure, and_(Factor.id == Measure.id, Measure.experiment)) \
            .group_by(Factor.id).all()
        measure_query = db.session.query(Measure.id.label('id'),
                                         func.count(Factor.id)) \
            .filter_by(trial_level=True) \
            .filter(Measure.experiment == experiment) \
            .join(Experiment) \
            .outerjoin(Factor, and_(Factor.id == Measure.id, Factor.experiment)) \
            .group_by(Measure.id).all()

        # Create the orders.
        header_ids = ['experiment_id',
                      'run_id',
                      'block_number',
                      'measured_block_number',
                      'trial_number',
                      'practice']

        factor_ids = list(v[0] for v in factor_query)
        measure_ids = list(v[0] for v in measure_query)

        # Yield the header row.
        yield ', '.join(itertools.chain(
                header_ids,
                ((v[0] if not v[1] else 'factor_' + v[0]) for v in factor_query),
                ((v[0] if not v[1] else 'measure_' + v[0]) for v in measure_query)
        )) + '\n'

        del factor_query
        del measure_query

        # From 3 records, yield each cell in the right order.
        def generate_cells(trial, factors, measures):
            for h in header_ids:
                yield trial.get(h, '')
            for f in factor_ids:
                yield factors.get(f, '')
            for m in measure_ids:
                yield measures.get(m, '')

        # Request factor values and measure values.
        factor_values = db.session.query(Factor.id.label('id'),
                                         FactorValue.id.label('value'),
                                         Trial.number,
                                         Block.number,
                                         Block.practice,
                                         Run.id,
                                         literal_column('"factors"')) \
            .join(Factor, FactorValue.factor) \
            .join(trial_factor_values, Trial, Block, Run)
        measure_values = db.session.query(Measure.id.label('id'),
                                          TrialMeasureValue.value.label('value'),
                                          Trial.number,
                                          Block.number,
                                          Block.practice,
                                          Run.id,
                                          literal_column('"measures"')) \
            .join(TrialMeasureValue, Trial, Block, Run)
        values = measure_values.union_all(factor_values) \
            .order_by(Run.id, Block.number, Trial.number)

        current_record = None
        current_measured_block_num = None
        current_trial_number = None
        current_block_number = None
        current_run_id = None
        for [value_id, value, trial_number, block_number, practice, run_id, value_group] in values:
            # Case we changed trial
            if current_record is not None and not (trial_number == current_trial_number and
                                                   block_number == current_block_number and
                                                   current_run_id == run_id):
                # Yield the current record.
                yield ','.join(generate_cells(**current_record)) + '\n'
                # Reset the values.
                current_record = None
            if not current_record:
                current_trial_number = trial_number
                current_measured_block_num = (
                    0 if not current_measured_block_num and not practice
                    else current_measured_block_num if practice
                    else current_measured_block_num + 1
                )
                current_block_number = block_number
                current_run_id = run_id
                current_record = {
                    'trial': {
                        'experiment_id': experiment.id,
                        'run_id': run_id,
                        'block_number': str(block_number),
                        'measured_block_number': (
                            '' if practice else str(current_measured_block_num)
                        ),
                        'trial_number': str(trial_number),
                        'practice': str(practice)
                    }, 'factors': {}, 'measures': {}
                }
            current_record[value_group][value_id] = value
        # Yield the last record
        yield ','.join(generate_cells(**current_record)) + '\n'

    return Response(generate(), mimetype='text/csv')


@exp_api.route('/import', methods=['POST'])
def expe_import():
    if request.method == 'POST':
        # retrieve the id of the experiment
        expe_id = parse_experiment_id(StringIO(request.data))
        print('Import experiment {}...'.format(expe_id))
        # check if the experiment already exists
        if db.session.query(Experiment.query.filter_by(id=expe_id).exists()).scalar():
            raise CannotImportExperiment('Experiment already exists.')
        # create the experiment and commit the data
        experiment = create_experiment(StringIO(request.data))
        db.session.add(experiment)
        db.session.commit()
        print('Experiment imported.')
        return expe_runs(experiment)


@exp_api.route('/experiment/<experiment>/available_run')
def get_free_run(experiment):
    available_run = (experiment.runs
                     .outerjoin(Block, Trial)
                     .filter(Run.token.is_(None))
                     .having(func.count(Trial.completion_date) == 0)
                     .group_by(Run)).first()

    if available_run:
        return jsonify(run_info(available_run))

    response = jsonify({
        'message': 'No available runs.',
        'type': 'NoAvailableRuns'
    })
    response.status_code = 410
    return response


@exp_api.route('/run/<experiment>/<run>')
def run_props(experiment, run):
    return jsonify(run_info(run))


@exp_api.route('/run/<experiment>/<run>/lock')
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


@exp_api.route('/run/<experiment>/<run>/unlock', methods=['POST'])
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
        return force_unlock_run(experiment, run)


@exp_api.route('/run/<experiment>/<run>/force_unlock')
def force_unlock_run(experiment, run):
    run.token = None
    db.session.commit()
    json_requested = (
        'json' in request.args and request.args['json'].lower() == 'true'
    ) or request.is_xhr
    if json_requested:
        return jsonify(run_info(run))
    return redirect(url_for('.expe_runs', experiment=experiment.id))


def run_info(run):
    return {
        'id': run.id,
        'experimentId': run.experiment.id,
        'completed': run.completed(),
        'started': run.started(),
        'trialCount': run.trial_count(),
        'blockCount': run.block_count(),
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
    return jsonify(_get_trial_info(trial))


@exp_api.route('/run/<experiment>/<run>/next_trial')
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
    return jsonify(_get_trial_info(next_trial))


@exp_api.route('/block/<experiment>/<run>/<int:block>')
def block_props(experiment, run, block):
    props = {
        'number': block.number,
        'measuredBlockNumber': block.measured_block_number(),
        'factorValues': dict((value.factor.id, value.id) for value in block.factor_values),
        'trialCount': block.trials.count()
    }
    return jsonify(props)


@exp_api.route(
    '/trial/<experiment>/<run>/<int:block>/<int:trial>',
    methods=('POST', 'GET', 'OPTIONS')
)
def trial_props(experiment, run, block, trial):
    if request.method == 'OPTIONS':
        resp = make_response()
        resp.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        return resp
    elif request.method == 'POST':
        data = request.get_json()

        # check the token
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

        data_measures = data['measures']
        if data_measures:
            add_measures_if_missing = ('ADD_MISSING_MEASURES' in app.config
                                       and app.config['ADD_MISSING_MEASURES'])
            # register trial measures
            for measure_id, measure_value in _convert_measures(data_measures['trial']):
                val = _get_measure_value(
                    measure_id, measure_value,
                    measure_level='trial',
                    trial=trial,
                    add_measure_if_missing=add_measures_if_missing
                )
                trial.measure_values.append(val)

            # register events
            event_num = 0
            for event_measures in data_measures['events']:
                values = []
                for measure_id, measure_value in _convert_measures(event_measures):
                    if measure_value is not None:
                        val = _get_measure_value(
                            measure_id, measure_value,
                            measure_level='event',
                            trial=trial,
                            add_measure_if_missing=add_measures_if_missing
                        )
                        values.append(val)

                Event(values, event_num, trial)
                event_num += 1

            trial.set_completed()
            db.session.commit()

    return jsonify(_get_trial_info(trial))


def _get_measure_value(
    measure_id,
    measure_value,
    measure_level,
    trial,
    add_measure_if_missing=False
):
    if measure_level not in ('event', 'trial'):
        raise ValueError("Unsupported measure level: " + measure_level)

    experiment = trial.experiment
    measures = experiment.measures
    measure = measures.get(measure_id, None)

    # case add unregistered measure types
    if add_measure_if_missing:
        if measure is None:
            # create the new measure type
            m_args = {
                'id': measure_id,
                'type': 'unregistered'
            }
            m_args[measure_level+'_level'] = True
            measure = Measure(**m_args)
            # register it
            experiment.measures[measure_id] = measure
            # show a warning
            msg = "Unknown {} measure key: '{}' (value: '{}'). New measure type registered.".format(
                measure_level,
                measure_id,
                measure_value
            )
            warnings.warn(msg, WrongMeasureKey)

        # if the level is incorrect
        elif not getattr(measure, measure_level + '_level'):
            # add the level
            setattr(measure, measure_level + '_level', True)
            # show a warning
            msg = ("Measure key '{}'(value: '{}') was not at the {} level. "
                   "Trial level added.").format(measure_level, measure_id, measure_value)
            warnings.warn(msg, WrongMeasureKey)
        return (
            TrialMeasureValue(measure_value, measure) if measure_level is 'trial'
            else EventMeasureValue(measure_value, measure)
        )

    # case refuse incorrect measure types
    elif measure is None:
        msg = "Invalid {} measure key: '{}' (value: '{}')".format(
            measure_level,
            measure_id,
            measure_value
        )
        raise WrongMeasureKey(msg)
    else:
        try:
            return (
                TrialMeasureValue(measure_value, measure) if measure_level is 'trial'
                else EventMeasureValue(measure_value, measure)
            )
        except MeasureLevelError:
            msg = "Measure key '{}'(value: '{}') is not at the {} level.".format(
                measure_id,
                measure_value,
                measure_level
            )
            warnings.warn(msg, WrongMeasureKey)


@exp_api.route('/trial/<experiment>/<run>/<int:block>/<int:trial>/stroke')
def trial_stroke(experiment, run, block, trial):
    events = []
    for event in trial.events:
        event_obj = {}
        for measure_value in event.measure_values.itervalues():
            event_obj[measure_value.measure.id] = measure_value.value
        events.append(event_obj)

    return render_template('strokes.html',
                           trial=trial,
                           dumps=json.dumps,
                           trial_events=events)


def _convert_measures(measures):
    for measure_path, value in _get_measures_paths(measures):
        if value is not None:
            yield '.'.join(measure_path), value


def _get_measures_paths(measures):
    if isinstance(measures, dict):
        for path_head, path_tail in measures.iteritems():
            for path_tail, value in _get_measures_paths(path_tail):
                yield [path_head] + path_tail, value
    elif isinstance(measures, list):
        path_head = 0
        for path_tail in measures:
            for path_tail, value in _get_measures_paths(path_tail):
                yield [str(path_head)] + path_tail, value
            path_head += 1
    else:
        yield [], measures


@exp_api.route('/trial/<experiment>/<run>/<int:block>/<int:trial>/events')
def events(experiment, run, block, trial):
    event_measures = sorted((measure for measure
                            in experiment.measures.itervalues()
                            if measure.event_level),
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
    trial_measures = sorted((measure
                             for measure in experiment.measures.itervalues()
                             if measure.trial_level),
                            key=lambda x: x.id)
    factor_values_names = dict(db.session.query(FactorValue.id, FactorValue.name)
                               .join(FactorValue.factor)
                               .filter(Factor.experiment == experiment)
                               .filter(FactorValue.name.isnot(None)))
    return render_template('results_static.html',
                           trials=list(_get_run_trials_info(run, completed_only=True)),
                           trial_measures=trial_measures,
                           factor_values_names=factor_values_names,
                           factors=factors,
                           run=run,
                           experiment=experiment)


def _get_run_trials_info(run, completed_only=False):
    exp_values = list(factor.default_value
                      for factor
                      in run.experiment.factors
                      if factor.default_value)
    measured_block_num = 0
    for block in run.blocks:
        is_block_started = False
        for trial in _get_block_trials_info(block,
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


def _get_block_trials_info(block,
                           completed_only=False,
                           exp_values=None,
                           measured_block_num=None,
                           block_values=None,
                           measures=True,
                           short=False):
    experiment = block.run.experiment
    exp_values = list(factor.default_value
                      for factor
                      in experiment.factors
                      if factor.default_value) if exp_values is None else exp_values
    block_values = block.factor_values
    trial_query = block.trials
    if completed_only:
        trial_query = trial_query.filter(Trial.completion_date.isnot(None))
    for trial in trial_query:
        factor_values = dict((value.factor.id, value.id)
                             for value
                             in itertools.chain(exp_values,
                                                block_values,
                                                trial.factor_values))

        result = {
            'number': trial.number,
            'factorValues': factor_values,
            'completionDate': _convert_date(trial.completion_date)
        }
        if not short:
            measured_block_num = (block.measured_block_number()
                                  if measured_block_num is None and not block.practice
                                  else measured_block_num)
            result.update({
                'experimentId': experiment.id,
                'runId': trial.run.id,
                'blockNumber': block.number,
                'practice': block.practice,
            })
            if measured_block_num is not None:
                result.update({
                    'measuredBlockNumber': measured_block_num
                })
        if measures:
            result.update({
                'measures': dict((m_value.measure.id, m_value.value)
                                 for m_value
                                 in trial.measure_values)
            })
        yield result


def _get_trial_info(trial):
    factors = trial.experiment.factors
    exp_values = (factor.default_value for factor in factors if factor.default_value)
    block_values = (value for value in trial.block.factor_values)
    factor_values = dict((value.factor.id, value.id)
                         for value
                         in itertools.chain(exp_values, block_values, trial.factor_values))
    measures = dict((m_value.measure.id, m_value.value)
                    for m_value
                    in trial.measure_values)
    answer = {
        'experimentId': trial.experiment.id,
        'runId': trial.run.id,
        'number': trial.number,
        'blockNumber': trial.block.number,
        'measuredBlockNumber': trial.block.measured_block_number(),
        'factorValues': factor_values,
        'measures': measures,
        'practice': trial.block.practice,
        'completionDate': _convert_date(trial.completion_date)
    }
    # if trial.completion_date:
    #     answer['completion_date'] = int(time.mktime(
    #         trial.completion_date.timetuple()))
    return answer


def _convert_date(date):
    return int(time.mktime(date.timetuple())) if date else None


@exp_api.route('/run/<experiment>/<run>/trials')
def run_trials(experiment, run):
    return Response(json.dumps(list(_get_run_trials_info(run))),  mimetype='application/json')


def _get_run_plan(run):
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
            'trials': list(_get_block_trials_info(block,
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
    return blocks


@exp_api.route('/run/<experiment>/<run>/plan')
def run_plan(experiment, run):
    return Response(json.dumps(list(_get_run_plan(run))),  mimetype='application/json')
