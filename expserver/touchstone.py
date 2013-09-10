__author__ = 'Quentin Roy'

from xml.etree import ElementTree
from xml.dom import pulldom
from model import Experiment, Run, Trial, Factor, FactorValue, Block, db, Measure


def create_experiment(touchstone_file):
    exp_dom = ElementTree.parse(touchstone_file).getroot()
    return _parse_experiment(exp_dom)


def parse_experiment_id(touchstone_file):
    doc = pulldom.parse(touchstone_file)
    for event, node in doc:
        if event == pulldom.START_ELEMENT and node.tagName == 'experiment':
            return node.getAttribute('id')


def _nonize_string(string):
    return None if string == '' else string


def _parse_experiment(dom):
    measures = (_parse_measure(measure_dom) for measure_dom in dom.findall('measure'))
    exp = Experiment(id=dom.get('id'),
                     name=_nonize_string(dom.get('name')),
                     factors=[_parse_factor(factor_dom) for factor_dom in dom.findall('factor')],
                     author=dom.get('author'),
                     measures=dict((measure.id, measure) for measure in measures),
                     description=_nonize_string(dom.get('description')))
    for run_dom in dom.findall('run'):
        _parse_run(run_dom, exp)
    return exp


def _parse_factor(dom):
    return Factor(id=dom.get('id'),
                  name=_nonize_string(dom.get('name')),
                  type=dom.get('type'),
                  kind=_nonize_string(dom.get('kind')),
                  tag=_nonize_string(dom.get('tag')),
                  values=[_parse_value(v_dom) for v_dom in dom.findall('value')])


def _parse_measure(dom):
    trial_level = False
    event_level = False
    for attrib, value in dom.items():
        norm_value = value.strip().lower()
        if 'log' in attrib and norm_value == 'ok':
            trial_level = True
        if 'cine' in attrib and norm_value == 'ok':
            event_level = True

    return Measure(id=dom.get('id'),
                  name=_nonize_string(dom.get('name')),
                  type=dom.get('type'),
                  trial_level=trial_level,
                  event_level=event_level)


def _parse_value(dom):
    return FactorValue(
        id=dom.get('id'),
        name=_nonize_string(dom.get('name')))


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