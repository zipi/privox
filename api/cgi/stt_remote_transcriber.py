import socket, random
from cgi_config import ACK_NAK_SIZE, STT_PORT
from cgi_util import bark

PRODUCER_FARMS = ['pfalpha', 'pfbeta']

def get_producer_farm():
    max_val = len(PRODUCER_FARMS)
    rnd_val = int( random.random() * 100 ) % max_val
    return PRODUCER_FARMS[rnd_val] + ".privox.io"


class STT_Transcriber:
    def __init__(self):
        self.text = ''
        self.err_msg = ''

    def send_freakin_data(self, sock, wav_data):
        # you would think after 20 years 
        # sendall() would work by now.
        total_sent = 0
        chunk_size = 1024
        while len(wav_data):
            chunk = wav_data[:chunk_size]
            sent = sock.send(chunk)
            total_sent += sent
            wav_data = wav_data[sent:]
            #bark("sent %s bytes" % (sent,))
        return total_sent


    def transcribe(self, user_key, model_name, wav_data, lang):
        self.text = 'Creepy Internal Error 101'
        self.err_msg = 'err'
        PV_PRODUCER_FARM = get_producer_farm()
        bark("stt - trying producer farm: %s" % (PV_PRODUCER_FARM,))
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.connect((PV_PRODUCER_FARM, STT_PORT))
            except:
                return "ERR-STT Can't connect to producer farm %s:%s." % (PV_PRODUCER_FARM, STT_PORT)
 
            # wait for 'who' packet and respond with type and key
            data = s.recv(ACK_NAK_SIZE)
            data = data.decode('utf-8')

            if data == 'who':
                hdr = "s%s" % (user_key,)
                s.sendall(hdr.encode('utf-8'))
            else:
                return "No who rcvd, bail"

            # TODO want fixed sizes where possible
            # make this a fixed size header
            header = "model=%s&len=%s&lang=%s" % (model_name, len(wav_data), lang)
            s.sendall(header.encode('utf-8'))

            #bark("stt_transcribe: sent header = %s" % (header,))
            try: data = s.recv(ACK_NAK_SIZE)
            except: return "remote endpoint died"

            data = data.decode('utf-8')
            #bark("stt_transcribe: Got data=%s" % (data,))
            
            if data == 'ack':
                num_bytes_sent = self.send_freakin_data(s, wav_data)
                data = s.recv(1024)

                if len(data) == 0:
                    return "no response from remote socket"

                self.text = data
                try: 
                    self.text = data.decode('utf-8')
                    self.err_msg = ''
                except: pass

            else:
                return "ack not rcvd, instead rcvd ---> %s" % (data,)

        return self.text

