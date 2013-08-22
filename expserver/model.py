__author__ = 'Quentin Roy'

from flask.ext.sqlalchemy import SQLAlchemy
from app import app

db = SQLAlchemy(app)


class Experiment(db.Model):
    _db_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id = db.Column(db.String(80), unique=True)
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


class Run(db.Model):
    _db_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    _experiment_db_id = db.Column(db.Integer, db.ForeignKey(Experiment._db_id), nullable=False)

    id = db.Column(db.String(10))

    experiment = db.relationship(Experiment,
                                 backref=db.backref('runs',
                                                    lazy='dynamic',
                                                    cascade="all, delete-orphan"),
                                 lazy='joined')

    __table_args__ = (
        db.UniqueConstraint("_experiment_db_id", "id"),
    )


    def __init__(self, id, experiment):
        self.id = id
        self.experiment = experiment

    def __repr__(self):
        return '<{} {} (experiment id: {})>' \
            .format(self.__class__.__name__,
                    self.id,
                    self.experiment.id if self.experiment else None)


def _free_number(number_list):
    numbers = sorted(number_list)
    i = 0
    for number in numbers:
        if number != i:
            return i
        i += 1
    return i


class Block(db.Model):
    _db_id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    _run_db_id = db.Column(db.Integer, db.ForeignKey(Run._db_id), nullable=False)

    run = db.relationship(Run,
                          backref=db.backref('blocks',
                                             lazy='dynamic',
                                             cascade="all, delete-orphan"),
                          lazy='joined')

    number = db.Column(db.Integer, nullable=False)
    practice = db.Column(db.Boolean)

    __table_args__ = (
        db.UniqueConstraint("_run_db_id", "number"),
    )

    def __init__(self, run, number=None, practice=False):
        self.practice = practice
        self.number = number if number is not None else _free_number(block.number for block in run.blocks)
        self.run = run

    def __repr__(self):
        return '<{} {} (run id: {}, experiment id: {})>' \
            .format(self.__class__.__name__,
                    self.number,
                    self.run.id if self.run is not None else None,
                    self.run.experiment.id if self.run is not None and self.run.experiment is not None else None)


class Trial(db.Model):
    _db_id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    _block_db_id = db.Column(db.Integer, db.ForeignKey(Block._db_id), nullable=False)

    block = db.relationship(Block,
                            backref=db.backref('trials',
                                               lazy='dynamic',
                                               cascade="all, delete-orphan"),
                            lazy='joined')

    number = db.Column(db.Integer, nullable=False)
    completed = db.Column(db.Boolean, default=False)

    __table_args__ = (
        db.UniqueConstraint("number", "_block_db_id"),
    )

    def __init__(self, block, number=None):
        self.number = number if number is not None else _free_number(trial.number for trial in block.trials)
        self.block = block

    def __repr__(self):
        return '<{} {} (block number: {}, run id: {}, experiment id: {}, completed: {})>' \
            .format(self.__class__.__name__,
                    self.number,
                    self.block.number if self.block else None,
                    self.block.run.id if self.block is not None and self.block.run is not None else None,
                    self.block.run.experiment.id if (self.block is not None and
                                                     self.block.run is not None and
                                                     self.block.run.experiment is not None) else None,
                    self.completed)


class Factor(db.Model):
    _db_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    _experiment_db_id = db.Column(db.Integer, db.ForeignKey(Experiment._db_id), nullable=False)

    id = db.Column(db.String(40), nullable=False)
    name = db.Column(db.String(200))
    type = db.Column(db.String(40))
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

    db_uri = os.path.abspath(os.path.join(os.path.dirname(__name__), '../model_test.db'))
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////' + db_uri


    def gen_factor_values():
        return (FactorValue('v{}'.format(v_num), 'Test value number {}'.format(v_num)) for v_num in range(3))

    def gen_factors():
        for f_num in range(3):
            values = list(gen_factor_values())
            yield Factor(id='f{}'.format(f_num),
                         values=values,
                         type=random.choice(('Integer', 'String')),
                         name='Test Factor number {}'.format(f_num))

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
                for _ in range(3):
                    block = Block(run)
                    for _ in range(10):
                        Trial(block)
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

            print('get factor f1: ' + repr(exp.get_factor('f1')))


    if os.path.exists(db_uri):
        db.drop_all()

    db.create_all()
    create_objs()
    read()

    # os.remove(db_uri)