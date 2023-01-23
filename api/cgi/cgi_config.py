
IN_FILE_SIZE = 100
ONE_MB = 1024 * 1024
# this is max for everybody, not just this key
MAX_POST_BODY_SIZE = 200 * ONE_MB

# where to go to validate a user
PV_VALIDATE_USER_URL = ''

PV_PRODUCER_FARM = 'pfalpha.privox.io'  # The server's hostname or IP address
STT_PORT = 1776  # The port used by the server
TTS_PORT = 1777  # The port used by the server
ACK_NAK_SIZE = 3

# voice paramater is basically model
DEFAULT_TTS_VOICE_MODEL = 'tts_models/en/vctk/vits'
DEFAULT_TTS_LANGUAGE = 'en'

DEFAULT_STT_QUALITY = 'fast'
MIN_WAV_FILE_SIZE = 100
