#!/bin/bash

nohup python -u ./src/tidal-server.py > ~/nohup_tidal.txt 2>&1 &
nohup python -u ./src/index.py > ~/nohup_index.txt 2>&1 &
nohup mitmdump --listen-port 8081 -s ./src/http-redirect-request.py > ~/nohup_mitmdump.txt 2>&1 &

tail -f ~/nohup_*.txt