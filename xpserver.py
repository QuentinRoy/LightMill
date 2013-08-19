from flask import Flask
from xp import Xp
import json

app = Flask(__name__)
xp = Xp("/Users/quentin/Workspace/PyCharm/Test/nomodexp.xml")


@app.route('/available_runs')
def available_runs():
    unstarted_runs = [run.id for run in xp.iter_runs() if not run.started()]
    return json.dumps(unstarted_runs)

@app.route('/uncompleted_runs')
def uncompleted_runs():
    uncompleted_runs = [run.id for run in xp.inter_runs() if run.started() and not run.completed()]
    return json.dumps(uncompleted_runs)

@app.route('/xp_id')
def xp_id():
    return xp.id()


@app.route('/next_trial/<run_id>')
def next_trial(run_id):
    run = xp.run(run_id)


if __name__ == '__main__':
    app.run(debug=True)
