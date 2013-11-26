__author__ = 'Quentin Roy'

# app must be imported (even if not use)
from expserver.run import app
from expserver.model import *
import os
from csv import DictWriter


def get_trial_dict_row(trial, fields):
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
        factor_name = fields['factor'][factor.id]['final_name']
        value_name = factor_value.name or factor_value.id
        row[factor_name] = convert_bool(value_name)
    for measure_value in trial.measure_values:
        measure = measure_value.measure
        measure_name = fields['measure'][measure.id]['final_name']
        row[measure_name] = convert_bool(measure_value.value)
    return row


def convert_bool(val):
    if val == 'true' or val == 'True' or val is True:
        return 1
    elif val == 'false' or val == 'False' or val is False:
        return 0
    else:
        return val


def iter_field_infos(field_types):
    for type_name, fields in field_types.iteritems():
        for field in fields:
            type_conflicts = dict((type_name, 0) for type_name in field_types)
            for other_type, other_fields in field_types.iteritems():
                for other_field in other_fields:
                    if field.name == other_field.name and other_field != field:
                        type_conflicts[other_type] += 1
            field_info = {
                'id': field.id,
                'type': type_name,
                'name': field.name,
                'conflicts': type_conflicts,
                'original_field': field
            }
            field_info['final_name'] = get_final_name(field_info)
            yield field_info


def get_final_name(field):
    final_name = field['name']
    for c_type, c_num in field['conflicts'].iteritems():
        if c_num > 0:
            if c_type == field['type']:
                return '{field_name} ({field_type} {field_id})'.format(field_name=field['name'],
                                                                       field_type=field['type'],
                                                                       field_id=field['id'])
                break
            else:
                final_name = '{field_name} ({field_type})'.format(field_name=field['name'],
                                                                  field_type=field['type'])
    return final_name


def create_fields(experiment):
    class Header:
        def __init__(self, h_id, name):
            self.id = h_id
            self.name = name

    headers = {'xpId': 'Experiment Id',
               'runId': 'Run Id',
               'blockNum': 'Block Number',
               'trialNum': 'Trial Number',
               'practice': 'Practice'}

    fields = {'header': list(Header(h_id, h_name) for h_id, h_name in headers.iteritems()),
              'factor': sorted(experiment.factors, key=lambda x: x.id),
              'measure': sorted(
                  (measure for measure in experiment.measures.itervalues() if measure.trial_level),
                  key=lambda x: x.id)}

    field_info = dict((type_name, {}) for type_name in fields)

    for field in iter_field_infos(fields):
        field_info[field['type']][field['id']] = field
    return field_info


def create_logger(experiment, target_path):
    fields = create_fields(experiment)

    target_file = open(target_path, 'w')

    field_names = []
    for sub_fields in fields.itervalues():
        for field in sub_fields.itervalues():
            field_names.append(field['final_name'])


    dict_writer = DictWriter(target_file, field_names)
    dict_writer.writeheader()
    return fields, dict_writer


def run_csv_export(run, logger, fields):
    print('Export Run {}:'.format(run.id))

    for trial in run.trials:
        row = get_trial_dict_row(trial, fields)
        logger.writerow(row)


class MultiLogger:
    def __init__(self, loggers):
        self._loggers = loggers

    def writerow(self, row):
        for logger in self._loggers:
            logger.writerow(row)


def xp_csv_export(experiment, target_dir):
    fields, xp_logger = create_logger(experiment, target_dir + '.csv')
    for run in experiment.runs:
        if run.started():
            _, run_logger = create_logger(experiment, os.path.join(target_dir, run.id + '.csv'))
            run_csv_export(run, MultiLogger([xp_logger, run_logger]), fields)


def csv_export(target_dir):
    for experiment in Experiment.query.order_by(Experiment.id).all():
        exp_dir = os.path.join(target_dir, experiment.id)
        if not os.path.exists(exp_dir):
            os.makedirs(exp_dir)
        xp_csv_export(experiment, exp_dir)


if __name__ == '__main__':
    csv_export('../export')