__author__ = 'Quentin Roy'

# app must be imported (even if not use)
from run import app
from model import *
import os
import sys
import time
from csv import DictWriter
from collections import OrderedDict

DELIMITER = ';'

def convert_bool(val):
    if str(val).lower() == 'true':
        return 1
    elif str(val).lower() == 'false':
        return 0
    else:
        return val


def iter_field_info(field_types):
    for type_name, fields in field_types.iteritems():
        for field in fields:
            field_name = field.name or field.id
            type_conflicts = dict((type_name, 0) for type_name in field_types)
            for other_type, other_fields in field_types.iteritems():
                for other_field in other_fields:
                    other_field_name = other_field.name or other_field.id
                    if field_name == other_field_name and other_field != field:
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
    final_name = field['name'] or field['id']
    for c_type, c_num in field['conflicts'].iteritems():
        if c_num > 0:
            if c_type == field['type']:
                return u'{field_name} ({field_type} {field_id})'.format(field_name=field['name'],
                                                                        field_type=field['type'],
                                                                        field_id=field['id'])
                break
            else:
                final_name = u'{field_name} ({field_type})'.format(field_name=field['name'],
                                                                   field_type=field['type'])
    return final_name


class Field:
    def __init__(self, h_id, name):
        self.id = h_id
        self.name = name


def create_trial_fields(experiment):

    headers = [('xpId', u'Experiment Name'),
               ('runId', u'Run Id'),
               ('blockNum', u'Block Number'),
               ('trialNum', u'Trial Number'),
               ('practice', u'Practice')]

    fields = {'header': list(Field(h_id, h_name) for h_id, h_name in headers),
              'factor': sorted(experiment.factors, key=lambda x: x.id),
              'measure': sorted(
                  (measure for measure in experiment.measures.itervalues() if measure.trial_level),
                  key=lambda x: x.id)}

    field_info = OrderedDict((type_name, OrderedDict()) for type_name in ['header', 'factor', 'measure'])

    # field info check for name conflicts and create field final names
    for field in iter_field_info(fields):
        field_info[field['type']][field['id']] = field
    return field_info


def create_event_fields(experiment):

    headers = [('xpId', u'Experiment Name'),
               ('runId', u'Run Id'),
               ('blockNum', u'Block Number'),
               ('trialNum', u'Trial Number'),
               ('evtNum', u'Event Number'),
               ('practice', u'Practice')]

    fields = {'header': list(Field(h_id, h_name) for h_id, h_name in headers),
              'factor': sorted(experiment.factors, key=lambda x: x.id),
              'measure': sorted(
                  (measure for measure in experiment.measures.itervalues() if measure.event_level),
                  key=lambda x: x.id)}

    field_info = OrderedDict((type_name, OrderedDict()) for type_name in ['header', 'factor', 'measure'])

    # field info check for name conflicts and create field final names
    for field in iter_field_info(fields):
        field_info[field['type']][field['id']] = field

    return field_info


def create_logger(fields, target_path):
    field_names = []

    for sub_fields in fields.itervalues():
        for field in sub_fields.itervalues():
            field_names.append(field['final_name'])

    target_file = open(target_path, 'w')
    dict_writer = DictWriter(target_file, field_names, delimiter=DELIMITER)
    dict_writer.writeheader()
    return dict_writer


