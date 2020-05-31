__author__ = "Quentin Roy"

from xml.etree import ElementTree
from xml.dom import pulldom
from .model import Experiment, Run, Trial, Factor, FactorValue, Block, db, Measure


class TouchStoneParsingException(Exception):
    pass


def update_experiment(touchstone_file):
    exp_dom = ElementTree.parse(touchstone_file).getroot()
    xp_id = parse_experiment_id(touchstone_file)
    experiments = Experiment.query.filter_by(id=xp_id).all()
    if len(experiments) > 0:
        print("Update experiment {}.".format(xp_id))
        return _parse_experiment(exp_dom, experiments[0], True)
    else:
        raise TouchStoneParsingException(
            "The experiment {} does not exist".format(xp_id)
        )


def create_experiment(touchstone_file):
    exp_dom = ElementTree.parse(touchstone_file).getroot()
    return _parse_experiment(exp_dom)


def parse_experiment_id(touchstone_file):
    doc = pulldom.parse(touchstone_file)
    for event, node in doc:
        if event == pulldom.START_ELEMENT and node.tagName == "experiment":
            return node.getAttribute("id")


def _nonize_string(string):
    return None if string == "" else string


def _parse_experiment(dom, exp=None, verbose=False):
    measures = (_parse_measure(measure_dom) for measure_dom in dom.findall("measure"))
    id = dom.get("id")
    if not id:
        raise TouchStoneParsingException("No experiment id.")
    exp = exp or Experiment(
        id=dom.get("id"),
        name=_nonize_string(dom.get("name")),
        factors=[_parse_factor(factor_dom) for factor_dom in dom.findall("factor")],
        author=dom.get("author"),
        measures=dict((measure.id, measure) for measure in measures),
        description=_nonize_string(dom.get("description")),
    )

    run_ids = set(run.id for run in exp.runs)
    for run_dom in dom.findall("run"):
        run_id = run_dom.get("id")
        if run_id not in run_ids:
            if verbose:
                print("Creation of run {}.".format(run_id))
            _parse_run(run_dom, exp)
        else:
            print("Run {} already present.".format(run_id))
    return exp


def _parse_factor(dom):
    values = []
    default_value = None
    for v_dom in dom.findall("value"):
        value = _parse_value(v_dom)
        values.append(value)
        default = v_dom.get("default")
        if default in ["true", "1", "True", "yes", "Yes"]:
            default_value = value

    return Factor(
        id=dom.get("id"),
        name=_nonize_string(dom.get("name")),
        type=dom.get("type"),
        kind=_nonize_string(dom.get("kind")),
        tag=_nonize_string(dom.get("tag")),
        values=values,
        default_value=default_value,
    )


def _parse_measure(dom):
    trial_level = False
    event_level = False
    for attrib, value in dom.items():
        norm_value = value.strip().lower()
        if "log" in attrib and norm_value == "ok":
            trial_level = True
        if "cine" in attrib and norm_value == "ok":
            event_level = True

    return Measure(
        id=dom.get("id"),
        name=_nonize_string(dom.get("name")),
        type=dom.get("type"),
        trial_level=trial_level,
        event_level=event_level,
    )


def _parse_value(dom):
    return FactorValue(id=dom.get("id"), name=_nonize_string(dom.get("name")))


def _parse_run(dom, experiment):
    run = Run(id=dom.get("id"), experiment=experiment)

    for block_dom in dom.iter():
        if block_dom.tag in ("block", "practice"):
            _parse_block(block_dom, run)
    return run


def _parse_factor_values_string(values_string, experiment):
    value_strings = values_string.split(",")
    value_seq = (
        value_string.split("=", 1)
        for value_string in value_strings
        if value_string != ""
    )
    values = []
    for factor_id, value_id in value_seq:
        # we cannot use a query so we have to filter by hand
        try:
            factor = next(
                factor for factor in experiment.factors if factor.id == factor_id
            )
            value = next(value for value in factor.values if value.id == value_id)
            values.append(value)
        except StopIteration:
            raise TouchStoneParsingException(
                "Factor or factor value not registered: {}={}".format(
                    factor_id, value_id
                )
            )
    return values


def _parse_block(dom, run):
    practice = dom.tag == "practice"
    values_string = dom.get("values")
    values = (
        _parse_factor_values_string(dom.get("values"), run.experiment)
        if values_string
        else []
    )
    block = Block(run=run, practice=practice, values=values)

    for trial_dom in dom.findall("trial"):
        _parse_trial(trial_dom, block)
    return block


def _parse_trial(dom, block):
    values_string = dom.get("values")
    values = (
        _parse_factor_values_string(values_string, block.experiment)
        if values_string
        else []
    )
    trial = Trial(block, values=values)
    return trial


if __name__ == "__main__":

    def main():
        from flask import Flask
        import default_settings

        # app creation
        app = Flask(__name__.split(".")[0])
        app.config["SQLALCHEMY_DATABASE_URI"] = default_settings.SQLALCHEMY_DATABASE_URI

        db.init_app(app)
        db.app = app

        with app.test_request_context():
            update_experiment(default_settings.TOUCHSTONE_FILE)
            db.session.commit()

    main()
