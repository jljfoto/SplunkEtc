import sys
import json
from urllib import urlencode
import urllib2


def log_event(settings, event, source, sourcetype, host, index):
    if event is None:
        sys.stderr.write("ERROR No event provided\n")
        return False
    query = [('source', source), ('sourcetype', sourcetype), ('index', index)]
    if host:
        query.append(('host', host))
    url = '%s/services/receivers/simple?%s' % (settings.get('server_uri'), urlencode(query))
    try:
        encoded_body = unicode(event).encode('utf-8')
        req = urllib2.Request(url, encoded_body, {'Authorization': 'Splunk %s' % settings.get('session_key')})
        res = urllib2.urlopen(req)
        if 200 <= res.code < 300:
            sys.stderr.write("DEBUG receiver endpoint responded with HTTP status=%d\n" % res.code)
            return True
        else:
            sys.stderr.write("ERROR receiver endpoint responded with HTTP status=%d\n" % res.code)
            return False
    except urllib2.HTTPError as e:
        sys.stderr.write("ERROR Error sending receiver request: %s\n" % e)
    except urllib2.URLError as e:
        sys.stderr.write("ERROR Error sending receiver request: %s\n" % e)
    except Exception as e:
        sys.stderr.write("ERROR Error %s\n" % e)
    return False


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] != "--execute":
        sys.stderr.write("FATAL Unsupported execution mode (expected --execute flag)\n")
        sys.exit(1)
    try:
        settings = json.loads(sys.stdin.read())
        config = settings['configuration']
        success = log_event(
            settings,
            event=config.get('event'),
            source=config.get('source'),
            sourcetype=config.get('sourcetype'),
            host=config.get('host'),
            index=config.get('index')
        )
        if not success:
            sys.exit(2)
    except Exception as e:
        sys.stderr.write("ERROR Unexpected error: %s\n" % e)
        sys.exit(3)
