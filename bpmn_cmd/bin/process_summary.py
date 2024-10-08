#!/usr/bin/env python
# coding=utf-8
#
# Copyright 2011-2015 Splunk, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"): you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
import datetime
import json
import os
import sys
from functools import reduce
from itertools import groupby
from itertools import chain
from math import sqrt


from more_itertools import pairwise
from collections import Counter

sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "lib"))

import utils

from splunklib.searchcommands import dispatch, EventingCommand, Configuration, Option


def return_obj(
        Id="",  # noqa: disable=E251
        case_id="",
        origin="",
        destination="",
        obj_type="",
        parents="",
        attr_list=""
):
    return {
        "Id": Id,
        "Origin": origin,
        "Destination": destination,
        "type": obj_type,
        "Parents": parents,
        "AttrList": attr_list
    }


def add_edge(origin, destination, label="", size: float = 1):
    return return_obj(
        origin=origin,
        destination=destination,
        obj_type="edge",
        attr_list=f'label="{label}",penwidth="{size}"'
    )


def add_node(name, color, label):
    return return_obj(
        Id=name,
        obj_type="node",
        attr_list=f'label="{label}",style="rounded,filled",fillcolor="{color}"'
    )



@Configuration()
class EventingCSC(EventingCommand):
    """
    The eventingcsc command filters records from the events stream returning only those for which the status is same
    as search query.

    Example:

    ``index="_internal" | head 4000 | eventingcsc status=200``

    Returns records having status 200 as mentioned in search query.
    """

    threshold = Option(
        doc='''**Syntax:** **threshold=***<value>*
        **Description:** Threshold for the edge count.''',
        require=False, default=0)

    def transform(self, records):

        # To connect with Splunk, use the instantiated service object which is created using the server-uri and
        # other meta details and can be accessed as shown below
        # Example:-
        #    service = self.service
        #    info = service.info //access the Splunk Server info
        logger = utils.setup_logger("ProcessSummary")
        now = datetime.datetime.now()

        logger.info(f"Started generating graph at t={now.strftime('%FT%T.%fZ')}")

        w_net = dict()
        ev_start_set = set()
        ev_end_set = set()
        ev_counter = {}

        def add(val, i=1):
            if val not in ev_counter.keys():
                ev_counter[val] = 0
            ev_counter[val] += i

        for i, record in enumerate(records):
            trace = record["Trace"].split(";")
            count = int(record["count"])
            for activity in trace:
                add(activity, count)

            if trace[0] not in ev_start_set:
                ev_start_set.add(trace[0])
            if trace[-1] not in ev_end_set:
                ev_end_set.add(trace[-1])
            for ev_i, ev_j in pairwise(trace):
                if ev_i not in w_net.keys():
                    w_net[ev_i] = Counter()
                w_net[ev_i][ev_j] += count

        trace_counts = sorted(chain(*[c.values() for c in w_net.values()]))

        trace_min = trace_counts[0]
        trace_max = trace_counts[-1]
        color_min = min(ev_counter.values())
        color_max = max(ev_counter.values())

        yield return_obj(
            Id="a1",
            obj_type="attr",
            attr_list=f'rankdir="LR"'
        )

        for event, successors in w_net.items():
            value = ev_counter[event]
            color = int(float(color_min - value) / float(color_min - color_max) * 100.00)
            my_color = "#fe5943" + str(hex(color))[2:]
            yield add_node(event, my_color, f'{event}\n{ev_counter[event]}')
            for successor, cnt in successors.items():
                yield add_edge(event, successor, str(cnt), size=4*cnt/(trace_max-trace_min)+0.1)

        add_node("start", "white", "start")
        for ev_start in ev_start_set:
            add_edge("start", ev_start)

        add_node("end", "white", "start")
        for ev_end in ev_end_set:
            add_edge(ev_end, "end")

        end = datetime.datetime.now()

        logger.info(f"Finished generating graph at t={end.strftime('%FT%T.%fZ')}")

        delta = end - now

        logger.info(f"Total time: {delta.total_seconds()}")



dispatch(EventingCSC, sys.argv, sys.stdin, sys.stdout, __name__)
