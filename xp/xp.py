
__author__ = 'Quentin Roy'

from xml.etree import ElementTree
from run import Run


class Xp():
    def __init__(self, config_file):
        self._dom = ElementTree.parse(config_file).getroot()
        self._id = self._dom.attrib["id"]

        # create all runs
        self._run_dict = {}
        self._runs = []
        for run_dom in self._dom.findall('run'):
            run = Run(run_dom, self)
            self._run_dict[run.id] = run
            self._runs.append(run)

    def run_ids(self):
        return self._run_dict.keys()

    def iter_runs(self):
        return (run for run in self._runs)

    def id(self):
        return self._id

    def run(self, run_id):
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