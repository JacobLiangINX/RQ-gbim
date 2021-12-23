#!/bin/sh
#export ORACLE_HOME=/usr/lib/oracle/11.2/client64
#export ORABIN=/usr/lib/oracle/11.2/client64

#export ORACLE_HOME=/opt/oracle/instantclient_19_9
#export ORABIN=/opt/oracle/instantclient_19_9
export LD_LIBRARY_PATH=/opt/oracle/instantclient_19_9:$LD_LIBRARY_PATH

python3 /usr/src/reMVC/app.py 
