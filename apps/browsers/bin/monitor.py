import sys, platform, os, subprocess, shutil, tempfile, json, time
from biplist import *
import cPickle as pickle
import splunk.bundle as bundle
import splunk.util as util
import pathfinder
import cStringIO as StringIO
import logging

AppPath = os.path.dirname(sys.path[0])
AppName = os.path.basename(AppPath)
SplunkHome = os.environ.get("SPLUNK_HOME")

logFile = os.path.join(SplunkHome, 'var', 'log', 'splunk', 'browsers_app.log')
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(name)s %(levelname)s %(message)s',
                    filename=logFile)
logger = logging.getLogger('monitor')


sqliteExec = {'Windows': 'sqlite3', 
              'Darwin': 'sqlite3_mac', 
              'Linux': 'sqlite3_lin'
             }
ieParserPath = os.path.join(AppPath, 'bin', 'iehv.exe')   

eventBreak = '--------------------------browsers-------------------------------'
            
class Config(object):
    def __init__(self, confName, sessionKey):
        self.sessionKey = sessionKey
        self.confName = confName
        
    def load(self):
        '''
        Read config file
        '''
        config = {}
        conf = None
        try:
            conf = bundle.getConf(self.confName, sessionKey=self.sessionKey, namespace=AppName, owner='-')
        except:
            return None

        for stanza in conf:
            if stanza == 'default':
                continue
            config[stanza] = dict(conf[stanza])
        return config
    
    def write(self, settings):
        if not settings or len(settings) == 0:
            return
            
        try:
            confObj = bundle.getConf(self.confName, sessionKey=self.sessionKey, namespace=AppName, owner='-')
        except:
            try:
                confObj = bundle.createConf(self.confName, sessionKey=self.sessionKey, namespace=AppName, owner='-')
            except Exception,e:
                logger.error('Error creating new conf file')
                return

        
        for stanza, kv in settings.items():
            confObj.beginBatch()
            for k, v in kv.items():
                confObj[stanza][k] = v
            confObj.commitBatch()
            

class CheckpointMgr(object):
    def __init__(self, profileKey):
        self.profileKey = profileKey
        self.cp_file = os.path.join(SplunkHome, 'var', 'lib', 'splunk', 'persistentstorage', 'browsers-checkpoint')
        
    def load(self):
        cp = {}
        if os.path.exists(self.cp_file) and os.path.getsize(self.cp_file) > 0:
            with file(self.cp_file, 'r') as f:
                cp = pickle.load(f)
                cp = cp.get(self.profileKey, {})
        return cp
        
    
    def save(self, type, lastId):
        '''
        Dumps a dict like {<browser/os_user/ff_profile>: {'history':5, 'downloads':1}}, containing the last row's id to a pickled file
        '''
        logger.debug('Save last %s id: %s' % (type, lastId))  
        if os.path.exists(self.cp_file) and os.path.getsize(self.cp_file) > 0:
            with file(self.cp_file, 'r') as f:
                cp = pickle.load(f)
            with file(self.cp_file, 'w') as f:
                if not self.profileKey in cp:
                    cp[self.profileKey] = {}
                cp[self.profileKey][type] = lastId
                pickle.dump(cp, f)
        else:
            cp = {self.profileKey: {type: lastId}}
            try: 
                with file(self.cp_file, 'w') as f:
                    pickle.dump(cp, f)    
            except Exception,e:
                logger.error(e)
                
                
