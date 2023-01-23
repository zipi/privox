#!/home/ec2-user/venv_privox/bin/python3
import datetime
import requests
import time, sys, cgi, os
import cgitb
cgitb.enable()
JS_KEY = ""

# this ends up in apache error log
def bark(msg):
    # this ends up in apache error log
    print(msg, file=sys.stderr)

bark("*** Starting playtest.py ***")

def bail(reason):
    """ return error and bail """
    print('Content-Type: text/plain\r\n\r\n', end='')
    print(reason)
    quit()

def get_available_for_key(user_key):
    """ get bytes available based on api key
        Output:
          -1 if key not found.
          0 if user has less than 100 bytes 
            remaining, otherwise the number
            of bytes the user has remaining."""
    return 200000

quality_to_model = {
        'fast':'tiny',
        'normal':'base',
        'better':'small',
        'best':'medium',
        'xcribe':'large',
        'xcribe2':'large-v2'
        }
quality_to_multiplier = {
        'fast': 1,
        'normal': 2,
        'better': 4,
        'best': 8,
        'xcribe': 16,
        'xcribe2': 32
        }

MIN_FILE_SIZE = 100
ONE_MB = 1024 * 1024

# this is max for everybody, not just this key
MAX_POST_BODY_SIZE = 200 * ONE_MB

cgi.maxlen = MAX_POST_BODY_SIZE
content_length = int(os.getenv('CONTENT_LENGTH', 0))
if content_length > MAX_POST_BODY_SIZE:
    bail("POST body too long")

# posted data not too big, continue with request
form = cgi.FieldStorage()

for key in form:
    bark(key)

# establish scope
inp = ''
text = ''
fileitem = ''

# get posted key/value data

bark("ckpt0001")
# key
text = form.getvalue('text')
voice = form.getvalue('voice')
# so all is good let's get to transcribing ...
user_key = ''
form_data = {
    'text': text,
    'key': JS_KEY,
    'voice': voice
}

# remove old files
where = "/home/ec2-user/Privox/media/"
with os.scandir(where) as entries:
    for entry in entries:
        if entry.name.endswith(".wav"):
            age = time.time() - entry.stat().st_mtime
            if age > 60:
                filename = os.path.join(where, entry.name)
                os.system("rm -f " + filename)

response = requests.post('http://api.privox.io/cgi-bin/tts.py', files=form_data)

filename = datetime.datetime.now().strftime("jswav_%Y-%m-%d_%H-%M-%S_%f.wav")

fh = open(where + filename, "wb")
fh.write(response.content)
fh.close()

print('Content-Type: text/plain\r\n\r\n', end='')
print('/media/' + filename)

