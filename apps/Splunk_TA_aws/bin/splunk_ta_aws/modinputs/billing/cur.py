import time
import csv
from datetime import timedelta
import json
import json.encoder
import re
import tempfile
import itertools
import cStringIO as StringIO
from splunksdc import logging
from splunksdc.collector import SimpleCollectorV1
from splunksdc.config import StanzaParser, IntegerField, StringField
from splunksdc.config import LogLevelField, DateTimeField
from splunksdc.archive import ArchiveFactory
from splunksdc.utils import LogExceptions, LogWith
from splunk_ta_aws import set_log_level
from splunk_ta_aws.common.proxy import ProxySettings
from splunk_ta_aws.common.credentials import AWSCredentialsProviderFactory, AWSCredentialsCache
from splunk_ta_aws.common.s3 import S3Bucket


logger = logging.get_module_logger()


class AWSBillingSettings(object):
    @classmethod
    def load(cls, config):
        content = config.load('aws_settings', stanza='aws_billing_cur')
        parser = StanzaParser([
            LogLevelField('log_level', default='WARNING')
        ])
        settings = parser.parse(content)
        return cls(settings)

    def __init__(self, settings):
        self._settings = settings

    def setup_log_level(self):
        set_log_level(self._settings.log_level)


class AWSBillingDataInput(object):
    def __init__(self, stanza):
        self._kind = stanza.kind
        self._name = stanza.name
        self._args = stanza.content
        self._start_time = int(time.time())

    @property
    def name(self):
        return self._name

    @property
    def start_time(self):
        return self._start_time

    @LogWith(datainput=name, start_time=start_time)
    @LogExceptions(logger, 'Data input was interrupted by an unhandled exception.', lambda e: -1)
    def run(self, app, config):
        settings = AWSBillingSettings.load(config)
        settings.setup_log_level()
        proxy = ProxySettings.load(config)
        proxy.hook_boto3_get_proxies()

        credentials = self._create_credentials(config)
        bucket = self._create_bucket()
        options = self._create_options()
        event_writer = self._create_event_writer(app)
        sourcetype = self._create_sourcetype()

        with app.open_checkpoint(self._name) as checkpoint:
            handler = AWSCostUsageReportHandler(
                checkpoint, credentials, bucket, event_writer, sourcetype, options
            )
            return handler.run(app, config)

    def _create_credentials(self, config):
        parser = StanzaParser([
            StringField('aws_account', required=True),
            StringField('aws_iam_role'),
        ])
        args = self._extract_arguments(parser)
        factory = AWSCredentialsProviderFactory(config)
        provider = factory.create(args.aws_account, args.aws_iam_role)
        credentials = AWSCredentialsCache(provider)
        return credentials

    def _create_bucket(self):
        parser = StanzaParser([
            StringField('bucket_name', required=True),
            StringField('bucket_region', required=True),
        ])
        args = self._extract_arguments(parser)
        return S3Bucket(args.bucket_name, args.bucket_region)

    def _create_options(self):
        parser = StanzaParser([
            StringField('report_prefix', default=u''),
            StringField('temp_folder', default=None),
            DateTimeField('start_date', default='1970-01', fmt='%Y-%m'),
            StringField('report_names', default=r'.*')
        ])
        return self._extract_arguments(parser)

    def _create_event_writer(self, app):
        stanza = self._kind + '://' + self._name
        parser = StanzaParser([
            StringField('index'),
            StringField('host'),
            StringField('stanza', fillempty=stanza),
        ])
        args = self._extract_arguments(parser)
        return app.create_event_writer(**vars(args))

    def _create_sourcetype(self):
        parser = StanzaParser([
            StringField('sourcetype', default='aws:billing:cur'),
        ])
        args = self._extract_arguments(parser)
        return args.sourcetype

    def _extract_arguments(self, parser):
        return parser.parse(self._args)


class AWSCostUsageReportJournal(object):
    def __init__(self, store):
        self._store = store

    def is_done(self, item):
        pair = self._store.find(item.key)
        if not pair:
            return False
        x = pair.value.strip('"')
        y = item.etag.strip('"')
        return x == y

    def mark_done(self, item):
        self._store.set(item.key, item.etag)

    def sweep(self):
        self._store.sweep()


