#Tasmota IRHVAC for HA v0.108+
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

***tasmota_irhvac.filters***
with payload of:
```javacript
{filters: "on", entity_id: clima.your_clima_entity_id}
```
where *filters:* can be "on" or "off" and *entity_id:* can be your climate entity_id, like, for example, *climate.kitchen_ac*

***tasmota_irhvac.clean***
with payload of:
```javacript
{clean: "on", entity_id: clima.your_clima_entity_id}
```
where *clean:* can be "on" or "off" and *entity_id:* can be your climate entity_id, like, for example, *climate.kitchen_ac*

***tasmota_irhvac.beep***
with payload of:
```javacript
{beep: "on", entity_id: clima.your_clima_entity_id}
```
where *beep:* can be "on" or "off" and *entity_id:* can be your climate entity_id, like, for example, *climate.kitchen_ac*

***tasmota_irhvac.sleep***
with payload of:
```javacript
{sleep: "-1", entity_id: clima.your_clima_entity_id}
```
where *sleep:* can be any string, that your AC supports, and *entity_id:* can be your climate entity_id, like, for example, *climate.kitchen_ac*
