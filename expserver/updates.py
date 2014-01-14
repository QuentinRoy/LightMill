__author__ = 'Quentin Roy'

from flask import Flask
from expserver.model import Experiment, db, Measure, TrialMeasureValue, Trial
from os import path


def add_xp_measure(xp, measure_id, measure_type, trial_level, event_level, measure_name=None):
    m = Measure(id=measure_id, name=measure_name, type=measure_type, trial_level=trial_level, event_level=event_level)
    xp.measures[m.id] = m
    db.session.commit()


def update_measure(xp, id, type=None, trial_level=None, event_level=None, name=None):
    print("Measure {}'s update".format(id))
    m = xp.measures[id]
    if trial_level is not None:
        m.trial_level = trial_level
    if event_level is not None:
        m.event_level = event_level
    if name is not None:
        m.name = name
    if type is not None:
        m.type = type
    db.session.commit()


def get_app(database):
    flask_app = Flask(__name__.split('.')[0])
    flask_app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + database
    db.init_app(flask_app)
    db.app = flask_app
    return flask_app

def set_trials_count(run, number):
    for block in run.blocks:
        trials = block.trials.all()
        n = len(trials)
        if n < number:
            for _ in range(number - n):
                t = Trial(block, values=[])
                db.session.add(t)
        elif n > number:
            for t in trials:
                if t.number > number:
                    db.session.delete(t)
    # db.session.flush()
    db.session.commit()


def calculate_duration(experiment, start_measure, end_measure, duration_measure, update=False):
    for run in experiment.runs:
        for trial in run.trials:
            # print('trial {}'.format(trial.number))
            values = trial.measure_values.all()
            # ugly way to find the measures but whatever
            dur_start = [val.value for val in values if val.measure.id == start_measure]
            dur_end = [val.value for val in values if val.measure.id == end_measure]
            if dur_start and dur_end:
                exec_duration = int(dur_end[0]) - int(dur_start[0])
                result_val = [val for val in values if val.measure.id == duration_measure]
                if result_val:
                    print("The value " + duration_measure + " already exists!")
                    if update:
                        result_val[0].value = exec_duration
                else:
                    trial.measure_values.append(TrialMeasureValue(exec_duration, experiment.measures[duration_measure]))
    db.session.commit()


if __name__ == '__main__':
    database = path.abspath('../experiments.db')
    app = get_app(database)
    xp = Experiment.query.first()

    update_measure(xp, id='timestamps.executionStart', name="Execution Start TimeStamp")
    update_measure(xp, id='timestamps.executionEnd', name="Execution End TimeStamp")
    # calculate_duration(xp, 'timestamps.executionStart', 'timestamps.drawingStart', 'durations.reaction', update = True)

    # for run in xp.runs:
    #    if not run.started():
    #        set_trials_count(run, 10)