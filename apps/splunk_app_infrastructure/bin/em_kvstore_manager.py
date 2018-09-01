# Copyright 2016 Splunk Inc. All rights reserved.
# Environment configuration
# N/A
# Standard Python Libraries
import json
# Third-Party Libraries
import urllib
import urllib2
# Custom Libraries
import em_common
from em_exceptions import ArgValidationException
import logging_utility
from em_constants import DEFAULT_BATCH_SIZE

logger = logging_utility.getLogger()


class EMKVStoreManager:
    """
    KVStore access
    """

    def __init__(self, collection, server_uri,
                 session_key, app, owner='nobody'):
        """
        Return KVStore Manager object
        """
        self.collection = urllib.quote(collection)
        self.server_uri = server_uri
        self.session_key = session_key
        self.app = urllib.quote(app)
        self.owner = urllib.quote(owner)

    def uri(self, name=None, query=None):
        """
        Create uri for kvstore request

        :param name: name after collection, usually _key
        :param query: query params
        :return: uri for kvstore request
        """
        qs = dict(output_mode='json')
        if query is not None:
            qs.update(query)
        if name is not None:
            return '%s/servicesNS/%s/%s/storage/collections/data/%s/%s?%s' % (
                self.server_uri, self.owner, self.app,
                self.collection, urllib.quote(name), urllib.urlencode(qs))
        else:
            return '%s/servicesNS/%s/%s/storage/collections/data/%s?%s' % (
                self.server_uri, self.owner, self.app,
                self.collection, urllib.urlencode(qs))

    def build_req(self, method, data=None, name=None, query=None):
        """
        Build request object

        :param method: HTTP Method
        :param data: body data
        :param name: key,etc.
        :param query: query params
        :return: request object
        """
        h = {'Authorization': 'Splunk %s' % self.session_key}
        if h is not None:
            h['Content-Type'] = 'application/json'
        req = urllib2.Request(self.uri(name, query=query), json.dumps(data), h)
        req.get_method = lambda: method
        return req

    def load(self, count=0, offset=0, fields='', params={}):
        """
        Load records with limit

        :param count: limitation
        :return: dict of records
        """
        req = self.build_req('GET', query=dict(
            limit=count, skip=offset, fields=fields, **params))
        res = urllib2.urlopen(req)
        return json.loads(res.read())

    def get(self, key):
        """
        Get records by _key

        :param key: record's key
        :return: dict of records
        """
        req = self.build_req('GET', name=key)
        try:
            res = urllib2.urlopen(req)
            return json.loads(res.read())
        except urllib2.HTTPError, e:
            if e.code == 404:
                return None
            else:
                raise e

    def update(self, key, data):
        """
        Update record by _key

        :param key: record's key
        :param data: body data dict
        :return: result object
        """
        req = self.build_req('PUT', name=key, data=data)
        res = urllib2.urlopen(req)
        return json.loads(res.read())

    def create(self, key, data):
        """
        Create record by _key

        :param key: record's key
        :param data: body data dict
        :return: result object
        """
        req = self.build_req('POST', data=(
            em_common.merge_dicts({"_key": key}, data)))
        res = urllib2.urlopen(req)
        return json.loads(res.read())

    def upsert(self, key, data):
        """
        Insert if it doesn't exist
        Update if it exists
        """
        r = self.get(key)
        if r is None:
            return self.create(key, data)
        else:
            return self.update(key, data)

    def delete(self, key):
        """
        Delete record by _key

        :param key: record's key
        :return: void
        """
        req = self.build_req('DELETE', name=key)
        urllib2.urlopen(req)

    def bulk_delete(self, query):
        """
        Bulk delete operation

        :param query: query
        :return: void
        """
        if not query:
            raise ArgValidationException(
                "Query is required for bulk_delete")

        try:
            req = self.build_req('DELETE', query=query)
            urllib2.urlopen(req)
        except urllib2.HTTPError, e:
            raise e

    def batch_save(self, data):
        """
        Perform multiple save operations in a batch
        """
        logger.debug('Batch saving data: {}'.format(data))
        if not data:
            raise ArgValidationException(
                "Batch saving failed: Batch is empty.")
        batches = (data[x:x + DEFAULT_BATCH_SIZE] for x in xrange(0, len(data), DEFAULT_BATCH_SIZE))
        for batch in batches:
            try:
                req = self.build_req('POST', name='batch_save', data=batch)
                urllib2.urlopen(req)
            except urllib2.HTTPError, e:
                logger.error(e)
                raise e
