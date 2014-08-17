from sqlalchemy.orm.exc import NoResultFound

__author__ = 'Quentin Roy'

from flask.ext.sqlalchemy import SQLAlchemy, BaseQuery
from datetime import datetime
from sqlalchemy.ext.declarative.api import AbstractConcreteBase, declared_attr
from sqlalchemy.orm.collections import attribute_mapped_collection
# import logging

db = SQLAlchemy()

# logging.basicConfig(filename="/Users/quentin/Workspace/Dev/xpserver/dbrequests.log", filemode='w', level=logging.INFO)
# logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

class ExperimentProgressError(Exception):
    pass


class Experiment(db.Model):
    class ExperimentQuery(BaseQuery):
        def get_by_id(self, experiment_id):
            return Experiment.query.filter(Experiment.id == experiment_id).one()

    query_class = ExperimentQuery

    _db_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id = db.Column(db.String(80), unique=True, index=True)
    name = db.Column(db.String(200))
    author = db.Column(db.String(200), nullable=True)
    description = db.Column(db.Text, nullable=True)

    factors = db.relationship('Factor',
                              backref=db.backref('experiment', lazy='joined'),
                              lazy='dynamic',
                              cascade="all, delete-orphan")

    measures = db.relationship('Measure',
                               backref=db.backref('experiment', lazy='joined'),
                               cascade="all, delete-orphan",
                               collection_class=attribute_mapped_collection('id'))

    def __init__(self, id, name, factors, measures, author=None, description=None):
        self.name = name
        self.id = id
        self.author = author
        self.description = description
        self.factors = factors
        self.measures = measures

    def __repr__(self):
        return "<{} {} (name: '{}')>" \
            .format(self.__class__.__name__, self.id, self.name)

    def get_factor(self, factor_id):
        return self.factors.filter_by(id=factor_id).one()

    def get_run(self, run_id):
        return self.runs.filter_by(id=run_id).one()

    def trial_measures(self):
        return self.measures.filter('Measure.trial_level' == True)

    def event_measures(self):
        return self.measures.filter('Measure.event_level' == True)


class Run(db.Model):
    class RunQuery(BaseQuery):
        def get_by_id(self, run_id, experiment_id):
            return Run.query.join(Experiment).filter(Run.id == run_id).filter(Experiment.id == experiment_id).one()

    query_class = RunQuery

    _db_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    _experiment_db_id = db.Column(db.Integer, db.ForeignKey(Experiment._db_id), nullable=False)

    id = db.Column(db.String(20), index=True)

    token = db.Column(db.String(20), unique=True)

    experiment = db.relationship(Experiment,
                                 backref=db.backref('runs',
                                                    lazy='dynamic',
                                                    cascade='all, delete-orphan'),
                                 lazy='joined')

    __table_args__ = (
        db.UniqueConstraint("_experiment_db_id", "id"),
        db.Index('index_xp_runs', '_experiment_db_id')
    )

    def __init__(self, id, experiment):
        self.id = id
        self.experiment = experiment

    @property
    def locked(self):
        return self.token is not None

    @property
    def trials(self):
        return Trial.query.options(db.joinedload(Trial.block)) \
            .join(Block, Run).order_by(Block.number, Trial.number) \
            .filter(Block.run == self)

    def current_trial(self):
        return self.trials.filter(Trial.completion_date == None).first()

    def __repr__(self):
        return '<{} {} (experiment id: {}, token: {})>' \
            .format(self.__class__.__name__,
                    self.id,
                    self.experiment.id if self.experiment else None,
                    self.token)

    def completed(self):
        exist_query = self.trials.filter(Trial.completion_date == None).exists()
        session_query = db.session.query(exist_query)
        completed = not session_query.scalar()
        return completed

    def started(self):
        exist_query = self.trials.filter(Trial.completion_date != None).exists()
        started = db.session.query(exist_query).scalar()
        return started

    def trial_count(self):
        return self.trials.count()

    def block_count(self):
        return self.blocks.count()

    def get_block(self, block_number):
        return self.blocks.filter(Block.number == block_number).one()

    def status(self):
        if self.completed():
            return "completed"
        elif self.started():
            return "started"
        else:
            return "unstarted"

    def previous(self):
        prev = None
        for run in self.experiment.runs.order_by(Run.id):
            if run == self:
                return prev
            else:
                prev = run

    def next(self):
        prev = None
        for run in self.experiment.runs.order_by(Run.id):
            if prev == self:
                return run
            else:
                prev = run


