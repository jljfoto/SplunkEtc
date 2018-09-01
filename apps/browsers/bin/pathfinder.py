import os, platform, json
import ConfigParser

basePath = {'Windows'      : ['c:\\', 'Users'], 
            'WindowsLegacy': ['c:\\', 'Documents and Settings'], 
            'Darwin'       : ['/', 'Users'], 
            'Linux'        : ['/', 'home']
           }
           
profile_path_map = {'firefox' : {'Windows'      : ['AppData', 'Roaming', 'Mozilla', 'Firefox'], 
                                 'WindowsLegacy': ['Local Settings', 'Application Data', 'Mozilla', 'Firefox'], 
                                 'Darwin'       : ['Library', 'Application Support', 'Firefox'], 
                                 'Linux'        : ['.mozilla', 'firefox']
                                },
                    'chrome'  : {'Windows'      : ['AppData', 'Local', 'Google', 'Chrome', 'User Data'], 
                                 'WindowsLegacy': ['Local Settings', 'Application Data', 'Google', 'Chrome', 'User Data'], 
                                 'Darwin'       : ['Library', 'Application Support', 'Google', 'Chrome'], 
                                 'Linux'        : ['.config', 'google-chrome']
                                },
                    'safari'  : {'Windows'      : ['AppData', 'Roaming', 'Apple Computer', 'Safari'],
                                 'WindowsLegacy': ['Local Settings', 'Application Data', 'Apple Computer', 'Safari'], 
                                 'Darwin'       : ['Library', 'Safari'], 
                                 'Linux'        : []
                                }
                    
                   }
                   
def getOsName():
    osName = platform.system()
    if osName == 'Windows' and int(platform.version()[:1]) < 6:
        osName = 'WindowsLegacy'
    return osName
                
def getBasePath(osUser=None):
    path = basePath.get(getOsName())
    if osUser:
        return path + [osUser]
    return path 
                
def getProfilePath(browser, osUser, profileName=None):
    if not browser in profile_path_map:
        logger.error('Browser %s is not supported' % browser)
        return None

    bPath = getBasePath(osUser)
    
    path = profile_path_map[browser].get(getOsName())

    endPath = []
    if profileName != None:
        if browser == 'firefox' and not getOsName() == 'Linux':
            endPath.append('Profiles')
        endPath.append(profileName)
    return os.path.join(*(bPath + path + endPath))

def listOsUsers():
    osName = getOsName()
    osUsers = []
    basePath = os.path.join(*getBasePath())
    if os.path.exists(basePath):
        osUsers = os.listdir(basePath)    
        if osName == 'Windows':
            osUsers = [u for u in osUsers if u not in ['All Users', 'Default', 'Default User', 'Public', 'desktop.ini']]
        elif osName == 'Darwin':
            osUsers = [u for u in osUsers if u not in ['Shared', '.localized']]
    return osUsers
   
def listFFProfiles(osUser):
    '''
    Reads profile.ini file and extracts profile names from it
    '''
    profiles = []
    profileIni = os.path.join(getProfilePath('firefox', osUser), 'profiles.ini')
    if os.path.exists(profileIni):
        config = ConfigParser.ConfigParser()
        config.read(profileIni)
        for section in config.sections():
            if section.startswith('Profile'):
                p = config.get(section, 'Path').replace('Profiles/','')
                if os.path.exists(os.path.join(getProfilePath('firefox', osUser,''), p)):
                    profiles.append(p)
    return profiles
    
def listChromeProfiles(osUser):
    profiles = []
    profileJson = os.path.join(getProfilePath('chrome', osUser), 'Local State')
    if os.path.exists(profileJson):
        with file(profileJson, 'r') as f:
            js = json.loads(f.read())
            try:
                for key in js['profile']['info_cache'].keys():
                    if os.path.exists(os.path.join(getProfilePath('chrome', osUser), key)):
                        profiles.append(key)
            except:
                pass

    return profiles
    
def listIEProfiles(osUser):
    return ['default'] if getOsName() == 'Windows' else []


def listSafariProfiles(osUser):
    return [''] if os.path.exists(getProfilePath('safari', osUser)) else []
    
def scan():
    '''
    Returns a list of tuples (os_user,browser_profile) for requested browser
    '''
    allProfiles = {}
    for osUser in listOsUsers():
        allProfiles[osUser] = {
            'Firefox': listFFProfiles(osUser),
            'Chrome': listChromeProfiles(osUser),
            'IE': listIEProfiles(osUser),
            'Safari': listSafariProfiles(osUser)}
    return allProfiles
    
def initConfig(sessionKey):
    profiles = scan()
    # create or update browsers.conf
    
                
