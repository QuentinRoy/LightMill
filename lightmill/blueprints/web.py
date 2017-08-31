import itertools
import os
from flask import render_template, redirect, Response
from flask.blueprints import Blueprint
from flask.helpers import url_for
from sqlalchemy import func
from sqlalchemy.sql.expression import literal_column
from ..model import Experiment, Run, Trial, Block, db, TrialMeasureValue, trial_factor_values, block_values
from ..model import Measure, FactorValue, Factor
from _utils import inject_model, convert_date
from api.run import generate_run_trials_info

web_blueprint = Blueprint('web', os.path.splitext(__name__)[0])
web_blueprint.url_value_preprocessor(inject_model)


def _toCamelCase(st):
    output = ''.join(x for x in st.title() if x.isalpha())
    return output[0].lower() + output[1:]


def _get_free_name(name, others, prefix):
    if name in others:
        name = prefix + name
        prop = name
        num = 0
        while prop in others:
            prop = name + '_' + str(num)
            num += 1
        return prop
    return name


@web_blueprint.route('/')
def index():
    return render_template('experiments_list.jinja',
                           experiments=Experiment.query.all())


@web_blueprint.route('/experiment/<experiment>')
def experiment(experiment):
    run_statuses = (db.session.query(Run,
                                     func.count(Trial.completion_date),
                                     func.count(Trial.number))
                    .outerjoin(Block, Trial)
                    .group_by(Run.id)).all()
    return render_template('experiment.jinja',
                           run_statuses=run_statuses,
                           experiment=experiment,
                           completed_nb=len(filter(lambda e: e[1] == e[2], run_statuses)),
                           total_nb=len(run_statuses))


@web_blueprint.route('/experiment/<experiment>.csv')
def generate_trial_csv(experiment):
    def generate():
        # Create a big request that selects factors and measures and if they have id
        # conflicts. Returns the ids in alpha order, factors first.
        factor_ids = map(
            lambda x: x[0],
            db.session.query(Factor.id).join(Experiment)
                                       .filter(Factor.experiment == experiment)
                                       .order_by(Factor.id)
        )
        measure_ids = map(
            lambda x: x[0],
            db.session.query(Measure.id).filter_by(trial_level=True)
                                        .filter(Measure.experiment == experiment)
                                        .join(Experiment)
                                        .order_by(Measure.id)
        )

        # Create the orders.
        header_ids = ['experiment_id',
                      'run_id',
                      'block_number',
                      'measured_block_number',
                      'trial_number',
                      'practice',
                      'server_completion_date']

        headers = map(_toCamelCase, header_ids)

        # Yield the header row.
        yield ','.join(itertools.chain(
            headers,
            (_get_free_name(f, itertools.chain(measure_ids, headers), '_factor_')
             for f in factor_ids),
            (_get_free_name(m, itertools.chain(factor_ids, headers), '_measure_')
             for m in measure_ids)
        )) + '\n'

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
                                         Trial.completion_date,
                                         Block.number,
                                         Block.practice,
                                         Run.id,
                                         literal_column('"factors"')) \
            .join(Factor, FactorValue.factor) \
            .join(trial_factor_values, Trial, Block, Run)
        measure_values = db.session.query(Measure.id.label('id'),
                                          TrialMeasureValue.value.label('value'),
                                          Trial.number,
                                          Trial.completion_date,
                                          Block.number,
                                          Block.practice,
                                          Run.id,
                                          literal_column('"measures"')) \
            .join(TrialMeasureValue, Trial, Block, Run)
        block_factor_values = db.session.query(Factor.id.label('id'),
                                               FactorValue.id.label('value'),
                                               literal_column('-1'),
                                               literal_column('null'),
                                               Block.number,
                                               Block.practice,
                                               Run.id,
                                               literal_column('"factors"')) \
            .join(Factor, FactorValue.factor) \
            .join(block_values, Block, Run)
    
        values = measure_values.union_all(factor_values, block_factor_values) \
            .order_by(Run.id, Block.number, Trial.number)

        # values = factor_values

        current_record = None
        current_measured_block_num = None
        current_trial_number = None
        current_block_number = None
        current_block_factors = {}
        current_run_id = None
        for [
            value_id,
            value,
            trial_number,
            completion_date,
            block_number,
            practice,
            run_id,
            value_group
        ] in values:
            # import pdb; pdb.set_trace()
            # Case we changed block
            if current_record is not None and not(block_number == current_block_number and
                                                  current_run_id == run_id):
                current_block_factors = {}
            # Case we changed trial
            if current_record is not None and not (trial_number == current_trial_number and
                                                   block_number == current_block_number and
                                                   current_run_id == run_id):
                
                if current_trial_number < 0:
                    # Case, the previous records were about block_initialization.
                    current_block_factors = current_record['factors']
                else:
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
                # print(type(completion_date))
                current_record = {
                    'trial': {
                        'server_completion_date': (
                            str(convert_date(completion_date)) if completion_date
                            else ''
                        ),
                        'experiment_id': experiment.id,
                        'run_id': run_id,
                        'block_number': str(block_number),
                        'measured_block_number': (
                            '' if practice else str(current_measured_block_num)
                        ),
                        'trial_number': str(trial_number),
                        'practice': str(practice)
                    },
                    'factors': current_block_factors.copy(),
                    'measures': {}
                }
            current_record[value_group][value_id] = value
        # Yield the last record
        yield ','.join(generate_cells(**current_record)) + '\n'

    # Create and return the response, allowing cross-origin requests.
    return Response(generate(), mimetype='text/csv', headers={
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'X-Requested-With, Content-Type'
    })


@web_blueprint.route('/run/<experiment>/<run>/unlock')
def unlock_run(experiment, run):
    run.token = None
    db.session.commit()
    return redirect(url_for('.experiment', experiment=experiment.id))


@web_blueprint.route('/run/<experiment>/<run>/results')
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
    return render_template('results_static.jinja',
                           trials=list(generate_run_trials_info(run, completed_only=True)),
                           trial_measures=trial_measures,
                           factor_values_names=factor_values_names,
                           factors=factors,
                           run=run,
                           experiment=experiment)


@web_blueprint.route('/trial/<experiment>/<run>/<int:block>/<int:trial>/events')
def events(experiment, run, block, trial):
    event_measures = sorted((measure for measure
                            in experiment.measures.itervalues()
                            if measure.event_level),
                            key=lambda x: x.id)
    return render_template('events.jinja',
                           trial=trial,
                           block=block,
                           event_measures=event_measures,
                           run=run,
                           experiment=experiment)
