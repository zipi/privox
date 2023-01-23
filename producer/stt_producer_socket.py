#!/usr/bin/env python
"""
stt_producer_socket: 
  a stt producer which adheres to the privox pull node protocol.
  this script connects a socket to a producer farm and waits 
  for requests to convert a wav file to a text string.
"""
VERSION="1.0"
print(VERSION)

import datetime, whisper, socket, numpy, time, sys, io
from zipfile import ZipFile

PRODUCER_FARMS = {
        'pfbeta':  {'ssl':'no'},
        'pfalpha': {'ssl':'no'},
        'spfbeta': {'ssl':'yes'}
        }

def usage():
    log_msg("Usage:")
    log_msg("    ./stt_prodeucer_socket.py API_KEY")
    log_msg("Where:")
    log_msg("    API_KEY is your user key from your profile page.")
    quit()


def log_msg(msg):
    now = str(datetime.datetime.now()).split(".")[0]
    print("[%s]%s" % (now, msg))


class STTProducerNode:
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

        log_msg("Waiting for rquests")

        client_state = "waiting_hdr"
        wav_data = b''
        wav_data_len = 0

        while client_state != "SCRAM":
            data = self.s.recv(1024)  # todo - fix this arbitrary size

            if len(data) == 0:
                self.err_msg = "Error, connection with cloud broken. Bailing!"
                self.status = "socket error"
                client_state = "SCRAM" # graceful exit

            if client_state == "waiting_hdr":
                header = data.decode("utf-8").split('&')
                log_msg("HDR: %s" % (header,))

                if not header[0]:
                    log_msg("Missing Header")

                elif header[0].startswith("ping"):
                    self.s.sendall(b'pong')
                    log_msg("Sent ['Pong']")

                elif header[0].startswith("model"):
                    model_name = header[0].split('=')[1]
                    wav_data_len = int( header[1].split('=')[1] )
                    lang = header[2].split('=')[1]
                    client_state = "waiting_wav"
                    self.s.sendall(b'ack')
                    log_msg("ACK'ed the header, new state = %s" % (client_state,))

                else:
                    log_msg("Ignoring invalid header = %s" % (header,))

            elif client_state == "waiting_wav":
                # else collecting wav data, could use a timeout here!
                wav_data += data

                if len(wav_data) >= wav_data_len:
                    client_state = "waiting_hdr"
                    log_msg("New state = %s" % (client_state,))

                    ## given wav_data, if compressed uncompress
                    ## otherwise pass it thru
                    zip_buffer = io.BytesIO(wav_data)
                    try:
                        with ZipFile(zip_buffer, 'r') as zip:
                            wav_data = zip.read("sample.wav")
                    except:
                        log_msg("Warning - wav data not compressed!")
 
                    text = ""
                    try:
                        # Convert buffer to float32 using NumPy                                                                                 
                        audio_as_np_int16 = numpy.frombuffer(wav_data, dtype=numpy.int16)
                        audio_as_np_float32 = audio_as_np_int16.astype(numpy.float32)

                        # Normalise float32 array so that values are between -1.0 and +1.0                                                      
                        max_int16 = 2**15
                        audio_normalised = audio_as_np_float32 / max_int16
                    except:
                        text = "local client error, could be bad wav data"
                        err_msg = "bad wav data"

                    if text == '':
                        try:
                            # load model
                            model = whisper.load_model(model_name)
                        except:
                            text = "local client error, could not load model (%s)" % (model_name,)
                            err_msg = "could not load model"

                    if text == '':
                        try:
                            # transcribe
                            start_time = time.time()
                            text = model.transcribe(audio_normalised, fp16=False, language=lang)["text"].strip()
                            elapsed = time.time() - start_time
                            log_msg("Took %s --->%s" % (elapsed, header))
                        except:
                            text = "local client error, could not load transcribe"
                            err_msg = "could not transcribe"

                    wav_data_len = 0
                    wav_data = b''
                    log_msg("client sending response back = %s" % (text,))
                    self.s.sendall(text.encode("utf-8"))
            else:
                log_msg("Bailing!")
                self.err_msg = "Error, connection with cloud broken. Bailing!"
                self.status = 'socket error'
                client_state = "SCRAM" 

if __name__ == "__main__":
    SLEEP_TIME = 60
    HOST = "pfalpha.privox.io"   # The server's hostname or IP address
    PORT = 1776                  # The server port to connect to

    if len(sys.argv) < 2:
        usage()
    MY_KEY = sys.argv[1]

    while True:
        for farm in PRODUCER_FARMS:
            ssl = PRODUCER_FARMS[farm]['ssl']
            HOST = farm + ".privox.io"
            print("\nTrying to connect to producer farm = %s, ssl = %s, url = %s" % (farm, ssl, HOST))
            spn = STTProducerNode(HOST, PORT)
            print("status %s" % (spn.status,))
            if spn.status == 'connected':
                spn.process()
            print("SPN exited, reason = %s, msg = %s" % (spn.status, spn.err_msg))

        # exhausted all farms, let's give it a rest for a while
        print("Exhausted all producer farms, sleeping for %s seconds" % (SLEEP_TIME,))
        time.sleep(SLEEP_TIME)

