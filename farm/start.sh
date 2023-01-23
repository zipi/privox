#!/bin/bash
source venv_privox/bin/activate
nohup python -u privox_socket_server.py tts > logs/tts.out 2>&1 &
nohup python -u privox_socket_server.py stt > logs/stt.out 2>&1 &

