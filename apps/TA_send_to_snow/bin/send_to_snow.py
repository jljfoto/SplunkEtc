###################################################################
##
## Imports
##
###################################################################

import splunk.Intersplunk as si
import datetime
import json
import logging
import requests
import socket
import time


###################################################################
## - Variables
## 	- Proxy host
## 	- Splunk Index
## 	- HEC token
## 	- HEC URL
## 	- Splunk Search Head
## 	- Log Path
##   - SerivceNow URL
##   - Number of retries before Alert
## 	- Debug Level
###################################################################

DEBUG = 0
SEND_SNOW = True

PROXY_HOST = "vsproxyNPGS.frbnpgs.com"
PROXY_PORT = 8080

SPLUNK_INDEX = "jljfoto"
SPLUNK_INDEX_PORT = 9997

HEC_Token = "F01849B7-147B-44A9-971C-181D11EA8770"
HEC_HOST = "jljfoto"
HEC_PORT = 8088
HEC_URL = "http://jljfoto:" + str(HEC_PORT) + "/services/collector/event"
HEC_Header = {'Authorization': 'Splunk ' + HEC_Token, 'content-type': 'application/json'}
header = {'content-type': 'application/json'}

SNOW_URL = "https://dev66655.service-now.com/api/now/v1/table/incident"
SNOW_HOST = "dev66655.service-now.com"
SNOW_PORT = 443
SNOW_USER = "splunk_user"
SNOW_PW = "integrate123!"
SNOW_AUTH = "auth=(" + SNOW_USER + "," + SNOW_PW + ")"
SNOW_Header = {"Content-Type":"application/json","Accept":"application/json"}

LOG_PATH = "/opt/splunk/etc/apps/TA_send_to_snow/logs/send_to_snow.log"

RETRIES = 3
RETRY_SLEEP_SECONDS = 1


###################################################################
##
## - Proxy
## 	- Verify that the proxy server is avaialble
## 	- Can we connect to ServiceNow?
##
## - Splunk
## 	- Is the Splunk Index available?
## 	- Is the HEC avaialble?
## 	- Is the Splunk Search Head available?
##
## - Log Path
## 	- Can we write to the log?
##
###################################################################

def check_port(HOST,PORT):
	if DEBUG:
		logger("check port")
	# Create a TCP socket
	try:
		s = socket.socket()
		if DEBUG:
			print datetime.datetime.now(),"SUCCESS: Socket opened to Splunk"
			logger("SUCCESS: Socket opened to Splunk")
	except Exception as ex:
		print datetime.datetime.now(),"FAIL: Attempting to open a socket to Splunk.  Reason: ",ex
		logger("FAIL: Attempting to open a socket to Splunk.  Reason: ",ex)

	try:
		s.connect((HOST, PORT))
		if DEBUG:
        		print datetime.datetime.now()," SUCCESS: Connected to %s on port %s" % (HOST, PORT)
			logger("SUCCESS: Connected to %s on port %s" % (HOST, PORT))
	except Exception as ex:
        	print datetime.datetime.now()," FAIL: Connection to %s on port %s failed: %s" % (HOST, PORT, ex)
		logger("FAIL: Connection to %s on port %s failed: %s" % (HOST, PORT, ex))



def verify_log_path(LOG_PATH):
	if DEBUG:
		logger("verify logfile")
		print datetime.datetime.now(),"Checking log file:",LOG_PATH
		logger("Checking log file:" + LOG_PATH)
	try:
		f = open(LOG_PATH,"a+")
		if DEBUG:
			print datetime.datetime.now()," SUCCESS: Log file %s opened for writing" % LOG_PATH
			logger("SUCCESS: Log file %s opened for writing" % LOG_PATH)
	except Exception as ex:
		print datetime.datetime.now()," FAIL: Attempt to open file %s failed with error %s " % (LOG_PATH,ex)
		logger("FAIL: Attempt to open file %s failed with error %s " % (LOG_PATH,ex))



