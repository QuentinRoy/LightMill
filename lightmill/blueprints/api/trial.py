import os
import itertools
import warnings
import json
from flask import jsonify, request, current_app as app
from flask.blueprints import Blueprint
from ..errors import UnknownElement
from .._utils import register_invalid_error, inject_model, allow_origin, answer_options
from .._utils import convert_date
from ...model import db, ExperimentProgressError, Measure, TrialMeasureValue, Event
from ...model import MeasureLevelError, EventMeasureValue


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


blueprint = Blueprint('trial', os.path.splitext(__name__)[0])
blueprint.url_value_preprocessor(inject_model)
register_invalid_error(blueprint, UnknownElement)
register_invalid_error(blueprint, WrongMeasureKey)
allow_origin(blueprint)
answer_options(blueprint)


@blueprint.errorhandler(ExperimentProgressError)
def handle_experiment_error(error):
    response = jsonify({
        'message': error.args[0],
        'type': error.__class__.__name__
    })
    response.status_code = 405
    return response


@blueprint.route('/<experiment>/<run>/<int:block>/<int:trial>', methods=['POST'])
def post_result(experiment, run, block, trial):
    # Do not use request.get_json() to support unset content type and allow POST requests
    # without preflight.
    data = json.loads(request.data)

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
    return trial_info(trial)


@blueprint.route('/<experiment>/<run>/<int:block>/<int:trial>', methods=['GET'])
def trial_info(trial, experiment=None, run=None, block=None):
    factors = trial.experiment.factors
    exp_values = (
        factor.default_value for factor in factors if factor.default_value)
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
        'completionDate': convert_date(trial.completion_date)
    }
    return jsonify(answer)


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


def _convert_measures(measures):
    for measure_path, value in _get_measures_paths(measures):
        if value is not None:
            yield '.'.join(measure_path), value


def _get_measures_paths(measures):
    if isinstance(measures, dict):
        for path_head, path_tail in measures.items():
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
