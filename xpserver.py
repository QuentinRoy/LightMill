from flask import Flask
from xp import Xp
import json
import os


dir = os.path.dirname(__file__)
app = Flask(__name__)
xp = Xp(os.path.join(dir, "nomodexp.xml"), os.path.join(dir, "logs"))


@app.route('/available_runs')
def available_runs():
    unstarted_runs = [run.id for run in xp.iter_runs() if not run.started()]
    return json.dumps(unstarted_runs)


@app.route('/uncompleted_runs')
def uncompleted_runs():
    uncompleted_runs = [run.id for run in xp.iter_runs() if run.started() and not run.completed()]
    return json.dumps(uncompleted_runs)


@app.route('/xp_id')
def xp_id():
    return xp.id


@app.route('/<run_id>/current_trial')
def current_trial(run_id):
    trial = xp.get_run(run_id).current_trial()
    values = trial.values()
    values.update({
        "trial_num": trial.num,
        "block_num": trial.block.num,
        "run_id": trial.run.id,
        "xp_id": trial.xp.id,
        "trial_count": len(trial.block),
        "block_count": trial.run.block_count()
    })
    return json.dumps(values)


if __name__ == '__main__':
    app.run(debug=True)