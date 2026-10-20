# Optional CPU temperature monitoring and mining shutdown (Home Assistant)

This guide is intended for a future stable release. It is documentation only: the
XMRig add-on does **not** read host CPU temperature, expose a temperature entity,
or enforce a thermal cutoff. Temperature availability depends on the specific
machine, firmware, hardware sensors and Home Assistant integrations. Users must
supply and verify their own trustworthy temperature entity.

## Before using the example

1. Identify a real CPU temperature entity in **Developer Tools → States**. Confirm
   it reports degrees Celsius, updates during CPU load, and belongs to the CPU
   you want to protect. A similarly named sensor may measure a different part.
2. Identify the **Mining** switch entity created by the XMRig MQTT integration.
   Its exact entity ID can vary. The switch controls the miner process, not the
   add-on itself.
3. Choose a conservative cutoff for your **own** CPU, cooling and environment
   based on manufacturer and hardware guidance. Do not treat a sample value as
   a universal safe limit. Test the shutdown action with Mining OFF first.
4. Keep Home Assistant, MQTT and the add-on operational; an HA automation is
   **not** a substitute for independent hardware thermal protections. If HA,
   the broker, sensor or add-on is unavailable, a shutdown command may fail.

## Example automation

In the Home Assistant automation YAML editor, replace both example entity IDs
and the example threshold **before enabling**. The value `75` below is an
illustrative placeholder, **not** a recommended temperature limit.

```yaml
alias: XMRig - stop mining on high or missing CPU temperature
mode: single
triggers:
  - trigger: numeric_state
    entity_id: sensor.replace_with_your_cpu_temperature
    above: 75  # EXAMPLE ONLY: choose a hardware-specific threshold
  - trigger: state
    entity_id: sensor.replace_with_your_cpu_temperature
    to: unavailable
  - trigger: state
    entity_id: sensor.replace_with_your_cpu_temperature
    to: unknown
  - trigger: homeassistant
    event: start
conditions: []
actions:
  - choose:
      - conditions:
          - condition: template
            value_template: >-
              {{ not is_number(states('sensor.replace_with_your_cpu_temperature'))
                 or states('sensor.replace_with_your_cpu_temperature') | float > 75 }}
        sequence:
          - action: switch.turn_off
            target:
              entity_id: switch.replace_with_your_xmrig_mining_switch
```

**Behavior:** The automation requests Mining OFF when the sensor crosses above
its configured limit, becomes `unknown`/`unavailable`, or Home Assistant
starts and the sensor is already above the limit or invalid. The numeric-state
trigger detects threshold crossings; it does not continuously repeat commands
while the value remains high. This automation **never turns mining back ON**.
It does not guarantee an OFF command is delivered during a network, MQTT,
Home Assistant, or add-on failure. Validate the real action and monitor the
resulting switch state on your own installation.

If your sensor reports Fahrenheit or another unit, convert the limit and
comparison appropriately. Review sensor update cadence, stale readings and
possible missing-value behavior; a stale but numeric value may not trigger this
automation. Hardware safeguards remain necessary.

## Release policy

This is an **optional example**, not a bundled default automation or a new
add-on feature. Do not add host privileges, disable Protection Mode, invent
CPU temperature values, or imply universal thermal protection. Keep the stable
`main` and published `v2.0.0-beta.2` release unchanged unless separately
approved.
