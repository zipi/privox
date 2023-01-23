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
        print("Broken endpoint connection detected! Closing connection")
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
    ping_data = {'auth_key':PRODUCER_FARM_AUTH_KEY, 'service':'STT', 'session_id':client_sockets[mysid]['session'], 'client_key':client_sockets[mysid]['key']}
    await write_transaction('ping', ping_data)
    return True


async def handle_producer_socket(client, sid, event, client_sockets):
    """ clients are also known as endpoints. they are the
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

    print("A new STT endpoint worker has come on line and is waiting for work", mysid)
    while not exit_flag:

        while not await event_wait(myevent, PING_FREQUENCY):
            # ping every second while waiting for work

            if not await ping_endpoint(loop, client, mysid, client_sockets):
                exit_flag = True
                break

        if exit_flag:
            print("Ping failed, aborting STT client socket")
            break

        # we got a request
        update_vals = {'status':'busy'}
        await update_client_sockets(mysid, update_vals, client_sockets)

        request_sid = client_sockets[mysid]['request_sid']
        language = client_sockets[request_sid]['language']

        fixed_len_size = str(len(client_sockets[mysid]['request_data']))
        while len(fixed_len_size) < 8:
            fixed_len_size = '0' + fixed_len_size

        packet_header = "model=%s&len=%s&lang=%s" % ( client_sockets[mysid]['model_name'], fixed_len_size, language )

        #print("SID:%s processing server request from %s, sending --->%s" % (mysid, request_sid, packet_header))

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
                # send wav data
                try:
                    await loop.sock_sendall(client, client_sockets[mysid]['request_data'])
                except:
                    response = "Error sending wav data to endpoint"
                    exit_flag = True

                if not exit_flag:
                    # wav data sent, wait for response
                    xact_start = time.time()
                    try:
                        request = (await loop.sock_recv(client, 255)).decode('utf8')
                        response = str(request)
                        xact_end = time.time()
                    except:
                        response = "Error trying to receive response"
                        exit_flag = True
            else:
                response = "Client Protocol Error: no ack in response to model"
                exit_flag = True

        # communicate response
        update_vals = {
                'xact_time':str( xact_end - xact_start ),
                'client_key':client_sockets[mysid]['key'],
                'response':response,
                'client_ip':client_sockets[mysid]['ip'],
                'client_port':client_sockets[mysid]['port'],
                'session':client_sockets[mysid]['session'],
                }
        await update_client_sockets(request_sid, update_vals, client_sockets)
        await set_socket_event(request_sid, client_sockets)

        # clean up
        await clear_socket_event(mysid, client_sockets)
        update_vals = {'status':'idle'}
        await update_client_sockets(mysid, update_vals, client_sockets)

    print("Client Socket exiting %s" % (mysid,))
    try:
        client.close()
    except:
        pass

