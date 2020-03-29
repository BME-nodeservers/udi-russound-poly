"""
Class to take an array of bytes and parse it based on the RNET 
message syntax.
"""

from enum import Enum

class RNET_MSG_TYPE(Enum):
    UNKNOWN = 0
    EVENT = 1
    ALL_ZONE_STATE = 2
    ALL_ZONE_INFO = 3
    ZONE_STATE = 4
    ZONE_SOURCE = 5
    ZONE_VOLUME = 6
    ZONE_BASS = 7
    ZONE_TREBLE = 8
    ZONE_LOUDNESS = 9
    ZONE_BALANCE = 10
    ZONE_TURN_ON_VOLUME = 11
    ZONE_BACKGROUND_COLOR = 12
    ZONE_DO_NOT_DISTURB = 13
    ZONE_PARTY_MODE = 14
    DISPLAY_FEEDBACK = 15
    SOURCE_BROADCAST = 16
    KEYPAD_SETUP = 17
    KEYPAD_PREVIOUS =18
    KEYPAD_NEXT = 19
    KEYPAD_PLUS = 20
    KEYPAD_MINUS = 21
    KEYPAD_SOURCE = 22
    KEYPAD_POWER = 23
    KEYPAD_STOP = 24
    KEYPAD_PAUSE = 25
    KEYPAD_FAV1 = 26
    KEYPAD_FAV2 = 27
    KEYPAD_PLAY = 28
    KEYPAD_VOL_UP = 29
    KEYPAD_VOL_DOWN = 30
    KEYPAD_POWER_LIGHT = 31
    IR_REMOTE = 32
    UPDATE_SOURCE_SELECTION = 33
    HANDSHAKE = 34
    RECEIEVE_DATA = 35
    UNDOCUMENTED = 36
    UNKNOWN_EVENT = 37
    UNKNOWN_SET = 38

