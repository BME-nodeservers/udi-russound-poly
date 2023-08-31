"""
Class to take an array of bytes and parse it based on the RNET 
message syntax.
"""

import logging
from enum import Enum

LOGGER = logging.getLogger()

#  RNET_MSG_TYPE is really message ID
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
    UNKNOWN_DISPLAY = 39
    DISPLAY_ZONE_STATE = 40
    DISPLAY_ZONE_SOURCE = 41
    DISPLAY_ZONE_VOLUME = 42
    DISPLAY_ZONE_BASS = 43
    DISPLAY_ZONE_TREBLE = 44
    DISPLAY_ZONE_LOUDNESS = 45
    DISPLAY_ZONE_BALANCE = 46
    DISPLAY_ZONE_TURN_ON_VOLUME = 47
    DISPLAY_ZONE_BACKGROUND_COLOR = 48
    DISPLAY_ZONE_DO_NOT_DISTURB = 49
    DISPLAY_ZONE_PARTY_MODE = 50
    CONTROLLER_CONFIG = 51
    CONTROLLER_DATA = 52
    LOST_CONNECTION = 255

SOURCE_NAMES = [
        "Aux 1", "Aux 2", "Aux", "Blues", "Cable 1", "Cable 2", "Cable 3",
        "Cable", "CD Changer", "CD Changer 1", "CD Changer 2",
        "CD Changer 3", "CD Player", "CD Player 1", "CD Player 2",
        "CD Player 3", "Classical", "Computer", "Country", "Dance Music",
        "Digital Cable", "DSS Reciever", "DSS 1", "DSS 2", "DSS 3",
        "DVD Changer", "DVD Changer 1", "DVD Changer 2", "DVD Changer 3",
        "DVD Player", "DVD Player 1", "DVD Player 2", "DVD Player 3",
        "Front Door", "Internet Radio", "Jazz", "Laser Disk", 
        "Media Server", "Mini Disk", "Mood", "Morning Music", "MP3",
        "Oldies", "POP", "Rear Door", "Religious", "ReplayTV", "Rock",
        "Satellite", "Satellite 1", "Satellite 2", "Satellite 3",
        "Special", "Tape", "Tape 1", "Tape 2", "TIVO", "Tuner 1",
        "Tuner 2", "Tuner 3", "Tuner", "TV", "VCR", "VCR 1", "VCR 2",
        "Source 1", "Source 2", "Source 3", "Source 4", "Source 5",
        "Source 6", "Source 7", "Source 8", "Custom Name 1",
        "Custom Name 2", "Custom Name 3", "Custom Name 4", "Custom Name 5",
        "Custom Name 6", "Custom Name 7", "Custom Name 8", "Custom Name 9",
        "Custom Name 10", "Sat Radio", "((<XM>))", "XM Radio", "XM 1",
        "XM 2", "XM 3", "Media Srv 1", "Media Srv 2", "Media Srv 3",
        "Her Music", "His Music", "Kids Music"
        ]

ZONE_NAMES = [
        "unassigned", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10",
        "11", "12", "13", "14", "15", "16", "Living Room", "Kitchen", "Dinning Room",
        "Bedroom", "Master Bedroom", "Bedroom 1", "Bedroom 2", "Bedroom 3",
        "Bedroom 4", "Bedroom 5", "Family Room", "Den", "Basement", "Front Yard",
        "Back Yard", "Deck", "Bathroom", "Bathroom 1", "Bathroom 2", "Bathroom 3",
        "Bathroom 4", "Garden", "Pool Area", "Pool Room", "Studio", "Control Room",
        "Tennis Court", "Sauna", "Office", "Office 1", "Office 2", "Office 3",
        "Office 4", "Theater", "custom name 1", "custom name 2", "custom name 3",
        "custom name 4", "custom name 5", "custom name 6", "custom name 7",
        "custom name 8", "custom name 9", "custom name 10"
        ]

