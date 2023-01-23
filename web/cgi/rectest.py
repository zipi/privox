#!/home/ec2-user/venv_privox/bin/python3
import requests
import time, sys, cgi, os
import cgitb
cgitb.enable()
JS_KEY = ""
"""
rectest.py - python cgi script to handle
javascript local post request for privox
api server.
"""
# this ends up in apache error log
def bark(msg):
    # this ends up in apache error log
    print(msg, file=sys.stderr)
    sys.stderr.flush()

bark("*** Starting rectest.py ***")

def bail(reason):
    """ return error and bail """
    print('Content-Type: text/plain\r\n\r\n', end='')
    print(reason)
    quit()

quality_to_model = {
        'fast':'tiny',
        'normal':'base',
        'better':'small',
        'best':'medium',
        'xcribe':'large',
        'xcribe2':'large-v2'
        }
MIN_FILE_SIZE = 100
ONE_MB = 1024 * 1024
MAX_WAV_SIZE = 2000000 # way too lg but anyway

# this is max for everybody, not just this key
MAX_POST_BODY_SIZE = 200 * ONE_MB

cgi.maxlen = MAX_POST_BODY_SIZE
content_length = int(os.getenv('CONTENT_LENGTH', 0))
if content_length > MAX_POST_BODY_SIZE:
    bail("POST body too long")

# posted data not too big, continue with request
form = cgi.FieldStorage()

# get posted key/value data

quality = form.getvalue('quality')
lang = form.getvalue('language')   # only 'en' (optimization)
engine = 'w'
fileitem = ''
try:
    fileitem = form['file']
except:
    bail("No File")

data = fileitem.file.read()   # read wav bytes
input_size = len(data)
if input_size > MAX_WAV_SIZE:
    bail("Too Many Bytes: req:%s, max:%s" % (input_size, MAX_WAV_SIZE))

if input_size < MIN_FILE_SIZE:
    bail("Too Small")

# determine model name
model_name = "base"   # default
if quality:
    model_name = quality_to_model.get(quality, None)
    if not model_name:
        bail("Bad Quality")

if lang and lang == 'en' and not quality.startswith("x"):
    model_name += ".en"

multipart_form_data = {
    'file': data,
    'language': lang,
    'key': JS_KEY,
    'xlate': 'xlate',
    'quality': quality,
    'model': model_name
}

response = requests.post('http://api.privox.io/cgi-bin/stt.py', files=multipart_form_data)
text = response.content

print('Content-Type: text/plain\r\n\r\n', end='')
print(text)

