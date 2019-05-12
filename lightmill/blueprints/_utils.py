import time
from flask import jsonify
from flask.helpers import make_response
from .errors import UnknownElement
from sqlalchemy.orm.exc import NoResultFound
from ..model import Trial, Block, Run, Experiment


def register_invalid_error(blueprint, errorType):
    @blueprint.errorhandler(errorType)
    def create_invalid_usage_response(error):
        error_dict = error.to_dict()
        error_dict['type'] = error.__class__.__name__
        response = jsonify(error_dict)
        response.status_code = error.status_code
        return response


def allow_origin(blueprint):
    @blueprint.after_request
    def create_response(response):
        """Makes all the api accessible from any origin"""
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers',
                             'X-Requested-With, Content-Type')
        return response


def answer_options(blueprint):
    @blueprint.route('/*', methods=['OPTIONS'])
    def options():
        resp = make_response()
        return resp


def _inject_trial(values):
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


def _inject_block(values):
    block = Block.query.get_by_number(
        values['block'], values['run'], values['experiment'])
    values['experiment'] = block.experiment
    values['block'] = block
    values['run'] = block.run


def _inject_run(values):
    run = Run.query.get_by_id(values['run'], values['experiment'])
    values['run'] = run
    values['experiment'] = run.experiment


def _inject_experiment(values):
    values['experiment'] = Experiment.query.get_by_id(values['experiment'])


def inject_model(endpoint, values):
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
                _inject_experiment(values)
            elif 'block' not in values:
                _inject_run(values)
            elif 'trial' not in values:
                _inject_block(values)
            else:
                _inject_trial(values)
    except NoResultFound:
        raise UnknownElement("Target not found.", payload={'request': values})


def convert_date(date):
    return int(time.mktime(date.timetuple()) * 1000. + date.microsecond / 1000.) if date else None
