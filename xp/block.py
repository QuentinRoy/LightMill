__author__ = 'quentin'
from trial import Trial

class Block:
    def __init__(self, dom, run, num):
        self.num = num
        self._dom = dom
        self._values = self._parse_values(self._dom.attrib["values"])
        self._run = run

        # create all trials
        self._trials = []
        for trial_dom in self._dom.findall('trial'):
            trial = Trial(trial_dom, self, len(self._trials))
            self._trials.append(trial)

    @staticmethod
    def _parse_values(values_string):
        value_strings = values_string.split(',')
        value_seq = (value_string.split('=', 1) for value_string in value_strings if value_string != "")
        return {key: value for (key, value) in value_seq}

    def values(self):
        return self._values.copy()

    @property
    def type(self):
        self._dom.tag

    @property
    def run(self):
        return self._run

    def trial(self, trial_num):
        return self._trials[trial_num]

    def iter_trials(self):
        return (trial for trial in self._trials)

    def __len__(self):
        return len(self._trials)

    @staticmethod
    def _parse_values(values_string):
        value_strings = values_string.split(',')
        value_seq = (value_string.split('=', 1) for value_string in value_strings if value_string != "")
        return {key: value for (key, value) in value_seq}

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