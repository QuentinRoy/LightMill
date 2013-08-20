__author__ = 'Quentin Roy'

from xml.etree import ElementTree
from .record import Measure, Factor
from .loger import Loger
from collections import OrderedDict


class _ExpElt(object):
    def status(self):
        if not self.started():
            return "unstarted"
        elif not self.completed():
            return "uncompleted"
        else:
            return "completed"

    @staticmethod
    def _parse_values(values_string):
        value_strings = values_string.split(',')
        value_seq = (value_string.split('=', 1) for value_string in value_strings if value_string != "")
        return {key: value for (key, value) in value_seq}


class Experiment(_ExpElt):
    def __init__(self, config_file, log_directory):
        self._dom = ElementTree.parse(config_file).getroot()
        self._id = self._dom.get("id")
        self._name = self._dom.get("name")
        self._author = self._dom.get("author")

        # create all runs
        self._runs = OrderedDict()
        for run_dom in self._dom.findall('run'):
            run = Run(run_dom, self)
            self._runs[run.id] = run

        self._measures = [Measure(dom=m_dom) for m_dom in self._dom.findall('measure')]
        self._factors = [Factor(f_dom) for f_dom in self._dom.findall("factor")]

        self._loger = Loger(self, log_directory)

    def run_ids(self):
        return self._runs.keys()

    def iter_runs(self):
        return self._runs.itervalues()

    @property
    def id(self):
        return self._id

    def get_run(self, run_id):
        return self._runs[run_id]

    def __len__(self):
        return len(self._runs)

    def completed(self):
        for run in self.iter_runs():
            if not run.completed():
                return False
        return True

    def started(self):
        for run in self.iter_runs():
            if run.started():
                return True
        return False

    def next_run(self):
        for run in self.iter_runs():
            if not run.started():
                return run

    @property
    def name(self):
        return self._name

    @property
    def author(self):
        return self._author

    @property
    def loger(self):
        return self._loger

    def measures(self):
        return self._measures[:]

    def factors(self):
        return self._factors[:]

    def properties(self):
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status(),
            "factors": OrderedDict((factor.id, factor.type) for factor in self._factors),
            "measures": OrderedDict((measure.id, measure.type) for measure in self._measures),
            "run_status": OrderedDict((run.id, run.status()) for run in self.iter_runs())
        }


class Run(_ExpElt):
    def __init__(self, dom, xp):
        self._dom = dom
        self._xp = xp
        self._id = self._dom.get("id")

        # create the blocks
        self._blocks = []
        for block_dom in self._dom.iter():
            if block_dom.tag in ("block", "practice"):
                self._blocks.append(Block(block_dom, self))

    @property
    def id(self):
        return self._id

    @property
    def xp(self):
        return self._xp

    def get_block(self, block_num):
        return self._blocks[block_num]

    def iter_blocks(self):
        return (block for block in self._blocks)

    def __len__(self):
        sum = 0
        for block in self._blocks:
            sum += len(block)
        return sum

    def block_count(self):
        return len(self._blocks)

    def trial_count(self):
        return sum(len(block) for block in self.iter_blocks())

    def completed(self):
        for block in self.iter_blocks():
            if not block.completed():
                return False
        return True

    def started(self):
        for block in self.iter_blocks():
            if block.started():
                return True
        return False

    def iter_trials(self):
        for block in self.iter_blocks():
            for trial in block.iter_trials():
                yield trial

    def current_trial(self):
        for trial in self.iter_trials():
            if not trial.completed():
                return trial

    def properties(self):
        current_trial = self.current_trial()
        return {
            "id": self.id,
            "block_count": self.block_count(),
            "trial_count": self.trial_count(),
            "status": self.status(),
            "current_trial": {
                "block": current_trial.block.num,
                "num": current_trial.num
            }
        }


class Block(_ExpElt):
    def __init__(self, dom, run):
        self._dom = dom
        self._factor_values = self._parse_values(self._dom.get("values"))
        self._run = run
        self._trials = [Trial(trial_dom, self) for trial_dom in self._dom.findall('trial')]

    def factor_values(self):
        return self._factor_values.copy()

    def properties(self):
        props = {
            "num": self.num(),
            "run_id": self.run.id,
            "xp_id": self.xp.id,
            "trial_count": len(self),
            "block_count": self.run.block_count(),
            "practice": self.is_practice,
            "status": self.status()
        }
        props.update(self._factor_values)
        return props

    def num(self):
        num = 0
        for block in self.run.iter_blocks():
            if block is self:
                return num
            else:
                num += 1

    @property
    def is_practice(self):
        return self._dom.tag == "practice"

    @property
    def run(self):
        return self._run

    @property
    def xp(self):
        return self.run.xp

    def get_trial(self, trial_num):
        return self._trials[trial_num]

    def iter_trials(self):
        return (trial for trial in self._trials)

    def __len__(self):
        return len(self._trials)

    def completed(self):
        for trial in self.iter_trials():
            if not trial.completed():
                return False
        return True

    def started(self):
        for trial in self.iter_trials():
            if trial.started():
                return True
        return False


class Trial(_ExpElt):
    def __init__(self, dom, block):
        self._dom = dom
        self._factor_values = self._parse_values(self._dom.get("values"))
        self._block = block
        self.results = None
        self.events = []

    @property
    def block(self):
        return self._block

    def num(self):
        num = 0
        for trial in self.block.iter_trials():
            if trial is self:
                return num
            num += 1

    def global_num(self):
        num = self.num()
        for block in self.run.iter_blocks():
            if block is self.block:
                return num
            num += len(block)

    def factor_values(self):
        # block values are copied before being returned
        values = self.block.factor_values()
        values.update(self._factor_values)
        return values

    def properties(self):
        props = self.block.properties()
        props.update({
            "block": props["num"],
            "num": self.num(),
            "global_num": self.global_num(),
            "status": self.status()
        })
        props.update(self.factor_values())
        return props

    @property
    def run(self):
        return self.block.run

    @property
    def xp(self):
        return self.run.xp

    def completed(self):
        return False

    def started(self):
        return False

    def previous_trial(self):
        prev = None
        for trial in self.block.iter_trials():
            if trial == self:
                return prev
            else:
                prev = trial

    def next_trial(self):
        num = self.num()
        if num >= len(self.block):
            return None
        else:
            return self.block.get_trial(num + 1)