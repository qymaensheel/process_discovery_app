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

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from splunklib.searchcommands import dispatch, EventingCommand, Configuration


@Configuration()
class EventingCSC(EventingCommand):
    """
    The eventingcsc command filters records from the events stream returning only those for which the status is same
    as search query.

    Example:

    ``index="_internal" | head 4000 | eventingcsc status=200``

    Returns records having status 200 as mentioned in search query.
    """

    # status = Option(
    #     doc='''**Syntax:** **status=***<value>*
    #     **Description:** record having same status value will be returned.''',
    #     require=True)

    def transform(self, records):

        # To connect with Splunk, use the instantiated service object which is created using the server-uri and
        # other meta details and can be accessed as shown below
        # Example:-
        #    service = self.service
        #    info = service.info //access the Splunk Server info
        current_case = None
        prev_activity = None
        prev_node_id = None
        graph = None
        nodes = {}
        i = 1
        for record in records:
            new_case = record['Case ID']
            node = record["Activity"]
            if new_case == current_case:
                yield {
                    "Case ID": record["Case ID"],
                    "Origin": prev_node_id,  # prev_activity,
                    "Destination": f"{graph}-{node}",  # record["Activity"],
                    "type": "edge",
                    "Parents": graph,
                    "AttrList": f''
                }
            else:
                current_case = new_case
                graph = f"graph{i}"
                nodes[current_case] = []
                i += 1
                yield {
                    "Id": graph,
                    "Case ID": "",
                    "Origin": "",
                    "Destination": "",
                    "type": "cluster",
                    "Parents": "",
                    "AttrList": f'label="Case {current_case}"'

                }
            if node not in nodes[current_case]:
                nodes[current_case].append(node)
                yield {
                    "Id": f"{graph}-{node}",
                    "Case ID": "",
                    "Origin": "",
                    "Destination": "",
                    "type": "node",
                    "Parents": graph,
                    "AttrList": f'label="{node}"'
                }

            prev_activity = record["Activity"]
            prev_node_id = f"{graph}-{node}"


dispatch(EventingCSC, sys.argv, sys.stdin, sys.stdout, __name__)
