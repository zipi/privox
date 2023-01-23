import contextlib, asyncio, aiohttp
import json
from privox_config import PV_VALIDATE_USER_URL, PV_POST_TRANSACTION_URL

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
    async with aiohttp.ClientSession() as session:
        headers = {'Content-Type': 'application/json', 'X-WHICH': which}
        async with session.post(PV_POST_TRANSACTION_URL, headers=headers, json=data) as resp:
            try:
                response = await resp.json()
            except:
                #print("Warning! JSON exception in write transaction. this usually means an error from the cgi-bin/transaction endpoint")
                pass

            return response
    return response


async def validate_client_connection(endpoint_key):
    validate_url = PV_VALIDATE_USER_URL + endpoint_key
    async with aiohttp.ClientSession() as session:
        headers = {'Content-Type': 'text/html'}
        async with session.get(validate_url, headers=headers) as resp:
            response = await resp.text()

            if response:
                try:
                    response = int( response.strip() )
                except:
                    return -1

                if response > 0:
                    return response

    print("Creepy Internal Error 103")
    return -1

