__author__ = 'Quentin Roy'

from run import app
from model import *
import os
from csv import DictWriter


def get_trial_dict_row(trial, fieldnames):
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
        if factor_name not in fieldnames:
            factor_name += ' (factor)'
        row[factor_name] = convert_bool(value_name)
    for measure_value in trial.measure_values:
        measure = measure_value.measure
        measure_name = measure.name or measure.id
        if measure_name not in fieldnames:
            measure_name += ' (measure)'
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
    header_names = ['Experiment Id', 'Run Id', 'Block Number', 'Trial Number', 'Practice']
    factor_names = []
    measure_names = []

    for factor in sorted(experiment.factors, key=lambda x: x.id):
        factor_name = factor.name or factor.id
        if factor_name in header_names:
            factor_name += ' (factor)'
        factor_names.append(factor_name)

    for measure in sorted(experiment.measures.itervalues(), key=lambda x: x.id):
        if measure.trial_level:
            measure_name = measure.name or measure.id
            # if there is a factor with the same name
            for index, factor_name in enumerate(factor_names):
                if factor_name == measure_name:
                    measure_name += ' (measure)'
                    factor_names[index] = factor_name+' (factor)'
                if factor_name == measure_name + ' (factor)':
                    measure_name += ' (measure)'
            measure_names.append(measure_name)

    field_names = header_names + factor_names + measure_names

    target_file = open(target_path, 'w')
    dict_writer = DictWriter(target_file, field_names)
    dict_writer.writeheader()
    return field_names, dict_writer


def run_csv_export(run, logger, fieldnames):
    print('Export Run {}:'.format(run.id))

    for trial in run.trials:
        row = get_trial_dict_row(trial, fieldnames)
        logger.writerow(row)


class MultiLogger:
    def __init__(self, loggers):
        self._loggers = loggers

    def writerow(self, row):
        for logger in self._loggers:
            logger.writerow(row)


def xp_csv_export(experiment, target_dir):
    fieldnames, xp_logger = create_logger(experiment, target_dir+'.csv')
    for run in experiment.runs:
        if run.completed():
            _, run_logger = create_logger(experiment, os.path.join(target_dir, run.id + '.csv'))
            run_csv_export(run, MultiLogger([xp_logger, run_logger]), fieldnames)


def csv_export(target_dir):
    for experiment in Experiment.query.order_by(Experiment.id).all():
        exp_dir = os.path.join(target_dir, experiment.id)
        if not os.path.exists(exp_dir):
            os.makedirs(exp_dir)
        xp_csv_export(experiment, exp_dir)


if __name__ == '__main__':
    csv_export('../export')