def logger(event):
        if DEBUG:
                print datetime.datetime.now(),"In Logger with event: ",event
                print datetime.datetime.now(),"In Logger with str(event): ",str(event)
                print " "
        # Attempt to log to the HEC
        HEC_TIME = str(time.time())
	HEC_Event = '{"time":"' + HEC_TIME + '","event":{"message":"' + str(event) + '"}}'
	
        if DEBUG:
		print "HEC_Event data type: ",type(HEC_Event)
                print datetime.datetime.now(),"Sending HEC_Event: ",HEC_Event
                #print datetime.datetime.now(),"HEC_Event1: ",HEC_Event1

        tries = 1
        success = 0
        while not success and tries < RETRIES:
                try:
			# requests version 2.22.0
                        #r = requests.post(HEC_URL, headers=HEC_Header, json=HEC_Event, verify=False)

                        # requests version 2.3.0
                        r = requests.post(HEC_URL, headers=HEC_Header, data=HEC_Event, verify=False)
			HEC_response = r.text
                except Exception as ex:
                        success = 0
                        if DEBUG:
                        	print datetime.datetime.now()," ERROR: Write to HEC failed. Reason:",ex
                        	print datetime.datetime.now()," HEC_Event: ",HEC_Event
                                print datetime.datetime.now()," Message: ", ex.message," attempt: ", tries
                                print datetime.datetime.now()," __class__.__name__: ", ex.__class__.__name__
                        time.sleep(RETRY_SLEEP_SECONDS)
                        tries = tries + 1
                else:
			for k,v in r.json().items():
				if DEBUG:
					print "key: ",k
					print "  value:",v
                                if k == "text" and v == "Success":
                                        success = 1
                                        HEC_Return_Status = v
                                if k == "code":
                                        HEC_Return_code = v
                        if DEBUG:
				print datetime.datetime.now(),"Received Status:",HEC_Return_Status," Return Code:",HEC_Return_code
                                print datetime.datetime.now(),"Response from HEC: ",r.text
                                print datetime.datetime.now(),"Successful Response from HEC"
                                print datetime.datetime.now(),"Data Sent: ", HEC_Event," Response:",r.json()

        # if that fails, log to file
        if DEBUG:
                print "after HEC try.  Success =",success
                print " "
        if not success:
                if DEBUG:
                        print datetime.datetime.now(),"HEC failed: Writing to log file:",LOG_PATH
                try:
                        f = open(LOG_PATH,"a+")
                        if DEBUG:
                                print datetime.datetime.now()," SUCCESS: Log file %s opened for writing" % LOG_PATH
                        try:
                                event = str(datetime.datetime.now()) + " " + event + "\n"
                                f.write(event)
                                if DEBUG:
                                        print datetime.datetime.now()," SUCCESS: Data successfully written to log",LOG_PATH
                        except Exception as f_ex:
                                print datetime.datetime.now(),"Unable to write log event to log file",LOG_PATH
                                print datetime.datetime.now(),"Log Event:",event
                                print datetime.datetime.now(),"Reason:",f_ex
                except Exception as ex:
                        print datetime.datetime.now()," FAIL: Attempt to open file %s failed with error %s " % (LOG_PATH,ex)


