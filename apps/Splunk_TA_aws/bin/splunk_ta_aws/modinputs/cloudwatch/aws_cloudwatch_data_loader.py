import threading
import time
import random

import aws_cloudwatch_consts as acc
import splunksdc.log as logging
import aws_cloudwatch_checkpointer as ackpt
import splunk_ta_aws.common.ta_aws_consts as tac
import splunk_ta_aws.common.ta_aws_common as tacommon
import boto3

logger = logging.get_module_logger()


class CloudWatchClient(object):
    def __init__(self, config):
        self._server_uri = config[tac.server_uri]
        self._session_key = config[tac.session_key]
        self._aws_account = config[tac.aws_account]
        self._aws_iam_role = config[tac.aws_iam_role]
        self._region_name = config['region']
        self._credentials = self._load_credentials()
        self._client = self._create_boto3_client(self._credentials)
        self._ec2_client = self._create_boto3_ec2_client(self._credentials)

    def _load_credentials(self):
        credentials = tacommon.load_credentials_from_cache(
            self._server_uri,
            self._session_key,
            self._aws_account,
            self._aws_iam_role
        )
        return credentials

    def _create_boto3_client(self, credentials):
        self._client = boto3.client(
            'cloudwatch',
            region_name=self._region_name,
            aws_access_key_id=credentials.aws_access_key_id,
            aws_secret_access_key=credentials.aws_secret_access_key,
            aws_session_token=credentials.aws_session_token
        )
        return self._client

    def _create_boto3_ec2_client(self, credentials):
        self._ec2_client = boto3.client(
            'ec2',
            region_name=self._region_name,
            aws_access_key_id=credentials.aws_access_key_id,
            aws_secret_access_key=credentials.aws_secret_access_key,
            aws_session_token=credentials.aws_session_token
        )
        return self._ec2_client

    def require_boto3_client(self):
        if self._credentials.need_retire():
            credentials = self._load_credentials()
            self._client = self._create_boto3_client(credentials)
            self._credentials = credentials
        return self._client

    def require_boto3_ec2_client(self):
        if self._credentials.need_retire():
            credentials = self._load_credentials()
            self._ec2_client = self._create_boto3_ec2_client(credentials)
            self._credentials = credentials
        return self._ec2_client

    def get_account_id(self):
        return self._credentials.account_id


