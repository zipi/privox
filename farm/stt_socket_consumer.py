import asyncio, datetime, json
from privox_utils import (
        event_wait, 
        remove_socket_from_client_sockets, 
        find_next_available_client,
        write_transaction,
        update_client_sockets,
        set_socket_event,
        delete_socket_key,
        PRODUCER_FARM_AUTH_KEY
        )

from privox_config import STT_CLIENT_REQUEST_TIMEOUT

async def handle_consumer_socket(client, sid, event, client_sockets, monitor_stats):
    """ a server socket is typically a request from a
    cgi handler who has been posted with a stt request"""
    loop = asyncio.get_event_loop()
    mysid = sid
    myevent = event
    endpoint_response = ''
    header = ''
    request = ''

    print("\n*** Server Socket %s Entering ***" % (sid,))
    # wait for header
    try:
        request = (await loop.sock_recv(client, 255)).decode('utf8')
    except:
        endpoint_response = "Error trying to get header from cgi, Bailing!"

    if len(request) == 0:
        print("Error, connection with cloud broken. Bailing!")
        endpoint_response = "Error, connection with cloud broken. Bailing!"
        try:
            await loop.sock_sendall(client, b'nak')
        except:
            endpoint_response = "Error trying to send nak to cgi"

    if endpoint_response == '':
        header = request.split('&')
        #print("HDR: %s" % (header,))

        if not header[0].startswith('model'):
            endpoint_response = "Invalid Header"
            try:
                await loop.sock_sendall(client, b'nak')
            except:
                endpoint_response = "Error trying to send nak to cgi"

    if endpoint_response == '':
        model_name = header[0].split('=')[1]
        wav_data_len = int( header[1].split('=')[1] )
        lang = header[2].split('=')[1] 

        # give request to client socket
        client_sid = await find_next_available_client(client_sockets)
        if client_sid == 0:
            endpoint_response = "no available clients"
            try:
                await loop.sock_sendall(client, b'nak')
            except:
                endpoint_response = "Error trying to send nak to cgi"

        else:
            update_vals = {'status':'busy'}
            await update_client_sockets(client_sid, update_vals, client_sockets)

            try:
                await loop.sock_sendall(client, b'ack')
            except:
                endpoint_response = "cant send ack to client"

            if endpoint_response == '':
                # wait for wav data
                try:
                    wav_data = b''
                    bytes_rcvd = 0
                    while bytes_rcvd < wav_data_len:
                        chunk = (await loop.sock_recv(client, 1024))
                        wav_data += chunk
                        bytes_rcvd += len(chunk)
   
                    update_vals = {'wav_data_size':bytes_rcvd, 'model_name':model_name, 'auth_key':PRODUCER_FARM_AUTH_KEY, 'language': lang}
                    await update_client_sockets(mysid, update_vals, client_sockets)

                    update_vals = {'request_sid':mysid, 'request_data':wav_data, 'model_name':model_name}
                    await update_client_sockets(client_sid, update_vals, client_sockets)

                    await set_socket_event(client_sid, client_sockets)

                except:
                    endpoint_response = "Exception - srvr_skt: looks like client socket died behind my back"

                if not await event_wait(myevent, STT_CLIENT_REQUEST_TIMEOUT):
                    # handle timeout here!
                    endpoint_response = "timed out waiting on client"
                else:
                    monitor_stats['successful_requests'] += 1
                    endpoint_response = client_sockets[mysid]['response']

                    await delete_socket_key(mysid, 'event', client_sockets)
                    await write_transaction('xact', client_sockets[mysid])

    try:
        await loop.sock_sendall(client, endpoint_response.encode('utf-8'))
    except:
        endpoint_response = "Error sending response to cgi request socket"

    print("*** Server Socket %s Exiting, result = %s ***\n" % (mysid, endpoint_response))
    try:
        client.close()
    except:
        pass

