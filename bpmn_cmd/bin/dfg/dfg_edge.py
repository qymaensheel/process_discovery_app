class DFGEdge:
    def __init__(self, src, tgt):
        self.is_loop = False
        if src == tgt:
            self.is_loop = True
        self.src = src
        self.tgt = tgt
        self.frequency = 0

    def __key(self):
        return self.src, self.tgt

    def inverse(self, other):
        return self.tgt == other.src and self.src == other.tgt

    def __lt__(self, other):
        return self.frequency > other.frequency

    def __gt__(self, other):
        return self.frequency < other.frequency

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        if type(self) is type(other):
            return self.src == other.src and self.tgt == other.tgt
        else:
            return False

    def __repr__(self):
        return f"{self.src} --> {self.tgt}"

    def increase_frequency(self):
        self.frequency += 1

    def decrease_frequency(self):
        self.frequency -= 1
