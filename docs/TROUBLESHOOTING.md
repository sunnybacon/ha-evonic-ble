# Troubleshooting

| Symptom | Check |
| --- | --- |
| No local adapter/device at setup | Mains power, local Linux adapter enabled and fire visible to its scanner. A proxy is insufficient. |
| Monitor unavailable | HCI monitor access is needed inside HA Core; generic BLE support does not establish permission. |
| Device unavailable | Check mains/range and close native apps fully on every household phone; disconnect touchscreen. Allow polling to recover. |
| App was only opened | Saved-fire auto-connect can occupy the fire before a Connect tap. |
| Brightness/target/Low–High rejected while Off | Expected. Turn on explicitly first; these requests do not turn the fire on. |
| Target/Low–High missing | Target and Low/High are standard controls since alpha.16. Check the installed version and restart after updating; no opt-in is needed. |
| Heater setting rejected in unknown mode | Inspect `controller_mode_raw`; 182 is unresolved. Native app manual mode can change schedules, so do not guess replacement commands. |
| Room temperature unknown, other controls valid | Missing/implausible room values are suppressed separately; 0–60 °C is a defensive assumption. |
| Slider jumps/responds slowly | Confirmation takes a few seconds; rapid requests coalesce. If jumping recurs, record values, times, final readback and service errors. A dashboard wrapper can recreate a control before confirmation. Supported slider delays or preserving an unchanged card may help; this is separate from the device integration. |
| HA started with mains absent | Setup retries/unavailable are expected, followed by status-only recovery after mains return. |
| Fire comes on after restoring mains | The appliance has restored its previous On state in a trial. HA does not restore power. |
| Fails after an HA upgrade | The client uses protected HA Bluetooth interfaces. Inspect compatibility errors before changing permissions or adapters. |

## Diagnostics and reporting

Download diagnostics from the integration entry in Devices & Services. This
uses cached data only, without connecting or operating the fire. It includes
settings/temperature, queue status, local adapter name and error type. Device
addresses, arbitrary entry fields and exception text are omitted. Review before
sharing; separately collected logs may identify devices.

Include HA/integration versions, host/adapter type, request, physical response
and approximate times. Note mains changes and competing apps/controllers.
Distinguish the appliance response from a card animation or HA-reported state.

Do not repeatedly resend heating requests when the result is unknown. Recovery
queries status without replaying writes. Use the appliance's own controls when
you need to establish physical state without a working BLE connection.