def send_to_snow(event):
	if DEBUG:
		logger("send to snow")
	SNOW_Event = str(event)

	tries = 1
	success = 0
	while not success and tries < RETRIES:
		try:
			r = requests.post(SNOW_URL, headers=SNOW_Header, auth=(SNOW_USER,SNOW_PW), data=SNOW_Event)
			#return_code = r.text
		except Exception as ex:
			logger("ERROR: Send to ServiceNow failed. Reason: " + str(r.text))
			print datetime.datetime.now(),"SNOW:  ERROR: Send to ServiceNow failed.  Reason:",ex.message
			success = 0
			if DEBUG:
				print datetime.datetime.now(),"SNOW:  Message: ", ex.message," attempt: ", tries
				logger("Message: " + ex.message)
				print datetime.datetime.now(),"SNOW:  Attributes: ",dir(ex)
                        	time.sleep(RETRY_SLEEP_SECONDS)
				logger("__class__.__name__: " + ex.__class__.__name__)
				print " "
			#time.sleep(RETRY_SLEEP_SECONDS)
			tries = tries + 1
		else:
			#print datetime.datetime.now(),"SNOW:  Data successfully sent to ServiceNow "
			success = 1
			key, value = r.json().popitem()
			SNOW_Response = value

			SNOW_INCident = "Not Created"
			SNOW_sys_id = "Not returned"
			SNOW_short_description = "Not returned"
			SNOW_description = "Not returned"
			for k,v in SNOW_Response.items():
				if k == "number":
					SNOW_INCident = v
				if k == "sys_id":
					SNOW_sys_id = v
				if k == "short_description":
					SNOW_short_description = v
				if k == "description":
					SNOW_description = v

			print datetime.datetime.now(),"SNOW:  INCIDENT:",SNOW_INCident,"created.   Sys_id:",SNOW_sys_id,"   Short_Description:",SNOW_short_description
			logger("INCIDENT: " + SNOW_INCident + " created.   Sys_id: " + SNOW_sys_id + "   Short_Description: " + SNOW_short_description)
			if DEBUG:
				print "SNOW: r.text: ",r.text
				print "SNOW:  "
				logger("r.text: " + str(r.text))
				print "SNOW: r.json() ",r.json()
				print " "
				logger("r.json(): " + str(r.json()))
				print "SNOW: SNOW_Response: ",SNOW_Response
				logger("SNOW: " +  SNOW_response)
				print "SNOW:  "
				for k,v in SNOW_Response.items():
					if DEBUG:
						print "SNOW: key: ",k
						print "SNOW:    value: ",v
						logger("from SNOW Response Items:  key: " + str(k) + " value: " + str(v))
				print datetime.datetime.now()," Data Sent: ", SNOW_Event, " attempt: ",tries
				logger('{"from SNOW: success": ' + SNOW_Event + '}' )

	if DEBUG:
		print "SNOW:  "


def main():
	if DEBUG:
		logger("main")

	check_port(PROXY_HOST,PROXY_PORT)
	check_port(SNOW_HOST,SNOW_PORT)
	check_port(HEC_HOST,HEC_PORT)
	check_port(SPLUNK_INDEX,SPLUNK_INDEX_PORT)
	verify_log_path(LOG_PATH)

	if DEBUG:
        	logger("MAIN: Start of Run")
		print "MAIN: Requests Version",requests.__version__
		print "MAIN: before si call"

	try:
		myresults,dummyresults,settings = si.getOrganizedResults() 
	except Exception as ex:
		print datetime.datetime.now(),"SEARCH_RESULTS: ERROR: Call to get Splunk Results failed.  Reason:",ex
                print datetime.datetime.now(),"SPLUNK_SEARCH: Response from Splunk:",str(myresults.text)
                logger("ERROR: Call to get Splunk Results failed.")
                logger(str(myresults.text))
                if DEBUG:
               		 print datetime.datetime.now(),"SNOW:  Message: ", ex.message
                         logger("Message: " + ex.message)
	else:
		for r in myresults: 
			if DEBUG:
				print datetime.datetime.now(),"MAIN: r=",r
				#logger("from MAIN: " + str(r))
			SNOW_Event = {}
			SEND_SNOW = True
			for k,v in r.items():
				SNOW_Event[k] = v
				if k == "nosend":
					print "nosend detected"
					SEND_SNOW = False

			### NOTE request to SNOW required data to be of type STR
			if SEND_SNOW:
				send_to_snow(str(SNOW_Event))
			else:
				print datetime.datetime.now(),"NO Send honored."
				logger("NO send honored")

	if DEBUG:
        	logger("MAIN: End of Run")


if __name__ == "__main__":
        main()
