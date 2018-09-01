import re
import em_constants as EMConstants
from em_exceptions import AlertInternalException

MANAGED_BY_TEMPLATE = '{app_name}:{managed_by}'


class EMAlert(object):
    """
    EMAlert class handles alert related logic
    """
    # Validation related constants
    ALLOWED_TYPES = ['group', 'entity']

    # SPL template for constructing final query
    SPL_TEMPLATE = (
        '{metric_spl}'
        '| stats list({aggregation}) as {aggregation} {split_by_clause}'
        '| eval past_value=mvindex({aggregation}, 0), current_value=mvindex({aggregation}, 1) | fields - {aggregation}'  # noqa
        '| eval CRITICAL=5, WARNING=3, INFO=1'
        '| eval past_state={past_against_threshold_spl}'
        '| eval current_state={current_against_threshold_spl}'
        '| eval state_change=if(current_state > past_state, "degrade", if(current_state == past_state, "no", "improve"))'  # noqa
        '| eval metric_name="{metric_name}",'  # put additional information into search result
        'aggregation_method="{aggregation}",'
        'managed_by_id="{managed_by_id}",'
        'managed_by_type="{managed_by_type}",'
        'threshold_info_min={info_min},'
        'threshold_info_max={info_max},'
        'threshold_warning_min={warning_min},'
        'threshold_warning_max={warning_max},'
        'threshold_critical_min={critical_min},'
        'threshold_critical_max={critical_max},'
        'ss_id="{ss_id}"'
        '{join_with_entities_clause}'
    )
    # Extract patterns are used extract information from metric_spl
    EXTRACT_PATTERNS = {
        'AGGREGATION': r'\|\smstats\s\S*\sas\s"(?P<aggregation>\w+)"',
        'SPLIT_BY': r'.*BY\s"(?P<split_by>\w+)"',
        'EARLIEST': r'earliest=\d*\.{0,}\d*\S{0,}',
        'LATEST': r'latest=\d*\.{0,}\d*\S{0,}',
        'SPAN': r'span=\d*\.{0,}\d*\S{0,}',
        'METRIC_NAME': r'.*metric_name="(?P<metric_name>\S+)"\s?'
    }

    def __init__(self, name, managed_by, managed_by_type, metric_spl, threshold, actions=None):
        """
        initialize an EMAlert instance
        :param name: name of the alert
        :param managed_by: id of entity/group this alert belongs to
        :param managed_by_type: type of object that manages this alert
        :param metric_spl: SPL to get metric data -- type: string
               example: | mstats avg(_value) as "Avg" WHERE "host"="akron.usa.com" AND ("cpu"="0" OR "cpu"="1") AND metric_name="cpu.system" earliest=1521045946.014 latest=1521049546.014 span=10s BY "cpu"  # noqa
        :param threshold: threshold object -- type: EMThreshold
        :param actions: list of alert actions to take -- type: EMAlertAction (or its subclass)
        """
        self.name = name
        self.managed_by = managed_by
        self.managed_by_type = managed_by_type
        self.metric_spl = metric_spl.strip()
        self.threshold = threshold
        self.actions = [] if not actions else actions
        self._validate()

    def _validate(self):
        if self.managed_by_type not in EMAlert.ALLOWED_TYPES:
            raise AlertInternalException('Type: %s is not allowed.' % self.managed_by_type)

    def _get_aggregation(self):
        """
        get aggregation method from SPL
        """
        aggreg_match = re.match(EMAlert.EXTRACT_PATTERNS['AGGREGATION'], self.metric_spl)
        if not aggreg_match:
            raise AlertInternalException('Aggregation method is missing from metric SPL')
        aggregation = aggreg_match.group('aggregation')
        return aggregation

    def _get_split_by(self):
        """
        get split by clause from SPL
        """
        split_by_match = re.match(EMAlert.EXTRACT_PATTERNS['SPLIT_BY'], self.metric_spl)
        if split_by_match:
            return split_by_match.group('split_by')
        return None

    def _get_metric_name(self):
        """
        get metric name from SPL
        """
        metric_name_match = re.match(EMAlert.EXTRACT_PATTERNS['METRIC_NAME'], self.metric_spl)
        if not metric_name_match:
            raise AlertInternalException('Metric name is missing from metric SPL')
        metric_name = metric_name_match.group('metric_name')
        return metric_name

    def _build_join_entities_clause(self, managed_by_type, id_dim_field=None):
        """
        get join with entities clause to fill in entities information
        :param managed_by_type: entity or group
        :param id_dim_field: only for group case
        :return:
        """
        entity_spl_template = (
            '| eval entity_id=managed_by_id '
            '| join type=inner max=0 entity_id [| inputlookup {entities_store} | rename _key as entity_id, title as entity_title]'  # noqa
            '| fields - dimensions.*, informational_dimensions'
        )
        group_spl_template = (
            '| rename {id_dim_field} as dimensions.{id_dim_field} '
            '| join type=inner max=0 dimensions.{id_dim_field} [| inputlookup {entities_store} | rename title as entity_title, _key as entity_id]'  # noqa
            '| fields - dimensions.*, informational_dimensions'
        )
        if managed_by_type == EMAlert.ALLOWED_TYPES[0]:
            valid_id_dimensions = reduce(lambda ids1, ids2: ids1 + ids2,
                                         map(lambda col: col['identifier_dimensions'],
                                             EMConstants.COLLECTORS))
            # only allow valid identifier dimensions
            if id_dim_field and id_dim_field in valid_id_dimensions:
                return group_spl_template.format(entities_store=EMConstants.STORE_ENTITIES,
                                                 id_dim_field=id_dim_field)
            raise AlertInternalException('%s is not a valid identifier dimension' % id_dim_field)
        else:
            return entity_spl_template.format(entities_store=EMConstants.STORE_ENTITIES)

    def convert_spl(self):
        """
        convert alert to SPL
        :return: string - result SPL
        """
        # get aggregation method
        aggregation = self._get_aggregation()
        # get split by criteria
        split_by = self._get_split_by()
        split_by_clause = 'by "%s"' % split_by if split_by else ''
        # get metric name
        metric_name = self._get_metric_name()
        # modify time range and span
        # TODO: do we need to dynamically set earliest & latet based on collection window ??
        pattern_repl_list = [
            (EMAlert.EXTRACT_PATTERNS['EARLIEST'], 'earliest=-2m'),
            (EMAlert.EXTRACT_PATTERNS['LATEST'], 'latest=now'),
            (EMAlert.EXTRACT_PATTERNS['SPAN'], 'span=1m')
        ]
        metric_spl = self.metric_spl
        for pattern, repl in pattern_repl_list:
            metric_spl = re.sub(pattern, repl, metric_spl)

        # build join with entities clause
        # NOTE: we are using split by field as identifier dimensio for group alert because we
        # enforce that in the frontend, this is a temporary solution as in ITOA-10988
        join_clause = self._build_join_entities_clause(self.managed_by_type, split_by)

        # build threshold SPL
        past_against_threshold_spl = self._build_threshold_spl('past_value')
        current_against_threshold_spl = self._build_threshold_spl('current_value')

        spl = EMAlert.SPL_TEMPLATE.format(
            metric_spl=metric_spl,
            aggregation=aggregation,
            split_by_clause=split_by_clause,
            past_against_threshold_spl=past_against_threshold_spl,
            current_against_threshold_spl=current_against_threshold_spl,
            metric_name=metric_name,
            managed_by_id=self.managed_by,
            managed_by_type=self.managed_by_type,
            ss_id=self.name,
            join_with_entities_clause=join_clause,
            **vars(self.threshold)
        )
        return spl

    def _build_threshold_spl(self, val_name):
        threshold_spl_template = (
            'if({val_name} >= {info_min} AND {val_name} < {info_max}, INFO, '
            'if({val_name} >= {warning_min} AND {val_name} < {warning_max}, WARNING, '
            'if({val_name} >= {critical_min} AND {val_name} < {critical_max}, CRITICAL, "None"'
            ')))'
        )
        return threshold_spl_template.format(
            val_name=val_name,
            **vars(self.threshold)
        )

    def to_params(self):
        """
        convert to splunk savedsearch params
        :return: dict
        """
        # add basic savedsearch data
        data = {
            'name': self.name,
            'alert.track': 1,
            'alert.severity': 6,
            'alert.managedBy': MANAGED_BY_TEMPLATE.format(
                app_name=EMConstants.APP_NAME,
                managed_by=self.managed_by
            ),
            'search': self.convert_spl(),
            # alert trigger condition settings
            'alert_condition': 'search state_change != "no"',
            'alert_type': 'custom',
            # set to run every 1 minute --  this could be something user configurable as well
            'cron_schedule': '*/1 * * * *',
            'is_scheduled': 1,
            # enable actions (REST doc is inaccurate -
            # http://docs.splunk.com/Documentation/Splunk/7.0.2/RESTREF/RESTsearch#saved.2Fsearches, actions cannot
            # be enabled by setting action.<action_name> to be 1)
            'actions': ','.join(map(lambda ac: ac.action_name, self.actions)),
            # set earliest & latest time
            'dispatch.earliest_time': '-2m',
            'dispatch.latest_time': 'now'
        }
        # add custom alert action data
        for action in self.actions:
            data.update(action.to_params())
        return data
