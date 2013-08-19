from run import Run
from trial import Trial
from xp import Xp
from block import Block

def _parse_values(values_string):
    value_strings = values_string.split(',')
    value_seq = (value_string.split('=', 1) for value_string in value_strings if value_string != "")
    return {key: value for (key, value) in value_seq}