class BrowserMonitor(object):
    def __init__(self, sessionKey):
        self.browsers = {}
        self.sessionKey = sessionKey
        self.sqliteShell = os.path.join(AppPath, 'bin', sqliteExec.get(platform.system()))
        
        # read config file
        self.config = Config(AppName, sessionKey)
        conf = self.config.load()
        if not conf:
            # FTR, init
            profiles = pathfinder.scan()
            idx = {}
            settings = {}
            for user in profiles:
                for browser in profiles[user]:
                    for profile in profiles[user][browser]:
                        idx[browser] = 1 if not idx.get(browser) else idx[browser]+1
                        stanza = '%s_%d' % (browser, idx[browser])
                        kv = {'profile_name': profile,
                              'os_user': user,
                              'disabled': 0}
                        settings[stanza] = kv
            self.config.write(settings)
            self.browsers = settings
        else:
            # just load from config file
            self.browsers = conf
            
    
    def _executeSqlite(self, sqliteFile, sqlQuery, sqlLastId):
        '''
        Runs a sqlQuery search against sqliteFile and saves the last row's id as a checkpoint for next request
        '''
        lastId = 0
       
        fd, tmpPath = tempfile.mkstemp()
        os.close(fd)
        shutil.copyfile(sqliteFile, tmpPath)
            
        cmd = [self.sqliteShell, '-line', tmpPath, sqlQuery]
        logger.debug(' '.join(cmd))
        p = subprocess.Popen(cmd, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate()
        if err:
            logger.error('Nothing was read from %s: %s' % (tmpPath, err))
            if os.path.exists(tmpPath):
                os.remove(tmpPath)
            return None

        for line in StringIO.StringIO(out).readlines():
            if line == '\r\n' or line == '\n':
                line = eventBreak
            print line.replace('\r\n','').replace('\n','')
        print eventBreak
        
        # Now get the last id for checkpoint
        cmd[1] = '-column'
        cmd[3] = sqlLastId
        p = subprocess.Popen(cmd, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        result = p.communicate()
        if not result[1] and result[0]:
            lastId = result[0].strip()
        else:
            logger.error('Error getting last id: %s' % result)
        
        # clean up temp file
        if os.path.exists(tmpPath):
            os.remove(tmpPath)
        
        return lastId
    

    def _processFirefox(self, browser, osUser, profileName):
        profilePath = pathfinder.getProfilePath(browser, osUser, profileName)
        if not profilePath or not os.path.exists(profilePath):
            logger.error('Profile path does not exist: %s ' % profilePath)
            return
        
        profileKey = '%s/%s/%s' % (browser, osUser, profileName)
        cpMgr = CheckpointMgr(profileKey)
        cp = cpMgr.load()
        extra_info =  "'%%s' as 'sourcetype', '%s' as 'browser', '%s' as 'os_user', '%s' as 'browser_profile'" % (browser, osUser, profileName.split('.')[1] if browser=='firefox' else profileName)

        # history
        src = os.path.join(profilePath, 'places.sqlite')
        where = 'WHERE h.id > %s' % cp.get('history') if cp.get('history') else ''
        sql = "SELECT datetime(h.visit_date/1000000,'unixepoch') as dt, p.url as url, p.title as title, h.visit_type as type, %s FROM moz_places p JOIN moz_historyvisits h ON p.id = h.place_id %s" % (extra_info % 'history', where)
        lastIdSql = "SELECT max(id) FROM moz_historyvisits"
        lastId = self._executeSqlite(src, sql, lastIdSql)
        cpMgr.save('history', lastId)
            
        # bookmarks
        src = os.path.join(profilePath, 'places.sqlite')
        where = 'WHERE b.id > %s' % cp.get('bookmarks') if cp.get('bookmarks') else ''
        bookmarksSQL = "SELECT datetime(b.dateAdded/1000000,'unixepoch') as dt, b.title as title, p.url as url, %s FROM moz_places p JOIN moz_bookmarks b ON p.id = b.fk %s" % (extra_info % 'bookmarks', where)
        lastIdSql = "SELECT max(id) FROM moz_bookmarks"
        lastId = self._executeSqlite(src, bookmarksSQL, lastIdSql)
        cpMgr.save('bookmarks', lastId)
        
        # downloads
        src = os.path.join(profilePath, 'downloads.sqlite')
        where = 'WHERE d.id > %s' % cp.get('downloads') if cp.get('downloads') else ''
        downloadsSQL = "SELECT datetime(d.startTime/1000000,'unixepoch') as dt, d.source as source, d.target as target, d.state as state, d.referrer as ref, d.mimeType as mimeType, d.currBytes as currBytes, d.maxBytes as maxBytes, d.preferredAction as prefAction, %s FROM moz_downloads d %s" % (extra_info % 'downloads', where)
        lastIdSql = "SELECT max(id) FROM moz_downloads"
        lastId = self._executeSqlite(src, downloadsSQL, lastIdSql)
        cpMgr.save('downloads', lastId)

    def _processChrome(self, browser, osUser, profileName):
        profilePath = pathfinder.getProfilePath(browser, osUser, profileName)
        if not profilePath or not os.path.exists(profilePath):
            logger.error('Profile path does not exist: %s ' % profilePath)
            return
        
        profileKey = '%s/%s/%s' % (browser, osUser, profileName)
        cpMgr = CheckpointMgr(profileKey)
        cp = cpMgr.load()
        extra_info =  "'%%s' as 'sourcetype', '%s' as 'browser', '%s' as 'os_user', '%s' as 'browser_profile'" % (browser, osUser, profileName.split('.')[1] if browser=='firefox' else profileName)
        
        # history
        src = os.path.join(profilePath, 'History')
        where = 'WHERE v.id > %s' % cp.get('history') if cp.get('history') else ''
        historySql = "SELECT datetime((v.visit_time/1000000-11644473600),'unixepoch') as dt, u.url as url, u.title as title, u.hidden as hidden, %s FROM urls u JOIN visits v ON u.id = v.url %s" % (extra_info % 'history', where)
        lastIdSql = "SELECT max(id) FROM visits"
        lastId = self._executeSqlite(src, historySql, lastIdSql)
        cpMgr.save('history', lastId)
        
        # bookmarks
        src = os.path.join(profilePath, 'Bookmarks')
        if not os.path.exists(src):
            logger.error('Chrome bookmarks file not found: %s' % src)
            return

        def loop(root, path, lastId):
            newLastId = lastId

            for bmark in root:
                if 'children' in bmark:
                    newpath = path + ' \ '+ bmark['name']
                    innerLastId = loop(bmark['children'], newpath, lastId)
                    if innerLastId > newLastId:
                        newLastId = innerLastId 
                else:
                    id = int(bmark['id'])
                    if id > newLastId:
                        newLastId = id
                    else:
                        continue
                        
                    _bmark = [('dt', time.strftime('%Y-%m-%d %H:%M:%S',  time.gmtime( (float(bmark['date_added'])-11644473600000000)/1000000 ))),
                              ('title', bmark['name']),
                              ('url', bmark['url']),
                              ('path', path),
                              ('sourcetype', 'bookmarks'),
                              ('browser', browser),
                              ('os_user', osUser),
                              ('browser_profile', profileName)
                             ]
                    output = '\n'.join(['%s = %s' % (pair[0].rjust(15), pair[1]) for pair in _bmark]) + '\n'
                    print output
                    print eventBreak

            return newLastId
                    
        lastId = int(cp.get('bookmarks', 0))
        lastIds = []
        with file(src, 'r') as f:
            js = json.loads(f.read())
            root = js.get('roots')
            for k in root:
                if 'children' in root[k] and len(root[k]['children']) > 0:
                    lastIds.append( loop(root[k]['children'], root[k]['name'], lastId) )
            
        if len(lastIds) > 0:
            lastId = max(lastIds)
        cpMgr.save('bookmarks', lastId)
        
        # downloads
        src = os.path.join(profilePath, 'History')
        where = 'WHERE d.id > %s' % cp.get('downloads') if cp.get('downloads') else ''
        sql = "SELECT datetime((d.start_time/1000000-11644473600),'unixepoch') as dt, d.referrer as source, d.target_path as target, d.state as state, d.received_bytes as currBytes, d.total_bytes as maxBytes, %s FROM downloads d %s" % (extra_info % 'downloads', where)
        lastIdSql = "SELECT max(id) FROM downloads"
        lastId = self._executeSqlite(src, sql, lastIdSql)
        cpMgr.save('downloads', lastId)

    def _processIe(self, browser, osUser, profileName):
        profileKey = '%s/%s/%s' % (browser, osUser, profileName)
        cpMgr = CheckpointMgr(profileKey)
        cp = cpMgr.load()
        cpLastEvent = cp.get('history')
        cmd = [ieParserPath, '/stab', '', '-user', osUser]
        logger.debug(' '.join(cmd))
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate()
        if err:
            logger.error('Nothing was read from %s: %s' % ('ie/'+osUser, err.strip()))
            return

        previousEvent = []
        topEvent = None
        for line in StringIO.StringIO(out).readlines():
            values = line.split('\t')
            if len(values) == 0 or (len(previousEvent)>3 and (values[0] == previousEvent[0] and values[3] == previousEvent[3])):
                # skip empty lines and dups 
                continue
                
            # convert to utc epoch time
            dtEpoch = time.gmtime(time.mktime(time.strptime(values[3], '%m/%d/%Y %I:%M:%S %p')))
            if isinstance(cpLastEvent, tuple) and (dtEpoch, values[0]) == cpLastEvent:
                # reached the checkpoint
                break
                
            if not topEvent:
                topEvent = (dtEpoch, values[0])    
                                
            dtstr = time.strftime('%Y-%m-%d %H:%M:%S', dtEpoch)
            
            # separate local files from remote urls
            sourcetype = 'history'
            for k in ['file://','res://','ms-help://','Computer']:
                if str(values[0]).startswith(k):
                    sourcetype = 'local'
            
            evt = [('dt', dtstr),
                   ('url', values[0]),
                   ('title', values[1]),
                   ('sourcetype', sourcetype),
                   ('browser', 'ie'),
                   ('os_user', osUser),
                   ('browser_profile', profileName)                   
                  ]
            output = '\n'.join(['%s = %s' % (pair[0].rjust(15), pair[1]) for pair in evt]) + '\n'
            print output
            print eventBreak
            
            previousEvent = values
        
        if topEvent:
            cpMgr.save('history', topEvent)
        
        return topEvent
    
    def _processSafari(self, browser, osUser, profileName):
        profilePath = pathfinder.getProfilePath(browser, osUser, profileName)
        if not profilePath or not os.path.exists(profilePath):
            logger.error('Profile path does not exist: %s ' % profilePath)
            return

        profileName = 'default' if not profileName else profileName
        profileKey = '%s/%s/%s' % (browser, osUser, profileName)
        cpMgr = CheckpointMgr(profileKey)
        cp = cpMgr.load()
        cpLastEvent = cp.get('history')
        
        # history
        cpDt = cp.get('history') 
        hPath = os.path.join(profilePath, 'History.plist')
        if os.path.exists(hPath):
            plist = readPlist(hPath)
            historyData = plist['WebHistoryDates']
            safariTimeOffset = 978307200 # timestamps start with jan 1 2001
            maxDt = None
            for subDict in historyData:
                dt = float(subDict['lastVisitedDate']) + safariTimeOffset
                if cpLastEvent and dt <= float(cpLastEvent):
                    continue
                elif dt > maxDt: 
                    maxDt = dt
                dt = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(dt))
                evt = [('dt', dt),
                       ('title', unicode(subDict['title']) if 'title' in subDict else 'N/A'),
                       ('url', unicode(subDict[''])),
                       ('visitCount', subDict['visitCount']),
                       ('sourcetype', 'history'),
                       ('browser', browser),
                       ('os_user', osUser),
                       ('browser_profile', profileName)  
                      ]
                print '\n'.join(['%s = %s' % (pair[0].rjust(15), pair[1]) for pair in evt]) + '\n'
                print eventBreak
            if maxDt:
                cpMgr.save('history', maxDt)
        
        # bookmarks
        bmPath = os.path.join(profilePath, 'Bookmarks.plist')
        if os.path.exists(bmPath):
            cpBm = cp.get('bookmarks') 
            uuids = []
            def _safBookmarkLoop(node, path):
                if 'WebBookmarkType' in node and node['WebBookmarkType'] == 'WebBookmarkTypeList' and 'Children' in node:
                    newpath = (path+' \ ' if path else '') + node['Title'] if 'Title' in node else ''
                    for child in node['Children']:
                        _safBookmarkLoop(child, newpath)
                else:
                    if 'URIDictionary' not in node:
                        return
                    if cpBm and node['WebBookmarkUUID'] in cpBm:
                        return
                    evt = [('dt', time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())),
                           ('path', path),
                           ('url', node['URIDictionary']['']),
                           ('title', node['URIDictionary']['title']),
                           ('sourcetype', 'bookmarks'),
                           ('browser', browser),
                           ('os_user', osUser),
                           ('browser_profile', profileName)  
                          ]
                    print '\n'.join(['%s = %s' % (pair[0].rjust(15), pair[1]) for pair in evt]) + '\n'
                    print eventBreak
                    uuids.append(node['WebBookmarkUUID'])
        
            plist = readPlist(bmPath)
            _safBookmarkLoop(plist, '')
            if len(uuids) > 0:
                cpMgr.save('bookmarks', '|'.join(uuids))
        
        # downloads
        dPath = os.path.join(profilePath, 'Downloads.plist')
        if os.path.exists(dPath):
            cpBm = cp.get('downloads') 
            uuids = []
            plist = readPlist(dPath)
            if 'DownloadHistory' in plist:
                for hEntry in plist['DownloadHistory']:
                    if cpBm and hEntry['DownloadEntryIdentifier'] in cpBm:
                        continue
                    evt = [('dt', time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())),
                           ('source', hEntry['DownloadEntryURL']),
                           ('target', hEntry['DownloadEntryPath']),
                           ('currBytes', hEntry['DownloadEntryProgressBytesSoFar']),
                           ('maxBytes', hEntry['DownloadEntryProgressTotalToLoad']),
                           ('sourcetype', 'downloads'),
                           ('browser', browser),
                           ('os_user', osUser),
                           ('browser_profile', profileName)  
                          ]
                    print '\n'.join(['%s = %s' % (pair[0].rjust(15), pair[1]) for pair in evt]) + '\n'
                    print eventBreak
                uuids.append(hEntry['DownloadEntryIdentifier'])
            if len(uuids) > 0:
                cpMgr.save('downloads', '|'.join(uuids))            
            
            
    def start(self):
        '''
        Goes through the list of configured browser targets and pools their databases for data
        '''
        for browser, conf in self.browsers.items():
            browser = browser.lower()[:browser.find('_')]
            osUser = conf.get('os_user')
            profileName = conf.get('profile_name')
            disabled = True if int(conf.get('disabled')) > 0 else False
            if disabled:
                continue
            
            if browser == 'firefox':
                self._processFirefox(browser, osUser, profileName)
            elif browser == 'chrome':
                self._processChrome(browser, osUser, profileName)
            elif browser == 'ie':
                self._processIe(browser, osUser, profileName)
            elif browser == 'safari':
                self._processSafari(browser, osUser, profileName)                

                

   
if __name__ == '__main__':
    '''
    We require a sessionKey argument to be passed to the script.
    '''
    skey = sys.stdin.readline()
    if skey:
        bm = BrowserMonitor(skey)
        bm.start()
    else:
        logger.error('sessionKey command line argument must be provided')