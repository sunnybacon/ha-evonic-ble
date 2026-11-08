# Device behaviour and Bluetooth transport

## Workaround

The tested fire returns ATT 0x11 during notification setup and ATT 0x0A on
acknowledged writes, even when it processes requests and transmits valid status.
BlueZ does not deliver those notifications normally. We send through BlueZ and
receive FFF2 status through a read-only Linux HCI monitor socket.

Only the selected adapter, target peer, current connection and resolved value
handle are accepted. The parser handles fragmentation and clears state on
disconnect/handle reuse. Other traffic is not recorded. A fresh status matching
the requested settings is required; ATT errors alone never count as success.

The local client pins a BlueZ path while preserving HA connection-slot tracking
and cleanup. This uses protected HA wrapper interfaces, with checks that fail
closed on incompatibility. Revalidate after HA/Bluetooth-library upgrades. This
is a maintenance limitation, not a general public route-pinning API. Remote
proxies cannot provide this local HCI receive path.

Operations connect briefly and disconnect in cleanup. Services are resolved
rather than taking the retry connector's cached-service shortcut, which caused
incomplete service collections after contention. No other devices' caches or
integrations are changed.

## Commands and recovery

One control request executes at a time. Brightness has a single latest waiting
value; intermediate coalesced values are not claimed to have been applied.
Other overlapping control types are rejected, except explicit Off, which
replaces waiting brightness and runs next. Started operations are not blindly
interrupted.

Waiting brightness is dropped on failure, cancellation or expiry. Explicit Off
remains eligible after an active brightness failure: a separate user request,
not a retry. Off cannot be delivered without a working connection.

Waiting plus execution has a 60-second request budget; cleanup can add five
seconds. The executor has a 40-second maximum; transport including lock wait
has a 35-second limit. Continuous slider input does not extend the deadline.

Invalid/inapplicable requests return validation errors without unavailability.
A genuine failed/uncertain mutation makes entities unavailable and schedules
a prompt status-only refresh. Recovery is coalesced and tied to entry lifecycle.
Only queries are repeated automatically. No control writes are replayed.

Queue state stays internal, available in debug logs/diagnostics. Entities
publish confirmed results and availability without pending attributes or an
hourglass. Requested values are not published as confirmed. The owner's card
uses the shared standard Tile template.

## Temperature and modes

Room temperature uses status bytes 5–6, unsigned tenths of a degree Celsius,
separately from target bytes 3–4. Readings near 20.4–21 °C were plausible against
a nearby thermostat at 20.7 °C. Polling continues while Off and readings changed
during heating trials. This is not calibration or a manufacturer specification.

A defensive 0–60 °C range suppresses implausible room readings independently of
valid power/settings. Natural measurement changes cannot fail setting confirmation.

Low / High preserves recognized controller modes. Target changes select manual
mode 0, matching the app. Unknown modes remain visible as `controller_mode_raw`;
182 appeared after touchscreen use, but its meaning is unresolved. Target and
heat-level writes are guarded in unknown modes. Power/brightness use separate
commands and preserve the mode in confirmation. No schedule editing is offered.

## Other controllers

The supplied Evonic BLE 2.8 app auto-connects saved fires at startup. Merely
opening an app can occupy the connection. Another household phone opened
e-touch around a restoration failure; HA recovered after it closed. Its exact
app version and connection were not captured, so timing supports contention
without proving it.

The rechargeable touchscreen connected intermittently/slowly; the cause is
unknown. One alpha.10 trial recovered automatically after it was fully powered
off, without HA refresh, reload, restart or control writes. Further touchscreen
testing is deferred because the owner does not intend to use it. Simultaneous
access and touchscreen schedule interactions remain unverified.
