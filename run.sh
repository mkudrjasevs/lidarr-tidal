#!/bin/bash

nohup python3 ./src/tidal-server.py > /tmp/nohup_tidal.txt 2>&1 &
nohup python3 ./src/index.py > /tmp/nohup_index.txt 2>&1 &
nohup mitmdump -s ./src/http-redirect-request.py > /tmp/nohup_mitmdump.txt 2>&1 &

tail -f ~/nohup_*.txt
