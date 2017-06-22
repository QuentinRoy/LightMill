import os
import itertools
from flask import jsonify
from flask.blueprints import Blueprint
from ...model import Trial
from .._utils import convert_date, allow_origin, inject_model, answer_options
from .._utils import register_invalid_error
from ..errors import UnknownElement

blueprint = Blueprint('block', os.path.splitext(__name__)[0])

blueprint.url_value_preprocessor(inject_model)
register_invalid_error(blueprint, UnknownElement)
allow_origin(blueprint)
answer_options(blueprint)


@blueprint.route('/<experiment>/<run>/<int:block>')
def block_props(experiment, run, block):
    props = {
        'number': block.number,
        'measuredBlockNumber': block.measured_block_number(),
        'factorValues': dict((value.factor.id, value.id) for value in block.factor_values),
        'trialCount': block.trials.count(),
        'practice': block.practice
    }
    return jsonify(props)


def generate_block_trials_info(block,
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
            'completionDate': convert_date(trial.completion_date)
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
