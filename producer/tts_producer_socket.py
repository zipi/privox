#!/usr/bin/env python3
"""
tts_socket_endpoint.py
tts endpoint. this script connects a socket to a producer farm 
and waits for requests to convert a text string to a wav file.
script uses the coqui tts models to perform the transcription.
"""
VERSION="1.0"
print(VERSION)

import datetime, socket, time, TTS, sys
from io import BytesIO
from pathlib import Path
from TTS.utils.manage import ModelManager
from TTS.utils.synthesizer import Synthesizer

PRODUCER_FARMS = {
#        'pfalpha': {'ssl':'no'},
        'pfbeta':  {'ssl':'no'},
        'spfbeta': {'ssl':'yes'}
        }

def usage():
    print()
    print("Usage:")
    print("    ./tts_producer_socket.py API_KEY")
    print("Where:")
    print("    API_KEY is your user key from your profile page.\n")
    print("")
    quit()


def log_msg(msg):
    now = str(datetime.datetime.now()).split(".")[0]
    print("[%s]%s" % (now, msg))


def produce_wav(text, io_buff, speaker_index, language, model_name):
    # convert text to a wav file using whisper
    path = Path(TTS.__file__).parent  / ".models.json"
    manager = ModelManager(path)
    speakers_file_path = None
    vocoder_path = None
    vocoder_config_path = None
    encoder_path = None
    encoder_config_path = None
    use_cuda = False

    model_path, config_path, model_item = manager.download_model(model_name)
    vocoder_name = model_item["default_vocoder"]

    synthesizer = Synthesizer(
            model_path,
            config_path,
            speakers_file_path,
            vocoder_path,
            vocoder_config_path,
            encoder_path,
            encoder_config_path,
            use_cuda,
        )
    wav = synthesizer.tts(text, speaker_index)
    synthesizer.save_wav(wav, io_buff)


def send_freakin_data(sock, bio_fh):
    # been doing it this way for over 30 years already.
    # you would think sendall/recvall would work by now
    total_sent = 0
    chunk_size = 1024
    wav_data = bio_fh.read()
    while len(wav_data):
        chunk = wav_data[:chunk_size]
        sent = sock.send(chunk)
        total_sent += sent
        wav_data = wav_data[sent:]

    return total_sent


class TTSProducerNode:
    def __init__(self, HOST, PORT):
        self.host = HOST
        self.port = PORT
        self.status = "connected"
        self.err_msg = "can't establish connection"
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.s.connect((HOST, PORT))
            self.err_msg = ""
        except:
            self.status = "inactive"

    def identity_established(self):
        # wait for 'who' packet and respond with type and key
        log_msg("Connected, waiting for 'who'")

        data = self.s.recv(3)
        data = data.decode("utf-8")
        if data == "who":
            response = 'c' + MY_KEY
            self.s.sendall(response.encode("utf-8"))
            return True
        return False


    def process(self):
        if not self.identity_established():
            self.status = "inactive"
            self.err_msg = "can't establish identity"
            return

        log_msg("Waiting for requests")

        wav_data_len = 0
        while True:
            # wait for requests and service them. 
            # bail if broken socket detected
            data = self.s.recv(1024)

            if len(data) == 0:
                self.err_msg = "Error, connection with cloud broken. Bailing!"
                return

            log_msg("rcvd %s bytes of data" % (len(data),))
 
            header = data.decode("utf-8").split("&")
            log_msg("HDR: %s" % (header,))

            if not header[0]:
                log_msg("Missing Header")

            elif header[0].startswith("ping"):
                self.s.sendall(b"pong")
                log_msg("Sent ['Pong']")

            elif header[0].startswith("model"):
                # required params
                model_name = header[0].split("=")[1]
                text_input = header[1].split("=")[1]

                # optional params
                language = "en"
                speaker = "p236"
                if len( header ) > 2:
                    language = header[2].split("=")[1]

                if len( header ) > 3:
                    speaker = header[3].split("=")[1]

                log_msg("lang:%s, spid:%s, model:%s, text:%s" % (language, speaker, model_name, text_input))

                # acknowledge header receipt
                self.s.sendall(b"ack")
                log_msg("Sent ack")

                # do it
                bio_fh = BytesIO()
                try:
                    produce_wav(text_input, bio_fh, speaker, language, model_name)
                except:
                    log_msg("Transcription Exception Caught!")

                wav_data_len = bio_fh.getbuffer().nbytes

                fixed_len_size = str(wav_data_len)
                while len(fixed_len_size) < 8:
                    fixed_len_size = "0" + fixed_len_size

                # tts protocol is get a text string send back a 
                # wav header and wav file. wav header is simply
                # a fixed length string representing the size
                self.s.sendall(fixed_len_size.encode("utf-8"))

                bio_fh.seek(0)
                sent = send_freakin_data(self.s, bio_fh)
                log_msg("%s bytes wav data sent" % (sent,))

            else:
                log_msg("Warning! Ignoring Invalid Header")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        usage()

    MY_KEY = sys.argv[1]
    SLEEP_TIME = 60
    PORT = 1777                  # The port used by the server

    while True:
        for farm in PRODUCER_FARMS:
            ssl = PRODUCER_FARMS[farm]['ssl']
            HOST = farm + ".privox.io"
            print("\nTrying to connect to producer farm = %s, ssl = %s, url = %s" % (farm, ssl, HOST))
            tpn = TTSProducerNode(HOST, PORT)
            print("status %s" % (tpn.status,))
            if tpn.status == 'connected':
                tpn.process()
            print("TPN exited, reason = %s, msg = %s" % (tpn.status, tpn.err_msg))

        # exhausted all farms, let's give it a rest for a while
        print("Exhausted all producer farms, sleeping for %s seconds" % (SLEEP_TIME,))
        time.sleep(SLEEP_TIME)

