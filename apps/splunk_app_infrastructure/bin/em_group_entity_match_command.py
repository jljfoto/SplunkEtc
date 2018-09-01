#!/usr/bin/env python

import sys
import em_declare  # noqa
from splunklib.searchcommands import \
    dispatch, StreamingCommand, Configuration, Option, validators
from collections import namedtuple
from em_constants import STORE_GROUPS

GroupRecord = namedtuple('GroupRecord', ['group_id', 'group_filter', 'group_content'])


@Configuration()
class EMGroupEntityMatchCommand(StreamingCommand):
    """ Match groups and entities based on group filter and entity dimensions

    ##Syntax

    .. code-block::
        emgroupentitymatch selectedGroupIds="states,aws_instances" retainInput=false

    ##Description
        This custom search command will add 'group_id' and 'group_title' to all input
        entity records if they are members of a group - otherwise it will be omitted from the results
        unless retainInput is 'true'.

        Options:
        1. selectedGroupIds -- indicates the selected groups that you want to match against the entities
        2. retainInput -- indicates if the original input records should be attached to the output records
                          if true, those records will have 'group_id' and 'group_title' set to 'N/A' for you
                          to distinguish them.

    ##Example

    .. code-block::
        | inputlookup em_entities
        | emgroupentitymatch selectedGroupIds="states,aws_instances" retainInput=false
        | stats count by group_title

    """

    _group_records = None

    selected_group_ids = Option(doc='List of selected group ids, separated by comma.',
                                name='selectedGroupIds',
                                default=None,
                                require=False,
                                validate=validators.List())
    retain_input_record = Option(doc='Boolean to indicate if user wants the input '
                                     'record to be added to the output without modification.',
                                 name='retainInput',
                                 default=False,
                                 require=False,
                                 validate=validators.Boolean())

    def stream(self, records):
        """
        Generator function that processes and yields event records to the Splunk stream pipeline.
        :param records: splunk event records
        :return:
        """
        self._setup_group_records()
        self.logger.debug('EMGroupEntityMatchCommand: %s', self)  # logs command line
        for record in records:
            if self.retain_input_record:
                record['group_id'] = 'N/A'
                record['group_title'] = 'N/A'
                yield record
            if len(self._group_records) > 0:
                for group_record in self._group_records:
                    if self._match_group_entity(record, group_record.group_filter):
                        record['group_id'] = group_record.group_id
                        record['group_title'] = group_record.group_content.get('title')
                        yield record
            else:
                yield record

    def _setup_group_records(self):
        """
        Grabs the groups from KV Store and builds out the filter objects if they have yet to be built
        :return: None
        """
        if self._group_records is None:
            collection = self.service.kvstore[STORE_GROUPS]
            group_data = collection.data.query()
            if self.selected_group_ids:
                selected_group_set = set(self.selected_group_ids)
                group_data = filter(lambda g: g['_key'] in selected_group_set, group_data)
            group_records = []
            for group in group_data:
                filter_val = group.get('filter')
                d = {}
                if filter_val:
                    for v in filter_val.split(','):
                        dim_name, dim_val = v.strip().split('=')
                        d.setdefault(dim_name, set()).add(dim_val)
                group_records.append(GroupRecord(group_id=group['_key'],
                                                 group_filter=d,
                                                 group_content=group))
            self._group_records = group_records

    def _match_group_entity(self, record, filter_dict):
        """
        Verify whether this record matches to group filters.
        Support wildcard in end of string
        :param record:
        :param filter_dict:
        :return:
        """
        for dim_name, dim_val_set in filter_dict.iteritems():
            record_vals = record.get('dimensions.%s' % dim_name)
            if not record_vals:
                return False
            if not isinstance(record_vals, list):
                record_vals = [record_vals]
            matched = False
            for rval in record_vals:
                # check if record value is one of the filter values
                if rval in dim_val_set:
                    matched = True
                    break
                # otherwise check if record value matches any of the fuzzy match values
                fuzzy_matches = filter(lambda v: v.endswith('*'), dim_val_set)
                if len(fuzzy_matches):
                    matched = any(rval.startswith(v[:-1]) for v in fuzzy_matches)
            if not matched:
                return False
        return True

dispatch(EMGroupEntityMatchCommand, sys.argv, sys.stdin, sys.stdout, __name__)
