# Test file

import os
import random
from flask import Flask
from __init__ import Experiment, Run, Block, Trial, Factor
from __init__ import FactorValue, Measure, Event, TrialMeasureValue
from __init__ import EventMeasureValue
from model import db


def gen_factor_values():
    return (
        FactorValue("v{}".format(v_num), "Test value number {}".format(v_num))
        for v_num in range(3)
    )


def gen_factors(num=3):
    for f_num in range(num):
        values = list(gen_factor_values())
        yield Factor(
            id="f{}".format(f_num),
            values=values,
            type=random.choice(("Integer", "String")),
            name="Test Factor number {}".format(f_num),
        )


def gen_measures(num=8):
    for m_num in range(num):
        levels = random.choice(((True, True), (True, False), (False, True)))
        yield Measure(
            id="m{}".format(m_num),
            type=random.choice(("Integer", "String")),
            name="Test Measure number {}".format(m_num),
            trial_level=levels[0],
            event_level=levels[1],
        )


def random_values(experiment, number):
    factors = random.sample(experiment.factors.all(), number)
    return [random.choice(factor.values) for factor in factors]


def create_objs():

    for exp_num in range(2):
        measures = dict((m.id, m) for m in gen_measures())
        trial_measure = Measure(
            id="trial_measure",
            type=random.choice(("Integer", "String")),
            trial_level=True,
        )
        measures[trial_measure.id] = trial_measure

        exp = Experiment(
            "E{}".format(exp_num),
            "Test Experiment number {}".format(exp_num),
            factors=list(gen_factors()),
            measures=measures,
        )

        event_measure = Measure(
            id="event_measure",
            type=random.choice(("Integer", "String")),
            event_level=True,
        )
        exp.measures[event_measure.id] = event_measure

        factor_sup = Factor(
            "fsup",
            type="Integer",
            name="Factor created after the experiment",
            values=list(gen_factor_values()),
        )
        exp.factors.append(factor_sup)

        for run_num in range(3):
            run = Run("S" + str(run_num), exp)
            for block_num in range(9):
                block = Block(
                    run, practice=block_num % 3 == 0, values=random_values(exp, 2)
                )
                for i in range(10):
                    trial = Trial(block, values=random_values(exp, 2))
                    trial.measure_values.append(
                        TrialMeasureValue(random.randint(0, 1000), trial_measure)
                    )
                    for j in range(5):
                        event = Event(
                            [
                                EventMeasureValue(
                                    "lorem value {}".format(random.randint(0, 1000)),
                                    event_measure,
                                )
                            ],
                            number=(i + 1) * j + j,
                        )
                        trial.events.append(event)

        db.session.add(exp)
        db.session.commit()


def read():
    for exp in Experiment.query.all():
        print("------ " + repr(exp) + " -------")
        print("factors:")
        for factor in exp.factors:
            print("  " + repr(factor))
        print("trials:")
        for run in exp.runs:
            for trial in run.trials:
                print("  " + repr(trial))

        print("Get factor f1: " + repr(exp.get_factor("f1")))
        print(
            "Last block measured block num: {}".format(
                exp.runs[0].blocks[-1].measured_block_number()
            )
        )


if __name__ == "__main__":
    app = Flask(os.path.splitext(__name__)[0])
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite://"
    db.init_app(app)

    with app.test_request_context():
        db.create_all()
        create_objs()
        read()
