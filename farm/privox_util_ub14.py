import contextlib, asyncio
import urllib.request
import json
from privox_config import PV_VALIDATE_USER_URL, PV_POST_TRANSACTION_URL

### Warning! do not use this file unless you can not run aiohttp
# If you can't run aiohttp then overwrite privox_utils.py with this
# file. 

PRODUCER_FARM_AUTH_KEY = ''

client_sockets_lock = asyncio.Lock()
async def event_wait(evt, timeout):
    # suppress TimeoutError because we'll return False in case of timeout
    with contextlib.suppress(asyncio.TimeoutError):
        await asyncio.wait_for(evt.wait(), timeout)

    return evt.is_set()


async def find_next_available_client(client_sockets):
    async with client_sockets_lock:
        for cs in client_sockets:
            if client_sockets[cs]['status'] == 'idle' and client_sockets[cs]['socket_type'] == 'client':
                # found an idle client socket
                client_sockets[cs]['status'] == 'busy'
                return client_sockets[cs]['sid']

        return 0


async def add_socket_to_client_sockets(client_request, client_sockets):
    async with client_sockets_lock:
        client_sockets[ client_request['sid'] ] = client_request


async def remove_socket_from_client_sockets(socket_id, client_sockets):
    async with client_sockets_lock:
        if socket_id not in client_sockets:
            print("WTF DUDE where's my key? %s" % (socket_id,))
            return

        try:
            del client_sockets[socket_id]
        except Exception as e:
            print("WTF! error trying to remove %s from client_sockets:%s" % (socket_id, e))
            pass


async def update_client_sockets(socket_id, datum, client_sockets):
    async with client_sockets_lock:
        for key in datum:
            client_sockets[socket_id][key] = datum[key]


async def set_socket_event(socket_id, client_sockets):
    async with client_sockets_lock:
        client_sockets[socket_id]['event'].set()


async def clear_socket_event(socket_id, client_sockets):
    async with client_sockets_lock:
        client_sockets[socket_id]['event'].clear()


async def delete_socket_key(socket_id, key, client_sockets):
    async with client_sockets_lock:
        del client_sockets[socket_id][key]


async def write_transaction(which, data):
    response = {}
    url = 'http://localhost/cgi-bin/transaction.py'
    req = urllib.request.Request(url)
    req.add_header('Content-Type', 'application/json')
    req.add_header('X-WHICH', which)
    with urllib.request.urlopen(req, json.dumps(data).encode('utf-8')) as response:
        return response.read()
    return response


async def validate_client_connection(endpoint_key):
    url = 'http://localhost/cgi-bin/validate_key.py?key=' + endpoint_key
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as response:
        return response.read()
    return -1
