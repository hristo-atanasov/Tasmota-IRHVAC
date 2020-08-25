# Tasmota-IRHVAC
Home Assistant platform for controlling IR Air Conditioners via Tasmota IRHVAC command and compatible harware

This is my new platform, that can **control hunderds of Air Conditioners**, out of the box, via **Tasmota IR transceivers**. It is based on the latest ***“tasmota-ircustom.bin” v8.1***. Currently it **works on Home Assistant 0.94 (may be some newer too) and from 0.103.x right to the latest 0.110.0 at this time**
The schematics to make such Tasmota IR Transceiver is shown on the picture. I recommend not to put this 100ohm resistor that is marked with light blue X. If you’re planning to power the board with microUSB and you have pin named *VU* connect the IRLED to it instead of *VIN*.

![image1](/images/schematics.jpeg)

Tasmota configuration looks like this:

![image2](/images/tasmota_config.jpeg)

After configuration open Tasmota console, point your AC remote to the IR receiver and press the button for turning the AC on.

If everything in the above steps is made right, you should see a line like this (example with Fujitsu Air Conditioner):

```javacript
{'IrReceived': {'Protocol': 'FUJITSU_AC', 'Bits': 128, 'Data': '0x0x1463001010FE09304013003008002025', 'Repeat': 0, 'IRHVAC': {'Vendor': 'FUJITSU_AC', 'Model': 1, 'Power': 'On', 'Mode': 'fan_only', 'Celsius': 'On', 'Temp': 20, 'FanSpeed': 'Auto', 'SwingV': 'Off', 'SwingH': 'Off', 'Quiet': 'Off', 'Turbo': 'Off', 'Econo': 'Off', 'Light': 'Off', 'Filter': 'Off', 'Clean': 'Off', 'Beep': 'Off', 'Sleep': -1}}}
```

If vendor is not *‘Unknown’* and you see the *‘IRHVAC’* key, containing information, you can be sure that it will work for you.

Next step is to download the files from this repo, get the folder named *"tasmota_irhvac"* and place it in your *"custom_components"* folder.
Reastart Home Assistant!
After restart add the config from *"configuration.yaml"* in your *"configuration.yaml"* file, but don’t save it yet, because you’ll need to replace all values with your speciffic AC values.
Using your remote and the IR Transceiver do the following steps to find your AC values that you have to fill in. You can find these values by looking in the console for them. They will appear in the ‘IrReceived’ JSON line (mentioned earlier).
Cycle trough all of your AC modes and write them in supported_modes. I have left some possible values commented.

Cycle trough your fan speeds and and write them down in supported_fan_speeds

If your AC doesnt support horizontal swinging remove *-"horizontal"* and *-"both"* from *supported_swing_list*

Enter your *hvac_model*

Change the *“min_temp”* and *“max_temp”* values with your AC min and max temp.
*target_temp* is the initial target temp. 26 is default value and if you don’t want to change it, you can just remove the line.
*away_temp* is the temp that will be set in away mode. If you don’t want to change it or you don’t need it you can remove that line.
You can also remove all lines that doesn’t need to be changed and are marked with “optional”.
Change the *name* with the desired name.
After you finish with the config, save it and restart Home Assistant. Once restarted you can add in LovelaceUI a new *thermostat card* and select the newly integrated AC.

This is a pic of 2 of my Tasmota IR transceivers, that I have mounted under my ACs so when using the ACs remote they have direct visual and update the state in Home Assistant (yes, it can do that too).

![image2](/images/multisensors.jpeg)

As an addition you can add these 2 scripts from *scripts.yaml* in your *scripts.yaml* and use them to send all kind of HEX IR codes and RAW IR codes, by just naming your multisensors using room name (lowercase) and the word “Multisensor”. Like *“kitchenMultisensor”* or *“livingroomMultisensor”*.

