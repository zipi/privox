import cgi, os, sys
import datetime
import cgitb
cgitb.enable()
from cgi_util import get_available_for_key
from cgi_util import bark
from cgi_config import (
            MAX_POST_BODY_SIZE, 
            DEFAULT_STT_QUALITY, 
            MIN_WAV_FILE_SIZE
        )

# this indicates you can 
# perform wav file translation
FFMPEG_IS_INSTALLED = True

class STT_CGI():
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

    def __init__(self, local_or_remote):
        self.error_msg = ''
        self.user_key = ''
        self.quality = ''
        self.lang = ''
        self.engine = 'w'
        self.xlate = ''

        # poor man's plugin
        from stt_remote_transcriber import STT_Transcriber
        if local_or_remote == "local":
            from stt_local_transcriber import STT_Transcriber
        self.transcriber = STT_Transcriber()

    def process_form(self):
        # validate post size
        cgi.maxlen = MAX_POST_BODY_SIZE
        content_length = int(os.getenv('CONTENT_LENGTH', 0))
        if content_length > MAX_POST_BODY_SIZE:
            self.error_msg = "Max CGI Body Size Exceeded"
            return

        # posted data not too big, continue with request
        form = cgi.FieldStorage()

        # api key
        self.user_key = form.getvalue('key')
        # no key no service
        if not self.user_key:
            self.error_msg = "No Key"
            return

        try: self.user_key = self.user_key.decode('utf-8')
        except: pass
    
        if type(self.user_key) != str:
            self.error_msg = "Bad Key Format"
            return

        # quality
        self.quality = form.getvalue('quality')
        if not self.quality:
            self.quality = DEFAULT_STT_QUALITY
        else:
            try: self.quality = self.quality.decode('utf-8')
            except: pass

        if type(self.quality) != str:
            self.error_msg = "Bad Quality Format"
            return

        # language
        self.lang = form.getvalue('language')  
        if not self.lang:
            self.lang = 'English'

        try: self.lang = self.lang.decode('utf-8')
        except: pass

        if type(self.lang) != str:
            self.error_msg = "Bad Language Format"
            return

        # determine model name
        self.model_name = "base"   # TODO config default
        quality_multiplier = self.quality_to_multiplier[self.quality]
        self.model_name = self.quality_to_model.get(self.quality, None)
        if not self.model_name:
            self.error_msg = "Bad Quality"
            return

        if self.lang == 'English' and not self.quality.startswith("x"):
            # careful here, x as in (x)cribe and (x)cribe2 which have no en
            self.model_name += ".en"

        # verify user has enough data remaining to make request
        max_user_bytes_remaining = int( get_available_for_key(self.user_key) )
        if max_user_bytes_remaining < 0:
            self.error_msg = "Invalid Key"
            return

        fileitem = ''
        try:
            fileitem = form['file']
        except:
            self.error_msg = "No File"
            return

        self.wav_data = fileitem.file.read()   # read wav bytes
        input_size = len(self.wav_data)

        bark("stt.py - received %s bytes from upload" % (input_size,))

        if input_size > max_user_bytes_remaining:
            self.error_msg = "Too Many Bytes"
            return

        if input_size < MIN_WAV_FILE_SIZE:
            self.error_msg = "Not Enough Bytes"
            return

        self.xlate = form.getvalue('xlate')   
        if self.xlate:
            try: self.xlate = self.xlate.decode('utf-8')
            except: pass
    
        if self.xlate and type(self.xlate) != str:
            self.error_msg = "Bad Translation Flag Format"
            return

    def transcribe(self):
        if self.xlate and self.xlate == "xlate":
            bark("stt_cgi.py: translate wav input data")
            # here we need to convert if the xlate flag is set. 
            # this is due to the ogg javascript sends us 
            if not FFMPEG_IS_INSTALLED:
                ## this will not work if you do not have ffmpeg
                ## installed so we add a config value for it
                self.error_msg = "Translation Requested but no FFMPEG"
                return

            filename_in = datetime.datetime.now().strftime("jswav_%Y-%m-%d_%H-%M-%S_%f.wav")
            filename_out = "new_" + filename_in
            filename_in = "/tmp/privox/" + filename_in
            filename_out = "/tmp/privox/" + filename_out

            fh = open(filename_in, "wb")
            fh.write(self.wav_data)
            fh.close()
            os.system("ffmpeg -i %s -ar 16000 -ac 1  %s" % (filename_in, filename_out))
            fh = open(filename_out, "rb")
            self.wav_data = fh.read()
            fh.close()
            os.system("rm -f " + filename_in)
            os.system("rm -f " + filename_out)

        bark("stt_cgi.py: calling transcriber")
        return self.transcriber.transcribe(self.user_key, self.model_name, self.wav_data, self.lang)

