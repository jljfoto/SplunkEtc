Author: Nimish Doshi
********************

This add-on uses the github distribution of the Levenshtein command to find
the raio or distance between two strings.

First install the distribution onto your indexer machine from here:

https://github.com/ztane/python-Levenshtein/

Change your directory where you got the Github distribution and run:
sudo python setup.py install

Remember where your *.egg file gets installed.
Untar this distribution add-on to $SPLUNK_HOME/etc/apps. Go to the bin
directory of the add-on and edit levenshtein.py.

##### CHANGE PATH TO your distribution FIRST ############                      sys.path.append("/Library/Python/2.7/site-packages/python_Levenshtein.egg")

Once you've changed the path to match that of your egg, save the file and
restart Splunk.

Usage:

|levenshtein (distance|ratio|all)  field1 field2 |table field1 field2 ratio

Example:

sourcetype=apache|levenshtein ratio client_domain src_domain |table client_domain src_domain ratio

sourcetype=apache|levenshtein distance client_domain src_domain |table client_domain src_domain distance

sourcetype=apache|levenshtein all client_domain src_domain |table client_domain src_domain distance ratio







