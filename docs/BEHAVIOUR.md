# Device behaviour and Bluetooth transport

## Bluetooth workaround

The tested controller returns ATT 0x11 during notification setup and ATT 0x0A
on acknowledged writes, even when it processes the request. BlueZ doesn't
deliver its notifications normally, so the integration sends through BlueZ
and receives FFF2 status through a read-only Linux HCI monitor socket.

The receiver checks the adapter, peer, live connection and notification value
handle. It handles fragmented packets and clears partial data on disconnect or
handle reuse. Other devices' traffic isn't recorded.

Local routing uses protected HA Bluetooth interfaces while retaining connection
slot tracking and cleanup. Compatibility needs checking after HA/Bluetooth
upgrades. Bluetooth proxies can't provide this receive path.

Each operation opens a short connection, resolves services and disconnects in
cleanup. Service caching is disabled because it produced incomplete service
collections after another controller used the fire.

## Commands and recovery

One control runs at a time. Rapid brightness changes keep only the latest
waiting value. Other overlapping controls are rejected, except Off: it replaces
waiting brightness and runs after the active operation.

Failed, cancelled or expired brightness requests are discarded. A separately
requested Off remains eligible after a brightness failure. Control writes
aren't automatically replayed; recovery only reads status.

Invalid or inapplicable requests return a validation error. Failed or uncertain
commands make the entities unavailable and schedule a status refresh. Commands
are confirmed against device settings before results are published. Queue state
is available in debug logs and diagnostics.

Timeouts are bounded: 60 seconds for a queued request, 40 seconds for its executor
and 35 seconds for transport including lock wait. Disconnect cleanup has a
five-second timeout. Continuous slider input doesn't extend a pending deadline.

## Room temperature

Status bytes 5–6 hold unsigned tenths of a degree Celsius; bytes 3–4 hold the
target. Room temperature is polled while Off if mains is available. Values outside
0–60°C become unknown without hiding otherwise valid controls. The sensor hasn't
been calibrated.

A zero triggers one more status query. If its notification wait expires, the
temperature becomes unknown and the first packet's confirmed controls are kept.
Write or receiver failures follow normal error recovery.

Repeated zeros are checked against the last valid temperature and its age.
The allowed drop is **2°C plus 0.5°C per elapsed minute**. This is a defensive
heuristic, not an Evonic specification. For example, 23°C followed by repeated
zeros one minute later is rejected.

Rejected or missing readings don't lower or refresh the reference. A valid
measurement restores reporting. Nonzero readings aren't smoothed, and old values
aren't presented as fresh measurements.

The reference uses monotonic time and resets on reload. Confirmed zero is allowed
at cold startup, near freezing or after enough time has elapsed. This means the
guard cannot detect every persistent sensor fault.

## Modes and other controllers

Changing target temperature selects manual mode, as the phone app does, and may
leave a native timing mode. Low/High preserves recognized modes. Unknown modes
remain visible as `controller_mode_raw`, but target/heat-level changes are blocked.
Mode 182 appeared after touchscreen use; its meaning is unresolved.

The Evonic BLE 2.8 app can connect to a saved fire as soon as it opens. Close
phone apps fully and disconnect the touchscreen while HA needs access.
Touchscreen connections were intermittent; further testing is deferred.

HA doesn't restore power at startup or reconnection. The appliance itself
resumed its previous On state after mains restoration in one trial.
