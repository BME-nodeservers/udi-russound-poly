
# Russound RNET polyglot

This is the Russound node server for the [Universal Devices ISY](https://www.universal-devices.com/residential/ISY)
[Polyglot interface](http://www.universal-devices.com/developers/polyglot/docs/)
with Polyglot V3 running on a [Polisy](https://www.universal-devices.com/product/polisy/)

(c) 2020,2021,2022 Robert Paauwe

This node server is intended to support the legacy
[Russound CAV/CAS whole house audio controllers](http://www.russound.com/).

The legacy Russound controllers use a serial protocal called RNET. However, this
node server expects to access the controller via a ethernet-to-serial converter.
This has been tested using a QualTech QSE-100 which supports both TCP and UDP
ethernet-to-serial conversion. However, this should work with any ethernet-to-serial
device that has a raw/transparent mode.

This supports multiple controllers but does so by creating individual nodes for each
controller.

## Installation

1. Backup Your ISY in case of problems!
   * Really, do the backup, please
2. Go to the Polyglot Store in the UI and install.
3. From the Polyglot dashboard, select the Russound RNET node server and configure (see configuration options below).
4. Once configured, the Russound RNET node server should update the ISY with the proper nodes and begin filling in the node data.
5. Restart the Admin Console so that it can properly display the new node server nodes.

### Node Settings
The settings for this node are:

#### Short Poll
   * Not used
#### Long Poll
   * Not used

#### IP Address
   * The IP Address of the serial device server conected to the Russound controller. 
#### Port
   * The UDP/TCP port number assigned by the serial device server for the serial port.
#### Network Protocol
   * Either UDP or TCP.
#### Russound Protocol 
   * Either RNET or RIO (Note, RIO protocol is not yet supported)


## Requirements
1. Polyglot V3.
2. ISY firmware 5.3.x or later
3. A ethnet to serial device
4. A Russound legacy CAV or CAA whole house controller

# Release Notes

- 2.0.0 03/03/2021
   - Port to work on PG3
- 1.0.4 06/16/2020
   - Convert logging in connection functions to Polyglot logging.
- 1.0.3 06/16/2020
   - Process undocumented message to get keypad source selection.
- 1.0.2 06/16/2020
   - Fix TCP networking code.
   - Fix get source info response.
- 1.0.1 06/10/2020
   - Add parameter for network protocol selection (UDP/TCP)
- 1.0.0 06/10/2020
   - Initial release to public github