class BatchEventWriter(object):
    def __init__(self, writer, source, sourcetype, **kwargs):
        self._writer = writer
        self._source = source
        self._sourcetype = sourcetype
        self._cache_lines = []
        self._cache_size = 0
        self._cache_threshold = 4 * 1024 * 1024
        self._meta_keys = kwargs.keys()
        self._meta_values = kwargs.values()

    def write(self, data):
        self._append(data)
        self._commit()

    def _append(self, line):
        self._cache_lines.append(line)
        self._cache_size += len(line)

    def _commit(self, flush=False):
        if not self._cache_size:
            return
        if self._cache_size >= self._cache_threshold or flush:
            logger.debug('Start writing events.', count=len(self._cache_lines))
            data = '\n'.join(itertools.chain(self._cache_lines, ['']))
            self._writer.write_fileobj(data, source=self._source, sourcetype=self._sourcetype)
            self._cache_lines = []
            self._cache_size = 0
            logger.debug('Write events done.', volume=len(data))

    def flush(self):
        self._commit(flush=True)


class CSVParser(object):
    def __init__(self, **kwargs):
        self._meta_keys = kwargs.keys()
        self._meta_values = kwargs.values()

    def parse(self, member):
        reader = csv.reader(member)
        fields = reader.next()
        keys = tuple(itertools.chain(fields, self._meta_keys))
        for row in reader:
            values = itertools.chain(row, self._meta_values)
            data = self._render(zip(keys, values))
            yield data

    @classmethod
    def _render(cls, pairs):
        segments = []
        for key, value in pairs:
            if not value:
                continue
            # encoding the value if whitespaces or quotes were found in value.
            if re.search(r'[ "]', value):
                value = json.encoder.encode_basestring(value)
            segments.append('{0}={1}'.format(key, value))
        return ', '.join(segments)


