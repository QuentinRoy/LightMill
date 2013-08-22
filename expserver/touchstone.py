__author__ = 'Quentin Roy'

from xml.etree import ElementTree
from model import Experiment, Run, Trial, Factor, FactorValue, Block


def create_experiment(touchstone_file, session):
    exp_dom = ElementTree.parse(touchstone_file).getroot()
    expe = _parse_experiment(exp_dom, session)
    session.add(expe)


def _nonizeString(string):
    return None if string == '' else string


def _parse_experiment(dom):
    exp = Experiment(id=dom.get('id'),
                     name=_nonizeString(dom.get('name')),
                     factors=[_parse_factor(factor_dom) for factor_dom in dom.findall('factor')],
                     author=dom.get('author'),
                     description=_nonizeString(dom.get('description')))
    for run_dom in dom.findall('run'):
        _parse_run(run_dom, exp)
    return exp


def _parse_factor(dom):
    return Factor(id=dom.get('id'),
                  name=_nonizeString(dom.get('name')),
                  type=dom.get('type'),
                  kind=_nonizeString(dom.get('kind')),
                  tag=_nonizeString(dom.get('tag')),
                  values=[_parse_value(v_dom) for v_dom in dom.findall('value')])


def _parse_value(dom):
    return FactorValue(
        id=dom.get('id'),
        name=_nonizeString(dom.get('name')))


def _parse_run(dom, experiment):
    run = Run(id=dom.get('id'),
              experiment=experiment)

    for block_dom in dom.iter():
        if block_dom.tag in ('block', 'practice'):
            _parse_block(block_dom, run)
    return run


def _parse_factor_values_string(values_string, experiment):
    value_strings = values_string.split(',')
    value_seq = (value_string.split('=', 1) for value_string in value_strings if value_string != "")
    values = []
    for factor_id, value_id in value_seq:
        # we cannot use a query so we have to filter by hand
        factor = next(factor for factor in experiment.factors if factor.id == factor_id)
        value = next(value for value in factor.values if value.id == value_id)
        values.append(value)
    return values


def _parse_block(dom, run):
    practice = dom.tag == 'practice'
    values = _parse_factor_values_string(dom.get('values'), run.experiment)
    block = Block(run=run,
                  practice=practice,
                  values=values)

    for trial_dom in dom.findall('trial'):
        _parse_trial(trial_dom, block)
    return block


def _parse_trial(dom, block):
    num = dom.get('number')
    values = _parse_factor_values_string(dom.get('values'), block.experiment)
    trial = Trial(block,
                  number=int(num) if num is not None else None,
                  values=values)
    return trial


if __name__ == '__main__':
    from app import app
    from model import db
    import os

    db_uri = os.path.abspath(os.path.join(os.path.dirname(__name__), '../parse_test.db'))
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////' + db_uri

    touchstone_file = os.path.abspath(os.path.join(os.path.dirname(__name__), '../experiment.xml'))

    if os.path.exists(db_uri):
        db.drop_all()

    db.create_all()
    create_experiment(touchstone_file, db.session)
    db.session.commit()