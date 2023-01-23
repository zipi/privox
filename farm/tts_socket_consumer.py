import asyncio, datetime, json
from privox_utils import (
        event_wait, 
        remove_socket_from_client_sockets, 
        find_next_available_client,
        write_transaction,
        update_client_sockets,
        set_socket_event,
        clear_socket_event,
        delete_socket_key,
        PRODUCER_FARM_AUTH_KEY
        )
from privox_config import TTS_CLIENT_REQUEST_TIMEOUT

async def handle_consumer_socket(client, sid, event, client_sockets, monitor_stats):
    """ a consumer socket is typically a request from a
    cgi handler who has been posted with a tts request"""
    loop = asyncio.get_event_loop()
    mysid = sid
    myevent = event
    endpoint_response = ''
    header = ''
    request = ''

    #print("TTS server socket activated")
    # wait for header
    try:
        request = (await loop.sock_recv(client, 255)).decode('utf8')
    except:
        endpoint_response = "Error trying to get header from cgi, Bailing!"

    if len(request) == 0:
        endpoint_response = "Error, Can't receive cgi header. Bailing!"
        try:
            # try to tell cgi i am aborting
            await loop.sock_sendall(client, b'nak')
        except:
            endpoint_response = "Error trying to send nak to cgi because of no header"

    if endpoint_response == '':
        header = request.split('&')
        #print("tts_server_socket_ Rcvd HDR: %s" % (header,))

        if not header[0].startswith('model'):
            endpoint_response = "Invalid Header. expected 'model', got %s" % (header[0],)
            try:
                await loop.sock_sendall(client, b'nak')
            except:
                endpoint_response = "Error trying to send nak to cgi, because bad header"

    if endpoint_response == '':
        language = 'en'
        speaker_index = 'p236'
        model_name = header[0].split('=')[1]
        text_input = header[1].split('=')[1] 

        if len( header ) > 2:
            language = header[2].split('=')[1] 

        if len( header ) > 3:
            speaker_index = header[3].split('=')[1] 

        #print("tts_server_socket-model:%s, lang:%s, idx:%s, text:%s:" % (model_name, language, speaker_index, text_input))

        # give request to client socket
        client_sid = await find_next_available_client(client_sockets)
        if client_sid == 0:
            endpoint_response = "no available clients"
            try:
                await loop.sock_sendall(client, b'nak')
            except:
                endpoint_response = "Error trying to send nak to cgi"

        else:
            update_vals = {
                    'wav_data_size':'',
                    'request_data':text_input,
                    'model_name':model_name,
                    'language':language,
                    'index':speaker_index,
                    'auth_key':PRODUCER_FARM_AUTH_KEY
                    }
            await update_client_sockets(mysid, update_vals, client_sockets)

            update_vals = {
                    'status':'busy',
                    'request_sid':mysid,
                    'request_data':text_input,
                    'model_name':model_name,
                    'language':language,
                    'index':speaker_index,
                    }
            await update_client_sockets(client_sid, update_vals, client_sockets)
            await set_socket_event(client_sid, client_sockets)

            if not await event_wait(myevent, TTS_CLIENT_REQUEST_TIMEOUT):
                endpoint_response = "timed out waiting on client"

            else:
                # send fixed len wav data size 
                fixed_size_len = client_sockets[mysid]['wav_data_size'] 

                try:
                    await loop.sock_sendall(client, fixed_size_len.encode('utf-8'))
                except:
                    endpoint_response = "srvr_socket: broken socket sending wav data length to cgi"

                # send wav data
                try:
                    await loop.sock_sendall(client, client_sockets[mysid]['response_data'])
                    monitor_stats['successful_requests'] += 1
                    endpoint_response = client_sockets[mysid]['response']
                except:
                    endpoint_response = "srvr_socket: broken socket sending wav data to cgi"

    print("Wav data sent, Server Socket %s exiting, response=%s" % (mysid,endpoint_response))
    # give cgi a change to receive data. we are going away after this anyway
    await asyncio.sleep(1)

    await delete_socket_key(mysid, 'event', client_sockets)
    await delete_socket_key(mysid, 'response_data', client_sockets)
    await write_transaction('xact', client_sockets[mysid])

    try:
        client.close()
    except:
        pass

    #print("tts server socket ended, should be no memory leak here! sid=%s, response=%s" % (mysid,endpoint_response))

