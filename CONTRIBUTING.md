# Contributing and reporting problems

This is an unofficial personal project developed with Codex assistance. Review
the protocol, transport and documented validation limits before proposing changes.
Use the development commands in docs/TESTING.md and preserve command guards,
confirmed-state handling, bounded cleanup and the no-write-replay policy.

For issues, provide HA/integration versions, host/adapter type, request and
physical response, approximate times, and whether another controller was open.
Download the integration's cached diagnostics where useful and review it first.
Do not publish tokens, credentials, Bluetooth addresses, private IP addresses,
full HA configuration, phone bug reports, APK files or raw household captures.
Use synthetic identifiers in test fixtures. These tests do not need a real fire.

Live heating tests need an observer and a restoration plan. Do not run automated
device-control tests against somebody else's installation.
