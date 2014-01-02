__author__ = 'Quentin Roy'

# app must be imported (even if not use)
from expserver.run import app
from expserver.model import *
import os
from csv import DictWriter

FIELD_DICT = {
    'header': {'practice': u'Practice', 'xpId': u'Experiment Id', 'trialNum': u'Trial Number', 'runId': u'Run Id',
               'blockNum': u'Block Number'},
    'measure': {u'correctRotDir': u'Correct Rotation Direction', u'lastPoint.y': u'Last Point y',
                u'lastPoint.x': u'Last Point x', u'durations.trial': u'Trial Duration',
                u'timestamps.trialInitEnd': u'Trial Init End TimeStamp', u'rotDir': u'Rotation Direction (measure)',
                u'endDir': u'End Direction (measure)',
                u'timestamps.drawingEnd': u'Drawing End TimeStamp',
                u'circleFitStdDev': u'Circle Fit Standard Deviation', u'revolutions': u'Revolutions',
                u'endAngleError': u'End Angle Error', u'circle.radius': u'Circle Radius',
                u'timestamps.trialStart': u'Trial Start TimeStamp', u'durations.init': u'Trial Initialization Duration',
                u'timestamps.drawingStart': u'Drawing Start TimeStamp',
                u'startAngle': u'Start Angle (measure)', u'endDirError': u'End Direction Error',
                u'firstPoint.x': u'First Point x', u'firstPoint.y': u'First Point y',
                u'endAngle': u'End Angle (measure)',
                u'durations.drawing': u'Drawing Duration',
                u'timestamps.executionEnd': u'Execution End TimeStamp',
                u'durations.reaction': u'Reaction Duration', u'circle.center.x': u'Circle Center x',
                u'circle.center.y': u'Circle Center y', u'startAngleError': u'Start Angle Error',
                u'revolutionError': u'Revolution Error', u'timestamps.trialEnd': u'Trial End TimeStamp',
                u'timestamps.trialInitStart': u'Trial Init Start TimeStamp',
                u'timestamps.executionStart': u'Execution Start TimeStamp'},
    'factor': {u'revolutions': u'Revolution Number', u'form': u'Form to draw', u'endAngle': u'End Angle (factor)',
               u'rotDir': u'Rotation Direction (factor)', u'startAngle': u'Start Angle (factor)',
               u'endDir': u'End Direction (factor)', u'size': u'Size'}}

FIELD_NAMES = [u'Experiment Id', u'Practice', u'Trial Number', u'Run Id', u'Block Number', u'Revolution Number',
               u'Form to draw', u'End Angle (factor)', u'Rotation Direction (factor)', u'Start Angle (factor)',
               u'End Direction (factor)', u'Size', u'Correct Rotation Direction', u'Last Point y', u'Last Point x',
               u'Trial Duration', u'Trial Init End TimeStamp', u'Rotation Direction (measure)',
               u'End Direction (measure)', u'Drawing End TimeStamp',
               u'Circle Fit Standard Deviation', u'Revolutions', u'End Angle Error', u'Circle Radius',
               u'Trial Start TimeStamp', u'Trial Initialization Duration',
               u'Drawing Start TimeStamp', u'Start Angle (measure)',
               u'End Direction Error', u'First Point x', u'First Point y', u'End Angle (measure)', u'Drawing Duration',
               u'Execution End TimeStamp', u'Reaction Duration', u'Circle Center x',
               u'Circle Center y', u'Start Angle Error', u'Revolution Error', u'Trial End TimeStamp',
               u'Trial Init Start TimeStamp', u'Execution Start TimeStamp']


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
        factor_name = FIELD_DICT['factor'][factor.id] if FIELD_DICT else fields['factor'][factor.id]['final_name']
        value_name = factor_value.name or factor_value.id
        row[factor_name] = convert_bool(value_name)
    for measure_value in trial.measure_values:
        measure = measure_value.measure
        measure_name = FIELD_DICT['measure'][measure.id] if FIELD_DICT else fields['measure'][measure.id]['final_name']
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
                return u'{field_name} ({field_type} {field_id})'.format(field_name=field['name'],
                                                                        field_type=field['type'],
                                                                        field_id=field['id'])
                break
            else:
                final_name = u'{field_name} ({field_type})'.format(field_name=field['name'],
                                                                   field_type=field['type'])
    return final_name


