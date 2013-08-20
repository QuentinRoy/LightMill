__author__ = 'Quentin Roy'

from .record import Measure, Record


class Loger():
    trial_file_names = "{run}_trials.csv"
    event_file_names = "{run}_events.csv"
    default_records = [
        Record(name="experiment name", id="xp_name", log_levels="event trial"),
        Record(name="run id", id="run_id", log_levels="event trial"),
        Record(name="trial num", id="trial_num", log_levels="event trial"),
        Record(name="trial count", id="trial_count", log_levels="event trial"),
        Record(name="block num", id="block_num", log_levels="event trial"),
        Record(name="block count", id="block_count", log_levels="event trial"),
        Record(id="practice", log_levels="trial")
    ]

    def __init__(self, exp, log_directory):
        self._log_directory = log_directory
        self._exp = exp
        # add the default measures
        records = self.default_records + self._exp.factors() + self._exp.measures()
        self._event_records = [rec for rec in records if rec.event_log]
        self._trial_records = [rec for rec in records if rec.trial_log]

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
            "experiment name": trial.xp.name,
            "experiment id": trial.xp.id,
            "author": trial.xp.author
        }