def _free_number(number_list):
    numbers = sorted(number_list)
    i = 0
    for number in numbers:
        if number != i:
            return i
        i += 1
    return i


block_values = db.Table(
    'block_values',
    db.Column('block_db_id', db.Integer, db.ForeignKey('block._db_id')),
    db.Column('factor_value_db_id', db.Integer, db.ForeignKey('factor_value._db_id')),
    db.Index('index_block_factor_values', 'block_db_id')
)


class Block(db.Model):
    class BlockQuery(BaseQuery):
        def get_by_number(self, block_number, run_id, experiment_id):
            return Block.query \
                .join(Run, Experiment) \
                .filter(Block.number == block_number,
                        Experiment.id == experiment_id,
                        Run.id == run_id).one()

    query_class = BlockQuery

    _db_id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    _run_db_id = db.Column(db.Integer, db.ForeignKey(Run._db_id), nullable=False, index=True)

    run = db.relationship(Run,
                          backref=db.backref('blocks',
                                             lazy='dynamic',
                                             cascade="all, delete-orphan",
                                             order_by='Block.number'),
                          lazy='joined')

    number = db.Column(db.Integer, nullable=False)
    practice = db.Column(db.Boolean)
    factor_values = db.relationship('FactorValue', secondary=block_values)

    __table_args__ = (
        db.UniqueConstraint("_run_db_id", "number"),
        db.Index("index_run_blocks", "_run_db_id")
    )

    @property
    def experiment(self):
        return self.run.experiment if self.run is not None else None

    def __init__(self, run, values, number=None, practice=False):
        self.practice = practice
        self.number = number if number is not None else _free_number(block.number for block in run.blocks)
        self.run = run
        self.factor_values = values

    def __repr__(self):
        return '<{} {} (run id: {}, experiment id: {}>' \
            .format(self.__class__.__name__,
                    self.number,
                    self.run.id if self.run is not None else None,
                    self.run.experiment.id if self.run is not None and self.run.experiment is not None else None)

    def measure_block_number(self):
        if not self.practice:
            i = 0
            for block in self.run.blocks.order_by(Block.number):
                if block is self:
                    return i
                elif not block.practice:
                    i += 1

    def length(self):
        return self.trials.count()


trial_factor_values = db.Table(
    'trial_factor_values',
    db.Column('trial_db_id', db.Integer, db.ForeignKey('trial._db_id')),
    db.Column('factor_value_db_id', db.Integer, db.ForeignKey('factor_value._db_id')),
    db.Index('index_trial_factor_values', 'trial_db_id')
)


