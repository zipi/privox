import socket, random, time, sys, cgi, os
from cgi_config import ACK_NAK_SIZE, TTS_PORT
from cgi_util import bark

PRODUCER_FARMS = ['pfalpha', 'pfbeta']

def get_producer_farm():
    max_val = len(PRODUCER_FARMS)
    rnd_val = int( random.random() * 100 ) % max_val
    return PRODUCER_FARMS[rnd_val] + ".privox.io"


class TTS_Transcriber:
    def __init__(self):
        self.wav_data = b''

    def recv_freakin_data(self, sock, wav_data_len):
        bytes_rcvd = 0
        chunk_size = 1024
        self.wav_data = b''
        while bytes_rcvd < wav_data_len:
            tmp_buff = sock.recv(chunk_size)
            self.wav_data += tmp_buff
            bytes_rcvd += len(tmp_buff)

        return bytes_rcvd


    def transcribe(self, user_key, model, voice, text_input, lang):
        result = 'TTS: Creepy Internal Error 101'
        PV_PRODUCER_FARM = get_producer_farm()
        bark("TTS selected %s" % (PV_PRODUCER_FARM,))
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.connect((PV_PRODUCER_FARM, TTS_PORT))
            except:
                return "Can't connect to backend!"

            # wait for 'who' packet and respond with type and key
            data = s.recv(ACK_NAK_SIZE)
            data = data.decode('utf-8')
            if data == 'who':
                hdr = "s%s" % (user_key,)
                s.sendall(hdr.encode('utf-8'))
            else:
                return "No who rcvd, bail"

            header = "model=%s&text=%s&lang=%s&idx=%s" % (model, text_input, lang, voice)
            s.sendall(header.encode('utf-8'))

            bark("tts.py - header sent, waiting for ack to send wav data")
            # TODO 8 is fixed size data length parameter
            try:
                data = s.recv(8)
            except:
                return "remote endpoint died"

            bark("rcvd:%s" % (data,))
            try:
                data = data.decode('utf-8')
                wav_data_len = int(data)
            except:
                return "producer farm error"

            #bark("tts.py - %s bytes will be received " % (wav_data_len,))
            wav_data_len = self.recv_freakin_data(s, wav_data_len)

            return "SUCCESS"

        return result

