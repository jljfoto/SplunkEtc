# Copyright (C) 2005-2014 Splunk Inc.  All Rights Reserved.  Version 6.x
# Author: Nimish Doshi
import sys,splunk.Intersplunk
import string
import getpass

##### CHANGE PATH TO your distribution FIRST ############                       
sys.path.append("/Library/Python/2.7/site-packages/python_Levenshtein-0.11.2-py2.7-macosx-10.9-intel.egg")

import Levenshtein

# uses levenshtein ratio or distance to compute likeness of two strings

if len(sys.argv) != 4:
    print "Usage |levenshtein (distance|ratio|all) string1 string2"
    sys.exit()


command=sys.argv[1]
string1=sys.argv[2]
string2=sys.argv[3]

results = []

try:

    results,dummyresults,settings = splunk.Intersplunk.getOrganizedResults()
    
    for r in results:
        if "_raw" in r:
            if command=="ratio":
                ratio=Levenshtein.ratio(r[string1], r[string2])
                r["ratio"]=ratio
            elif command=="distance":
                distance=Levenshtein.distance(r[string1], r[string2])
                r["distance"]=distance
            else:
                distance=Levenshtein.distance(r[string1], r[string2])
                r["distance"]=distance
                ratio=Levenshtein.ratio(r[string1], r[string2])
                r["ratio"]=ratio

except:
    import traceback
    stack =  traceback.format_exc()
    results = splunk.Intersplunk.generateErrorResults("Error : Traceback: " + str(stack))

splunk.Intersplunk.outputResults( results )
