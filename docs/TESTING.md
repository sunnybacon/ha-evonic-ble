# Testing

Last recorded code baseline: beta.1, 15 November 2026.
Device testing used one legacy controller on a Raspberry Pi, with HA 2026.11.0
and 2026.11.1.

## Device checks

| Check | Recorded result |
| --- | --- |
| Controls | Power and brightness changes were physically observed. Target temperature and Low/High matched device readback. |
| Controls while Off | Brightness, target and preset changes were rejected without turning the fire on. |
| Rapid brightness changes | Selected coalescing, failure-discard and Off-priority trials passed. |
| Mains interruption | Status-only recovery was observed without replaying commands. Loss during the actual write still needs testing. |
| Startup without mains | Setup retried and recovered after mains returned. |
| Phone app contention | Selected connect/release/recovery trials passed. Opening another app coincided with one failure; its connection wasn't captured. |
| Touchscreen | One recovery trial passed after the screen was powered off. Connecting was intermittent; further testing is deferred. |
| Idle unload/re-enable | Settings were preserved. Unloading during an active command remains untested. |
| Room temperature | Readings were plausible against a nearby thermostat and updated while Off. The sensor hasn't been calibrated. |
| Diagnostics | Cached export and omission of the fire's address were checked. |
| Marketplace updates | Manual-install adoption and later updates through beta.1 preserved the existing entities and resumed status reads after restart. |

Beta.1's temperature guard still needs ordinary-use observation to confirm its
effect on intermittent zero readings. Open work is tracked in the
[checklist](../REMAINING_WORK.md).

## Automated checks

Beta.1 passed 107 offline tests, Ruff lint/format checks, Hassfest and Marketplace
validation. Tests cover packet filtering, command validation, queueing,
confirmation, recovery, cancellation and cleanup.

Temperature tests include isolated/repeated zeros, elapsed time, cold startup,
gradual cooling, recovery and missing measurements. Timeout tests distinguish
a missing notification from a failed query write, including failures after a
mutation, cancellation and malformed responses.

The tests use fake Bluetooth clients and simplified HA boundaries. They don't
replace a real HA lifecycle suite or physical radio tests.

From the repository root, in a development virtual environment:

```sh
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
python -m ruff check custom_components tests
python -m ruff format --check custom_components tests
```

These commands don't connect to a fire. For a release's actual CI results, see
[GitHub Actions](https://github.com/sunnybacon/ha-evonic-ble/actions).
