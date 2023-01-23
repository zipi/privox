import datetime, asyncio, shutil, socket, time, uuid, glob, sys, os

from privox_utils import (
        event_wait, 
        add_socket_to_client_sockets, 
        remove_socket_from_client_sockets, 
        update_client_sockets,
        validate_client_connection
        )
from privox_config import (
        PV_AUTH_RESPONSE_SIZE,
        PV_DEFAULT_SOCKET_HOST,
        PV_DEFAULT_SOCKET_PORT_STT,
        PV_DEFAULT_SOCKET_PORT_TTS,
        PV_USER_KEY_NOT_FOUND
)

# per server so if you are running both stt and tts then double this
MAX_SERVER_SOCKETS = 256

# frequency in seconds between monitor stats dumps
MONITOR_DUMP_FREQUENCY = 60

def usage():
    print("""
        Usage:
             privox_socket_server service port
        Where:
             service is either tts or stt
             port is the port the service listens on
             if port is not included it defaults to
             1776 for stt and 1777 for tts.
                   """)
    sys.exit(-1)


async def monitor(monitor_stats):
    # print rps and srps every MONITOR_DUMP_FREQUENCY seconds
    while True:
        last_socket_id = monitor_stats['socket_id']
        last_successful_requests = monitor_stats['successful_requests']
        await asyncio.sleep(MONITOR_DUMP_FREQUENCY)
        now = datetime.datetime.now()
        print("[%s]SRPS:%s, RPS:%s" % ( 
                                   now.strftime("%Y-%m-%d %H:%M:%S"),
                                   (monitor_stats['successful_requests'] - last_successful_requests) / 10, 
                                   (monitor_stats['socket_id'] - last_socket_id) / 10 ))


async def socket_handler(client, sid, event, client_sockets, monitor_stats):
    """ send a 'who' packet and determine what kind of socket I am. 
    get back a 17 byte string where the first byte is the type and 
    the next 16 bytes are the auth key. dispatch accordingly."""
    loop = asyncio.get_event_loop()
    ret_code = ''

    #print("Send auth challenge packet")
    packet_header = 'who'
    try:
        await loop.sock_sendall(client, packet_header.encode('utf8'))
    except:
        ret_code = "Error trying to send 'who' packet, aborting socket!"

    #print("Await auth challenge response")
    if ret_code == '':
        try:
            response = (await loop.sock_recv(client, PV_AUTH_RESPONSE_SIZE)).decode('utf8')
        except:
            ret_code = "Error waiting for auth challenge response, aborting socket!"

    #print("Auth challenge response received ---> %s" % (response,))
    socket_type = 'x'
    socket_key = ''
    if ret_code == '' and response:
        socket_type = response[0]
        socket_key = response[1:]
    else:
        ret_code = "Error, who response sorely lacking, aborting socket"

    if ret_code == '':
        # dispatch based on connection type
        update_vals = {'key':socket_key}
        await update_client_sockets(sid, update_vals, client_sockets)

        if socket_type == 's':
            allowed_bytes = await validate_client_connection(socket_key)

            #print("PriVox:SocketServer- Request from consumer %s, who has %s bytes remaining" % (socket_key, allowed_bytes))
            #if allowed_bytes < 100:   # don't validate for now as this is probably the cgi server key
            if False:
                ret_code = "Invalid endpoint key. Probably out of bandwidth. Shutting down socket %s" % (sid,)
            else:
                try:
                    update_vals = {'socket_type':'server', 'status':'busy'}
                    await update_client_sockets(sid, update_vals, client_sockets)
                    await handle_consumer_socket(client, sid, event, client_sockets, monitor_stats)
                except:
                    ret_code = "Server socket died"

        elif socket_type == 'c':
            allowed_bytes = await validate_client_connection(socket_key)

            #print("PriVox:SocketServer- Request from producer who has %s bytes remaining" % (allowed_bytes,))
            if allowed_bytes == PV_USER_KEY_NOT_FOUND:
                ret_code = "Unknown producer attempting to connect: REJECTED!"

            else:
                try:
                    await handle_producer_socket(client, sid, event, client_sockets)
                except:
                    ret_code = "Client socket died"

        else:
            ret_code = "Invalid socket type (first byte from user not c or s) %s" % (socket_type, sid)

    svc = client_sockets[sid]['service']
    print("SID %s/%s removing myself from memory. result=%s" % (svc, sid, ret_code))
    await remove_socket_from_client_sockets(sid, client_sockets)


async def run_server(service, host, port):
    client_sockets = {}
    socket_id = 1

    monitor_stats = {
        'successful_requests': 0,
        'socket_id':socket_id
        }

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #server.bind(('localhost', 1776))
    server.bind((host, port))
    server.listen(MAX_SERVER_SOCKETS)
    server.setblocking(False)

    loop = asyncio.get_event_loop()
    loop.create_task(monitor(monitor_stats))

    while True:
        client, conn_info = await loop.sock_accept(server)

        ip_addr = conn_info[0]
        port = conn_info[1]
        event = asyncio.Event()
        session_id = str(uuid.uuid4()).upper()

        client_request = {'service':service,
                          'sid':socket_id, 
                          'ip':ip_addr, 
                          'port':port, 
                          'client_ip':'', 
                          'client_port':'', 
                          'socket_type':'client', 
                          'key':'', 
                          'client_key':'', 
                          'status':'idle', 
                          'request_sid':0, 
                          'model_name':'', 
                          'request':'', 
                          'request_data':'', 
                          'response':'', 
                          'response_data':'', 
                          'language':'', 
                          'index':'', 
                          'session':session_id, 
                          'event':event}

        await add_socket_to_client_sockets(client_request, client_sockets)
        loop.create_task(socket_handler(client, socket_id, event, client_sockets, monitor_stats))

        socket_id +=1 
        monitor_stats['socket_id'] = socket_id



if len(sys.argv) < 2:
    usage()

port = PV_DEFAULT_SOCKET_PORT_STT
which_service = sys.argv[1]
if which_service not in ['stt', 'tts']:
    print("Invalid service")
    sys.exit(-1)

# this what we call plugabble modules :-)
port = PV_DEFAULT_SOCKET_PORT_STT
if which_service == 'tts':
    port = PV_DEFAULT_SOCKET_PORT_TTS
    from tts_socket_producer import handle_producer_socket
    from tts_socket_consumer import handle_consumer_socket
else:
    from stt_socket_producer import handle_producer_socket
    from stt_socket_consumer import handle_consumer_socket

if len(sys.argv) > 2:
    port = sys.argv[2]
try:
    port = int( port )
except:
    print("Invalid Port!")
    sys.exit(-1)

print("%s listening on port %s" % (which_service, port))

asyncio.run(run_server(which_service, PV_DEFAULT_SOCKET_HOST, port))

