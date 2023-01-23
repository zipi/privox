import asyncio, time
from privox_utils import (
        event_wait, 
        write_transaction, 
        update_client_sockets,
        set_socket_event,
        clear_socket_event,
        PRODUCER_FARM_AUTH_KEY
        )

PING_FREQUENCY = 10
PING_PONG_SIZE = 4
ACK_NAK_LEN = 3

async def ping_endpoint(loop, client, mysid, client_sockets):
    """ returns False if ping failed or 
    True if it succeeded """
    ping = b'ping'
    try:
        await loop.sock_sendall(client, ping)
    except:
        print("Broken endpoint connection detected!")
        update_vals = {'status':'DEAD!'}
        await update_client_sockets(mysid, update_vals, client_sockets)
        client.close()
        return False

    try:
        request = (await loop.sock_recv(client, PING_PONG_SIZE)).decode('utf8')
    except:
        client.close()
        return False

    response = str(request)
    ping_data = {'auth_key':PRODUCER_FARM_AUTH_KEY, 'service':'TTS', 'session_id':client_sockets[mysid]['session'], 'client_key':client_sockets[mysid]['key']}

    await write_transaction('ping', ping_data)
    return True


async def handle_producer_socket(client, sid, event, client_sockets):
    """ producers are also known as endpoints. they are the
    sockets that send the data to the endpoint that does 
    the actual work. """
    loop = asyncio.get_event_loop()
    mysid = sid
    myevent = event
    request = None
    response = ''
    xact_start = 0
    xact_end = 0
    exit_flag = False
    stupid_buffer = b''
    print("A new TTS endpoint worker has come on line and is waiting for work", mysid)
    while not exit_flag:

        while not await event_wait(myevent, PING_FREQUENCY):
            # ping every 'ping frequency' while waiting for work

            if not await ping_endpoint(loop, client, mysid, client_sockets):
                exit_flag = True
                break

        if exit_flag:
            print("Ping failed, aborting client socket")
            break

        # we got a request
        update_vals = {'status':'busy'}
        await update_client_sockets(mysid, update_vals, client_sockets)

        request_sid = client_sockets[mysid]['request_sid']
        packet_header = "model=%s&text=%s&lang=%s&idx=%s" % ( client_sockets[mysid]['model_name'], client_sockets[mysid]['request_data'], client_sockets[mysid]['language'], client_sockets[mysid]['index'] )

        print("TTS Client Socket: SID:%s processing TTS server request from %s, sending --->%s" % (mysid, request_sid, packet_header))
        try:
            # send header
            await loop.sock_sendall(client, packet_header.encode('utf8'))
        except:
            response = "Error trying to send request header to endpoint, socket exiting!"
            exit_flag = True

        if not exit_flag:
            # wait response
            try:
                request = (await loop.sock_recv(client, ACK_NAK_LEN)).decode('utf8')
                response = str(request)
            except:
                response = "Error trying to send request header to endpoint, socket exiting!"
                exit_flag = True

        if not exit_flag:
            if response == 'ack':

                xact_start = time.time()
                # rcv wav data length fixed 8 byte string
                try:
                    wav_data_len = (await loop.sock_recv(client, 8)).decode('utf8')
                except:
                    response = "Error receiving wav data len from endpoint"
                    exit_flag = True

                fixed_size_len = wav_data_len
                wav_data_len = int(wav_data_len)

                # rcv wav data
                bytes_rcvd = 0
                chunk_size = 1024
                stupid_buffer = b''
                while bytes_rcvd < wav_data_len:
                    try:
                        tmp_buff = (await loop.sock_recv(client, chunk_size))
                    except Exception as e:
                        print(e)
                        response = "Error receiving wav data from endpoint"
                        exit_flag = True
                        break

                    bytes_rcvd += len(tmp_buff)
                    stupid_buffer += tmp_buff

                xact_end = time.time()

            else:
                response = "Client Protocol Error: no ack in response to model"
                exit_flag = True

        # communicate response
        update_vals = {
                'response_data': stupid_buffer,
                'xact_time': str( xact_end - xact_start ),
                'client_key': client_sockets[mysid]['key'],
                'response': response,
                'wav_data_size': fixed_size_len,
                'client_ip': client_sockets[mysid]['ip'],
                'client_port': client_sockets[mysid]['port'],
                'session': client_sockets[mysid]['session']
                }
        # clean up
        await update_client_sockets(request_sid, update_vals, client_sockets)
        await set_socket_event(request_sid, client_sockets)
        await clear_socket_event(mysid, client_sockets)
        update_vals = {'status':'idle'}
        await update_client_sockets(mysid, update_vals, client_sockets)

    print("TTS Client Socket exiting %s, reason = %s" % (mysid, response))
    try:
        client.close()
    except:
        pass


