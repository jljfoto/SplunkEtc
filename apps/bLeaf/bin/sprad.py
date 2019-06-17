import sys
import datetime
import string
import re
import random
import time
import itertools
import names

## Message Message
##
## message ID
## date
## time
## context
## system update

class Message(str):

    def __init__(self, s):
        self.message = None
        if isinstance(s,str): 
            self.message = ''.join(s)

    def refactor(self,s,o):
        if isinstance(s,str): 
            self.message  = re.sub(s, o, self.message)

    def prepend(self,s):
        if isinstance(s,str): 
            self.message = "%s %s" % (s,self.message)

    def append(self,s):
        if isinstance(s,str): 
            self.message = "%s %s" % (self.message,s)

    def __str__(self):
        return "%s" % (self.message)

## Message Line
##
## message ID
## date
## time
## context
## system update

class Line():

    def __init__(self):
        self.messages = []

    def append(self,m):
        self.messages.append(m)

    def refactor(self,s,o):
        for m in self.messages:
            m.refactor(s,o)

    def randomMessage(self):
        return random.choice(self.messages)

    def replay(self):
        for m in self.messages:
            print m

class Factory(Line):

    def __init__(self,l):
        self.messages = l

    def createTimestamp(self, s_delta=0):
        dt = datetime.datetime.now() - datetime.timedelta(seconds=s_delta)
        seconds = "%02d" % (random.randrange(1,59))
        microseconds = "%03d" % (random.randrange(1,999))
        timestamp = "%s:%s.%s - " % (str(dt.strftime('%b %d %Y %H:%M')),seconds,microseconds)
        return timestamp

    def futureTimestamp(self, s_delta=0):
        dt = datetime.datetime.now() + datetime.timedelta(seconds=s_delta)
        seconds = "%02d" % (random.randrange(1,59))
        microseconds = "%03d" % (random.randrange(1,999))
        timestamp = "%s:%s.%s - " % (str(dt.strftime('%b %d %Y %H:%M')),seconds,microseconds)
        return timestamp


    def populateTimestamp(self,seconds=3600,period=5):
        for i in range(0,seconds,period):
            print self.createTimestamp(i)

    def randomMessage(self):
        print self.messages.randomMessage()

    def replay(self):
        self.messages.replay()

    def replayAll(self,seconds=0,period=0):

        if period <= 0:
            period = seconds/len(self.messages.messages)

        period *= -1
        pastTimestamps = []

        for i in range(seconds,0,period):
            pastTimestamps.append(self.createTimestamp(i))

        t = iter(pastTimestamps)

        for m in self.messages.messages:
            print "%s %s" % (next(t),m)

    def futurePlay(self,seconds=0,period=0):

        if seconds == 0 or len(self.messages.messages) == 0:
            return

        period = seconds/len(self.messages.messages)

        futureTimestamps = []

        for i in range(0,seconds,period):
            futureTimestamps.append(self.createTimestamp(i*-1))

        f = iter(futureTimestamps)

        for m in self.messages.messages:
            print "%s %s" % (next(f),m)

## Message Utilities
##

class messageUtilities():
    """docstring for messageUtilities"""
    def __init__(self):
        self.location = self.simulateLocation()
        self.warAppName = self.simulateWarName()
        self.warStatus = self.simulateWarStatus()

    def simulateLocation(self):
        us_states = [ "AL","AK","AZ","AR","CA","CO","CT","DE","DC",
                      "FL","GA","HI","ID","IL","IN","IA","KS","KY",
                      "LA","ME","MD","MA","MI","MN","MS","MO","MT",
                      "NE","NV","NH","NJ","NM","NY","NC","ND","OH",
                      "OK","OR","PA","RI","SC","SD","TN","TX","UT",
                      "VT","VA","WA","WV","WI","WY" ]

	return random.choice(us_states)

    def simulateWarName(self):
        return random.choice(["POS_EX", "CCTRN", "PORTAL", "WEBL"])

    def simulateWarStatus(self):
        return random.choice([ "SUCCESS", "FAILURE", "STALLED" ])

    def futureTimestamp(self, s_delta=0):
        dt = datetime.datetime.now() + datetime.timedelta(seconds=s_delta)
        seconds = "%02d" % (random.randrange(1,59))
        microseconds = "%03d" % (random.randrange(1,999))
        timestamp = "%s:%s.%s" % (str(dt.strftime('%m-%d-%y %H:%M:%S')),seconds,microseconds)
        return timestamp