def create_fields(experiment):
    class Header:
        def __init__(self, h_id, name):
            self.id = h_id
            self.name = name

    headers = {'xpId': u'Experiment Id',
               'runId': u'Run Id',
               'blockNum': u'Block Number',
               'trialNum': u'Trial Number',
               'practice': u'Practice'}

    fields = {'header': list(Header(h_id, h_name) for h_id, h_name in headers.iteritems()),
              'factor': sorted(experiment.factors, key=lambda x: x.id),
              'measure': sorted(
                  (measure for measure in experiment.measures.itervalues() if measure.trial_level),
                  key=lambda x: x.id)}

    field_info = dict((type_name, {}) for type_name in fields)

    for field in iter_field_infos(fields):
        field_info[field['type']][field['id']] = field
    return field_info


def get_event_field_names(experiment):
    fields = [u'Experiment Id', u'Run Id', u'Block Number', u'Trial Number', u'Practice']

    for measure in experiment.measures.itervalues():
        if measure.event_level:
            fields.append(measure.name or measure.id)

    return fields


def create_trial_logger(experiment, target_path):
    fields = None

    if not FIELD_NAMES:
        create_fields(experiment)

        #    field_dict = {}
        for sub_fields in fields.itervalues():
            for field in sub_fields.itervalues():
            #            field_type_names = field_dict.get(field['type'], {})
            #            field_dict[field['type']] = field_type_names
            #            field_type_names[field['id']] = field['final_name']
                field_names.append(field['final_name'])

                #    print(field_dict)

    target_file = open(target_path, 'w')
    dict_writer = DictWriter(target_file, FIELD_NAMES if FIELD_NAMES else field_names)
    dict_writer.writeheader()
    return fields, dict_writer


def run_csv_export(run, trial_logger, events_log_dir, fields):
    print('Export Run {}:'.format(run.id))

    field_names = get_event_field_names(run.experiment)
    if not os.path.exists(events_log_dir):
        os.makedirs(events_log_dir)

    for trial in run.trials:
        row = get_trial_dict_row(trial, fields)
        trial_logger.writerow(row)

        target_path = os.path.join(events_log_dir, "{}-{}.csv".format(trial.block.number, trial.number))
        target_file = open(target_path, 'w')
        events_logger = DictWriter(target_file, field_names)
        events_logger.writeheader()

        for event in trial.events:
            row = get_event_row(trial, event)
            events_logger.writerow(row)


def get_event_row(trial, event):
    fields = {
        u'Experiment Id': trial.experiment.id,
        u'Run Id': trial.run.id,
        u'Block Number': trial.block.measure_block_number(),
        u'Trial Number': trial.number,
        u'Practice': trial.block.practice
    }
    for measure_value in event.measure_values.itervalues():
        measure = measure_value.measure
        fields[measure.name or measure.id] = measure_value.value
    return fields


class MultiLogger:
    def __init__(self, loggers):
        self._loggers = loggers

    def writerow(self, row):
        for logger in self._loggers:
            logger.writerow(row)


def xp_csv_export(experiment, target_dir):
    fields, xp_logger = create_trial_logger(experiment, target_dir + '.csv')
    for run in experiment.runs:
        if run.started():
            _, run_logger = create_trial_logger(experiment, os.path.join(target_dir, run.id + '.csv'))
            event_dir = os.path.join(target_dir, run.id)
            run_csv_export(run, MultiLogger([xp_logger, run_logger]), event_dir, fields)


def csv_export(target_dir):
    for experiment in Experiment.query.order_by(Experiment.id).all():
        exp_dir = os.path.join(target_dir, experiment.id)
        if not os.path.exists(exp_dir):
            os.makedirs(exp_dir)
        xp_csv_export(experiment, exp_dir)


if __name__ == '__main__':
    csv_export('../export')