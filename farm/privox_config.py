#
# stick any manifest constants shared by the 
# system in here. use PV_ convention for
# pseudo namespacing.
#

# validate response shared with cgi script
PV_USER_KEY_NOT_FOUND = -1

# where to validate a user key
PV_VALIDATE_USER_URL = ''

# where to post json results transactions 
PV_POST_TRANSACTION_URL = ''

# various keys and identifiers
PV_STT_PRODUCER_FARM_AUTH_KEY = ''
PV_TTS_PRODUCER_FARM_AUTH_KEY = ''

# operational values
PV_STT_CLIENT_TIME_OUT = 20
PV_TTS_CLIENT_TIME_OUT = 20

# socket server constants
PV_AUTH_RESPONSE_SIZE = 17
PV_DEFAULT_SOCKET_HOST = '0.0.0.0'
PV_DEFAULT_SOCKET_PORT_STT = 1776
PV_DEFAULT_SOCKET_PORT_TTS = 1777

STT_CLIENT_REQUEST_TIMEOUT = 60
TTS_CLIENT_REQUEST_TIMEOUT = 60