class Trial(db.Model):
    class TrialQuery(BaseQuery):
        def get_by_number(self, trial_number, block_number, run_id, experiment_id):
            return Trial.query \
                .join(Block, Run, Experiment) \
                .filter(Trial.number == trial_number,
                        Block.number == block_number,
                        Experiment.id == experiment_id,
                        Run.id == run_id).one()

    query_class = TrialQuery

    _db_id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    _block_db_id = db.Column(db.Integer, db.ForeignKey(Block._db_id), nullable=False, index=True)

    block = db.relationship(Block,
                            backref=db.backref('trials',
                                               lazy='dynamic',
                                               cascade="all, delete-orphan",
                                               order_by='Trial.number'),
                            lazy='joined')

    factor_values = db.relationship('FactorValue', secondary=trial_factor_values)
    number = db.Column(db.Integer, nullable=False)
    completion_date = db.Column(db.DateTime)
    measure_values = db.relationship('TrialMeasureValue',
                                     cascade="all, delete-orphan",
                                     backref=db.backref('trial'),
                                     lazy='dynamic')

    events = db.relationship('Event',
                             cascade="all, delete-orphan",
                             backref=db.backref('trial'),
                             lazy="dynamic",
                             order_by='Event.number')

    __table_args__ = (
        db.UniqueConstraint("number", "_block_db_id"),
        db.Index("index_block_trials", "_block_db_id")
    )


    @property
    def completed(self):
        return self.completion_date is not None

    def set_completed(self):
        previous = self.previous()
        if self.completed:
            raise ExperimentProgressError("Trial already completed.")
        if previous is not None and not previous.completed:
            raise ExperimentProgressError("Cannot complete trial {}: previous trial is not completed yet. "
                                          "Trials must be completed sequentially.".format(repr(self)))
        self.completion_date = datetime.today()

    def previous(self):
        if self.number > 0:
            return Trial.query.get_by_number(self.number - 1, self.block.number, self.run.id, self.experiment.id)
        elif self.block.number > 0:
            block = Block.query.get_by_number(self.block.number - 1, self.run.id, self.experiment.id)
            return block.trials.filter(Trial.number == block.length() - 1).one()

    def next(self):
        if self.number + 1 < self.block.length():
            return Trial.query.get_by_number(self.number + 1, self.block.number, self.run.id, self.experiment.id)
        elif self.block.number + 1 < self.run.block_count():
            return Trial.query.get_by_number(0, self.block.number + 1, self.run.id, self.experiment.id)

    @property
    def experiment(self):
        run = self.run
        return run.experiment if run is not None else None

    @property
    def run(self):
        return self.block.run if self.block is not None else None

    def iter_all_factor_values(self):
        unseen = set(self.experiment.factors)
        for value in self.factor_values:
            unseen.remove(value.factor)
            yield value
        for value in self.block.factor_values:
            unseen.remove(value.factor)
            yield value
        for factor in unseen:
            if factor.default_value:
                yield factor.default_value


    def __init__(self, block, values, number=None):
        self.number = number if number is not None else _free_number(trial.number for trial in block.trials)
        self.block = block
        self.factor_values = values

    def record_measure_value(self, measure_id, value):
        measure = Measure.query.get_by_id(measure_id, self.experiment.id)
        measure_value = TrialMeasureValue(value, measure)
        self.measure_values[measure_id] = measure_value

    def __repr__(self):
        return '<{} {} (block number: {}, run id: {}, experiment id: {}, completion date: {})>' \
            .format(self.__class__.__name__,
                    self.number,
                    self.block.number if self.block else None,
                    self.block.run.id if self.block is not None and self.block.run is not None else None,
                    self.block.run.experiment.id if (self.block is not None and
                                                     self.block.run is not None and
                                                     self.block.run.experiment is not None) else None,
                    self.completion_date.ctime() if self.completion_date else None)


class Factor(db.Model):
    _db_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    _experiment_db_id = db.Column(db.Integer, db.ForeignKey(Experiment._db_id), nullable=False)
    _default_value_db_id = db.Column(db.Integer, db.ForeignKey('factor_value._db_id',
                                                               use_alter=True,
                                                               name="fk_default_value"))

    id = db.Column(db.String(80), nullable=False)
    name = db.Column(db.String(200))
    type = db.Column(db.String(80))
    kind = db.Column(db.String(20))
    tag = db.Column(db.String(80))

    default_value = db.relationship('FactorValue',
                                    uselist=False,
                                    post_update=True,
                                    foreign_keys=[_default_value_db_id])

    __table_args__ = (
        db.UniqueConstraint("id", "_experiment_db_id"),
        db.Index("index_xp_factors", "_experiment_db_id")
    )

    def __init__(self, id, values, type, name=None, kind=None, tag=None, default_value=None):
        if default_value is not None and default_value not in values:
            raise "Factor default value must be in values"
        self.id = id
        self.name = name
        self.type = type
        self.kind = kind
        self.tag = tag
        self.values = values
        self.default_value = default_value

    def __repr__(self):
        return "<{} {} (name: '{}', experiment id: {}, type: {}, kind: {}, tag: {}>" \
            .format(self.__class__.__name__,
                    self.id,
                    self.name,
                    self.experiment.id if self.experiment is not None else None,
                    self.type,
                    self.kind,
                    self.tag)


class FactorValue(db.Model):
    _db_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    _factor_db_id = db.Column(db.Integer, db.ForeignKey(Factor._db_id), nullable=False)

    id = db.Column(db.String(40), nullable=False)
    name = db.Column(db.String(200))

    factor = db.relationship('Factor',
                             backref=db.backref('values',
                                                lazy='joined'),
                             single_parent=True,
                             lazy='joined',
                             foreign_keys=[_factor_db_id],
                             cascade="all, delete-orphan")

    __table_args__ = (
        db.UniqueConstraint('id', '_factor_db_id'),
        db.Index('index_factor_factorvalue', '_factor_db_id')
    )

    @property
    def is_default(self):
        return self.factor.default_value is self

    def __init__(self, id, name=None):
        self.id = id
        self.name = name

    def __repr__(self):
        return "<{class_name} {id} (name: '{name}', factor id: {factor}>".format(
            id=self.id,
            name=self.name,
            class_name=self.__class__.__name__,
            factor=self.factor.id if self.factor is not None else None
        )


