#
# Russound RNET support functions.
#
#  Open a connection to the Russound device
#  Wait for messages from the Russound device

from udi_interface import LOGGER
import time
import socket
import threading
import rnet_message

class Connection:
    LOGGER = None
    def __init__(self, ipaddress, port):
        self.ip = ipaddress
        self.port = int(port)
        self.connected = False
        self.sock = None
        self.controller = 1
        self.incoming = []

    def IncomingQueue(self, data):
        self.incoming.append(data)

    def isConnected(self):
        return self.connected

    def Connect(self):
        self.connected = False

    def Send(self, data):
        LOGGER.debug('Connection: send:: {}'.format(data))

    def getResponse(self):
        # CAV takes about 24 seconds, CAM takes about 44 seconds
        # to load the config.
        timeout = 600  # 60 seconds.
        while timeout > 0 and len(self.incoming) == 0:
            time.sleep(.1)
            timeout -= 1

        LOGGER.debug('getRsponse: queue non-zero or timeout {}'.format(timeout))
        if timeout == 0:
            return -1

        LOGGER.debug('getResponse:: queue = {}'.format(self.incoming))
        resp = self.incoming.pop()
        return resp

    def MessageLoop(self, processCommand):
        LOGGER.debug('Connection: Initialize message loop to {}'.format(processCommand))

    '''
    def get_info(self, zone, info_type):
    def set_param(self, zone, param, level):
    def send_event(self, controller, zone, value):
    def set_source(self, zone, source):
    def set_state(self, zone, state):
    def volume(self, zone, level):
    def request_config(self, controller):
    '''

