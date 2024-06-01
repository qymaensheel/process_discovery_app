import sys

from .dfg_edge import DFGEdge
from .dfg_node import DFGNode


class DFG:
    def __init__(self, log, concurrency_threshold, filtering_percentile_threshold):
        self.log = log
        self.source = None
        self.sink = None

        if concurrency_threshold == 0:
            self.concurrency_threshold = sys.maxsize
        else:
            self.concurrency_threshold = concurrency_threshold
        if filtering_percentile_threshold == 0:
            self.filtering_percentile_threshold = sys.maxsize
        else:
            self.filtering_percentile_threshold = filtering_percentile_threshold

        self.nodes: list[DFGNode] = []
        self.edges: list[DFGEdge] = []
        self.outgoings = {}
        self.incomings = {}
        self.self_loops = []
        self.short_loops = []
        self.concurrency_relations = []
        self.infrequent_behavior = []
        self.prepare_log()

    def prepare_log(self):
        traces = self.log
        self.source = DFGNode('Register')
        self.sink = DFGNode('End')
        # Extract all Nodes from the log
        for trace in traces:
            for evt in trace:
                node = DFGNode(evt)
                if node not in self.nodes:
                    if node.label == 'Register':
                        self.source = node
                    elif node.label == 'End':
                        self.sink = node
                    self.nodes.append(node)
        # Extract all Edges from the log
        for trace in traces:
            for idx in range(len(trace) - 1):
                src = self.nodes[self.nodes.index(DFGNode(trace[idx]))]
                tgt = self.nodes[self.nodes.index(DFGNode(trace[idx + 1]))]
                edge = DFGEdge(src, tgt)
                if edge not in self.edges:
                    edge.increase_frequency()
                    self.edges.append(edge)
                else:
                    self.edges[self.edges.index(edge)].increase_frequency()
        self.edges.sort()

        # Detect, remove and store self-loops
        self.self_loops = [x.src for x in self.edges if x.src == x.tgt]
        self.edges = [x for x in self.edges if x.src != x.tgt]

        # Detect, remove and store short-loops i.e. length 2 loops = A -> B -> A
        for trace in traces:
            for idx in range(len(trace) - 2):
                a = self.nodes[self.nodes.index(DFGNode(trace[idx]))]
                b = self.nodes[self.nodes.index(DFGNode(trace[idx + 1]))]
                c = self.nodes[self.nodes.index(DFGNode(trace[idx + 2]))]
                if a == c and a != b:
                    if a not in self.self_loops and b not in self.self_loops:
                        self.edges[self.edges.index(DFGEdge(a, b))].is_loop = True
                        self.edges[self.edges.index(DFGEdge(b, a))].is_loop = True
        for edge in self.edges:
            if edge.is_loop:
                self.short_loops.append(edge)
                self.remove_edge(edge)
        # Detect, remove and store concurrency relations i.e A->B, B->A, that neither of those is a short loop
        # And neither is a self-loop -> both conditions are guaranteed because loops were already removed by now
        for edge in self.edges:
            for edge2 in self.edges:
                if edge.inverse(edge2) and edge != edge2:
                    concurrency_denominator = abs(edge.frequency - edge2.frequency) / (edge.frequency + edge2.frequency)
                    if concurrency_denominator < self.concurrency_threshold:
                        if edge not in self.concurrency_relations:
                            self.concurrency_relations.append(edge)
                        if edge2 not in self.concurrency_relations:
                            self.concurrency_relations.append(edge2)
                    else:
                        if edge.frequency < edge2.frequency:
                            if edge not in self.infrequent_behavior:
                                self.infrequent_behavior.append(edge)
                        else:
                            if edge2 not in self.infrequent_behavior:
                                self.infrequent_behavior.append(edge2)
        self.edges = [x for x in self.edges if x not in self.concurrency_relations and x not in self.infrequent_behavior]
        self.discover_outgoings()
        self.discover_incomings()
        self.filtration()

    def filtration(self):
        source = self.source
        sink = self.sink
        forward_capacities = {}
        backward_capacities = {}
        forward_capacities[source] = sys.maxsize
        forward_capacities[sink] = 0
        backward_capacities[sink] = sys.maxsize
        backward_capacities[source] = 0
        best_edges = []
        for node in self.nodes:
            if node != self.source and node != self.sink:
                forward_capacities[node] = 0
                backward_capacities[node] = 0
                f_i = max(self.incomings[node], key=lambda x: x.frequency)
                f_o = min(self.outgoings[node], key=lambda x: x.frequency)
                best_edges.append(f_i)
                best_edges.append(f_o)
        filtering_threshold = self.compute_filtering_threshold(best_edges)
        best_predecessor_from_source = {}
        best_successor_to_sink = {}
        self.discover_best_predecessors_from_source(forward_capacities, best_predecessor_from_source)
        self.discover_best_successors_to_sink(backward_capacities, best_successor_to_sink)
        for node in self.nodes:
            if node != self.source and best_predecessor_from_source[node] not in best_edges:
                best_edges.append(best_predecessor_from_source[node])
            if node != self.sink and best_successor_to_sink[node] not in best_edges:
                best_edges.append(best_successor_to_sink[node])
        to_remove = []
        for edge in self.edges:
            if edge not in best_edges or edge.frequency <= filtering_threshold:
                to_remove.append(edge)
        self.edges = [x for x in self.edges if x not in to_remove]

    def discover_best_predecessors_from_source(self, forward_capacities, best_predecessor_from_source):
        unvisited = [x for x in self.nodes if x != self.source]
        to_visit = [self.source]
        while len(to_visit) > 0:
            predecessor = to_visit.pop()
            for outgoing_edge in self.outgoings[predecessor]:
                target = outgoing_edge.tgt
                edge_frequency = outgoing_edge.frequency
                max_capacity = min(forward_capacities[predecessor], edge_frequency)
                if max_capacity > forward_capacities[target]:
                    forward_capacities[target] = max_capacity
                    best_predecessor_from_source[target] = outgoing_edge
                    if target not in unvisited and target not in to_visit:
                        unvisited.append(target)
                if target in unvisited:
                    unvisited.remove(target)
                    to_visit.append(target)

    def discover_best_successors_to_sink(self, backward_capacities, best_successor_to_sink):
        unvisited = [x for x in self.nodes if x != self.sink]
        to_visit = [self.sink]
        while len(to_visit) > 0:
            successor = to_visit.pop()
            for incoming_edge in self.incomings[successor]:
                source = incoming_edge.src
                edge_frequency = incoming_edge.frequency
                max_capacity = min(backward_capacities[successor], edge_frequency)
                if max_capacity > backward_capacities[source]:
                    backward_capacities[source] = max_capacity
                    best_successor_to_sink[source] = incoming_edge
                    if source not in unvisited and source not in to_visit:
                        unvisited.append(source)
                if source in unvisited:
                    unvisited.remove(source)
                    to_visit.append(source)

    def discover_outgoings(self):
        self.outgoings[self.sink] = []
        for node in self.nodes:
            for edge in self.edges:
                if edge.src == node:
                    if node not in self.outgoings:
                        self.outgoings[node] = [edge]
                    else:
                        if edge not in self.outgoings[node]:
                            self.outgoings[node].append(edge)

    def discover_incomings(self):
        self.incomings[self.source] = []
        for node in self.nodes:
            for edge in self.edges:
                if edge.tgt == node:
                    if node not in self.incomings:
                        self.incomings[node] = [edge]
                    else:
                        if edge not in self.incomings[node]:
                            self.incomings[node].append(edge)

    def compute_filtering_threshold(self, best_edges):
        best_edges.sort(reverse=True)
        locator = int(round((len(best_edges)) * self.filtering_percentile_threshold))
        if locator == len(best_edges):
            locator -= 1
        return best_edges[locator].frequency

    def remove_edge(self, to_remove):
        self.edges.remove(to_remove)
