import os
import splunk.admin as admin
import pathfinder
import splunk.entity as en
import splunk.rest as rest

class ConfigBrowsersApp(admin.MConfigHandler):
    '''
    Set up supported arguments
    '''
    def setup(self):
        self.appName = 'browsers'
        if self.requestedAction == admin.ACTION_EDIT:
            for arg in ['profiles', 'history', 'bookmarks', 'downloads']:
               self.supportedArgs.addOptArg(arg)
                
    '''
    Lists configurable parameters
    '''
    def handleList(self, confInfo):
        confDict = self.readConf("browsers")
        if None != confDict:
            for stanza, settings in confDict.items():
                for key, val in settings.items():
                    confInfo[stanza].append(key, val)
            
        for browser in ['Firefox', 'Chrome', 'IE', 'Safari']:
            _getProfileList(browser, confInfo)
            
    '''
    Controls parameters
    '''
    def handleEdit(self, confInfo):
        name = self.callerArgs.id
        args = self.callerArgs
        
        profiles = ''
        settings = {'history': 0, 'bookmarks': 0, 'downloads': 0}
        
        if 'profiles' in args:
            profiles = args['profiles'][0] or ''
        if 'history' in args:
            settings['history'] = args['history'][0] or 0
        if 'bookmarks' in args:
            settings['bookmarks'] = args['bookmarks'][0] or 0
        if 'downloads' in args:
            settings['downloads'] = args['downloads'][0] or 0

        # create or update browsers.conf
        if len(profiles) > 0:
            instances = profiles.split(',')
            i = 1
            for instance in instances:
                p = instance.strip().split('/')
                osUser = p[0]
                profileName = p[1]
                _name = '%s_%d' % (name, i)
                settings['profile_name'] = profileName
                settings['os_user'] = osUser
                
                self.writeConf('browsers', _name, settings)
                i+=1
        
        # fix path separator in inputs.conf
        _enableInputs(self.appName, self.getSessionKey())
        

def _getProfileList(browser, confInfo):
    profiles = []
    for result in pathfinder.search(browser):
        profiles.append('/'.join(result))
    
    profiles = ', '.join(profiles) if len(profiles) > 0 else ''
    confInfo[browser].append('profiles', profiles)    
    confInfo[browser].append('history', '0')
    confInfo[browser].append('downloads', '0')
    confInfo[browser].append('bookmarks', '0')

def _enableInputs(appName, sessionKey):
    os_altsep = '\\' if os.path.sep == '/' else '/'
    
    inputsConf = en.getEntities('data/inputs/script', sessionKey=sessionKey, search='eai:acl.app='+appName)
    for stanza in inputsConf:
        if stanza.endswith('monitor.py'):
            uri = None
            if os_altsep in stanza:
                uri = inputsConf[stanza].getLink('disable')
            else:
                uri = inputsConf[stanza].getLink('enable')
            if uri: 
                serverResponse, serverContent = rest.simpleRequest(uri, sessionKey=sessionKey, method='POST')                        
        
    
# initialize the handler
admin.init(ConfigBrowsersApp, admin.CONTEXT_NONE)        

