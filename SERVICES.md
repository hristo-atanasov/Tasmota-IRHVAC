# Services in Tasmota IRHVAC for HA v0.108+ and newer
Supprort for setting econo, turbo, quiet, light, filters, clean, beep and sleep via newly added services

In Tasmota IRHVAC for HA v0.108+ I've added 8 more services for controlling Air Conditioner's functions like these mentioned above. By adding this functionality, this doesnt mean, that your AC support it. Nor that Tasmota IRHVAC library supports it. You are using this functionality on your own will and risk.
Newly added services are:

***tasmota_irhvac.set_econo***
with payload of:
```javacript
{econo: "on", entity_id: clima.your_clima_entity_id}
```
where *econo* can be "on" or "off" and entity_id can be your climate entity_id, like, for example, *climate.kitchen_ac*

***tasmota_irhvac.set_turbo***
with payload of:
```javacript
{turbo: "on", entity_id: clima.your_clima_entity_id}
```
where *turbo* can be "on" or "off" and entity_id can be your climate entity_id, like, for example, *climate.kitchen_ac*
***tasmota_irhvac.set_quiet***
with payload of:
```javacript
{quiet: "on", entity_id: clima.your_clima_entity_id}
```
where *quiet* can be "on" or "off" and entity_id can be your climate entity_id, like, for example, *climate.kitchen_ac*

***tasmota_irhvac.set_light***
with payload of:
```javacript
{light: "on", entity_id: clima.your_clima_entity_id}
```
where *light:* can be "on" or "off" and *entity_id:* can be your climate entity_id, like, for example, *climate.kitchen_ac*

***tasmota_irhvac.set_filters***
with payload of:
```javacript
{filters: "on", entity_id: clima.your_clima_entity_id}
```
where *filters:* can be "on" or "off" and *entity_id:* can be your climate entity_id, like, for example, *climate.kitchen_ac*
* Note that it is **filters** instead of **filter**, because "filter" is reserved word and we cannot use it.*

***tasmota_irhvac.set_clean***
with payload of:
```javacript
{clean: "on", entity_id: clima.your_clima_entity_id}
```
where *clean:* can be "on" or "off" and *entity_id:* can be your climate entity_id, like, for example, *climate.kitchen_ac*

***tasmota_irhvac.set_beep***
with payload of:
```javacript
{beep: "on", entity_id: clima.your_clima_entity_id}
```
where *beep:* can be "on" or "off" and *entity_id:* can be your climate entity_id, like, for example, *climate.kitchen_ac*

***tasmota_irhvac.set_sleep***
with payload of:
```javacript
{sleep: "-1", entity_id: clima.your_clima_entity_id}
```
where *sleep:* can be any string, that your AC supports, and *entity_id:* can be your climate entity_id, like, for example, *climate.kitchen_ac*

# Example with Template Switch
Example from **configuration.yaml**. Please, use only these services, that are supported from your AC!

```yaml
switch:
  - platform: template
    switches:
      kitchen_climate_econo:
        friendly_name: "Econo"
        value_template: "{{ is_state_attr('climate.kitchen_ac', 'econo', 'on') }}"
        turn_on:
          service: tasmota_irhvac.set_econo
          data:
            entity_id: climate.kitchen_ac
            econo: 'on'
        turn_off:
          service: tasmota_irhvac.set_econo
          data:
            entity_id: climate.kitchen_ac
            econo: 'off'
  - platform: template
    switches:
      kitchen_climate_turbo:
        friendly_name: "Turbo"
        value_template: "{{ is_state_attr('climate.kitchen_ac', 'turbo', 'on') }}"
        turn_on:
          service: tasmota_irhvac.set_turbo
          data:
            entity_id: climate.kitchen_ac
            turbo: 'on'
        turn_off:
          service: tasmota_irhvac.set_turbo
          data:
            entity_id: climate.kitchen_ac
            turbo: 'off'
  - platform: template
    switches:
      kitchen_climate_quiet:
        friendly_name: "Quiet"
        value_template: "{{ is_state_attr('climate.kitchen_ac', 'quiet', 'on') }}"
        turn_on:
          service: tasmota_irhvac.set_quiet
          data:
            entity_id: climate.kitchen_ac
            quiet: 'on'
        turn_off:
          service: tasmota_irhvac.set_quiet
          data:
            entity_id: climate.kitchen_ac
            quiet: 'off'
  - platform: template
    switches:
      kitchen_climate_light:
        friendly_name: "Light"
        value_template: "{{ is_state_attr('climate.kitchen_ac', 'light', 'on') }}"
        turn_on:
          service: tasmota_irhvac.set_light
          data:
            entity_id: climate.kitchen_ac
            light: 'on'
        turn_off:
          service: tasmota_irhvac.set_light
          data:
            entity_id: climate.kitchen_ac
            light: 'off'
  - platform: template
    switches:
      kitchen_climate_filter:
        friendly_name: "Filter"
        value_template: "{{ is_state_attr('climate.kitchen_ac', 'filters', 'on') }}"
        turn_on:
          service: tasmota_irhvac.set_filters
          data:
            entity_id: climate.kitchen_ac
            filters: 'on'
        turn_off:
          service: tasmota_irhvac.set_filters
          data:
            entity_id: climate.kitchen_ac
            filters: 'off'
  - platform: template
    switches:
      kitchen_climate_clean:
        friendly_name: "Clean"
        value_template: "{{ is_state_attr('climate.kitchen_ac', 'clean', 'on') }}"
        turn_on:
          service: tasmota_irhvac.set_clean
          data:
            entity_id: climate.kitchen_ac
            clean: 'on'
        turn_off:
          service: tasmota_irhvac.set_clean
          data:
            entity_id: climate.kitchen_ac
            clean: 'off'
  - platform: template
    switches:
      kitchen_climate_beep:
        friendly_name: "Beep"
        value_template: "{{ is_state_attr('climate.kitchen_ac', 'beep', 'on') }}"
        turn_on:
          service: tasmota_irhvac.set_beep
          data:
            entity_id: climate.kitchen_ac
            beep: 'on'
        turn_off:
          service: tasmota_irhvac.set_beep
          data:
            entity_id: climate.kitchen_ac
            beep: 'off'
  - platform: template
    switches:
      kitchen_climate_sleep:
        friendly_name: "Sleep"
        value_template: "{{ is_state_attr('climate.kitchen_ac', 'sleep', '0') }}"
        turn_on:
          service: tasmota_irhvac.set_sleep
          data:
            entity_id: climate.kitchen_ac
            sleep: '1'
        turn_off:
          service: tasmota_irhvac.set_sleep
          data:
            entity_id: climate.kitchen_ac
            sleep: '0'
```
