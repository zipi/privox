import sys, datetime
import urllib.request
from cgi_config import PV_VALIDATE_USER_URL

JS_KEY = ""
SILENT = False

def bark(msg):
    # this ends up in apache error log
    if not SILENT:
        now = str(datetime.datetime.now()).split(".")[0]
        msg = "[%s]%s" % (now, msg)
        print(msg, file=sys.stderr)
        sys.stderr.flush()


def bail(reason):
    """ return error and bail """
    print('Content-Type: text/plain\r\n\r\n', end='')
    sys.stdout.flush()
    print(reason)
    sys.stdout.flush()
    quit()


def get_available_for_key(user_key):
    if user_key == JS_KEY:
        return '2000000'

    request_url = urllib.request.urlopen( PV_VALIDATE_USER_URL + user_key )
    return request_url.read().decode('utf-8')


