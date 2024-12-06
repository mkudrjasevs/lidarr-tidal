#!/bin/bash

nohup python ./src/tidal-server.py > ~/nohup_tidal.txt 2>&1 &
nohup python ./src/index.py > ~/nohup_index.txt 2>&1 &
nohup mitmdump --listen-port 8081 -s ./src/http-redirect-request.py > ~/nohup_mitmdump.txt 2>&1 &

tail -f ~/nohup_*.txt