import socket
import datetime


DEBUG = 0
HOST_LIST = "jljfoto", "wikihost","raspberrypi","passport","mb-air","mb-air2","mb-pro","nas","newpi"
PORT = 22

def check_port(HOST,PORT):
        # Create a TCP socket
        try:
                s = socket.socket()
                #s = socket.create_connection(address, timeout=10)
		s.settimeout(2.0)
                if DEBUG:
                        print datetime.datetime.now(),"SUCCESS: Socket opened"
        except Exception as ex:
                print datetime.datetime.now(),"FAIL: Attempting to open a socket to",HOST,".  Reason: ",ex

        try:
                s.connect((HOST, PORT))
                print datetime.datetime.now()," SUCCESS: Connected to %s on port %s" % (HOST, PORT)
        except Exception as ex:
                print datetime.datetime.now()," FAIL: Connection to %s on port %s failed: %s" % (HOST, PORT, ex)



def main():

	for i in HOST_LIST:
        	check_port(i,PORT)

if __name__ == "__main__":
        main()