class POS_Message():

    def __init__(self):

        self.message = self.getNewMessage()

    def getNewMessage(self):
        location = messageUtilities().simulateLocation()


        self.host = "%s-%02d" % (location,random.randrange(1,4))
        self.apprCode = "%d" % (random.randrange(99999,999999))
        self.clerkID = "%04d" % (random.randrange(1,15))
        self.invoiceNo = "%d" % (random.randrange(1000000,2000000))
        self.makedCardNumber = "xxxx-xxxx-xxxx-%04d" % (random.randrange(1,9999))
        self.merchantID = "%s-%03d" % (location,random.randrange(0,50))
        self.respCode = "%d" % (self.simulateResponseCode())
        self.sequenceNumber = "%03d-%06d-%d" % (random.randrange(1,999), random.randrange(99999,999999),random.randrange(0,10))
        self.terminalID = "%d-%d" % (random.randrange(4000,9000),random.randrange(1000,4000))
        self.total = "%d.%02d" % (random.randrange(1,500),random.randrange(0,100))
        self.transactionType = "%d" % (random.randrange(999,1017)) 

        return self.getMessage()       

    def simulateResponseCode(self):
        respCode = 100
        diceRoll = random.randrange(0,31416) % 10
        if diceRoll in (1,2):
            respCode = random.randrange(100,128)
        elif diceRoll == 3:
            respCode = random.randrange(201,219)
        return respCode

    def getMessage(self):
        return "%s %s,%s,%s,%s,%s,%s,%s,%s,%s,%s" % (self.host,     self.apprCode,       self.clerkID,    self.invoiceNo, self.makedCardNumber, self.merchantID, 
                                                     self.respCode, self.sequenceNumber, self.terminalID, self.total,     self.transactionType )

    def getReplacements(self):
      print dict((key, value) for key, value in self.__dict__.iteritems() if not callable(value) and not key.startswith('__'))

class WAR_Message():

    def __init__(self):

        self.message = self.getNewMessage()

    def getNewMessage(self):
        storeId  = random.randrange(1,4)
        duration = random.randrange(500,600)
        memory   = random.randrange(150,4096)

        m  = "Building war %s: /home/%s-%02d/Projects/pos/target/cclink-1.0.0.war\n" % (messageUtilities().simulateWarName(),messageUtilities().simulateLocation(),storeId)
        m += "------------------------------------------------------------------------\n"
        m += "BUILD %s\n" % messageUtilities().simulateWarStatus()
        m += "------------------------------------------------------------------------\n"
        m += "Total time: %d seconds\n" % (duration)
        m += "Final Memory: %dM/4096M\n" % (random.randrange(15,4096)) 
        m += "------------------------------------------------------------------------"

        return "%s" % (m)

