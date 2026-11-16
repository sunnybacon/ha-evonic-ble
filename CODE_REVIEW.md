# Code review

The integration was reviewed with GPT-6 Astra on 15 November 2026, at alpha.17.
The review covered all runtime modules, command sequencing, Bluetooth packet
handling, setup/shutdown, diagnostics and tests. It used the existing project
context and offline fault injection; it wasn't an independent human audit.

## Findings and follow-up

| Finding | Outcome |
| --- | --- |
| The optional zero-temperature check could swallow a Bluetooth write timeout. | Fixed in beta.1. Only notification-wait expiry produces unknown temperature; write failures follow normal recovery. |
| A poll can wake during a new command burst. | The transport lock still serializes sessions. No incorrect final state was demonstrated; the source comment was clarified. More realistic scheduling coverage remains useful. |
| Many tests substitute small stand-ins for HA classes. | Full HA lifecycle/service tests remain on the [checklist](REMAINING_WORK.md). |

Shutdown registration was checked against
[HA Core 2026.11.1](https://github.com/home-assistant/core/blob/2026.11.1/homeassistant/helpers/update_coordinator.py).
The coordinator already registers its shutdown hook; no extra unload hook was needed.

An earlier review found cancellation masking during disconnect cleanup, fixed
in alpha.15. Beta.1 also adds a plausibility guard for repeated zero temperatures;
its assumptions and limits are in [device behaviour](docs/BEHAVIOUR.md).

The beta.1 baseline has 107 passing offline tests, lint/format checks, Hassfest
and Marketplace validation. These checks don't cover every real-radio failure
or establish compatibility with other controllers. See [testing](docs/TESTING.md).
