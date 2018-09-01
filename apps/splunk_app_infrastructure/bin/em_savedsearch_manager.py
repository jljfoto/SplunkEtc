import em_constants
import em_common
import urllib
import urllib2
import json
import logging_utility
from em_exceptions import SavedsearchInternalException

logger = logging_utility.getLogger()

# need to set user to 'nobody' because creating savedsearch
# with wildcard user or app name is not allowed
SAVEDSEARCH_ENDPOINT_TEMPLATE = '{server_uri}/servicesNS/nobody/{app_name}/saved/searches/{name}?{query_params}'


class EMSavedSearchManager(object):

    def __init__(self, session_key, server_uri):
        self.session_key = session_key
        self.server_uri = server_uri

    def _build_url(self, name='', query_params=None):
        query_params = {} if not query_params else query_params
        query_params.update({
            'output_mode': 'json'
        })
        url = SAVEDSEARCH_ENDPOINT_TEMPLATE.format(server_uri=em_common.get_server_uri(),
                                                   app_name=em_constants.APP_NAME,
                                                   name=urllib.quote(name),
                                                   query_params=urllib.urlencode(query_params))
        return url

    def _make_request(self, url, method='GET', data=None):
        h = {
            'Authorization': 'Splunk %s' % self.session_key,
            'Content-Type': 'application/json'
        }
        try:
            encoded_data = urllib.urlencode(data) if data else None
            # Note: cannot use json.dumps on data because splunk savedsearch REST doesn't like it
            request = urllib2.Request(url, data=encoded_data, headers=h)
            request.get_method = lambda: method
            response = urllib2.urlopen(request)
            return json.loads(response.read())
        except urllib2.HTTPError as e:
            raise SavedsearchInternalException(e)

    def load(self, count=-1, offset=0):
        url = self._build_url(query_params=dict(
            count=count,
            offset=offset
        ))
        response = self._make_request(url, 'GET')
        return response

    def get(self, name):
        url = self._build_url(name)
        response = self._make_request(url, 'GET')
        return response

    def create(self, data):
        url = self._build_url()
        response = self._make_request(url, 'POST', data=data)
        return response

    def update(self, name, data):
        url = self._build_url(name)
        response = self._make_request(url, 'POST', data=data)
        return response

    def delete(self, name):
        url = self._build_url(name)
        response = self._make_request(url, 'DELETE')
        return response

    def bulk_delete(self, savedsearch_query):
        """
        Yeah, I know this doesn't exactly make use of a more efficient way, but let's
        abstract out the bulk logic here

        There is no bulk delete endpoint for saved searches, so the only way we can do this is
        make 1 call and delete each search individually.
        """
        search_stanza = ' OR '.join(savedsearch_query)
        query_params = {
            'output_mode': 'json',
            'search': search_stanza,
            'count': -1
        }
        fetch_searches_url = self._build_url(query_params=query_params, name='')
        associated_saved_searches = self._make_request(fetch_searches_url, 'GET')
        searches = associated_saved_searches['entry']
        for search in searches:
            search_name = search.get('name')
            delete_search_url = self._build_url(name=search_name)
            logger.info('Deleting the saved search %s...' % search_name)
            self._make_request(delete_search_url, 'DELETE')