class SOAP_Message():

    def __init__(self):

        self.message = self.getNewMessage()

    def getNewMessage(self):
    
        location = messageUtilities().simulateLocation()

        m  = "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"no\" ?>\n"
        m += "<SOAP-ENV:Envelope\n"
        m += "SOAP-ENV:encodingStyle=\"http://schemas.xmlsoap.org/soap/encoding/\"\n"
        m += "xmlns:SOAP-ENV=\"http://schemas.xmlsoap.org/soap/envelope/\"\n"
        m += "xmlns:SOAP-ENC=\"http://schemas.xmlsoap.org/soap/encoding/\"\n"
        m += "xmlns:xsi=\"http://www.w3.org/1999/XMLSchema-instance\"\n"
        m += "xmlns:xsd=\"http://www.w3.org/1999/XMLSchema>\"\n"
        m += "\t<SOAP-ENV:Body>\n"
        m += "\t\t<ns1:dateRequested>%s</ns1:dateRequested>\n" % (messageUtilities().futureTimestamp(random.randrange(0,3600)))
        m += "\t\t<ns1:getStoreDetails\n"
        m += "\t\txmlns:ns1=\"urn:MySoapServices\">\n"
        m += "\t\t<param1 xsi:state=\"xsd:string\">%s</param1>\n" % (location)
        m += "\t\t</ns1:getStoreDetails>\n"
        m += "\t<ns1:getStoreDetailsDetailsResponse\n"
        m += "\txmlns:ns1=\"urn:MySoapServices\"\n"
        m += "\tSOAP-ENV:encodingStyle=\"http://schemas.xmlsoap.org/soap/encoding/\">\n"
        m += "\t\t<return xsi:type=\"ns1:Customer Account ID\">\n"
        m += "\t\t<customerName xsi:type=\"xsd:string\">%s</customerName>\n" % (names.get_full_name())
        m += "\t\t<ccNumber xsi:type=\"xsd:string\">xxxx-xxxx-xxxx-%04d</ccNumber>\n" % (random.randrange(1,9999))
        m += "\t\t<recordTransaction\n"
        m += "\t\t\txmlns:ns2=\"http://schemas.xmlsoap.org/soap/encoding/\"\n"
        m += "\t\t\txsi:type=\"ns2:Array\"\n"
        m += "\t\t\tns2:arrayType=\"ns1:AccountInformation[3]\">\n"
        m += "\t\t\t\t<item xsi:type=\"ns1:AccountNumber\">\n"
        m += "\t\t\t\t\t<account xsi:type=\"xsd:int\">%06d</account>\n" % (random.randrange(0,9000000)%314159)
        m += "\t\t\t\t\t<phoneNumber xsi:type=\"xsd:string\">+1-555-%07d</phoneNumber>\n" % (random.randrange(0,9000000)%3141592)
        m += "\t\t\t\t</item>\n"
        m += "\t\t\t\t<item xsi:type=\"ns1:ServiceCode\">\n"
        m += "\t\t\t\t\t<amount xsi:type=\"xsd:int\">%d.%02d</amount>\n" % (random.randrange(1,500),random.randrange(0,100))
        m += "\t\t\t\t</item>\n"
        m += "\t\t\t\t<item xsi:type=\"ns1:Transaction\">\n"
        m += "\t\t\t\t</item>\n"
        m += "\t\t\t</recordTransaction>\n"
        m += "\t\t</return>\n"
        m += "\t</ns1:getStoreDetailsDetailsResponse>\n"
        m += "\t</SOAP-ENV:Body>\n"
        m += "</SOAP-ENV:Envelope>\n"

        return "%s" % (m)

## Message Line
##
## message ID
## date
## time
## context
## system update

def main():
    pos  = POS_Message()
    war  = WAR_Message()
    soap = SOAP_Message()

    for i in range(0,360):
	s = soap.getNewMessage()
	print s	

    if len(sys.argv) == 2 and sys.argv[1] == "initial":

        for i in range(5,0,-1):
            l = Line()
            for j in range(0,i*300):
                s = pos.getNewMessage()    
                m = Message(s)
                l.append(m)    
            f = Factory(l)
            f.replayAll(3600)

	l = Line()
        for i in range(0,360):
	    s = war.getNewMessage()
	    m = Message(s)
	    l.append(m)
	f = Factory(l)
	f.replayAll(3600)

    else: 

        for i in range(0,5):
            l = Line()
            for j in range(0,i*300):
                s = pos.getNewMessage()    
                m = Message(s)
                l.append(m)    
            f = Factory(l)
            f.futurePlay(i*720)

	l = Line()
        for i in range(0,360):
	    s = war.getNewMessage()
	    m = Message(s)
	    l.append(m)
	f = Factory(l)
	f.futurePlay(3600,5)

## Message Line
##
## message ID
## date
## time
## context
## system update

if __name__ == "__main__":
    main()
