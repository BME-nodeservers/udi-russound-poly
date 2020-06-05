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
    global russound_connected
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
    global russound_connected
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
    global russound_connected
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
#   messages start with 0xf0 and end with 0xf7
def russound_loop_udp(sock, processCommand):
    buf = bytearray(50)
    st = 0
    global russound_connected

    while russound_connected:
        try:
            udp = sock.recvfrom(4096)
            #_LOGGER.debug(udp)

            data = udp[0]
            for b in data:
                if st == 0:  # looking for start byte
                    if b == 0xf0:
                        buf[st] = b
                        st += 1
                else: # looking for end byte
                    if b == 0xf7:
                        buf[st] = b
                        st = 0
                        _LOGGER.warning('recv: ' + ' '.join('{:02x}'.format(x) for x in data))
                        msg = rnet_message.RNetMessage(buf)
                        processCommand(msg)
                    else:
                        buf[st] = b
                        st += 1
                        
        except BlockingIOError:
            _LOGGER.info('waiting on data')
            pass
        except ConnectionResetError as msg:
            _LOGGER.error('Connection error: ' + msg)
            russound_connected = False

def setIDs(data, start, control_id, zone_id, keypad_id):
    data[start]     = control_id
    data[start + 1] = zone_id
    data[start + 2] = keypad_id

def setPath(data, start, target, source= []):
    idx = start

    data[idx] = len(target)
    idx += 1
    for i in range(0, len(target)):
        data[idx] = target[i]
        idx += 1

    data[idx] = len(source)
    for i in range(0, len(source)):
        data[idx] = source[i]
        idx += 1


def checksum(data, length):
    cksum = 0

    for b in data:
        cksum += b

    cksum += length
    cksum = cksum & 0x007f

    return cksum

# Send a request to the controller to send various types of information
# about a specific zone.
#  0x0401 - current volume
#  0x0402 - selected source
#  0x0406 - current on/off state
#  0x0407 - all info
#  0x0500 - current bass level
#  0x0501 - current treble level
#  0x0502 - current loudness level
#  0x0503 - current balance
#  0x0404 - current turn on volume
#  0x0505 - current background color
#  0x0506 - current do not distrub
#  0x0507 - current party mode
def russound_get_info(sock, zone, info_type):
    _LOGGER.warning('Entered get_info()')
    path_len = (info_type & 0xff00) >> 8
    if path_len == 5:
        data = bytearray(18)
    else:
        data = bytearray(17)

    data[0] = 0xf0
    setIDs(data, 1, 0, 0, 0x7f)
    setIDs(data, 4, 0, zone, 0x70)
    data[7] = 0x01

    if path_len == 5:
        setPath(data, 8, [0x02, 0x00, zone, 0x00, (info_type & 0x00ff)])
        data[15] = 0x00
        data[16] = checksum(data, 16)
        data[17] = 0xf7
    else:
        setPath(data, 8, [0x02, 0x00, zone, (info_type & 0x00ff)])
        data[14] = 0x00
        data[15] = checksum(data, 15)
        data[16] = 0xf7

    _LOGGER.warning('sending: ' + ''.join('{:02x}'.format(x) for x in data))
    sock.sendto(data, ('192.168.92.38', 5000))

def russound_send_msg(sock, zone):
    data = bytearray(36)
    data[0] = 0xf0
    setIDs(data, 4, 0, 0, 0x70)
    data[7] = 0
    data[21] = ord('a')
    data[22] = ord(' ')
    data[23] = ord('m')
    data[24] = ord('e')
    data[25] = ord('s')
    data[26] = ord('s')
    data[27] = ord('a')
    data[28] = ord('g')
    data[29] = ord('e')
    setIDs(data, 1, 0x7f, 0, 0)
    setPath(data, 8, [0x01, 0x01], [])
    data[12] = 0x00
    data[13] = 0x00
    data[14] = 0x01
    data[15] = 0x00
    data[16] = 0x10
    data[17] = 0x00

    data[34] = checksum(data, 34)
    data[35] = 0xf7

    _LOGGER.warning('sending: ' + ' '.join('{:02x}'.format(x) for x in data))
    sock.sendto(data, ('192.168.92.38', 5000))



def russound_loop_udp_old(sock, processCommand):
    old_data = None
    global russound_connected
    while russound_connected:
        try:
            udp = sock.recvfrom(4096)
            #_LOGGER.debug(udp)

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
                    #_LOGGER.warning('incomplete data')
                    old_data = data

        except BlockingIOError:
            _LOGGER.info('waiting on data')
            pass
        except ConnectionResetError as msg:
            _LOGGER.error('Connection error: ' + msg)
            russound_connected = False

