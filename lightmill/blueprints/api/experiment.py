import os
from flask.blueprints import Blueprint
from flask import jsonify
from sqlalchemy import func
from .run import run_info
from ..errors import UnknownElement
from .._utils import allow_origin, answer_options, inject_model, register_invalid_error
from ...model import Block, Trial, Run

blueprint = Blueprint('experiment', os.path.splitext(__name__)[0])


blueprint.url_value_preprocessor(inject_model)
register_invalid_error(blueprint, UnknownElement)
allow_origin(blueprint)
answer_options(blueprint)


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
