#!/bin/bash

nohup python3 ./src/tidal-server.py > /tmp/nohup_tidal.txt 2>&1 &
nohup python3 ./src/index.py > /tmp/nohup_index.txt 2>&1 &
nohup mitmdump --listen-port 8081 -s ./src/http-redirect-request.py > /tmp/nohup_mitmdump.txt 2>&1 &