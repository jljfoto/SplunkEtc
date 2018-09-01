# Copyright 2016 Splunk Inc. All rights reserved.
APP_NAME = 'splunk_app_infrastructure'

STORE_COLLECTORS = 'em_collector_configs'
STORE_ENTITIES = 'em_entities'
STORE_GROUPS = 'em_groups'
STORE_THRESHOLDS = 'em_thresholds'
INDEX_METRICS = 'em_metrics'
DEFAULT_BATCH_SIZE = 200
ACTIVE = 'active'
INACTIVE = 'inactive'
DISABLED = 'disabled'

# Default metric used for color by in tile view
DEFAULT_METRIC_FOR_COLOR_BY = 'Availability'

# Endpoint to fetch latest created alerts
LATEST_ALERTS_ENDPOINT = '%s/servicesNS/-/%s/admin/alerts/-?%s'

# Endpoint to fetch metadata about created alert
ALERTS_METADATA_ENDPOINT = '%s/servicesNS/-/%s/saved/searches/%s?%s'

# Endpoint to fetch results via search_id
SEARCH_RESULTS_ENDPOINT = '%s/servicesNS/-/%s/search/jobs/%s/results'

# Regular expression to extract alerting entity and alerting metric
ALERTS_SEARCH_EXTRACTION = r'\(?\"(host|InstanceId)\"=\"(?P<alerting_entity>[^\"]+)\"\)? ' \
    'AND metric_name=\"(?P<metric_name>[^\"]+)\"'

COLLECTORS = [
    {
        # Name of this collector. Unique value
        'name': 'os',
        # Title of this collector
        'title': 'OS Metrics Collector',
        # Predicate to search for entities
        # which are collected by this collector
        'source_predicate': 'cpu.*',
        # Dimensions which identifies entity's title
        'title_dimension': 'host',
        # Dimensions which identifies the entity
        'identifier_dimensions': ['host'],
        # Dimensions which describes the entity
        'informational_dimensions': '*',
        # Blacklisted dimensions we don't want to collect
        'blacklisted_dimensions': ['punct', 'val', 'metric_type', 'cpu', 'extracted_host'],
        # It's possible there is a lag time when events hit HEC endpoint
        # until events are indexed. Default is 10 seconds
        'monitoring_lag': 10,
        # Search timerange, how long does the search look back
        'monitoring_calculation_window': 60,
        # Dimensions that can be mapped to human-readable strings
        # This is an array to make it an ordered list
        'dimension_display_names': [
            {'os': {'en-us': 'OS'}},
            {'ip': {'en-us': 'IP Address'}},
            {'os_version': {'en-us': 'Version'}}
        ],
        # Enabled/Disabled
        'disabled': 0,
        # Vital OS metrics
        'vital_metrics': [
            'cpu.system',
            'cpu.user',
            'cpu.idle',
            'memory.free',
        ],
        # Correlated event data used to construct search for related log events
        'correlated_event_data': {
            'unix_logs': {
                # base search is used as a first pass filer to find events
                # correlated to this collector -- eg. sourcetype=syslog
                'base_search': {
                    # a Boolean filter, takes a boolean operator and a list of filters
                    # (matching BooleanFilter class in em_correlation_filters)
                    'type': 'or',
                    'filters': [
                        {
                            # a Basic filter, takes a type, field and values
                            # (matching BasicFilter class in em_correlation_filters)
                            'type': 'include',
                            'field': 'sourcetype',
                            'values': ['*']
                        }
                    ]
                },
                # entity filters are used to correlate between metrics and logs
                # by searching for logs whose value of event_field is the value of dimension_name
                # in metrics data -- eg. host=alabama.usa.com
                'entity_filters': {
                    'type': 'or',
                    'filters': [
                        {
                            # an Entity filter, takes a event_field and dimension_name
                            # (matching EntityFilter class in em_correlation_filters)
                            'event_field': 'host',
                            'dimension_name': 'host'
                        }
                    ]
                }
            }
        }
    },
    {
        'name': 'aws_cloudwatch_ec2',
        'title': 'AWS CloudWatch EC2 Metrics Collector',
        'source_predicate': 'AWS/EC2*',
        'title_dimension': 'InstanceId',
        'identifier_dimensions': ['InstanceId'],
        'informational_dimensions': '*',
        'blacklisted_dimensions': ['punct', 'val', 'metric_type', 'unit', 'host'],
        'monitoring_lag': 10,
        # 2x default polling interval because AWS CloudWatch has a 10min delay in data sampling
        'monitoring_calculation_window': 1200,
        'disabled': 0,
        'dimension_display_names': [
            {'InstanceType': {'en-us': 'Instance Type'}},
            {'ImageId': {'en-us': 'AMI ID'}},
            {'region': {'en-us': 'AWS Region'}},
            {'InstanceId': {'en-us': 'Instance ID'}},
            {'PublicDnsName': {'en-us': 'DNS Name (public)'}},
            {'PrivateDnsName': {'en-us': 'DNS Name (private)'}},
            {'PublicIpAddress': {'en-us': 'IP Address (public)'}},
            {'PrivateIpAddress': {'en-us': 'IP Address (private)'}},
            {'Architecture': {'en-us': 'Architecture'}},
        ],
        'correlated_event_data': {
            'cloudwatchlogs': {
                'base_search': {
                    'type': 'or',
                    'filters': [
                        {
                            'type': 'include',
                            'field': 'sourcetype',
                            'values': ['aws:cloudwatchlogs']
                        }
                    ]
                },
                'entity_filters': {
                    'type': 'or',
                    'filters': [
                        {
                            'event_field': 'source',
                            'dimension_name': 'InstanceId',
                            # because sometimes exact match cannot be performed
                            # due to the format of data - using "partial" indicates that we expect the value
                            # of "source" in logs data includes that of "InstanceId" in metrics data
                            'match_criteria': 'partial'
                        }
                    ]
                }
            }
        }
    },
    {
        'name': 'aws_cloudwatch_ebs',
        'title': 'AWS CloudWatch EBS Metrics Collector',
        'source_predicate': 'AWS/EBS*',
        'title_dimension': 'VolumeId',
        'identifier_dimensions': ['VolumeId'],
        'informational_dimensions': '*',
        'blacklisted_dimensions': ['punct', 'val', 'metric_type', 'unit', 'host'],
        'monitoring_lag': 10,
        # 2x default polling interval because AWS CloudWatch has a 10min delay in data sampling
        'monitoring_calculation_window': 1200,
        'disabled': 0,
    },
    {
        'name': 'aws_cloudwatch_elb',
        'title': 'AWS CloudWatch ELB Metrics Collector',
        'source_predicate': 'AWS/ELB*',
        'title_dimension': 'LoadBalancerName',
        'identifier_dimensions': ['LoadBalancerName'],
        'informational_dimensions': '*',
        'blacklisted_dimensions': ['punct', 'val', 'metric_type', 'unit', 'host'],
        'monitoring_lag': 10,
        # 2x default polling interval because AWS CloudWatch has a 10min delay in data sampling
        'monitoring_calculation_window': 1200,
        'disabled': 0,
    }
]
