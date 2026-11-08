# Roadmap and known validation limits

This personal integration has been tested against one legacy Evonic BLE
controller on a Raspberry Pi with Home Assistant 2026.11.0. Initial public
version: 0.1.0-alpha.16. Wider compatibility is not established.

Completed:

- Power, target temperature, Low/High, brightness and room-temperature entities.
- Physical control/readback trials and Off-state guards.
- Bounded serialized commands, brightness coalescing and explicit Off priority.
- Selected mains/native-app/touchscreen recovery trials without command replay.
- Cached diagnostics, official brand artwork and installation/troubleshooting docs.
- 95 offline regression tests plus lint/format checks at the publication checkpoint.

Remaining validation and maintenance:

- At least 48 hours of ordinary-use observation, including resource use and recovery.
- Actual radio loss during mutation/readback, adapter/range loss and Pi reboot.
- Entry unload during an active command and a file-version rollback trial.
- Full real-HA lifecycle/service tests and independent review beyond the developing
  assistant's focused review.
- Additional controller models and sensor calibration before broader claims.
- Revalidation of protected HA Bluetooth interfaces after relevant upgrades.
- Investigate unknown controller mode 182 if schedule/controller support is extended.

Further touchscreen concurrency testing is deferred; simultaneous native app/HA
access is not supported reliably. Bluetooth proxies require another transport
and are not currently supported. Schedule editing is out of scope.

Any personal dashboard customizations are independent of this integration and
are not prerequisites for publication or installation.
