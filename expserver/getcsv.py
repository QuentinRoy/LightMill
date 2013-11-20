__author__ = 'Quentin Roy'

from run import app
from model import *
import os
from csv import DictWriter


def get_trial_dict_row(trial):
    print('  Trial {} of block {}'.format(trial.number, trial.block.number))
    row = {
        'Experiment Id': trial.run.experiment.id,
        'Run Id': trial.run.id,
        'Block Number': trial.block.measure_block_number(),
        'Trial Number': trial.number,
        'Practice': convert_bool(trial.block.practice)
    }
    for factor_value in trial.iter_all_factor_values():
        factor = factor_value.factor
        factor_name = factor.name or factor.id
        value_name = factor_value.name or factor_value.id
        row[factor_name] = convert_bool(value_name)
    for measure_value in trial.measure_values:
        measure = measure_value.measure
        measure_name = measure.name or measure.id
        row[measure_name] = convert_bool(measure_value.value)
    return row


def convert_bool(val):
    if val == 'true' or val == 'True' or val is True:
        return 1
    elif val == 'false' or val == 'False' or val is False:
        return 0
    else:
        return val


def create_logger(experiment, target_path):
    fieldnames = ['Experiment Id', 'Run Id', 'Block Number', 'Trial Number', 'Practice']

    for factor in sorted(experiment.factors, key=lambda x: x.id):
        fieldnames.append(factor.name or factor.id)

    for measure in sorted(experiment.measures.itervalues(), key=lambda x: x.id):
        if measure.trial_level:
            fieldnames.append(measure.name or measure.id)

    target_file = open(target_path, 'w')
    dict_writer = DictWriter(target_file, fieldnames)
    dict_writer.writeheader()
    return dict_writer


def run_csv_export(run, logger):
    print('Export Run {}:'.format(run.id))

    for trial in run.trials:
        row = get_trial_dict_row(trial)
        logger.writerow(row)


class MultiLogger:
    def __init__(self, loggers):
        self._loggers = loggers

    def writerow(self, row):
        for logger in self._loggers:
            logger.writerow(row)


def xp_csv_export(experiment, target_dir):
    xp_logger = create_logger(experiment, target_dir+'.csv')
    for run in experiment.runs:
        if run.completed():
            run_logger = create_logger(experiment, os.path.join(target_dir, run.id + '.csv'))
            run_csv_export(run, MultiLogger([xp_logger, run_logger]))


def csv_export(target_dir):
    for experiment in Experiment.query.order_by(Experiment.id).all():
        exp_dir = os.path.join(target_dir, experiment.id)
        if not os.path.exists(exp_dir):
            os.makedirs(exp_dir)
        xp_csv_export(experiment, exp_dir)


if __name__ == '__main__':
    csv_export('../export')