class CloudWatchDataLoader(object):
    def __init__(self, config):
        """
        :config: a list of dict object
        {
        "polling_interval": 60,
        "sourcetype": yyy,
        "index": zzz,
        "region": xxx,
        "key_id": aws key id,
        "secret_key": aws secret key
        "period": 60,
        "metric_namespace": namespace,
        "statistics": statistics
        "metric_configs": [
            {
                "Dimensions": [{"Value": "i-8b9eaa2f", "Name": "InstanceId"}],
                "MetricName": metric_name,
            },
        ],
        }
        """

        tacommon.set_proxy_env(config)
        self._config = config
        self._stopped = False
        self._lock = threading.Lock()
        self._ckpt = ackpt.CloudWatchCheckpointer(config)
        self._source = "{}:{}".format(
            config[tac.region], config[acc.metric_namespace])
        self._max_api_saver_count = \
            self._config[acc.max_api_saver_time] / self._config[acc.period]

        self._client = CloudWatchClient(config)

        self._supplemental_data = {
            acc.period: config[acc.period],
            tac.account_id: self._client.get_account_id(),
        }

        self._instances_data_list = []
        self._metadata_name_list = [
            'ImageId', 'InstanceId', 'InstanceType', 'PrivateIpAddress',
            'PublicIpAddress', 'PrivateDnsName', 'PublicDnsName', 'Architecture'
        ]

    def __call__(self):
        with logging.LogContext(datainput=self._config[tac.datainput]):
            self.index_data()

    def index_data(self):
        start = time.time()
        with logging.LogContext(start_time=start):
            msg = "collecting cloudwatch namespace={}, metric_name={} datainput={}, end_time={}".format(
                self._config[acc.metric_namespace],
                self._config[acc.metric_configs][0]["MetricName"],
                self._config[tac.datainput],
                self._ckpt.max_end_time())

            if self._config[acc.use_metric_format]:
                if not self._config[tac.use_hec]:
                    logger.warning('Enable HEC to support send event to metric index.')
                    return
                if 'Average' not in self._config[acc.statistics]:
                    logger.warning('Only datapoint contains average statistic is able to send to metric index.')
                    return

            if self._lock.locked():
                logger.debug(
                    "Last round of %s is not done yet", msg)
                return

            logger.info("Start %s", msg)
            with self._lock:
                try:
                    self._do_index_data()
                except Exception:
                    logger.exception("Failed of %s.", msg)
            logger.info("End of %s, one_batch_cost=%s", msg, time.time() - start)

    def _do_index_data(self):
        records = []
        for dimension in self._config[acc.metric_configs]:
            if self._stopped:
                return

            empty_poll = self._ckpt.get_empty_poll(dimension)
            if 2 <= empty_poll <= self._max_api_saver_count:
                self._ckpt.increase_empty_poll(dimension)
                logger.debug(
                    "Skip namespace=%s, dimension=%s, metric_name=%s, "
                    "datainput=%s to save API",
                    self._config[acc.metric_namespace],
                    dimension["Dimensions"], dimension["MetricName"],
                    self._config[tac.datainput])
                continue

            start, end = self._ckpt.get_time_range(dimension)
            client = self._client.require_boto3_client()
            datapoints = self._do_one_dimension(client, dimension, start, end)
            if datapoints:
                logger.debug("Successfully get statistics.",
                             dimension=dimension,
                             datainput=self._config[tac.datainput],
                             start=start,
                             end=end)
                self._ckpt.reset_empty_poll(dimension)
                self._ckpt.set_start_time(dimension, end)
                records.append([dimension, datapoints])
            else:
                logger.debug("Failed to get statistics.",
                             dimension=dimension,
                             datainput=self._config[tac.datainput],
                             start=start,
                             end=end)
                if empty_poll > self._max_api_saver_count:
                    self._ckpt.reset_empty_poll(dimension)
                self._ckpt.increase_empty_poll(dimension)

        if records:
            self._index_data(records)

    def _handle_too_many_datapoints(self, e, dimension):
        if (e.message and
                    "InvalidParameterCombination" in e.message and
                    "reduce the datapoints" in e.message):
            self._ckpt.progress_start_time(dimension, 1000)
            logger.info(
                "Handle too many datainputs for namespace=%s, dimension=%s,"
                "metric_name=%s, datainput=%s. New start_time=%s",
                self._config[acc.metric_namespace],
                dimension["Dimensions"],
                dimension["MetricName"],
                self._config[tac.datainput],
                self._ckpt.get_start_time(dimension))
            return True
        return False

    def _do_one_dimension(self, client, dimension, start_time, end_time):
        if start_time == end_time:
            return None

        # perf_start = time.time()
        logger.debug(
            "Collect dimensions=%s, start_time=%s, end_time=%s for datainput=%s",
            dimension, start_time, end_time, self._config[tac.datainput])

        for i in xrange(4):
            try:
                response = client.get_metric_statistics(
                    Namespace=self._config[acc.metric_namespace],
                    MetricName=dimension["MetricName"],
                    Dimensions=dimension["Dimensions"],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=self._config[acc.period],
                    Statistics=self._config[acc.statistics])
            except Exception as ex:
                if "Rate exceeded" in ex.message:
                    tacommon.sleep_until(
                        random.randint(20, 60), self.stopped)
                logger.exception(
                    "Failed to get metrics for namespace=%s, dimension=%s,"
                    "metric_name=%s, datainput=%s, start_time=%s, "
                    "end_time=%s.",
                    self._config[acc.metric_namespace],
                    dimension["Dimensions"],
                    dimension["MetricName"],
                    self._config[tac.datainput],
                    start_time, end_time)
                self._handle_too_many_datapoints(ex, dimension)
                tacommon.sleep_until(2 ** (i + 1), self.stopped)
            else:
                break
        else:
            return None

        if not tacommon.is_http_ok(response):
            logger.error(
                "Failed to get metrics for namespace=%s, dimension=%s, "
                "metric_name=%s, errorcode=%s.",
                self._config[acc.metric_namespace],
                dimension["Dimensions"],
                dimension["MetricName"],
                tacommon.http_code(response))
            return None

        # logger.debug("one_dimension_cost=%s", time.time() - perf_start)
        return response.get("Datapoints")

    @staticmethod
    def _build_dimension_str(dimension):
        return ",".join(
            ["{Name}=[{Value}]".format(**d)
             for d in sorted(dimension["Dimensions"])])

    def _index_data(self, records):
        writer = self._config[tac.event_writer]
        sourcetype = self._config.get(tac.sourcetype, "aws:cloudwatch")
        events = []
        use_metric_format = self._config[acc.use_metric_format]
        if use_metric_format:
            client = self._client.require_boto3_ec2_client()
            self._instances_data_list = self._get_instance_metadata(client)
        for dimension, datapoints in records:
            for datapoint in datapoints:
                datapoint.update(self._supplemental_data)
                evt_time = tacommon.total_seconds(datapoint["Timestamp"])
                del datapoint["Timestamp"]
                if use_metric_format:
                    metric_datapoint = self._create_metric_datapoint(dimension, datapoint)
                    data = self._build_metric_str(metric_datapoint, evt_time)
                    fields = metric_datapoint
                else:
                    datapoint[acc.metric_dimensions] = self._build_dimension_str(dimension)
                    datapoint[acc.metric_name] = dimension["MetricName"]
                    data = datapoint
                    fields = None
                event = writer.create_event(
                    index=self._config.get(tac.index, "default"),
                    host=self._config.get(tac.host, ""),
                    source=self._source,
                    sourcetype=sourcetype,
                    time=evt_time,
                    unbroken=False,
                    done=False,
                    events=data,
                    fields=fields)
                events.append(event)
        writer.write_events(events, retry=10)

    def _create_metric_datapoint(self, dimension, datapoint):
        metric_data = dict()
        metric_data["metric_name"] = "{namespace}.{metric_name}".format(namespace=self._config[acc.metric_namespace],
                                                                        metric_name=dimension["MetricName"])
        metric_data["metric_type"] = self._config[acc.metric_namespace]
        metric_data["_value"] = datapoint["Average"]
        metric_data["unit"] = datapoint["Unit"]
        metric_data["region"] = self._config[tac.region]

        for dim in dimension.get("Dimensions", []):
            metric_data[dim["Name"]] = dim["Value"]
            for instance_data in self._instances_data_list:
                if (dim["Value"] == instance_data["InstanceId"]):
                    for name in self._metadata_name_list:
                        if name in instance_data:
                            # If instance metadata is not a string, then it will get flattened out, the certain
                            # instance metadata will be done as part of PBL-1444.
                            metric_data[name] = instance_data[name]

                    # loop through Tags, to get all tags and put into custom_dims
                    # <type 'list'>: [{u'Value': 'waitomo team', u'Key': 'owner'}, {u'Value': 'testing', u'Key': 'purpose'}]
                    for tag in instance_data['Tags']:
                        k = tag.get("Key")
                        v = tag.get("Value")
                        if k in metric_data.keys():
                            str_list = metric_data[k].split(",")
                            if v not in str_list:
                                str_list.append(v)
                                metric_data[k] = ",".join(str_list)
                        else:
                            metric_data[k] = v

        return metric_data

    def _get_instance_metadata(self, client):
        result_key = "Reservations"
        instances_data_list = []

        params = {
            "DryRun": False
        }

        try:
            paginator = client.get_paginator('describe_instances')
            for response in paginator.paginate(**params):
                logger.debug(response)
                if not tacommon.is_http_ok(response):
                    logger.error(
                        "Failed to describe instances, error=%s", response)
                    break

                if not response.get(result_key):
                    logger.error(
                        "describe instances return no result", )
                    break

                for item in response[result_key]:
                    for instance in item["Instances"]:
                        instance_data = dict()
                        # add Tags, Tags is dictionary format data.
                        instance_data['Tags'] = instance['Tags']

                        for name in self._metadata_name_list:
                            # if name is not listed in instance object, skip it.
                            if name in instance:
                                instance_data[name] = instance[name]

                        instances_data_list.append(instance_data)

        except Exception:
            # When we encountered any errors, just return what we have
            logger.exception("Failed to describe instances.")

        return instances_data_list

    def _build_metric_str(self, metric_datapoint, timestamp):
        base_format = "{time} {dimensions}"
        return base_format.format(time=timestamp,
                                  dimensions=" ".join(("{}={}".format(k, v) for k, v in metric_datapoint.items())))

    def get_interval(self):
        return self._config.get(tac.polling_interval, 60)

    def stop(self):
        self._stopped = True
        logger.info("CloudWatchDataLoader is going to exit")

    def stopped(self):
        return self._stopped or self._config[tac.data_loader_mgr].stopped()

    def get_props(self):
        return self._config
