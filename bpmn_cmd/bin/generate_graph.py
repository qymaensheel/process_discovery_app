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
import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from splunklib.searchcommands import dispatch, EventingCommand, Configuration, Option


def return_obj(
    Id="",  # noqa: disable=E251
    case_id="",
    origin="",
    destination="",
    obj_type="",
    parents="",
    attr_list="",
):
    return {
        "Id": Id,
        "Origin": origin,
        "Destination": destination,
        "type": obj_type,
        "Parents": parents,
        "AttrList": attr_list,
    }


@Configuration()
class EventingCSC(EventingCommand):
    """
    The eventingcsc command filters records from the events stream returning only those for which the status is same
    as search query.

    Example:

    ``index="_internal" | head 4000 | eventingcsc status=200``

    Returns records having status 200 as mentioned in search query.
    """

    caseid = Option(
        doc='''**Syntax:** **caseid=***<value>*
        **Description:** Case ID column name.''',
        require=False)
    activity = Option(
        doc='''**Syntax:** **activity=***<value>*
        **Description:** Activity column name.''',
        require=False)
    start = Option(
        doc='''**Syntax:** **start=***<value>*
        **Description:** Start Timestamp column name.''',
        require=False)
    end = Option(
        doc='''**Syntax:** **end=***<value>*
        **Description:** End Timestamp column name.''',
        require=False)
    date = Option(
        doc='''**Syntax:** **date=***<value>*
        **Description:** End Timestamp column name.''',
        require=False)

    def transform(self, records):

        if not self.caseid:
            self.caseid = "Case ID"
        if not self.activity:
            self.activity = "Activity"
        if not self.start:
            self.start = "Start Timestamp"
        if not self.end:
            self.end = "Complete Timestamp"
        if not self.date:
            self.date = "%Y/%d/%m %H:%M:%S.%f"

        current_case = None
        prev_node_id = None
        graph = None
        nodes = {}
        i = 1

        yield return_obj(
            Id="a1",
            obj_type="attr",
            attr_list=f'rankdir="LR"'
        )

        for record in records:
            new_case = record[self.caseid]
            node = record[self.activity]
            if new_case == current_case:
                yield {
                    "Case ID": record[self.caseid],
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
                try:
                    start_time = datetime.datetime.strptime(record[self.start], self.date)
                    complete_time = datetime.datetime.strptime(record[self.end], self.date)
                except ValueError:
                    start_time = complete_time = 0
                total_time = str(complete_time - start_time)
                yield {
                    "Id": f"{graph}-{node}",
                    "Case ID": "",
                    "Origin": "",
                    "Destination": "",
                    "type": "node",
                    "Parents": graph,
                    "AttrList": f'label="{node}\n{total_time}"'
                }

            prev_node_id = f"{graph}-{node}"


dispatch(EventingCSC, sys.argv, sys.stdin, sys.stdout, __name__)