def run_csv_export(run, trial_logger, events_log_dir,
                   trial_fields, event_fields, global_event_logger=None):
    print('Export Run {}:'.format(run.id))

    trial_export_time = 0
    event_export_time = 0
    trial_count = 0
    event_count = 0

    run_start = time.time()

    if not os.path.exists(events_log_dir):
        os.makedirs(events_log_dir)

    for trial in run.trials:
        sys.stdout.write('  Trial {} of block {}...'.format(
                    trial.number,
                    trial.block.number))
        sys.stdout.flush()
        factor_values = list(trial.iter_all_factor_values())
        trial_start = time.time()
        trial_event_count = 0
        trial_events_time = 0
        row = get_trial_row(trial, trial_fields, factor_values)
        trial_logger.writerow(row)
        trial_row_end = time.time()

        events_path = os.path.join(events_log_dir,
                                   "{}-{}-{}.csv".format(run.id,
                                                         trial.block.number,
                                                         trial.number))
        events_logger = create_logger(event_fields, events_path)

        event_rows_start = time.time()
        for event in trial.events:
            trial_event_count += 1
            event_start = time.time()
            row = get_event_row(event, event_fields, factor_values)
            events_logger.writerow(row)
            if global_event_logger:
                global_event_logger.writerow(row);
            event_end = time.time()
            trial_events_time += (event_end - event_start)

        trial_end = time.time()
        trial_duration = trial_end - trial_start
        trial_export_time += trial_duration
        event_export_time += trial_events_time
        event_count += trial_event_count
        trial_count += 1
        print(' exported ({:.02f} sec, {} events, trial row: {}sec, event rows: {}sec, event mean: {}sec)'.format(
              trial_duration,
              trial_event_count,
              trial_row_end - trial_start,
              trial_end - event_rows_start,
              float(trial_events_time) / trial_event_count))


    run_end = time.time()
    print('Run {} exported.'.format(run.id))
    print('{} sec, {:.2f} sec/trials, {:} ms/events, {} trials, {} events'.format(
                        round(run_end - run_start),
                        trial_export_time / trial_count,
                        round((event_export_time / event_count) * 1000),
                        trial_count,
                        event_count))



def get_trial_row(trial, fields, factor_values):
    row = {
        u'Experiment Name': trial.experiment.name or trial.experiment.id,
        u'Run Id': trial.run.id,
        u'Block Number': trial.block.number,
        u'Trial Number': trial.number,
        u'Practice': convert_bool(trial.block.practice)
    }
    for factor_value in factor_values:
        factor = factor_value.factor
        factor_name = fields['factor'][factor.id]['final_name']
        value_name = factor_value.name or factor_value.id
        row[factor_name] = convert_bool(value_name)
    for measure_value in trial.measure_values:
        measure = measure_value.measure
        measure_name = fields['measure'][measure.id]['final_name']
        row[measure_name] = convert_bool(measure_value.value)
    return row


def get_event_row(event, fields, factor_values):
    trial = event.trial
    row = {
        u'Experiment Name': trial.experiment.name or trial.experiment.id,
        u'Run Id': trial.run.id,
        u'Block Number': trial.block.number,
        u'Trial Number': trial.number,
        u'Practice': convert_bool(trial.block.practice),
        u'Event Number': event.number
    }
    for factor_value in factor_values:
        factor = factor_value.factor
        factor_name = fields['factor'][factor.id]['final_name']
        value_name = factor_value.name or factor_value.id
        row[factor_name] = convert_bool(value_name)
    for measure_value in event.measure_values.values():
        measure = measure_value.measure
        measure_name = fields['measure'][measure.id]['final_name']
        row[measure_name] = convert_bool(measure_value.value)
    return row


class MultiLogger:
    def __init__(self, loggers):
        self._loggers = loggers

    def writerow(self, row):
        for logger in self._loggers:
            logger.writerow(row)


def xp_csv_export(experiment, target_dir):

    # create the field list
    trial_fields = create_trial_fields(experiment)
    event_fields = create_event_fields(experiment)

    # create the main logger
    xp_logger = create_logger(trial_fields,
                              os.path.join(target_dir, experiment.id + '.csv'))
    # create the event logger
    event_logger = create_logger(event_fields,
                                 os.path.join(target_dir,
                                              experiment.id + '-events.csv'))

    # create the directories
    runs_dir = os.path.join(target_dir, 'runs')
    events_dir = os.path.join(target_dir, 'events')
    if not os.path.exists(runs_dir):
        os.makedirs(runs_dir)
    if not os.path.exists(events_dir):
        os.makedirs(events_dir)

    # log each run
    for run in experiment.runs:
        if run.started():
            run_logger = create_logger(trial_fields,
                                       os.path.join(runs_dir, run.id + '.csv'))
            run_csv_export(run,
                           MultiLogger([xp_logger, run_logger]),
                           events_dir, trial_fields, event_fields,
                           event_logger)


def csv_export(target_dir):
    for experiment in Experiment.query.order_by(Experiment.id).all():
        exp_dir = os.path.abspath(os.path.join(target_dir, experiment.id))
        if not os.path.exists(exp_dir):
            os.makedirs(exp_dir)
        xp_csv_export(experiment, exp_dir)


if __name__ == '__main__':
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else 'export'
    csv_export(path)
