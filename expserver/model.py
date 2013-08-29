__author__ = 'Quentin Roy'

from flask.ext.sqlalchemy import SQLAlchemy, BaseQuery
from datetime import datetime
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

    def __init__(self, id, name, factors, author=None, description=None):
        self.name = name
        self.id = id
        self.author = author
        self.description = description
        self.factors = factors

    def __repr__(self):
        return "<{} {} (name: '{}')>" \
            .format(self.__class__.__name__, self.id, self.name)

    def get_factor(self, factor_id):
        return self.factors.filter_by(id=factor_id).one()

    def get_run(self, run_id):
        return self.runs.filter_by(id=run_id).one()


class Run(db.Model):
    class RunQuery(BaseQuery):
        def get_by_id(self, run_id, experiment_id):
            return Run.query.filter(Run.id == run_id) \
                .filter(Experiment.id == experiment_id).one()

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
    db.Column('factor_value_db_id', db.Integer, db.ForeignKey('factor_value._db_id'))
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
    values = db.relationship('FactorValue', secondary=block_values)

    __table_args__ = (
        db.UniqueConstraint("_run_db_id", "number"),
    )

    @property
    def experiment(self):
        return self.run.experiment if self.run is not None else None

    def __init__(self, run, values, number=None, practice=False):
        self.practice = practice
        self.number = number if number is not None else _free_number(block.number for block in run.blocks)
        self.run = run
        self.values = values

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


trial_values = db.Table(
    'trial_values',
    db.Column('trial_db_id', db.Integer, db.ForeignKey('trial._db_id')),
    db.Column('factor_value_db_id', db.Integer, db.ForeignKey('factor_value._db_id'))
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

    values = db.relationship('FactorValue', secondary=trial_values)
    number = db.Column(db.Integer, nullable=False)
    completion_date = db.Column(db.DateTime, index=True)

    __table_args__ = (
        db.UniqueConstraint("number", "_block_db_id"),
    )

    @property
    def completed(self):
        return self.completion_date is not None

    def set_completed(self):
        previous = self.previous_trial()
        if self.completed:
            raise ExperimentProgressError("Trial already completed.")
        if previous is not None and not self.previous_trial().completed:
            raise ExperimentProgressError("Cannot complete trial {}: previous trial is not completed yet. "
                                          "Trials must be completed sequentially.".format(repr(self)))
        self.completion_date = datetime.today()

    def previous_trial(self):
        if self.number <= 0:
            if self.block.number > 0:
                block = Block.query.get_by_number(self.block.number - 1, self.run.id, self.experiment.id)
                return block.trials.filter(Trial.number == block.length() - 1).one()
        else:
            return Trial.query.get_by_number(self.number - 1, self.block.number, self.run.id, self.experiment.id)

    @property
    def experiment(self):
        run = self.run
        return run.experiment if run is not None else None

    @property
    def run(self):
        return self.block.run if self.block is not None else None

    def iter_all_values(self):
        for value in self.values:
            yield value
        for value in self.block.values:
            yield value

    def __init__(self, block, values, number=None):
        self.number = number if number is not None else _free_number(trial.number for trial in block.trials)
        self.block = block
        self.values = values

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

    id = db.Column(db.String(80), nullable=False)
    name = db.Column(db.String(200))
    type = db.Column(db.String(80))
    kind = db.Column(db.String(20))
    tag = db.Column(db.String(80))

    values = db.relationship('FactorValue',
                             backref=db.backref('factor', lazy='joined'),
                             lazy='joined',
                             cascade="all, delete-orphan")

    __table_args__ = (
        db.UniqueConstraint("id", "_experiment_db_id"),
    )

    def __init__(self, id, values, type, name=None, kind=None, tag=None):
        self.id = id
        self.name = name
        self.type = type
        self.kind = kind
        self.tag = tag
        self.values = values

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
    _factor_db_id = db.Column(db.String(40), db.ForeignKey(Factor._db_id), nullable=False)

    id = db.Column(db.String(10), nullable=False)
    name = db.Column(db.String(200))
    value = db.Column(db.Text)

    __table_args__ = (
        db.UniqueConstraint("id", "_factor_db_id"),
    )

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

    def gen_factors():
        for f_num in range(3):
            values = list(gen_factor_values())
            yield Factor(id='f{}'.format(f_num),
                         values=values,
                         type=random.choice(('Integer', 'String')),
                         name='Test Factor number {}'.format(f_num))

    def random_values(experiment, number):
        factors = random.sample(experiment.factors.all(), number)
        return [random.choice(factor.values) for factor in factors]

    def create_objs():

        for exp_num in range(2):

            exp = Experiment('E{}'.format(exp_num),
                             'Test Experiment number {}'.format(exp_num),
                             factors=list(gen_factors()))

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
                        Trial(block, values=random_values(exp, 2))
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
                for block in run.blocks:
                    for trial in block.trials:
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