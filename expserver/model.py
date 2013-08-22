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

    factors = db.relationship('Factor', backref='experiment')

    def __init__(self, id, name, factors, author=None, description=None):
        self.name = name
        self.id = id
        self.author = author
        self.description = description
        self.factors = factors

    def __repr__(self):
        return "<{} {} (name: '{}')>" \
            .format(self.__class__.__name__, self.id, self.name)


class Run(db.Model):
    _db_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    _experiment_db_id = db.Column(db.Integer, db.ForeignKey(Experiment._db_id), nullable=False)

    id = db.Column(db.String(10))

    experiment = db.relationship(Experiment, backref='runs')

    __table_args__ = (
        db.UniqueConstraint("_experiment_db_id", "id"),
    )


    def __init__(self, id, experiment):
        self.id = id
        self.experiment = experiment

    def __repr__(self):
        return '<{} {} (experiment id: {})>' \
            .format(self.__class__.__name__, self.id, self.experiment.id)


class Block(db.Model):
    _db_id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    _run_db_id = db.Column(db.Integer, db.ForeignKey(Run._db_id), nullable=False)

    run = db.relationship(Run, backref='blocks')

    number = db.Column(db.Integer, nullable=False)
    practice = db.Column(db.Boolean)

    __table_args__ = (
        db.UniqueConstraint("_run_db_id", "number"),
    )

    def __init__(self, number, run, practice=False):
        self.number = number
        self.run = run
        self.practice = practice

    def __repr__(self):
        return '<{} {} (run id: {}, experiment id: {})>' \
            .format(self.__class__.__name__, self.num, self.run.id, self.run.experiment.id)


class Trial(db.Model):
    _db_id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    _block_db_id = db.Column(db.Integer, db.ForeignKey(Block._db_id), nullable=False)

    block = db.relationship(Block, backref='trials')

    number = db.Column(db.Integer, nullable=False)
    completed = db.Column(db.Boolean, default=False)

    __table_args__ = (
        db.UniqueConstraint("number", "_block_db_id"),
    )

    def __init__(self, number, block, experiment=None):
        self.number = number
        self.block = block
        self.experiment = experiment

    def __repr__(self):
        return '<{} {} (block number: {}, run id: {}, experiment id: {}, completed: {})>' \
            .format(self.__class__.__name__,
                    self.number,
                    self.block.number,
                    self.block.run.id,
                    self.block.run.experiment.id,
                    self.completed)


class Factor(db.Model):
    _db_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    _experiment_db_id = db.Column(db.Integer, db.ForeignKey(Experiment._db_id), nullable=False)

    id = db.Column(db.String(40), nullable=False)
    name = db.Column(db.String(200))
    type = db.Column(db.String(80))
    kind = db.Column(db.String(20))
    tag = db.Column(db.String(80))

    values = db.relationship('FactorValue', backref="factor")

    __table_args__ = (
        db.UniqueConstraint("id", "_experiment_db_id"),
    )

    def __init__(self, id, values, name=None, type=None, kind=None, tag=None):
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
                    self.experiment.id,
                    self.type,
                    self.kind,
                    self.tag)


class FactorValue(db.Model):
    _db_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    _factor_db_id = db.Column(db.String(40), db.ForeignKey(Factor._db_id))

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
        return "<{class} {id} (name: '{name}', factor id: {factor}".format({
            "id": self.id,
            "name": self.name,
            "class": self.__class__.__name__,
            "factor": self.factor.id
        })


if __name__ == '__main__':
    import os
    from random import randint

    db_uri = os.path.abspath(os.path.join(os.path.dirname(__name__), '../model_test.db'))
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////' + db_uri


    def gen_factor_values():
        return (FactorValue('v{}'.format(v_num), 'Test value number {}'.format(v_num)) for v_num in range(3))

    def gen_factors():
        for f_num in range(3):
            values = list(gen_factor_values())
            yield Factor('f{}'.format(f_num), values, 'Test Factor number {}'.format(f_num))


    def create_objs():

        for exp_num in range(2):

            exp = Experiment('E{}'.format(exp_num),
                             'Test Experiment number {}'.format(exp_num),
                             factors=list(gen_factors()))

            factor_sup = Factor('fsup', name='Factor created after the experiment', values=list(gen_factor_values()))
            exp.factors.append(factor_sup)

            for run_num in range(4):
                run = Run('S' + str(run_num), exp)
                for block in (Block(i, run) for i in range(3)):
                    db.session.add(block)
                    for trial in (Trial(i, block) for i in range(10)):
                        db.session.add(trial)
            db.session.add(exp)
            db.session.add(run)
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


    if os.path.exists(db_uri):
        db.drop_all()

    db.create_all()
    create_objs()
    read()

    # os.remove(db_uri)