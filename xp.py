__author__ = 'Quentin Roy'

from xml.etree import ElementTree
from csv import DictWriter, DictReader


class Xp:
    def __init__(self, config_file, log_directory):
        self._dom = ElementTree.parse(config_file).getroot()
        self._id = self._dom.get("id")
        self._name = self._dom.get("name")
        self._author = self._dom.get("author")

        # create all runs
        self._run_dict = {}
        self._runs = []
        for run_dom in self._dom.findall('run'):
            run = Run(run_dom, self)
            self._run_dict[run.id] = run
            self._runs.append(run)

        measures = [Measure(dom=m_dom) for m_dom in self._dom.findall('measure')]
        self._loger = XPLoger(measures, log_directory)

    def run_ids(self):
        return self._run_dict.keys()

    def iter_runs(self):
        return (run for run in self._runs)

    @property
    def id(self):
        return self._id

    def get_run(self, run_id):
        return self._run_dict[run_id]

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


class Run:
    def __init__(self, dom, xp):
        self._dom = dom
        self._xp = xp
        self._id = self._dom.get("id")
        self._blocks = []

        # create the blocks
        for block_dom in self._dom.iter():
            if block_dom.tag in ("block", "practice"):
                block = Block(block_dom, self, len(self._blocks))
                self._blocks.append(block)

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


def _parse_values(values_string):
    value_strings = values_string.split(',')
    value_seq = (value_string.split('=', 1) for value_string in value_strings if value_string != "")
    return {key: value for (key, value) in value_seq}


class Block:
    def __init__(self, dom, run, num):
        self.num = num
        self._dom = dom
        self._values = _parse_values(self._dom.get("values"))
        self._run = run

        # create all trials
        self._trials = []
        for trial_dom in self._dom.findall('trial'):
            trial = Trial(trial_dom, self, len(self._trials))
            self._trials.append(trial)

    def values(self):
        return self._values.copy()

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


class Trial():
    def __init__(self, dom, block, num):
        self.num = num
        self._dom = dom
        self._values = _parse_values(self._dom.get("values"))
        self._block = block
        self.results = None
        self.events = []

    @property
    def block(self):
        return self._block

    def values(self):
        # block values are copied before being returned
        values = self.block.values()
        values.update(self._values)
        return values

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
        if self.num == 0:
            return None
        else:
            return self.block.get_trial(self.num - 1)

    def next_trial(self):
        if self.num + 1 >= len(self.block):
            return None
        else:
            return self.block.get_trial(self.num + 1)


class Measure:
    def __init__(self, dom=None, trial_level=False, event_level=False, name="", id="", type=""):
        self._dom = dom
        if dom is not None:
            self.id = self._dom.get("id")
            self.name = self._dom.get("name", "")
            self.type = self._dom.get("type")

            # set the log level of the measure
            self.trial_level = False
            self.event_level = False
            for attrib, value in self._dom.items():
                if "cine" in attrib and value == "ok":
                    self.event_level = True
                if "log" in attrib and value == "ok":
                    self.trial_level = True
        else:
            self.id = id
            self.trial_level = trial_level
            self.event_level = event_level
            self.name = name
            self.type = type


    @property
    def name(self):
        return self._name if self._name != "" else self.id

    @name.setter
    def name(self, value):
        self._name = value


class XPLoger():
    trial_file_names = "{run}_trials.csv"
    event_file_names = "{run}_events.csv"
    default_measures = [
        Measure(name="xp name", id="xp_name", event_level=True, trial_level=True),
        Measure(name="run id", id="run_id", event_level=True, trial_level=True),
        Measure(name="trial num", id="trial_num", event_level=True, trial_level=True),
        Measure(name="trial count", id="trial_count", trial_level=True),
        Measure(name="block num", id="block_num", event_level=True, trial_level=True),
        Measure(name="block count", id="block_count", event_level=True),
        Measure(id="practice", trial_level=True)
    ]

    def __init__(self, measures, log_directory):
        self._log_directory = log_directory
        # add the default measures
        measures = self.default_measures + measures
        self._event_measures = [measure for measure in measures if measure.event_level]
        self._trial_measures = [measure for measure in measures if measure.trial_level]
        self.event_measure_processors = []
        self.trial_measure_processors = [self._trial_base_info_process, ]

    def trial_completed(self, trial):
        trial_level_info = self._process_trial_measures(trial)
        print("run {run} block {block} trial {trial} completed".format(trial_level_info))


    def _process_trial_measures(self, trial, info={}):
        to_apply = self.trial_measure_processors[:]
        last_to_apply = []
        while len(to_apply) and len(to_apply) != len(last_to_apply):
            remaining = []
            for process in to_apply:
                proc_res = process(trial, info)
                if (proc_res):
                    info.update(proc_res)
                else:
                    remaining.append(process)
            to_apply, last_to_apply = remaining, to_apply
        return info


    def synchronize(self, xp):
        raise NotImplemented("Not available yet")


    @staticmethod
    def _trial_base_info_process(trial, info):
        return {
            "trial num": trial.num,
            "trial count": len(trial.block),
            "block num": trial.block.num,
            "block count": trial.xp.block_count(),
            "run id": trial.get_run.id,
            "xp name": trial.xp.name,
            "xp id": trial.xp.id,
            "author": trial.xp.author
        }