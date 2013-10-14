__author__ = 'Quentin Roy'


from run import app
from model import *
import os
from csv import DictWriter


def get_trial_dict_row(trial):
    print('Trial {} of block {}'.format(trial.number, trial.block.number))
    row = {
        'Experiment Id': trial.run.experiment.id,
        'Run Id': trial.run.id,
        'Block Number': trial.block.measure_block_number(),
        'Trial Number': trial.number,
        'Practice': trial.block.practice
    }
    for factor_value in trial.iter_all_factor_values():
        factor = factor_value.factor
        factor_name = factor.name or factor.id
        value_name = factor_value.name or factor_value.id
        row[factor_name] = value_name
    for measure_value in trial.measure_values:
        measure = measure_value.measure
        measure_name = measure.name or measure.id
        row[measure_name] = measure_value.value
    return row


def run_csv_export(run, target_path):
    experiment = run.experiment
    fieldnames = ['Experiment Id', 'Run Id', 'Block Number', 'Trial Number', 'Practice']

    for factor in sorted(experiment.factors, key=lambda x: x.id):
        fieldnames.append(factor.name or factor.id)

    for measure in sorted(experiment.measures.itervalues(), key=lambda x: x.id):
        if measure.trial_level:
            fieldnames.append(measure.name or measure.id)

    target_file = open(target_path, 'w')
    dict_writer = DictWriter(target_file, fieldnames)
    dict_writer.writeheader()

    for trial in run.trials:
        row = get_trial_dict_row(trial)
        dict_writer.writerow(row)


def xp_csv_export(experiment, target_dir):
    for run in experiment.runs:
        if run.completed():
            target_file = os.path.join(target_dir, run.id + '.csv')
            run_csv_export(run, target_file)


def csv_export(target_dir):
    for experiment in Experiment.query.order_by(Experiment.id).all():
        exp_dir = os.path.join(target_dir, experiment.id)
        if not os.path.exists(exp_dir):
            os.makedirs(exp_dir)
        xp_csv_export(experiment, exp_dir)


if __name__ == '__main__':
    csv_export('../export')