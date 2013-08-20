__author__ = 'Quentin Roy'


class Record(object):
    def __init__(self, id, name=None, log_levels=[], type="String"):
        self._id = id
        self._name = name
        self._log_levels = log_levels.replace("_", " ").split() if isinstance(log_levels, basestring) else log_levels
        self.type = type

    @property
    def name(self):
        if self._name is not None and self._name != "":
            return self._name
        else:
            return self.id

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def id(self):
        return self._id

    def trial_log(self):
        return "trial" in self._log_levels

    def event_log(self):
        return "event" in self._log_level


class Measure(Record):
    def __init__(self, dom):
        super(Measure, self).__init__(dom.get("id"), dom.get("name"))
        self._dom = dom
        self.type = self._dom.get("type")

        # set the log level of the measure
        for attrib, value in self._dom.items():
            if "cine" in attrib and value == "ok":
                self._log_levels.append("event")
            if "log" in attrib and value == "ok":
                self._log_levels.append("trial")


class Factor(Record):
    def __init__(self, dom):
        super(Factor, self).__init__(dom.get("id"), dom.get("name"), ["trial"])
        self.kind = dom.get("kind")
        self.tag = dom.get("tag")
        self.type = dom.get("type")
        self._values = {(v.get("id"), v.get("name")) for v in dom.findall("value")}

    def get_value_name(self, value_id):
        name = self._values[value_id]
        return name if name != "" else value_id

    def iter_values(self):
        return self._values.iterkeys()