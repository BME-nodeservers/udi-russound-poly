#
# Russound support functions.
#
#  Open a connection to the Russound device
#  Wait for messages from the Russound device

import logging
import time
import socket
import threading
import rnet_message
#from rnet_message import RNET_MSG_TYPE

_LOGGER = logging.getLogger(__name__)
russound_connected = False

## Connect to the Russound via UDP broadcasts
def russound_connect_udp(port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # share it
    try:
        sock.bind(('0.0.0.0', int(port)))
        logging.warning('Successfully connected to Russound via rnet.')
        russound_connected = True
    except socket.error as msg:
        _LOGGER.error('Error trying to connect to russound controller.')
        _LOGGER.error(msg)
        sock = None

    return sock


## Connect to the Russound via IP address (serial/IP adaptor)
def russound_connect_tcp(ip, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((ip, int(port)))
        _LOGGER.warning('Successfully connected to Russound via rnet.')
        russound_connected = True
    except socket.error as msg:
        _LOGGER.error('Error trying to connect to russound controller.')
        _LOGGER.error(msg)
        sock = None
        
    return sock


# Main loop waits for messages from Russound and then processes them
def russound_loop_tcp(sock, processCommand):
    old_data = None
    while russound_connected:
        try:
            data = sock.recv(4096)
            #logging.warning('len= %s data= %s', len(data), '[{}]'.format(', '.join(hex(x) for x in data)))
            # Need to break this up into multiple messages?

            if old_data is not None:
                data = old_data + data
                old_data = None
            
            end = data.find(0xf7) + 1
            msg = rnet_message.RNetMessage(data[0:end])
            processCommand(msg)

            data = data[end:]
            if len(data) > 2:
                end = data.find(0xf7) + 1
                if end > 0:
                    msg = rnet_message.RNetMessage(data[0:end])
                    processCommand(msg)
                else:
                    _LOGGER.warning('incomplete data')
                    old_data = data

        except BlockingIOError:
            _LOGGER.info('waiting on data')
            pass
        except ConnectionResetError as msg:
            _LOGGER.error('Connection error: ' + msg)
            russound_connected = False


# Main loop waits for messages from Russound and then processes them
def russound_loop_udp(sock, processCommand):
    old_data = None
    while russound_connected:
        try:
            udp = sock.recvfrom(4096)
            _LOGGER.warning(udp)
            data = udp[0]

            if old_data is not None:
                data = old_data + data
                old_data = None
            
            end = data.find(0xf7) + 1
            msg = rnet_message.RNetMessage(data[0:end])
            processCommand(msg)

            data = data[end:]

            if len(data) > 2:
                end = data.find(0xf7) + 1
                if end > 0:
                    msg = rnet_message.RNetMessage(data[0:end])
                    processCommand(msg)
                else:
                    _LOGGER.warning('incomplete data')
                    old_data = data

        except BlockingIOError:
            _LOGGER.info('waiting on data')
            pass
        except ConnectionResetError as msg:
            _LOGGER.error('Connection error: ' + msg)
            russound_connected = False

