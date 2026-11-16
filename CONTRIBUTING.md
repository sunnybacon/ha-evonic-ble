# Contributing

Read the [device behaviour](docs/BEHAVIOUR.md) before changing the transport or
command handling. Preserve input validation, fresh-state confirmation, bounded
cleanup and the rule that control writes aren't automatically replayed.
Run the [development checks](docs/TESTING.md) before submitting changes.

## Reporting a problem

Include:

- HA and integration versions, plus host and Bluetooth adapter type.
- What you requested, what the fire physically did and approximately when.
- Whether mains power changed or another app/controller was connected.
- Integration diagnostics, if useful, after checking them for private information.

Don't post credentials, private device/IP addresses, full HA configuration,
phone bug reports, APKs or raw household captures. Use synthetic identifiers
in test fixtures.

Offline tests don't need a fire. Live heating tests need someone present and
a plan to restore the previous settings.
