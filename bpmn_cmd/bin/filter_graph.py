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

import os
import sys


from dfg import DFG

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

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
        attr_list=f'label="{label}",penwidth={size}'
    )


def add_node(name):
    return return_obj(
        Id=name,
        obj_type="node",
        attr_list=f'label="{name}"'
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

    concurrency = Option(
        doc='''**Syntax:** **concurrency=***<value>*
        **Description:** Concurrency Threshold for the edge count.''',
        require=False)

    percentile = Option(
        doc='''**Syntax:** **percentile=***<value>*
        **Description:** Percentile Threshold for the edge count.''',
        require=False)

    def transform(self, records):

        # To connect with Splunk, use the instantiated service object which is created using the server-uri and
        # other meta details and can be accessed as shown below
        # Example:-
        #    service = self.service
        #    info = service.info //access the Splunk Server info

        log = []

        for record in records:
            trace = record["Trace"].split(";")
            log.append(trace)

        dfg = DFG(log=log,
                  concurrency_threshold=int(self.concurrency),
                  filtering_percentile_threshold=float(self.percentile)/100)
        # yield {
        #     "dfg_log_len": len(dfg.log),
        #     "sink": dfg.sink,
        #     "edges": str(dfg.edges),
        #     "nodes": str(dfg.nodes)
        # }

        for edge in dfg.edges:
            # yield {
            #     "obj": f"edge {edge.src} {edge.tgt} {edge.frequency}"
            # }
            yield add_edge(
                origin=edge.src,
                destination=edge.tgt,
                label=edge.frequency
            )

        for node in dfg.nodes:
            # yield {
            #     "obj": f"node {node.label}"
            # }
            yield add_node(
                name=node.label
            )


dispatch(EventingCSC, sys.argv, sys.stdin, sys.stdout, __name__)
