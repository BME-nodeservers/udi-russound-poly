
# russound-polyglot

This is the Russound Poly for the [Universal Devices ISY994i](https://www.universal-devices.com/residential/ISY) [Polyglot interface](http://www.universal-devices.com/developers/polyglot/docs/) with  [Polyglot V2](https://github.com/Einstein42/udi-polyglotv2)
(c) 2020 Robert Paauwe
MIT license.

This node server is intended to support the legacy [Russound CAV/CAS whole house audio controllers](http://www.russound.com/).

The legacy Russound controllers use a serial protocal called RNET. However, this node server expects to access the controller via a ethernet-to-serial converter. The only configuration tested and supported is a QualTech serial device server running in raw UDP mode.

This only supports a single controller with 6 zones and 6 sources.

## Installation

1. Backup Your ISY in case of problems!
   * Really, do the backup, please
2. Go to the Polyglot Store in the UI and install.
3. Add NodeServer in Polyglot Web
   * After the install completes, Polyglot will reboot your ISY, you can watch the status in the main polyglot log.
4. Once your ISY is back up open the Admin Console.
5. Configure the node server with your station ID.

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
#### Zone 1
   * The name for zone 1
#### Zone 2
   * The name for zone 2
#### Zone 3
   * The name for zone 3
#### Zone 4
   * The name for zone 4
#### Zone 5
   * The name for zone 5
#### Zone 6
   * The name for zone 6

#### Configuring source names
   * It's possible to configure the source names to match your configuration. When the node iserver is installed, it will make a copy of the default nls profile file. You can then manually edit this copy with the correct source names and then update the profile files on the ISY.

   * To change the source names look for the strings SOURCE-1 through SOURCE-6 and change
 the names.  Then, from the ISY admin console, find the Russound node and use the "Update Profile" button to push the changed file to the ISY. You'll need to restart the admin console to see the change.

   * You can also change the lables in the Russound node to display your specific source names.  Look for ST-ctl-GV1-NAME through ST-ctl-GV6-NAME in the nls file and update them with your source names.


## Requirements

1. Polyglot V2 itself should be run on Raspian Stretch.
  To check your version, ```cat /etc/os-release``` and the first line should look like
  ```PRETTY_NAME="Raspbian GNU/Linux 9 (stretch)"```. It is possible to upgrade from Jessie to
  Stretch, but I would recommend just re-imaging the SD card.  Some helpful links:
   * https://www.raspberrypi.org/blog/raspbian-stretch/
   * https://linuxconfig.org/raspbian-gnu-linux-upgrade-from-jessie-to-raspbian-stretch-9
2. This has only been tested with ISY 5.0.14 so it is not guaranteed to work with any other version.

# Upgrading

Open the Polyglot web page, go to nodeserver store and click "Update" for "Russound".

For Polyglot 2.0.35, hit "Cancel" in the update window so the profile will not be updated and ISY rebooted.  The install procedure will properly handle this for you.  This will change with 2.0.36, for that version you will always say "No" and let the install procedure handle it for you as well.

Then restart the Russound nodeserver by selecting it in the Polyglot dashboard and select Control -> Restart, then watch the log to make sure everything goes well.

The Roku nodeserver keeps track of the version number and when a profile rebuild is necessary.  The profile/version.txt will contain the Russound profile_version which is updated in server.json when the profile should be rebuilt.

# Release Notes

- 1.0.2 06/16/2020
   - Process undocumented message to get keypad source selection.
- 1.0.2 06/16/2020
   - Fix TCP networking code.
   - Fix get source info response.
- 1.0.1 06/10/2020
   - Add parameter for network protocol selection (UDP/TCP)
- 1.0.0 06/10/2020
   - Initial release to public github