```yaml
ir_code:
  sequence:
  - data_template:
      payload: '{"Protocol":"{{ protocol }}","Bits": {{ bits }},"Data": 0x{{ data }}}'
      topic: 'cmnd/{{ room }}Multisensor/irsend'
    service: mqtt.publish
ir_raw:
  sequence:
  - data_template:
      payload: '0, {{ data }}'
      topic: 'cmnd/{{ room }}Multisensor/irsend'
    service: mqtt.publish
```

You can then use these scripts, for the exmple, in a *button card*. Create a new card, put inside it the content of the *card_configuration.yaml*, change *bits:*, *data:*, *protocol:* and *room:* with your desired values and test it. :)

```yaml
cards:
  - cards:
      - action: service
        color: white
        icon: 'mdi:power'
        name: Turn On Audio HEX
        service:
          action: ir_code
          data:
            bits: 12
            data: A80
            protocol: SONY
            room: kitchen
          domain: script
        style:
          - color: white
          - background: green
          - '--disabled-text-color': white
        type: 'custom:button-card'
      - action: service
        color: white
        icon: 'mdi:power'
        name: Turn Off Audio HEX
        service:
          action: ir_code
          data:
            bits: 12
            data: E85
            protocol: SONY
            room: kitchen
          domain: script
        style:
          - color: white
          - background: red
          - '--disabled-text-color': white
        type: 'custom:button-card'
      - action: service
        color: white
        icon: 'mdi:power'
        name: Test AC Raw
        service:
          action: ir_raw
          data:
            data: >-
              3290, 1602,  424, 390,  424, 390,  424, 1232,  398, 390,  424,
              1212,  420, 390,  424, 390,  424, 390,  424, 1232,  398, 1234, 
              398, 390,  424, 390,  426, 390,  424, 1232,  400, 1230,  398,
              392,  424, 390,  426, 390,  426, 390,  424, 390,  424, 390,  424,
              390,  424, 392,  424, 390,  424, 392,  424, 390,  424, 390,  424,
              390,  424, 1232,  398, 390,  424, 390,  426, 390,  424, 390,  424,
              392,  424, 390,  424, 392,  426, 1230,  400, 390,  424, 390,  426,
              390,  424, 390,  424, 1232,  400, 1232,  398, 1232,  398, 1232, 
              400, 1232,  398, 1232,  400, 1232,  400, 1232,  400, 390,  426,
              390,  424, 1206,  424, 390,  424, 390,  424, 392,  424, 390,  424,
              392,  424, 390,  426, 390,  424, 390,  424, 1230,  402, 1230, 
              402, 390,  424, 390,  424, 1230,  402, 390,  424, 390,  424, 390, 
              424, 390,  424, 390,  426, 390,  424, 1230,  402, 1228,  402,
              390,  424, 390,  424, 390,  426, 390,  424, 390,  426, 390,  424,
              390,  424, 390,  426, 390,  426, 390,  424, 390,  424, 390,  426,
              390,  424, 390,  424, 392,  426, 390,  424, 390,  424, 392,  424,
              390,  424, 390,  424, 390,  424, 390,  424, 390,  424, 390,  424,
              390,  424, 390,  426, 390,  426, 390,  424, 390,  424, 392,  424,
              390,  424, 390,  424, 390,  424, 390,  424, 392,  424, 390,  424,
              390,  424, 390,  426, 390,  424, 392,  424, 390,  424, 392,  424,
              390,  424, 390,  424, 1228,  404, 388,  424, 390,  424, 392,  424,
              1228,  404, 1228,  402, 1228,  402, 390,  426, 1228,  402, 390, 
              424, 390,  424
            room: bedroom
          domain: script
        style:
          - color: white
          - background: blue
          - '--disabled-text-color': white
        type: 'custom:button-card'
    type: vertical-stack
type: vertical-stack
```

More info about parts needed and discussion about it: [IN THIS HA COMMUNITY THREAD](https://community.home-assistant.io/t/tasmota-mqtt-irhvac-controler/162915/31)
