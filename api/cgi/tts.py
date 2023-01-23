#!/usr/bin/python3
import socket, time, sys, cgi, os
import urllib.request
import cgitb
cgitb.enable()
sys.path.append(os.getcwd())

from cgi_util import bark, bail, get_available_for_key
from datetime import datetime
from tts_cgi import TTS_CGI
from cgi_config import MAX_POST_BODY_SIZE, PV_PRODUCER_FARM, TTS_PORT, ACK_NAK_SIZE, DEFAULT_TTS_VOICE_MODEL, DEFAULT_TTS_LANGUAGE

"""
tts.py - python cgi script to handle http post request to convert
a text string to a wav file indirectly using a pool of TTS server
farms or if so configure3d, to transcribe locally. Text in, wav 
data out. this is the code run on a cgi server like apache/nginx

Usage:
  curl -X POST -F "text=testing one two three" -F "engine=tts" -F "model=tts/some/model" F "voice=voice1" -F "language=en" -F "key=mykey" localhost/cgi-bin/tts.py
  the above also represent the default values. only text, voice, language and key are supported

Where:
  key      = the user's api key
  text     = a bunch of text to be converted to wav file

  Optional values 
    language = the language to be used (default=en)
    voice = the voice to be used (default=voice1, only voice2 also supported)

  Unsupported values 
    engine  = currently only TTS supported. soon Mimic3
    model  = currently ignored.  eventually engine-model-voice will be supported

Everything is optional except key and text.
"""
tts_cgi = TTS_CGI("remote")
if tts_cgi.error_msg != '':
    bail(tts_cgi.error_msg)

tts_cgi.process_form()
if tts_cgi.error_msg != '':
    bail(tts_cgi.error_msg)

retry_ctr = 3
result = ''
while retry_ctr > 0 and result != "SUCCESS":
    result = tts_cgi.transcribe()
    bark("try tts transcribe, ctr = %s, result = %s" % (retry_ctr,result))
    retry_ctr -= 1

# otherwise all is good, send back wav data
print('Content-Type: audio/x-wav\r\n\r\n', end='')
sys.stdout.flush() 
sys.stdout.buffer.write(tts_cgi.transcriber.wav_data)
sys.stdout.flush() 

