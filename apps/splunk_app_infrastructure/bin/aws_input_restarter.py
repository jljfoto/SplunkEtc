# Copyright 2016 Splunk Inc. All rights reserved.
# Environment configuration
import em_declare  # noqa
# Standard Python Libraries
import sys
import traceback
import json
# Third-Party Libraries
import urllib
import urllib2
import modinput_wrapper.base_modinput
from splunklib import modularinput as smi
# Custom Libraries
import em_constants
import em_common as EMCommon
import logging_utility

logger = logging_utility.getLogger()


class AWSInputRestarter(modinput_wrapper.base_modinput.SingleInstanceModInput):
    """
    AWS Input Restarter
    This ModInput restarts certain AWS inputs to workaround TA-AWS bugs
    """

    def __init__(self):
        """
        Init modular input
        """
        super(AWSInputRestarter, self).__init__('em', 'aws_input_restarter')

    def get_scheme(self):
        """
        Overloaded splunklib modularinput method
        """
        scheme = smi.Scheme('aws_input_restarter')
        scheme.title = ('Splunk Insights for Infrastructure - AWS Input Restarter')
        scheme.description = (
            'Restarts certain AWS inputs to workaround TA-AWS bugs')
        log_level = 'The logging level of the modular input. Defaults to DEBUG'
        scheme.add_argument(smi.Argument('log_level', title='Log Level',
                                         description=log_level,
                                         required_on_create=False))

        return scheme

    def get_app_name(self):
        """
        Overloaded splunklib modularinput method
        """
        return em_constants.APP_NAME

    def validate_input(self, definition):
        """
        Overloaded splunklib modularinput method
        """
        pass

    def collect_events(self, inputs, ew):
        """
        Main loop function, run every "interval" seconds

        This loops picks one CloudWatch input and restarts it

        :return: void
        """
        self.session_key = self._input_definition.metadata['session_key']
        input_stanza, stanza_args = inputs.inputs.popitem()
        try:
            request = self.generate_cloudwatch_input_request('GET')

            logger.info('Fetching AWS CloudWatch inputs...')
            response = urllib2.urlopen(request)
            response = json.loads(response.read())

            # If there's an input, disable then enable it
            if not len(response.get('entry', [])):
                return

            input_name = response['entry'][0]['name']
            logger.info('Attempting to restart AWS CloudWatch input: ' + input_name)
            disable_request = self.generate_cloudwatch_input_request(
                'POST',
                data={'disabled': 1},
                name=input_name)

            enable_request = self.generate_cloudwatch_input_request(
                'POST',
                data={'disabled': 0},
                name=input_name)

            logger.info('Disabling AWS CloudWatch input: ' + input_name)
            disable_response = urllib2.urlopen(disable_request)
            disable_response = json.loads(disable_response.read())

            logger.info('Enabling AWS CloudWatch input: ' + input_name)
            enable_response = urllib2.urlopen(enable_request)
            enable_response = json.loads(enable_response.read())

            logger.info('Modular input execution complete!')
        except:
            error_type, error, tb = sys.exc_info()
            message = 'Modular input execution failed: ' + unicode(error)
            logger.error(message + '\nTraceback:\n' + ''.join(traceback.format_tb(tb)))

    def generate_cloudwatch_input_request(self, method, data=None, name=None):
        base_url = '%s/servicesNS/nobody/Splunk_TA_aws/splunk_ta_aws_aws_cloudwatch/%s?%s'
        headers = {
            'Authorization': 'Splunk %s' % self.session_key,
            'Content-Type': 'application/json'
        }

        # Handle the query params that are passed in
        server_uri = EMCommon.get_server_uri()
        query_params = dict(output_mode='json')
        query_params['count'] = 1
        query_params['offset'] = 0

        # Build the URL and make the request
        url = base_url % (server_uri, name or '', urllib.urlencode(query_params))
        request = urllib2.Request(
            url,
            urllib.urlencode(data) if data else None,
            headers=headers)
        request.get_method = lambda: method

        return request

if __name__ == '__main__':
    exitcode = AWSInputRestarter().run(sys.argv)
    sys.exit(exitcode)
    pass
