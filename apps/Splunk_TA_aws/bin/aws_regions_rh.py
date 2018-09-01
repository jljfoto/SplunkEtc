"""
Custom REST Endpoint for enumerating AWS regions.
"""

import aws_bootstrap_env

from boto3.session import Session
from botocore.session import create_loader

import splunk
import splunk.admin
from splunksdc import log as logging
from splunktaucclib.rest_handler.error import RestError
import splunk_ta_aws.common.ta_aws_consts as tac
import splunk_ta_aws.common.ta_aws_common as tacommon
from solnlib.splunkenv import get_splunkd_uri

logger = logging.get_module_logger()

ACCOUNT_OPT_ARGS = ['account', 'aws_account']
DUMMY_BOTO3_SESSION = Session()


def _load_description_of_regions():
    loader = create_loader()
    endpoints = loader.load_data('endpoints')
    regions = dict()
    for partition in endpoints['partitions']:
        regions.update(partition['regions'])
    return regions


class DummyRegion(object):
    def __init__(self, name):
        if isinstance(name, unicode):
            name = name.encode('utf-8')
        self.name = name

    @staticmethod
    def from_names(names):
        return [DummyRegion(name) for name in names]


class ConfigHandler(splunk.admin.MConfigHandler):

    def setup(self):
        self.supportedArgs.addReqArg('aws_service')
        for account_arg in ACCOUNT_OPT_ARGS:
            self.supportedArgs.addOptArg(account_arg)

    def handleList(self, confInfo):
        service = self.callerArgs.data['aws_service'][0]

        account_category = None
        for account_arg in ACCOUNT_OPT_ARGS:
            if account_arg in self.callerArgs.data:
                account_name = self.callerArgs.data[account_arg][0]
                account = tacommon.get_account(get_splunkd_uri(), self.getSessionKey(), account_name)
                account_category = account.category
                break

        if service == 'aws_cloudwatch':
            import boto.ec2.cloudwatch
            regions = boto.ec2.cloudwatch.regions()
        elif service == 'aws_cloudtrail':
            import boto.cloudtrail
            regions = boto.cloudtrail.regions()
        elif service == 'aws_config':
            import boto.sqs
            regions = boto.sqs.regions()
        elif service == 'aws_config_rule':
            import boto.configservice
            # FIXME, hard code for now
            regions = DummyRegion.from_names([
                'us-east-1',
                'us-east-2',
                'us-west-1',
                'us-west-2',
                'ap-southeast-1',
                'ap-southeast-2',
                'ap-northeast-1',
                'ap-northeast-2',
                'eu-central-1',
                'eu-west-1',
            ])
        elif service == 'aws_cloudwatch_logs':
            import boto.logs
            regions = boto.logs.regions()
        elif service == 'aws_description':
            import boto.ec2
            regions = boto.ec2.regions()
        elif service == 'aws_inspector':
            regions = DummyRegion.from_names([
                'us-east-1',
                'us-west-2',
                'ap-northeast-2',
                'ap-south-1',
                'ap-southeast-2',
                'ap-northeast-1',
                'eu-west-1',
            ])
        elif service == 'aws_kinesis':
            regions = DummyRegion.from_names(
                DUMMY_BOTO3_SESSION.get_available_regions('kinesis', 'aws') +
                DUMMY_BOTO3_SESSION.get_available_regions('kinesis', 'aws-us-gov') +
                DUMMY_BOTO3_SESSION.get_available_regions('kinesis', 'aws-cn')
            )
        elif service == 'aws_sqs_based_s3' or service == 'splunk_ta_aws_sqs':
            import boto.sqs
            regions = boto.sqs.regions()
        elif service == 'aws_s3':
            import boto.s3
            regions = boto.s3.regions()
        else:
            msg = "Unsupported aws_service={} specified.".format(service)
            raise RestError(400, msg)
        descriptions = _load_description_of_regions()
        for region in regions:
            region_category = tac.RegionCategory.COMMERCIAL
            if region.name.find('us-gov-') != -1:
                region_category = tac.RegionCategory.USGOV
            elif region.name.find('cn-') != -1:
                region_category = tac.RegionCategory.CHINA

            if account_category is None or region_category == account_category:
                confInfo[region.name].append('label', descriptions[region.name]['description'])

        if len(confInfo) == 0:
            raise RestError(400, 'This service is not available for your AWS account.')

def main():
    splunk.admin.init(ConfigHandler, splunk.admin.CONTEXT_NONE)


if __name__ == '__main__':
    main()
