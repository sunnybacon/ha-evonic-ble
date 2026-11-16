# Troubleshooting

| Symptom | Check |
| --- | --- |
| No local adapter/device at setup | Mains power, local Linux adapter enabled and fire visible to its scanner. A proxy is insufficient. |
| Monitor unavailable | HCI monitor access is needed inside HA Core; generic BLE support does not establish permission. |
| Device unavailable | Check mains/range and close native apps fully on every household phone; disconnect touchscreen. Allow polling to recover. |
| App was only opened | Saved-fire auto-connect can occupy the fire before a Connect tap. |
| Brightness/target/Low–High rejected while Off | Expected. Turn on explicitly first; these requests do not turn the fire on. |
| Target/Low–High missing | These controls are included by default. Check the installed version and restart after updating. |
| Heater setting rejected in unknown mode | Inspect `controller_mode_raw`; 182 is unresolved. Native app manual mode can change schedules, so do not guess replacement commands. |
| Room temperature unknown, other controls valid | Missing or implausible readings are suppressed. Since beta.1 this includes abrupt repeated zeros. See the [temperature guard](BEHAVIOUR.md#room-temperature). |
| Slider jumps/responds slowly | Confirmation takes a few seconds; rapid changes keep the latest waiting value. If jumping continues, record the requested/final values and times, and which dashboard card you use. |
| HA started with mains absent | Setup retries/unavailable are expected, followed by status-only recovery after mains return. |
| Fire comes on after restoring mains | The appliance has restored its previous On state in a trial. HA does not restore power. |
| Fails after an HA upgrade | The client uses protected HA Bluetooth interfaces. Inspect compatibility errors before changing permissions or adapters. |

## Diagnostics and reporting

Download diagnostics from the integration entry in Devices & Services. It uses
cached settings, temperature, queue status, adapter name and error type without
operating the fire. The integration's diagnostic data omits the device address
and exception text. Check the whole download and any logs before sharing them.

For a report, include versions, host/adapter type, what you requested, the fire's
physical response and approximate times. Note mains changes and other controllers.

Do not repeatedly resend heating requests when the result is unknown. Recovery
queries status without replaying writes. Use the appliance's own controls when
you need to establish physical state without a working BLE connection.