KEY_NAMES = [
        "Play", "Stop", "Pause", "Previous", "Next", "Plus", "Minus", 
        "Fav 1", "Fav 2", "Source", "Power", "Volume Up", "Volume Down"
        ]

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

        """
          0x00 = Data Message (set data)
          0x01 = Request Data (request parameter's value)
          0x02 = Handshake
          0x05 = Data Message (Event message to display)
          0x06 = Rendered Display Message

          Setting a parameter can be done two ways:
            1. A set data message sent directly to the parameter
            2. An event message sent to controller to set the value
        """
        self.message_type = message[7]
        if self.message_type == 0x00:
            self.parse_set_data(message)
        elif self.message_type == 0x01:
            self.parse_request_data(message)
        elif self.message_type == 0x02:
            self.message_id = RNET_MSG_TYPE.HANDSHAKE
        elif self.message_type == 0x05:
            self.parse_event(message)
        elif self.message_type == 0x06:
            self.parse_display(message)
        elif self.message_type == 0xff:
            self.message_id = RNET_MSG_TYPE.LOST_CONNECTION
        else:
            self.message_id = RNET_MSG_TYPE.UNKNOWN
        

    def TargetPath(self, message):
        """
          Paths define which object should be modified.  A path
          starts with depth followed by subdirectory numbers. For example
          3.1.2.8 means path has depth of 3.

          What do these "subdirectory numbers mean?
        """
        cnt = message[8]
        self.target_paths = message[9:9 + cnt]

        return (9 + cnt)

    def SourcePath(self, message, st):
        cnt = message[st]
        st += 1
        self.source_paths = message[st:st + cnt]

        return (st + cnt)

    def parse_event(self, message):
        p_idx = self.TargetPath(message)
        s_idx = self.SourcePath(message, p_idx)

        # typically, only the TargetPath is of interest
        if p_idx != 9: # i.e. target path len > 0
            self.message_id = self.decode_paths(self.target_paths)

        """
           event[0] is the event ID
           event[1] is the event timestamp
           event[2] is the event data
           event[3] is the event priority
           event[4] is the event raw

           What parts of the event do we want to expose via properties?
        (self.e_id, self.e_ts, self.e_data, self.e_priority, self.e_raw) = self.get_event(message, idx)
        """
        self.data = None
        event = self.get_event(message, s_idx)

        """
          FIXME:  Why are we setting self.data to most of the message
           [1:16] below?  Seems like we shouldn't need most of that info
           in self.data and should parse out just the relevant parts
        """
        if event[0] == 0xBF: # remote control ir button event
            self.messge_id = RNET_MSG_TYPE.IR_REMOTE
            self.data = event[2]
        elif event[0] == 0xDC: # zone on/of
            self.message_id = RNET_MSG_TYPE.ZONE_STATE
            # FIXME: We were using EventTS for state.  that seems wrong
            self.data = message[1:16]
            self.data = event[1] # ?????  what's in Event[2] then?
            LOGGER.error('Event: ZONE_STATE: data = {}, ts= {}'.format(event[2], event[1]))
        elif event[0] == 0xDD: # all zone on/of
            self.message_id = RNET_MSG_TYPE.ALL_ZONE_STATE
            self.data = message[1:16]
        elif event[0] == 0xC1: # set source
            self.message_id = RNET_MSG_TYPE.ZONE_SOURCE
            sefl.data = message[18] # selected source - 1
        elif event[0] == 0xC5: # set power light
            self.message_id = RNET_MSG_TYPE.KEYPAD_POWER_LIGHT
            self.data = event[2]
        elif event[0] == 0xC8: # update source selection
            self.message_id = RNET_MSG_TYPE.UPDATE_SOURCE_SELECTION
            self.data = bytearray(2)
            self.data[0] = event[2] & 0xff
            self.data[1] = (event[2] >> 8) & 0xff
        elif event[0] == 0xCE: # set volume
            self.message_id = RNET_MSG_TYPE.ZONE_VOLUME
            # set e_id, e_zone, e_data?
            self.data = message[1:16]
            #self.e_data = self.data[0]
        elif event[0] == 0x64:
            self.message_id = RNET_MSG_TYPE.KEYPAD_SETUP
        elif event[0] == 0x65:
            self.message_id = RNET_MSG_TYPE.UNKNOWN_EVENT
            LOGGER.error('UNKNOWN event ID = {} timestamp = {} data= {}'.format(event[0], event[1], event[2]))
            self.data = event[2]
        elif event[0] == 0x67:
            self.message_id = RNET_MSG_TYPE.KEYPAD_PREVIOUS
        elif event[0] == 0x68:
            self.message_id = RNET_MSG_TYPE.KEYPAD_NEXT
        elif event[0] == 0x69:
            self.message_id = RNET_MSG_TYPE.KEYPAD_PLUS
        elif event[0] == 0x6A:
            self.message_id = RNET_MSG_TYPE.KEYPAD_MINUS
        elif event[0] == 0x6b:
            self.message_id = RNET_MSG_TYPE.KEYPAD_SOURCE
        elif event[0] == 0x6c:
            self.message_id = RNET_MSG_TYPE.KEYPAD_POWER
            self.data = message[1:16]
        elif event[0] == 0x6d:
            self.message_id = RNET_MSG_TYPE.KEYPAD_STOP
        elif event[0] == 0x6e:
            self.message_id = RNET_MSG_TYPE.KEYPAD_PAUSE
        elif event[0] == 0x6f:
            self.message_id = RNET_MSG_TYPE.KEYPAD_FAV1
        elif event[0] == 0x70:
            self.message_id = RNET_MSG_TYPE.KEYPAD_FAV2
        elif event[0] == 0x73:
            self.message_id = RNET_MSG_TYPE.KEYPAD_PLAY
        elif event[0] == 0x7f:
            self.message_id = RNET_MSG_TYPE.KEYPAD_VOL_UP
        elif event[0] == 0x80:
            self.message_id = RNET_MSG_TYPE.KEYPAD_VOL_DOWN
        elif event[0] == 0x97:
            self.message_id = RNET_MSG_TYPE.KEYPAD_VOL_UP
        elif event[0] == 0x98:
            self.message_id = RNET_MSG_TYPE.KEYPAD_VOL_DOWN
        else:
            self.message_id = RNET_MSG_TYPE.UNKNOWN_EVENT
            LOGGER.error('UNKNOWN event ID = {} timestamp = {} data= {}'.format(event[0], event[1], event[2]))


    def parse_set_data(self, message):
        p_idx = self.TargetPath(message)
        s_idx = self.SourcePath(message, p_idx)

        # typically, only the TargetPath is of interest
        if p_idx != 9: # i.e. target path len > 0
            self.message_id = self.decode_paths(self.target_paths)
        else:
            self.message_id = self.decode_paths(self.source_paths)

        """
          FIXME: Again, why is self.data being set to the
          entire message (1:22) below.  Seems like we really need to
          parse out the important bits here.

          A set data message should be sent by the controller in response
          to a request data message. However, the format of this info
          is not really documented May need to experiment by sending
          request data message and decode what is sent back
        """
        if self.message_id == RNET_MSG_TYPE.ALL_ZONE_INFO:
            self.data = message[20:31]
        elif self.message_id == RNET_MSG_TYPE.ZONE_STATE:
            #LOGGER.error('SetData: zone state: {}'.format(message))
            self.data = message[1:20]
            self.data = message[11] 
        elif self.message_id == RNET_MSG_TYPE.ZONE_SOURCE:
            self.data = message[20]
        elif self.message_id == RNET_MSG_TYPE.ZONE_VOLUME:
            LOGGER.error('SetData: zone volume: {}'.format(message))
            self.data = message[1:21]
        elif self.message_id == RNET_MSG_TYPE.ZONE_BASS:
            self.data = message[20]
        elif self.message_id == RNET_MSG_TYPE.ZONE_TREBLE:
            self.data = message[20]
        elif self.message_id == RNET_MSG_TYPE.ZONE_LOUDNESS:
            self.data = message[20]
        elif self.message_id == RNET_MSG_TYPE.ZONE_BALANCE:
            self.data = message[20]
        elif self.message_id == RNET_MSG_TYPE.ZONE_TURN_ON_VOLUME:
            self.data = message[20]
        elif self.message_id == RNET_MSG_TYPE.ZONE_BACKGROUND_COLOR:
            self.data = message[20]
        elif self.message_id == RNET_MSG_TYPE.ZONE_DO_NOT_DISTURB:
            self.data = message[20]
        elif self.message_id == RNET_MSG_TYPE.ZONE_PARTY_MODE:
            self.data = message[20]
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
        elif self.message_id == RNET_MSG_TYPE.EVENT:
            LOGGER.error('Standard event')
            self.data = message[20]
        elif self.message_id == RNET_MSG_TYPE.CONTROLLER_CONFIG:
            (pkc_cnt, pkc_num, dlen, data) = self.decode_packet(message, s_idx)
            self.packet_count = pkc_cnt
            self.packet_number = pkc_num
            self.data = data
        else:
            # What is in the paths that decoded to something not
            # listed above?
            self.message_id = RNET_MSG_TYPE.UNKNOWN_SET
            self.data = message[20]

    def parse_request_data(self, message):
        self.message_id = RNET_MSG_TYPE.RECEIEVE_DATA

    def parse_display(self, message):
        """
          Messages related to display and status

          These can be messages sent from controller to display requesting
          specific things be displayed.   In general, we probably 
          shouldn't be doing anything with these at this time.

          If we wanted to emulate a display keypad, then these
          would be used to update that.
        """
        (value1, value2, flash, rtype) = self.localDisplay(message, 8)

        # There are lots of render types, which do we want to handle?
        if rtype == 5:  # source name from string table _sourceNames
            # value2 is source number
            self.message_id = RNET_MSG_TYPE.DISPLAY_ZONE_SOURCE
            self.data = value1
            try:
                LOGGER.error('Render: source[{}] = {}'.format(self.data, SOURCE_NAMES[value1]))
            except:
                LOGGER.error('Render: source name (see source table?) {}'.format(self.data))

        elif rtype == 9: # key name from keytable
            LOGGER.error('Keypad keypress: (see keyNames table) {}'.format(value1))
            self.message_id = RNET_MSG_TYPE.UNKNOWN_DISPLAY
        elif rtype == 16: # volume
            self.message_id = RNET_MSG_TYPE.DISPLAY_ZONE_VOLUME
            self.data = value1
        elif rtype == 17: # bass
            self.message_id = RNET_MSG_TYPE.DISPLAY_ZONE_BASS
            self.data = value1
        elif rtype == 18: # treble
            self.message_id = RNET_MSG_TYPE.DISPLAY_ZONE_TREBLE
            self.data = value1
        elif rtype == 19: # balance
            self.message_id = RNET_MSG_TYPE.DISPLAY_ZONE_BALANCE
            self.data = value1
        elif rtype == 24: # from string table _StringTable
            self.message_id = RNET_MSG_TYPE.DISPLAY_FEEDBACK
            self.data = value1 + (value2 << 8)
            LOGGER.error('Render: string table id = {}'.format(self.data))
        else:
            LOGGER.error('Render: type = {}, data = {}'.format(rtype, value1))
            self.message_id = RNET_MSG_TYPE.UNKNOWN_DISPLAY


    def localDisplay(self, message, idx):
        value1 = 0
        value2 = 0
        flash = 0
        rtype = 0
        for i in range(0, 5):
            if message[idx] == 0xf1:
                idx += 1
                d = ~message[idx] & 0xff
            else:
                d = message[idx] & 0xff

            if i == 0:
                value1 = d  # value low byte
            elif i == 1:
                value2 = d  # value high byte (render typd dependent)
            elif i == 2:
                flash = d  # flash time low byte
            elif i == 3:
                flash = flash | (d << 8) # flash high byte
            elif i == 4:
                rtype = d  # render type

            idx += 1

        return (value1, value2, flash, rtype)

    """
      The path defines a specific object/parameter. When parsing
      set data messages, the target path should hold the parameter
      that we are trying to set.

      They look like:
      2/controller?/zone/<parameter>
      2/controller/zone/x/<parameter>

      2/0/1 - is a standard event

      1/0 - 
      1/1 - something to do with display
    """
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
            elif path[1] == 0x0 and len(path) == 5:
                if path[4] == 0x00:
                    return RNET_MSG_TYPE.ZONE_BASS
                elif path[4] == 0x01:
                    return RNET_MSG_TYPE.ZONE_TREBLE
                elif path[4] == 0x02:
                    return RNET_MSG_TYPE.ZONE_LOUDNESS
                elif path[4] == 0x03:
                    return RNET_MSG_TYPE.ZONE_BALANCE
                elif path[4] == 0x04:
                    return RNET_MSG_TYPE.ZONE_TURN_ON_VOLUME
                elif path[4] == 0x05:
                    return RNET_MSG_TYPE.ZONE_BACKGROUND_COLOR
                elif path[4] == 0x06:
                    return RNET_MSG_TYPE.ZONE_DO_NOT_DISTURB
                elif path[4] == 0x07:
                    return RNET_MSG_TYPE.ZONE_PARTY_MODE
            elif path[1] == 0x0 and len(path) == 2:
                # path[2] == 01 means ???
                return RNET_MSG_TYPE.EVENT
            elif path[1] == 0x4 and len(path) == 2:
                return RNET_MSG_TYPE.EVENT
        elif path[0] == 0x01:
            if path[1] == 0x01:
                return RNET_MSG_TYPE.DISPLAY_FEEDBACK
            elif path[1] == 0x00:
                return RNET_MSG_TYPE.EVENT
        elif path[0] == 0x03 and len(path) == 3:
            if path[1] == 0x00:
                if path[2] == 0x02:
                    return RNET_MSG_TYPE.CONTROLLER_CONFIG
                elif path[2] == 0x01:
                    # unknown
                    return RNET_MSG_TYPE.CONTROLLER_DATA
                elif path[2] == 0x00:
                    # unknown
                    return RNET_MSG_TYPE.CONTROLLER_DATA
            elif path[1] == 0x01:
                if path[2] == 0x00:
                    #unknown
                    return RNET_MSG_TYPE.CONTROLLER_DATA
                elif path[2] == 0x01:
                    # unknown
                    return RNET_MSG_TYPE.CONTROLLER_DATA
                elif path[2] == 0x02:
                    return RNET_MSG_TYPE.CONTROLLER_DATA
        elif path[0] == 0x04 and len(path) == 2:
            return RNET_MSG_TYPE.CONTROLLER_DATA

        return RNET_MSG_TYPE.UNKNOWN

    def decode_packet(self, message, idx):
        lo = int(message[idx])
        hi = int(message[idx+1])
        pknum = lo + (hi << 8)
        idx += 2

        lo = int(message[idx])
        hi = int(message[idx+1])
        pkcnt = lo + (hi << 8)
        idx += 2

        lo = int(message[idx])
        hi = int(message[idx+1])
        l = lo + (hi << 8)
        idx += 2
        
        data = message[idx:idx+l]
        return (pkcnt, pknum, l, data)


    def get_event(self, message, idx):
        # Event starts at message[?] 
        #(e_id, timestamp, e_self.data, priority) = self.get_event(message)

        # event is 7 bytes long, but some bytes might be preceeded
        # by 0xf1 to indicate that they need to be inverted.

        event_id = 0
        event_ts = 0
        event_data = 0
        event_priority = 0
        event_raw = message[idx:idx+8]

        for i in range(0, 7):
            if message[idx] == 0xf1:
                idx += 1
                d = ~message[idx] & 0xff
            else:
                d = message[idx] & 0xff

            if i == 0:
                event_id = int(d)
            elif i == 1:
                event_id = event_id | (int(d) << 8)
            elif i == 2:
                event_ts = int(d)
            elif i == 3:
                event_ts = event_ts | (int(d) << 8)
            elif i == 4:
                event_data = int(d)
            elif i == 5:
                event_data = event_data | (int(d) << 8)
            elif i == 5:
                event_priority = int(d)

            idx += 1

        return (event_id, event_ts, event_data, event_priority, event_raw)


    """
      Class Properties:
        MessageType is an enum into the RNET_MSG_TYPE class
        MessageData is any data associated with the message
        MessageRaw is the raw byte array

        MessageIRButton is the button code for an IR message
           shouldn't this just be in MessageData?
        TargetZone is the zone being targeted by the message
        TargetController is the controller being targeted by the message
        TargetKeypad is the keypad that is being targeted by the message
        SourceZone is the zone that sent the messae
        MessageText return the text message from display feedback

        // Why do we need the paths, doesn't look like we do
        SourcePaths
        TargetPaths

        // Debug  --- fix this so that it returns debug strings for
        //            both 05 and 06 messages
        EventStr dump of the event info
    """


    def MessageType(self):
        return self.message_id

    def MessageData(self):
        return self.data

    def MessageRaw(self):
        return self.raw_data

    def MessageIRButton(self):
        return self.event_data

    def TargetZone(self):
        return self.target_zone_id

    def TargetController(self):
        return self.target_controller_id

    def SourceZone(self):
        return self.source_zone_id

    def TargetKeypad(self):
        return self.target_keypad_id

    def EventStr(self):
        event_string = 'event id = 0x%x' % self.e_id
        event_string += ' event ts = 0x%x' % self.e_ts
        event_string += ' event data = 0x%x' % self.e_data
        event_string += ' event priority = 0x%x' % self.e_priority
        return event_string

    def MessageText(self):
        # convert data to string and return
        if self.message_id == RNET_MSG_TYPE.DISPLAY_FEEDBACK:
            return self.data.decode("utf-8")
        return ""

    def SourcePaths(self):
        return self.source_paths

    def TargetPaths(self):
        return self.target_paths

    def PacketCount(self):
        return self.packet_count

    def PacketNumber(self):
        return self.packet_number

    




