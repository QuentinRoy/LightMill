
__author__ = 'Quentin Roy'


class Trial():
    def __init__(self, dom, block, num):
        self.num = num
        self._dom = dom
        self._values = self._parse_values(self._dom.attrib["values"])
        self._block = block

    @property
    def block(self):
        return self._block

    def values(self):
        # block values are copied
        return self.block.values().update(self._values)

    @staticmethod
    def _parse_values(values_string):
        value_strings = values_string.split(',')
        value_seq = (value_string.split('=', 1) for value_string in value_strings if value_string != "")
        return {key: value for (key, value) in value_seq}


    def completed(self):
        return False

    def started(self):
        return False