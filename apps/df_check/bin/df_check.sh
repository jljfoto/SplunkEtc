#!/bin/bash

# Filesystem      Size   Used  Avail Capacity iused               ifree %iused  Mounted on

for i in `df -k | grep "^/dev" | awk '{ "date +%Y-%m-%dT%T" | getline dte } {print "time=\""dte"\",disk=\""$1"\",size=\""$2"\",used=\""$3"\",avail=\""$4"\",capacity=\""$5"\",iused=\""$6"\",ifree=\""$7"\",iused_pct=\""$8"\",fs=\""$9"\""}'`
do
	echo $i
done
