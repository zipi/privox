import cgi, os
from cgi_util import get_available_for_key
from cgi_config import MAX_POST_BODY_SIZE, DEFAULT_TTS_VOICE_MODEL, DEFAULT_TTS_LANGUAGE

from cgi_util import bark

class TTS_CGI():
    def __init__(self, local_or_remote):
        self.result = ''
        self.error_msg = ''

        # poor man's plugin
        from tts_remote_transcriber import TTS_Transcriber
        if local_or_remote == "local":
            from tts_local_transcriber import TTS_Transcriber
        self.transcriber = TTS_Transcriber()

    def process_form(self):
        voices = {"voice1":"p236", "voice2":"p270"}
        # validate post size
        cgi.maxlen = MAX_POST_BODY_SIZE
        content_length = int(os.getenv('CONTENT_LENGTH', 0))
        if content_length > MAX_POST_BODY_SIZE:
            self.error_msg = "Max CGI Body Size Exceeded"
            return

        # posted data not too big, continue with request
        self.form = cgi.FieldStorage()

        # api key
        self.user_key = self.form.getvalue('key')
        try: self.user_key = self.user_key.decode('utf-8')
        except: pass
        if type(self.user_key) != str:
            self.error_msg = "Invalid API Key Format"
            return

        # no key no service
        if not self.user_key:
            self.error_msg = "Missing API Key"
            return

        # text
        self.text_input = self.form.getvalue('text') 
        try: self.text_input = self.text_input.decode('utf-8')
        except: pass
        if type(self.text_input) != str:
            self.error_msg = "Invalid Text Input Format"
            return

        if not self.text_input:
            self.error_msg = "Missing Text Input"
            return

        # which voice to use
        self.voice = self.form.getvalue('voice')
        try: self.voice = self.voice.decode('utf-8')
        except: pass
        if type(self.voice) != str:
            self.error_msg = "Invalid Voice Input Format"
            return

        if self.voice not in voices:
            self.error_msg = "Invalid Voice Selected, voice1 or voice2 only"
            return

        self.speaker_index = voices[self.voice]

        # language
        self.lang = self.form.getvalue('language')   # only 'en' (optimization)
        try: self.lang = self.lang.decode('utf-8')
        except: pass
        if self.lang and type(self.lang) != str:
            self.error_msg = "Invalid Language Input Format"
            return

        if not self.lang:
            self.lang = DEFAULT_TTS_LANGUAGE

        # verify user has enough data remaining 
        max_user_bytes_remaining = int( get_available_for_key(self.user_key) )
        if max_user_bytes_remaining < 0:
            self.error_msg = "Invalid API Key"
            return

    def transcribe(self):
        result = self.transcriber.transcribe(self.user_key, DEFAULT_TTS_VOICE_MODEL, self.speaker_index, self.text_input, self.lang)
        self.error_msg = result
        return result