class RNETConnection(Connection):
    LOGGER = None
    def __init__(self, ipaddress, port, udp):
        super().__init__(ipaddress, port)
        self.udp = udp
        self.protocol = 'RNET'

    ## Connect to the Russound via UDP broadcasts
    def __russound_connect_udp(self, port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # share it
        try:
            self.sock.bind(('0.0.0.0', int(port)))
            LOGGER.info('Successfully connected to Russound rnet via UDP.')
            self.connected = True
        except socket.error as msg:
            LOGGER.error('Error trying to connect to russound controller.')
            LOGGER.error(msg)
            self.sock = None

        return self.sock


    ## Connect to the Russound via IP address (serial/IP adaptor)
    def __russound_connect_tcp(self, ip, port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.sock.connect((ip, int(port)))
            LOGGER.info('Successfully connected to Russound rnet via TCP.')
            self.connected = True
        except socket.error as msg:
            LOGGER.error('Error trying to connect to russound controller.')
            LOGGER.error(msg)
            self.sock = None
        
        return self.sock

    def Connect(self):
        self.connected = False

        if self.udp:
            self.__russound_connect_udp(self.port)
        else:
            self.__russound_connect_tcp(self.ip, self.port)


    def Send(self, data):
        try:
            if self.udp:
                self.sock.sendto(data, (self.ip, self.port))
            else:
                self.sock.send(data)
        except Exception as e:
            LOGGER.error('Socket failure:  Unable to send data to device.')
            self.connected = False


    # Main loop waits for messages from Russound and then processes them
    def __russound_loop_tcp(self, processCommand):
        buf = bytearray(100)
        st = 0
        invert = False

        while self.connected:
            try:
                data = self.sock.recv(4096)
                #LOGGER.debug(data)

                for b in data:
                    if st == 0:  # looking for start byte
                        if b == 0xf0:
                            buf[st] = b
                            st += 1
                    else: # looking for end byte
                        if b == 0xf7:
                            buf[st] = b

                            # copy the bytes to an array sized for message
                            dbuf = bytearray(st+1)
                            dbuf = buf[0:st]
                            LOGGER.debug('recv: ' + ' '.join('{:02x}'.format(x) for x in dbuf))
                            msg = rnet_message.RNetMessage(dbuf)
                            processCommand(msg)

                            # if message is a set data, send an ack back
                            if dbuf[7] == 0:  
                                self.acknowledge(1)
                            st = 0
                            invert = False
                        elif b == 0xf1:  # invert byte
                            invert = True
                        else:
                            if invert:
                                invert = False
                                buf[st] = 0xff & ~b
                            else:
                                buf[st] = b
                            st += 1
                        
            except BlockingIOError:
                LOGGER.info('waiting on data')
                pass
            except ConnectionResetError as msg:
                LOGGER.error('Connection error: ' + str(msg))
                self.connected = False
                # Need to send a special message back that indicates 
                # the lost connection
                buf[0] = 0xff
                buf[6] = 0xff
                buf[7] = 0xff
                processCommand(rnet_message.RNetMessage(buf))
                self.socket.close()

    # Main loop waits for messages from Russound and then processes them
    #   messages start with 0xf0 and end with 0xf7
    def __russound_loop_udp(self, processCommand):
        buf = bytearray(50)
        st = 0

        while self.connected:
            try:
                udp = self.sock.recvfrom(4096)
                #LOGGER.debug(udp)

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
                            LOGGER.debug('recv: ' + ' '.join('{:02x}'.format(x) for x in data))
                            msg = rnet_message.RNetMessage(buf)
                            processCommand(msg)
                        else:
                            buf[st] = b
                            st += 1
                        
            except BlockingIOError:
                LOGGER.info('waiting on data')
                pass
            except ConnectionResetError as msg:
                LOGGER.error('Connection error: ' + msg)
                self.connected = False
                self.sock.close()

    def MessageLoop(self, processCommand):
        if self.udp:
            self.__russound_loop_udp(processCommand)
        else:
            self.__russound_loop_tcp(processCommand)

    def setIDs(self, data, start, control_id, zone_id, keypad_id):
        data[start]     = control_id
        data[start + 1] = zone_id
        data[start + 2] = keypad_id


    ## private functions???
    def setPath(self, data, start, target, source= []):
        idx = start

        data[idx] = len(target)
        idx += 1
        for i in range(0, len(target)):
            data[idx] = target[i]
            idx += 1

        data[idx] = len(source)
        idx += 1
        for i in range(0, len(source)):
            data[idx] = source[i]
            idx += 1

    def setData(self, data, start, raw):
        idx = start
        for i in range(0, len(raw)):
            data[idx] = raw[i]
            idx += 1

    def checksum(self, data, length):
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
    #
    # This is currently hard coding the controller as controller 1
    def get_info(self, ctrl, zone, info_type):
        path_len = (info_type & 0xff00) >> 8
        if path_len == 5:
            data = bytearray(18)
        else:
            data = bytearray(17)

        data[0] = 0xf0
        self.setIDs(data, 1, (ctrl - 1), 0, 0x7f)
        self.setIDs(data, 4, 0, zone, 0x70)
        data[7] = 0x01  # message type, request data

        # 02/controller/zone/parameter or 02/controller/zone/00/parameter
        if path_len == 5:
            self.setPath(data, 8, [0x02, int(ctrl - 1), zone, 0x00, (info_type & 0x00ff)])
            data[15] = 0x00
            data[16] = self.checksum(data, 16)
            data[17] = 0xf7
        else:
            self.setPath(data, 8, [0x02, int(ctrl - 1), zone, (info_type & 0x00ff)])
            data[14] = 0x00
            data[15] = self.checksum(data, 15)
            data[16] = 0xf7

        LOGGER.debug('sending get_info: ' + ''.join('{:02x}'.format(x) for x in data))
        self.Send(data)

    # params 0x00 = bass, 0x01 = treble, 0x02 = loudness, 0x03 = balance,
    #        0x04 = turn on vol, 0x05 = background color, 0x06 = do no disturb,
    #        0x07 = party mode
    # Use set data message type
    def set_param(self, controller, zone, param, level):
        data = bytearray(24)

        data[0] = 0xf0
        self.setIDs(data, 1, (controller - 1), 0, 0x7f)
        self.setIDs(data, 4, 0, 0, 0x70)
        self.setData(data, 7, [0x00, 0x05, 0x02, 0x00])
        data[11] = zone
        data[12] = 0x00
        data[13] = param
        self.setData(data, 14, [0x00, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00])
        data[21] = level
        data[22] = self.checksum(data, 22)
        data[23] = 0xf7

        LOGGER.debug('sending set_param: ' + ' '.join('{:02x}'.format(x) for x in data))
        self.Send(data)

    """
      We can proably simplify the function below by creating a send_event()
      function that takes controller, zone and data.
    """

    def send_event(self, controller, zone, value):
        data = bytearray(22)

        data[0] = 0xf0
        self.setIDs(data, 1, (controller - 1), 0, 0x7f)          # Tartet ID's
        self.setIDs(data, 4, 0, zone, 0x70)       # Source ID's
        data[7] = 0x05                            # event message type
        self.setData(data, 8, [0x02, 0x00, 0x00]) # Target path, standard event
        self.setData(data, 11, [0x00])            # Source path
        self.setData(data, 12, [0xf1, 0x3e])      # Event source
        self.setData(data, 14, [0x00, value])     # data value
        self.setData(data, 16, [0x00, zone])      # zone
        self.setData(data, 18, [0x00, 0x01])      # priority
        data[20] = self.checksum(data, 20)
        data[21] = 0xf7

    # Use event message type
    def set_source(self, controller, zone, source):
        data = bytearray(22)

        data[0] = 0xf0
        self.setIDs(data, 1, (controller - 1), 0, 0x7f)
        self.setIDs(data, 4, 0, zone, 0x70)
        self.setData(data, 7, [0x05, 0x02, 0x00, 0x00, 0x00])
        self.setData(data, 12, [0xf1, 0x3e, 0x00, 0x00, 0x00])
        data[17] = source
        data[18] = 0x00
        data[19] = 0x01
        data[20] = self.checksum(data, 20)
        data[21] = 0xf7

        LOGGER.debug('sending set_source: ' + ' '.join('{:02x}'.format(x) for x in data))
        self.Send(data)

    # Use event message type
    def set_state(self, controller, zone, state):
        data = bytearray(22)

        data[0] = 0xf0
        self.setIDs(data, 1, (controller - 1), 0, 0x7f)
        self.setIDs(data, 4, 0, 0x00, 0x70)
        self.setData(data, 7, [0x05, 0x02, 0x02, 0x00, 0x00])
        self.setData(data, 12, [0xf1, 0x23, 0x00])
        data[15] = state
        data[16] = 0x00
        data[17] = zone
        data[18] = 0x00
        data[19] = 0x01
        data[20] = self.checksum(data, 20)
        data[21] = 0xf7

        LOGGER.debug('sending set_state: ' + ' '.join('{:02x}'.format(x) for x in data))
        self.Send(data)

    # Use event message type
    def volume(self, controller, zone, level):
        data = bytearray(22)

        data[0] = 0xf0
        self.setIDs(data, 1, (controller - 1), 0, 0x7f)
        self.setIDs(data, 4, 0, zone, 0x70)
        data[7] = 0x05
        data[8] = 0x02
        data[9] = 0x02
        data[10] = 0x00
        data[11] = 0x00
        data[12] = 0xf1
        data[13] = 0x21
        data[14] = 0x00
        data[15] = level
        data[16] = 0x00
        data[17] = zone
        data[18] = 0x00
        data[19] = 0x01
        data[20] = self.checksum(data, 20)
        data[21] = 0xf7

        LOGGER.debug('sending volume: ' + ''.join('{:02x}'.format(x) for x in data))
        self.Send(data)

    # Request the configuration information from the controller
    def request_config(self, controller):
        data = bytearray(23)

        data[0] = 0xf0
        self.setIDs(data, 1, (controller - 1), 0, 0x7f)
        self.setIDs(data, 4, 0, 0, 0x7b)
        data[7] = 1 # request data
        self.setPath(data, 8, [0x03, int(controller - 1), 0x02], [0x03, 0x00, 0x02])
        self.setData(data, 16, [0x00, 0xf1, 0x00, 0xf1, 0x00])
        data[21] = self.checksum(data, 21)
        data[22] = 0xf7

        LOGGER.debug('sending request config: ' + ''.join('{:02x}'.format(x) for x in data))
        self.Send(data)

    # Send an ack back to the controller.
    def acknowledge(self, controller):
        data = bytearray(11)
        data[0] = 0xf0  #start of message
        self.setIDs(data, 1, (controller - 1), 0, 0x7f)
        self.setIDs(data, 4, 0, 0, 0x7b)
        data[7] = 2 # handshake
        data[8] = 2 # type of message we're acknowldgeding
        data[9] = self.checksum(data, 9)
        data[10] = 0xf7
        LOGGER.debug('sending request config: ' + ''.join('{:02x}'.format(x) for x in data))
        self.Send(data)

    # for debugging -- send a message to all keypads
    def send_msg(self, zone):
        data = bytearray(36)
        data[0] = 0xf0
        self.setIDs(data, 4, 0, 0, 0x70)
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
        self.setIDs(data, 1, 0x7f, 0, 0)
        self.setPath(data, 8, [0x01, 0x01], [])
        data[12] = 0x00
        data[13] = 0x00
        data[14] = 0x01
        data[15] = 0x00
        data[16] = 0x10
        data[17] = 0x00

        data[34] = self.checksum(data, 34)
        data[35] = 0xf7

        LOGGER.debug('sending message: ' + ' '.join('{:02x}'.format(x) for x in data))
        self.Send(data)


class RIOConnection(Connection):
    def __init__(self, ipaddress, port, udp):
        super().__init__(ipaddress, port)
        self.protocol = 'RIO'
        self.sock = None

    ## Connect to the Russound via IP address 
    def Connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.sock.connect((self.ip, int(self.port)))
            self.connected = True
        except socket.error as msg:
            LOGGER.error('Error trying to connect to russound controller.')
            LOGGER.error(msg)
            self.sock = None
        
        return self.sock

    def Send(self, data):
        try:
            if self.sock:
                LOGGER.debug('RIO: Sending {}'.format(data.encode()))
                data += '\r\n'
                self.sock.sendall(data.encode())
            else:
                LOGGER.debug('Error trying to connect to russound controller.')
                self.Connect()
        except socket.error:
            LOGGER.debug('Error trying to connect to russound controller.')
            self.Connect()

    # Main loop waits for messages from Russound and then processes them
    def MessageLoop(self, processCommand):
        while self.connected:
            try:
                data = self.sock.recv(4096)
                if data == b'':
                    LOGGER.debug('Connection Closed by Russound!')
                    self.connected = False
                    break

                riocmd = data.splitlines()
                for x in riocmd:
                    try:
                        processCommand(x.decode())
                    except Exception as e:
                        LOGGER.error('Data received error!  {}'.format(e))
            except BlockingIOError:
                LOGGER.info('waiting on data')
                pass
            except ConnectionResetError as msg:
                LOGGER.error('Connection error: ' + str(msg))
                self.connected = False

        self.sock.close()
        self.sock = None


    # Send a request to the controller to send various types of information
    # about a specific zone.
    #  name - Zone name
    #  volume - current volume
    #  currentSource - selected source
    #  status - current on/off state
    #  all - all info
    #  bass - current bass level
    #  treble- current treble level
    #  loudness - current loudness level
    #  balance - current balance
    #  turnOnVolume - current turn on volume
    #  doNotDisturb - current do not distrub
    #  partyMode - current party mode
    def get_info(self, ctrl, rioZone, info_type):
        data = ''
        if info_type == 'all':
            data = 'WATCH ' + rioZone + ' ON\r\n'
        else:
            data = 'GET ' + rioZone + '.' + info_type + '\r\n'
        if data != '':
            self.Send(data)
        else:
            LOGGER.debug('Unkown request!')
        

    # params 0 = bass, 1 = treble, 2 = loudness, 3 = balance,
    #        4 = turn on vol, 5 = mute, 6 = do no disturb, 7 = party mode
    def set_param(self, ctrl, rioZone, param, level):
        LOGGER.debug('sending Zone:' + rioZone + ' level:' + str(level) )
        if param == 0:
            data = 'SET ' + rioZone + '.bass="' + str(level-10) + '"\r\n'
        if param == 1:
            data = 'SET ' + rioZone + '.treble="' + str(level-10) + '"\r\n'
        if param == 2:
            if level == 0:
                data = 'SET ' + rioZone + '.loudness="OFF"\r\n'
            else:
                data = 'SET ' + rioZone + '.loudness="ON"\r\n'
        if param == 3:
            data = 'SET ' + rioZone + '.balance="' + str(level-10) + '"\r\n'
        if param == 4:
            data = 'SET ' + rioZone + '.turnOnVolume="' + str(level) + '"\r\n'
        if param == 5:
            if level == 0:
                data = 'EVENT ' + rioZone + '!ZoneMuteOff\r\n'
            else:
                data = 'EVENT ' + rioZone + '!ZoneMuteOn\r\n'
        if param == 6:
            if level == 0:
                data = 'EVENT ' + rioZone + '!DoNotDisturb OFF\r\n'
            else:
                data = 'EVENT ' + rioZone + '!doNotDisturb ON\r\n'
        if param == 7:
            if level == 0:
                data = 'EVENT ' + rioZone + '!PartyMode OFF\r\n'
            else:
                data = 'EVENT ' + rioZone + '!PartyMode ON\r\n'
        self.Send(data)

    def set_source(self, ctrl, rioZone, source):
        # Source index from zero.  I.E. source = 0 means source #1
        data = 'EVENT ' + rioZone + '!KeyRelease SelectSource ' + str(source+1) + '\r\n'
        self.Send(data)

    def set_state(self, ctrl, rioZone, state):
        if state == 1:
            data = 'EVENT ' + rioZone + '!ZoneOn\r\n'
            self.Send(data)
        else:
            data = 'EVENT ' + rioZone + '!ZoneOff\r\n'
            self.Send(data)

    def volume(self, ctrl, rioZone, level):
        data = 'EVENT ' + rioZone + '!KeyPress Volume ' + str(level) + '\r\n'
        self.Send(data)

    '''
    def getResponse(self):
        while len(self.incoming) == 0:
            time.sleep(.1)
        LOGGER.debug('getResponse:: queue = {}'.format(self.incoming))
        resp = self.incoming.pop()
        #LOGGER.debug('getResponse:: returning [{}]'.format(resp))
        return resp
    '''

    # helper function, call get_info for each zone, source
    def request_config(self, ctrl):
        # TODO: Can we loop through controllers here and skip any that don't return type?
        # Get device type
        max_sources = 0
        LOGGER.error('In request_config({})'.format(ctrl))
        for ctrl in range(1,6):
            data = 'GET C[{}].type'.format(ctrl)
            self.Send(data)
            ctrl_type = self.getResponse()
            if ctrl_type.startswith('E'): # error
                LOGGER.info('No controller found at address {}'.format(ctrl))
            else:
                LOGGER.error('Controller type = {}'.format(ctrl_type))
                if ctrl_type.startswith('MBX'):
                    max_zones = 1
                    max_sources += 1
                elif ctrl_type.startswith('X'):
                    # x-series
                    max_zones = 1
                    max_sources += 1
                elif ctrl_type.startswith('MCA-88'):
                    max_zones = 8
                    max_sources += 8
                elif ctrl_type.startswith('MCA-C5'):
                    max_zones = 8
                    max_sources += 8
                else:
                    max_zones = 6
                    max_sources += 6

                for z in range(1, max_zones+1):
                    rioZone = 'C[{}].Z[{}]'.format(ctrl, z)
                    self.get_info(1, rioZone, 'name')
                    zname = self.getResponse()
                    LOGGER.debug('GOT info for {} = {}'.format(rioZone, zname))

        # max source is either 6, 8, or 1 depending on device.
        for s in range(1, max_sources+1):
            rioZone = 'S[{}]'.format(s)
            self.get_info(1, rioZone, 'name')
            sname = self.getResponse()
            LOGGER.debug('GOT info for {} = {}'.format(rioZone, sname))



    