class RNetMessage():

    def __init__(self, message):
        idx = 1
        self.raw_data = message

        self.message_id = RNET_MSG_TYPE.UNKNOWN
        self.target_controller_id = message[1]
        self.target_zone_id = message[2]
        self.target_keypad_id = message[3]
        self.source_controller_id = message[4]
        self.source_zone_id = message[5]
        self.source_keypad_id = message[6]
        self.message_type = message[7]

        if self.message_type == 0x02 or self.message_type == 0x06:
            # Don't parse these messages?
            self.message_id = RNET_MSG_TYPE.UNKNOWN
            idx = 8
        else:
            num_paths = message[8]
            self.target_paths = message[num_paths:8]

            idx = 9 + num_paths
            src_paths = message[idx]
            idx += 1
            self.source_paths = message[src_paths:idx]
            idx += int(src_paths)

            # the rest of the message format depends on the target
            # path information. There are two types of messages:
            #  1) events where the self.data will be the event self.data
            #  2) send self.data where the self.data is what is being sent

            if num_paths == 0:
                self.message_id = self.decode_paths(self.source_paths)
            else:
                self.message_id = self.decode_paths(self.target_paths)

        # for each message id type
        if self.message_type == 0x00:  # set data: sets a parameters value
            if self.message_id == RNET_MSG_TYPE.ALL_ZONE_INFO:
                self.data = message[11:20]
            elif self.message_id == RNET_MSG_TYPE.ZONE_STATE:
                self.data = message[1:20]
            elif self.message_id == RNET_MSG_TYPE.ZONE_SOURCE:
                self.data = message[1:21]
            elif self.message_id == RNET_MSG_TYPE.ZONE_VOLUME:
                # set e_id, e_zone, e_data?
                self.data = message[1:21]
                self.e_data = self.data[0]
            elif self.message_id == RNET_MSG_TYPE.ZONE_BASS:
                self.data = message[1:22]
            elif self.message_id == RNET_MSG_TYPE.ZONE_TREBLE:
                self.data = message[1:22]
            elif self.message_id == RNET_MSG_TYPE.ZONE_LOUDNESS:
                self.data = message[1:22]
            elif self.message_id == RNET_MSG_TYPE.ZONE_BALANCE:
                self.data = message[1:22]
            elif self.message_id == RNET_MSG_TYPE.ZONE_TURN_ON_VOLUME:
                self.data = message[1:22]
            elif self.message_id == RNET_MSG_TYPE.ZONE_BACKGROUND_COLOR:
                self.data = message[1:22]
            elif self.message_id == RNET_MSG_TYPE.ZONE_DO_NOT_DISTURB:
                self.data = message[1:22]
            elif self.message_id == RNET_MSG_TYPE.ZONE_PARTY_MODE:
                self.data = message[1:22]
            elif self.message_id == RNET_MSG_TYPE.DISPLAY_FEEDBACK:
                #if source_zone_id == 0x79:
                #    #if message[21] & 0x10 > 0:
                #    #    # source sent message
                #    #elif message[21] & 0x20 > 0:
                #    #    # source sent message
                #elif source_zone_id = 0x7d:
                #    # do nothing
                #else:
                #    # again do nothing
                self.message_id = RNET_MSG_TYPE.DISPLAY_FEEDBACK
            else:
                # What is in the paths that decoded to something not
                # listed above?
                self.message_id = RNET_MSG_TYPE.UNKNOWN_SET
        elif self.message_type == 0x01:  # request data request a parameter's value
            self.message_id = RNET_MSG_TYPE.RECEIEVE_DATA
        elif self.message_type == 0x02:  # handshake
            self.message_id = RNET_MSG_TYPE.HANDSHAKE
            self.data = message[1:idx]
        elif self.message_type == 0x05:  # event, 7 bytes long
            (self.e_id, self.e_ts, self.e_data, self.e_priority) = self.get_event(message, idx)
            if self.e_id == 0xBF: # remote control ir button event
                self.messge_id = RNET_MSG_TYPE.IR_REMOTE
            elif self.e_id == 0xDC: # zone on/of
                self.message_id = RNET_MSG_TYPE.ZONE_STATE
                self.data = message[1:16]
            elif self.e_id == 0xDD: # all zone on/of
                self.message_id = RNET_MSG_TYPE.ALL_ZONE_STATE
                self.data = message[1:16]
            elif self.e_id == 0xC1: # set source
                self.message_id = RNET_MSG_TYPE.ZONE_SOURCE
                self.data = message[1:18]
            elif self.e_id == 0xC5: # set source
                self.message_id = RNET_MSG_TYPE.KEYPAD_POWER_LIGHT
                self.data = self.e_data
            elif self.e_id == 0xC8: # update source selection
                self.message_id = RNET_MSG_TYPE.UPDATE_SOURCE_SELECTION
                self.data = bytearray(2)
                self.data[0] = self.e_data & 0xff
                self.data[1] = (self.e_data >> 8) & 0xff
            elif self.e_id == 0xCE: # set volume
                self.message_id = RNET_MSG_TYPE.ZONE_VOLUME
                # set e_id, e_zone, e_data?
                self.data = message[1:16]
                self.e_data = self.data[0]
            elif self.e_id == 0x64:
                self.message_id = RNET_MSG_TYPE.KEYPAD_SETUP
            elif self.e_id == 0x67:
                self.message_id = RNET_MSG_TYPE.KEYPAD_PREVIOUS
            elif self.e_id == 0x68:
                self.message_id = RNET_MSG_TYPE.KEYPAD_NEXT
            elif self.e_id == 0x69:
                self.message_id = RNET_MSG_TYPE.KEYPAD_PLUS
            elif self.e_id == 0x6A:
                self.message_id = RNET_MSG_TYPE.KEYPAD_MINUS
            elif self.e_id == 0x6b:
                self.message_id = RNET_MSG_TYPE.KEYPAD_SOURCE
            elif self.e_id == 0x6c:
                self.message_id = RNET_MSG_TYPE.KEYPAD_POWER
            elif self.e_id == 0x6d:
                self.message_id = RNET_MSG_TYPE.KEYPAD_STOP
            elif self.e_id == 0x6e:
                self.message_id = RNET_MSG_TYPE.KEYPAD_PAUSE
            elif self.e_id == 0x6f:
                self.message_id = RNET_MSG_TYPE.KEYPAD_FAV1
            elif self.e_id == 0x70:
                self.message_id = RNET_MSG_TYPE.KEYPAD_FAV2
            elif self.e_id == 0x73:
                self.message_id = RNET_MSG_TYPE.KEYPAD_PLAY
            elif self.e_id == 0x7f:
                self.message_id = RNET_MSG_TYPE.KEYPAD_VOL_UP
            elif self.e_id == 0x80:
                self.message_id = RNET_MSG_TYPE.KEYPAD_VOL_DOWN
            elif self.e_id == 0x97:
                self.message_id = RNET_MSG_TYPE.KEYPAD_VOL_UP
            elif self.e_id == 0x98:
                self.message_id = RNET_MSG_TYPE.KEYPAD_VOL_DOWN
            else:
                self.message_id = RNET_MSG_TYPE.UNKNOWN_EVENT
                self.data = self.e_id
        elif self.message_type == 0x06:  # event, 7 bytes long
            (self.e_data, self.e_ts, self.e_id, self.e_zone, unknown) = self.type_6(message, idx)
            self.data = message[idx:]
            if self.e_id == 0x90:  # zone Volume
                self.message_id = RNET_MSG_TYPE.ZONE_VOLUME
                self.target_zone_id = sefl.e_zone
            else:
                self.message_id = RNET_MSG_TYPE.UNDOCUMENTED


    def type_6(self, message, idx):
        undoc_1 = 0
        undoc_2 = 0
        undoc_3 = 0
        undoc_4 = 0
        undoc_5 = 0
        for i in range(0, 5):
            if message[idx] == 0xf1:
                idx += 1
                d = ~message[idx] & 0xff
            else:
                d = message[idx] & 0xff

            if i == 0:
                undoc_1 = d
            elif i == 1:
                undoc_2 = d
            elif i == 2:
                undoc_3 = d
            elif i == 3:
                undoc_4 = d
            elif i == 4:
                undoc_5 = d

            idx += 1

        return (undoc_1, undoc_2, undoc_3, undoc_4, undoc_5)

    def decode_paths(self, path):
        # path is a bytearray
        if path[0] == 0x00:
            if path[1] == 0x0 and len(path) == 2:
                return RNET_MSG_TYPE.EVENT
        elif path[0] == 0x02:
            if path[1] == 0x0 and len(path) == 4:
                # path[2] is the zone
                # path[3] is the type
                if path[3] == 0x01:
                    return RNET_MSG_TYPE.ZONE_VOLUME
                elif path[3] == 0x02:
                    return RNET_MSG_TYPE.ZONE_SOURCE
                elif path[3] == 0x04:
                    return RNET_MSG_TYPE.ALL_ZONE_INFO
                elif path[3] == 0x06:
                    return RNET_MSG_TYPE.ZONE_STATE
                elif path[3] == 0x07:
                    return RNET_MSG_TYPE.ALL_ZONE_INFO
            elif path[1] == 0x0 and path.length == 5:
                if path[4] == 0x00:
                    return RNET_MSG_TYPE.ZONE_BASS
                elif path[4] == 0x01:
                    return RNET_MSG_TYPE.ZONE_TREBLE
                elif path[4] == 0x02:
                    return RNET_MSG_TYPE.ZONE_LOUDNESS
                elif path[4] == 0x03:
                    return RNET_MSG_TYPE.ZONE_BALNCE
                elif path[4] == 0x04:
                    return RNET_MSG_TYPE.ZONE_TURN_ON_VOLUME
                elif path[4] == 0x05:
                    return RNET_MSG_TYPE.ZONE_BACKGROUND_COLOR
                elif path[4] == 0x06:
                    return RNET_MSG_TYPE.ZONE_DO_NOT_DISTURB
                elif path[4] == 0x07:
                    return RNET_MSG_TYPE.ZONE_PARTY_MODE
            elif path[1] == 0x0 and path.length == 2:
                return RNET_MSG_TYPE.EVENT
        elif path[0] == 0x01:
            if path[1] == 0x01:
                return RNET_MSG_TYPE.DISPLAY_FEEDBACK
            elif path[1] == 0x00:
                return RNET_MSG_TYPE.EVENT

        return RNET_MSG_TYPE.UNKNOWN

    def get_event(self, message, idx):
        # Event starts at message[?] 
        #(e_id, timestamp, e_self.data, priority) = self.get_event(message)

        # event is 7 bytes long, but some bytes might be preceeded
        # by 0xf1 to indicate that they need to be inverted.

        event_id = 0
        event_ts = 0
        event_data = 0
        event_priority = 0

        for i in range(0, 7):
            if message[idx] == 0xf1:
                idx += 1
                d = ~message[idx] & 0xff
            else:
                d = message[idx] & 0xff

            if i == 0:
                event_id = int(d)
            elif i == 1:
                event_id = event_id | (d << 8)
            elif i == 2:
                event_ts = int(d)
            elif i == 3:
                event_ts = event_ts | (d << 8)
            elif i == 4:
                event_data = int(d)
            elif i == 5:
                event_data = event_data | (d << 8)
            elif i == 5:
                event_priority = int(d)

            idx += 1

        return (event_id, event_ts, event_data, event_priority)

    def MessageType(self):
        return self.message_id

    def MessageData(self):
        return self.data

    def MessageIRButton(self):
        return self.event_data

    def TargetZone(self):
        return self.target_zone_id

    def TargetController(self):
        return self.target_controller_id

    def MessageX(self):
        return int(self.message_type)

    def TargetKeypad(self):
        return self.target_keypad_id

    def EventStr(self):
        event_string = 'event id = 0x%x' % self.e_id
        event_string += ' event ts = 0x%x' % self.e_ts
        event_string += ' event data = 0x%x' % self.e_data
        event_string += ' event priority = 0x%x' % self.e_priority
        return event_string

    def EventId(self):
        return self.e_id

    def EventData(self):
        return self.e_data

    def EventZone(self):
        return self.e_zone

    def MessageText(self):
        # convert data to string and return
        if self.message_id == RNET_MSG_TYPE.DISPLAY_FEEDBACK:
            return self.data.decode("utf-8")
        return ""

    def SourcePaths(self):
        return self.source_paths

    def TargetPaths(self):
        return self.target_paths





