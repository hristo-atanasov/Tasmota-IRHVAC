# Tasmota-IRHVAC
Home Assistant platform for controlling IR Air Conditioners via Tasmota IRHVAC command and compatible harware

This is my new platform, that can control hunderds of Air Conditioners, out of the box, via Tasmota IR transceivers. It is based on the latest “tasmota-ircustom.bin” v8.1. I’m looking for testers, because I wrote it for me and I’m using 0.94.1 version of Hass.io 1 and I want to make it work for newest versions, so everyone can use it. Currently it works fine on my version and I tried to make it universal so it can work on all versions, but I’m not sure.
The schematics to make such Tasmota IR Transceiver is shown on the picture. I recommend not to put this 100ohm resistor that is marked with light blue X. If you’re planning to power the board with microUSB and you have pin named VU connect the IRLED to it instead of VIN.

After configuration open Tasmota console, point your AC remote to the IR receiver and press the button for turning the AC on.

If everything in the above steps is made right, you should see a line like this (example with Fujitsu Air Conditioner):
{'IrReceived': {'Protocol': 'FUJITSU_AC', 'Bits': 128, 'Data': '0x0x1463001010FE09304013003008002025', 'Repeat': 0, 'IRHVAC': {'Vendor': 'FUJITSU_AC', 'Model': 1, 'Power': 'On', 'Mode': 'fan_only', 'Celsius': 'On', 'Temp': 20, 'FanSpeed': 'Auto', 'SwingV': 'Off', 'SwingH': 'Off', 'Quiet': 'Off', 'Turbo': 'Off', 'Econo': 'Off', 'Light': 'Off', 'Filter': 'Off', 'Clean': 'Off', 'Beep': 'Off', 'Sleep': -1}}}

If protocol is no ‘Unknown’ and you see the ‘IRHVAC’ key, containing information, you can be sure that it will work for you.

Next step is to download the files from this repo and place them in a folder named "tasmota_irhvac". Then place this folder in your "custom_components" folder.
Reastart Home Assistant!
After restart put the following config in your configuration.yaml file, but don’t save it yet, because you’ll need to replace all values with your AC values