class AWSCostUsageReportHandler(object):
    _MIN_TTL = timedelta(minutes=30)

    def __init__(self, checkpoint, credentials, bucket, event_writer, sourcetype, options):
        self._credentials = credentials
        self._bucket = bucket
        self._checkpoint = checkpoint
        self._event_writer = event_writer
        self._prefix = options.report_prefix
        self._sourcetype = sourcetype
        self._start_date = options.start_date.strftime('%Y%m')
        self._temp_folder = options.temp_folder
        self._selector = re.compile(options.report_names)
        self._archive = ArchiveFactory.create_default_instance()

    def _is_interested_report(self, name):
        if name == '/':
            return False
        return self._selector.search(name)

    def _discover_reports(self):
        logger.info('Start discovering reports.')
        prefix = self._prefix
        if prefix and not prefix.endswith('/'):
            prefix += '/'
        bucket = self._bucket
        credentials = self._keep_credentials_alive()
        s3 = bucket.client(credentials)
        folders = bucket.list_folders(s3, prefix)
        reports = [name for name in folders if self._is_interested_report(name)]
        logger.info('Discover reports done.', reports=reports)
        return reports

    def _discover_manifests(self, report, start_date):
        logger.info('Start discovering manifests.', report=report)
        date_range_pattern = re.compile(r'\d{8}-\d{8}')
        bucket = self._bucket
        credentials = self._keep_credentials_alive()
        s3 = bucket.client(credentials)
        marker = report + start_date
        manifests = []
        while True:
            files = bucket.list_files(s3, report, marker)
            if not files:
                break
            marker = files[-1].key
            for item in files:
                parts = item.key.split('/')
                if not parts[-1].endswith('-Manifest.json'):
                    continue
                report_date = parts[-2]
                if not date_range_pattern.match(report_date):
                    continue
                if start_date > report_date:
                    continue
                logger.info('Manifest file is found.', key=item.key, etag=item.etag)
                manifests.append(item)
        logger.info('Discovering manifests is done.', report=report)
        return manifests

    def _get_manifest(self, manifest):
        bucket = self._bucket
        credentials = self._keep_credentials_alive()
        s3 = bucket.client(credentials)
        content = StringIO.StringIO()
        bucket.fetch(s3, manifest.key, content)
        return json.load(content)

    def _ingest_report(self, manifest):
        try:
            # use epoch time as transaction id
            txid = str(int(time.time()))
            content = self._get_manifest(manifest)
            count = 0

            for key in content.get('reportKeys', []):
                bucket = self._bucket
                credentials = self._keep_credentials_alive()
                s3 = bucket.client(credentials)
                with self._open_temp_file() as cache:
                    headers = bucket.transfer(s3, key, cache)
                    uri = self._make_uri(key)
                    count += self._index_report(uri, cache, txid)

            self._index_digest(manifest, content, txid, count)
            return True
        except Exception:
            logger.exception('An error occurred while ingesting report.', mainfiest=manifest.key)
            return False

    def _keep_credentials_alive(self):
        if self._credentials.need_retire(self._MIN_TTL):
            self._credentials.refresh()
        return self._credentials

    def _open_temp_file(self):
        return tempfile.NamedTemporaryFile(dir=self._temp_folder)

    def _make_uri(self, key):
        uri = 's3://' + self._bucket.name + '/' + key
        return uri.encode('utf-8')

    def _index_report(self, uri, cache, txid):
        logger.info('Start sending events for indexing', uri=uri)
        count = 0
        for member, uri in self._archive.open(cache, uri):
            batch = BatchEventWriter(self._event_writer, source=uri, sourcetype=self._sourcetype)
            parser = CSVParser(_txid=txid)
            for event in parser.parse(member):
                batch.write(event)
                count += 1
            batch.flush()
        logger.info('Sent report for indexing done.', uri=uri, number_of_event=count)
        return count

    def _index_digest(self, header, content, txid, count):
        # ingest the digest file
        uri = self._make_uri(header.key)
        logger.info('Start sending manifest for indexing', uri=uri, size=header.size, etag=header.etag.strip('"'))
        # by default, the sourcetype of the digest file is the original sourcetype plus ":digest"
        # e.g. aws:billing:cur -> aws:billing:cur:digest
        content['lastModified'] = header.last_modified.replace(tzinfo=None).isoformat()
        content['txid'] = txid
        content['eventCount'] = count
        sourcetype = self._sourcetype + ':digest'
        data = json.dumps(content)
        self._event_writer.write_fileobj(data, source=uri, sourcetype=sourcetype)
        logger.info('Sent digest for indexing done.', uri=uri, size=len(data))

    def run(self, app, config):
        start_date = self._start_date
        journal = AWSCostUsageReportJournal(self._checkpoint)
        for container in self._discover_reports():
            for manifest in self._discover_manifests(container, start_date):
                if app.is_aborted():
                    return 0
                if journal.is_done(manifest):
                    continue
                if self._ingest_report(manifest):
                    journal.mark_done(manifest)
        journal.sweep()
        return 0


def modular_input_run(app, config):
    inputs = app.inputs()
    datainput = AWSBillingDataInput(inputs[0])
    return datainput.run(app, config)


def main():
    from requests.packages import urllib3
    urllib3.disable_warnings()
    arguments = {
        'aws_account': {
            'title': 'The name of AWS account.'
        },
        'aws_iam_role': {
            'title': 'The name of IAM user would be assumed.'
        },
        'bucket_name': {
            'title': 'What is the name of bucket.'
        },
        'bucket_region': {
            'title': 'Where is the bucket located.'
        },
        'report_names': {
            'title': 'A regex pattern for selecting reports.'
        },
        'report_prefix': {
            'title': 'The report prefix.'
        },
        'start_date': {
            'title': 'Monitoring reports later than the date.'
        },
        'temp_folder': {
            'title': 'An alternative temp folder path.'
        },
    }

    SimpleCollectorV1.main(
        modular_input_run,
        title='AWS Billing (Cost And Usage Report)',
        use_single_instance=False,
        arguments=arguments,
    )