class Measure(db.Model):
    class MeasureQuery(BaseQuery):
        def get_by_id(self, measure_id, experiment_id):
            return Measure.query \
                .join(Experiment) \
                .filter(Measure.id == measure_id,
                        Experiment.id == experiment_id).one()

    query_class = MeasureQuery

    _db_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    _experiment_db_id = db.Column(db.Integer, db.ForeignKey(Experiment._db_id), nullable=False)

    id = db.Column(db.String(80), nullable=False)
    trial_level = db.Column(db.Boolean, nullable=False)
    event_level = db.Column(db.Boolean, nullable=False)
    name = db.Column(db.String(200))
    type = db.Column(db.String(80))

    __table_args__ = (
        db.CheckConstraint("trial_level OR event_level", name='at_least_one'),
        # db.UniqueConstraint("id", "_experiment_db_id"),
        db.Index('index_measure', 'id', '_experiment_db_id', unique=True),
        # db.Index('index_xp_measure', '_experiment_db_id')
    )

    def __init__(self, id, type, event_level=False, trial_level=False, name=None):
        self.id = id
        self.name = name
        self.type = type
        self.event_level = event_level
        self.trial_level = trial_level

    def levels(self):
        levels = []
        if self.trial_level:
            levels.append('trial')
        if self.event_level:
            levels.append('event')
        return levels

    def __repr__(self):
        levels = self.levels()
        return "<{} {} (name: '{}', experiment id: {}, type: {}, level{}: {})>" \
            .format(self.__class__.__name__,
                    self.id,
                    self.name,
                    self.experiment.id if self.experiment is not None else None,
                    self.type,
                    's' if len(levels) > 1 else '',
                    ' and '.join(levels))


class Event(db.Model):
    _db_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    _trial_db_id = db.Column(db.Integer, db.ForeignKey(Trial._db_id), nullable=False)
    number = db.Column(db.Integer, nullable=False)
    measure_values = db.relationship('EventMeasureValue',
                                     cascade="all, delete-orphan",
                                     backref=db.backref('event'),
                                     lazy='joined',
                                     collection_class=attribute_mapped_collection('measure.id'))

    def __init__(self, measure_values, number, trial=None):
        for measure_value in measure_values:
            self.measure_values[measure_value.measure.id] = measure_value
        self.number = number
        self.trial = trial


    __table_args__ = (
        db.UniqueConstraint('number', '_trial_db_id'),
        db.Index('index_trial_events', '_trial_db_id')
    )


class MeasureValue(AbstractConcreteBase, db.Model):
    _db_id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    @declared_attr
    def _measure_db_id(cls):
        return db.Column(db.Integer, db.ForeignKey(Measure._db_id), nullable=False)

    value = db.Column(db.Text, nullable=False)

    @declared_attr
    def measure(cls):
        return db.relationship(Measure, lazy='joined')

    def __init__(self, value, measure, experiment_id=None):
        if not isinstance(measure, Measure):
            try:
                measure = Measure.query.get_by_id(measure, experiment_id)
            except NoResultFound:
                raise NoResultFound("Cannot find target measure: " + measure)

        self.measure = measure
        self.value = value

    def __repr__(self):
        return "<{} of {} (value: '{}')>".format(self.__class__.__name__,
                                                 self.measure.id,
                                                 self.value)


class MeasureLevelError(ValueError):
    pass


class TrialMeasureValue(MeasureValue):
    __tablename__ = 'trial_measure_value'
    __mapper_args__ = {'concrete': True,
                       'polymorphic_identity': 'trial_measure_value'}
    _trial_db_id = db.Column(db.Integer, db.ForeignKey(Trial._db_id), nullable=False)

    __table_args__ = (
        db.UniqueConstraint("_measure_db_id", "_trial_db_id"),
        db.Index('index_trial_measure_values', '_trial_db_id'),
    )

    def __init__(self, *args, **kwargs):
        super(TrialMeasureValue, self).__init__(*args, **kwargs)
        if not self.measure.trial_level:
            raise MeasureLevelError("Associated measure ({}) is not at the trial level.".format(self.measure.id))


