class DFGNode:
    def __init__(self, label, is_start=False, is_sink=False):
        self.label = label
        self.is_start = is_start
        self.is_sink = is_sink

    def __key(self):
        return self.label

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        if type(self) is type(other):
            return self.label == other.label
        else:
            return False

    def __repr__(self):
        return f"{self.label}"