class EventMeasureValue(MeasureValue):
    __tablename__ = 'event_measure_value'
    __mapper_args__ = {'concrete': True,
                       'polymorphic_identity': 'event_measure_value'}
    _event_db_id = db.Column(db.Integer, db.ForeignKey(Event._db_id), nullable=False)

    __table_args__ = (
        db.UniqueConstraint("_measure_db_id", "_event_db_id"),
        db.Index('index_event_measure_values', '_event_db_id'),
    )

    def __init__(self, *args, **kwargs):
        super(EventMeasureValue, self).__init__(*args, **kwargs)
        if not self.measure.event_level:
            raise MeasureLevelError("Associated measure ({}) is not at the event level.".format(self.measure.id))


#################################
#                               #
#           TEST                #
#                               #
#################################

if __name__ == '__main__':
    import os
    import random
    from flask import Flask

    print('Model Debug')

    def gen_factor_values():
        return (FactorValue('v{}'.format(v_num), 'Test value number {}'.format(v_num)) for v_num in range(3))

    def gen_factors(num=3):
        for f_num in range(num):
            values = list(gen_factor_values())
            yield Factor(id='f{}'.format(f_num),
                         values=values,
                         type=random.choice(('Integer', 'String')),
                         name='Test Factor number {}'.format(f_num))

    def gen_measures(num=8):
        for m_num in range(num):
            levels = random.choice(((True, True), (True, False), (False, True)))
            yield Measure(id='m{}'.format(m_num),
                          type=random.choice(('Integer', 'String')),
                          name='Test Measure number {}'.format(m_num),
                          trial_level=levels[0],
                          event_level=levels[1])

    def random_values(experiment, number):
        factors = random.sample(experiment.factors.all(), number)
        return [random.choice(factor.values) for factor in factors]

    def create_objs():

        for exp_num in range(2):
            measures = list(gen_measures())
            trial_measure = Measure(id='trial_measure',
                                    type=random.choice(('Integer', 'String')),
                                    trial_level=True)
            event_measure = Measure(id='event_measure',
                                    type=random.choice(('Integer', 'String')),
                                    event_level=True)
            measures.append(trial_measure)

            exp = Experiment('E{}'.format(exp_num),
                             'Test Experiment number {}'.format(exp_num),
                             factors=list(gen_factors()),
                             measures=measures)
            exp.measures.append(event_measure)

            factor_sup = Factor('fsup',
                                type='Integer',
                                name='Factor created after the experiment',
                                values=list(gen_factor_values()))
            exp.factors.append(factor_sup)

            for run_num in range(3):
                run = Run('S' + str(run_num), exp)
                for block_num in range(9):
                    block = Block(run,
                                  practice=block_num % 3 == 0,
                                  values=random_values(exp, 2))
                    for _ in range(10):
                        trial = Trial(block, values=random_values(exp, 2))
                        trial.measure_values.append(TrialMeasureValue(random.randint(0, 1000), trial_measure))
                        for _ in range(5):
                            event = Event(
                                [EventMeasureValue("lorem value {}".format(random.randint(0, 1000)), event_measure)])
                            trial.add_event(event)

            db.session.add(exp)
            db.session.commit()

    def read():
        for exp in Experiment.query.all():
            print('------ ' + repr(exp) + ' -------')
            print('factors:')
            for factor in exp.factors:
                print('  ' + repr(factor))
            print('trials:')
            for run in exp.runs:
                for trial in run.trials:
                    print('  ' + repr(trial))

            print('Get factor f1: ' + repr(exp.get_factor('f1')))
            print('Last block measured block num: {}'.format(exp.runs[0].blocks[-1].measure_block_number()))

    db_uri = os.path.abspath(os.path.join(os.path.dirname(__name__), '../model_test.db'))
    app = Flask(os.path.splitext(__name__)[0])
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////' + db_uri
    db.init_app(app)

    with app.test_request_context():
        if os.path.exists(db_uri):
            db.drop_all()

        db.create_all()
        create_objs()
        read()

        # os.remove(db_uri)
