# Testing and limits

Checkpoint: alpha.16, 8 November 2026. Iterative Codex-assisted development and
testing used the owner's single controller. Tests reduce specific risks; they
do not establish universal compatibility.

| Check | Result and limit |
| --- | --- |
| Power/brightness/Low–High/target | Alpha.14 readback regression passed; owner observed On/dim/full/Off. Heater and target requests matched readback. |
| Off-state guards | Brightness, target and preset rejected without power-on or unavailability. |
| Rapid brightness/queue | Selected coalescing, failure discard and Off-priority trials passed. Off cannot be delivered without mains. |
| Mains interruption | Status-only recovery/no write replay observed. Some losses interrupted reconnect rather than actual write/readback. |
| HA startup without mains | Alpha.15 retry/unavailable followed by loaded status after mains return, without manual refresh or control writes. |
| Native app | Selected occupancy/release/recovery trials passed. Another phone's opening coincided with failure; its connection was not independently captured. |
| Touchscreen | One powered-off release/recovery passed. Connection intermittent; further testing deferred. |
| Idle unload/re-enable | Alpha.14 passed with Off/settings preserved; active-command unload not covered. |
| Room temperature | Nearby-thermostat plausibility, Off polling and changing readings observed; not calibration. |
| Cached diagnostics | Alpha.15 runtime export and address omission checked. |

Focused review found cancellation masking in rejected-backend cleanup. Alpha.15
fixed it with failing-before/passing-after tests. See [review scope](../CODE_REVIEW.md).

Alpha.16 makes target temperature and Low/High standard controls. Regression
coverage verifies their feature flags and service mapping, including existing
entries with the old option disabled. Three tests of the removed opt-in policy
were retired; the Off/unknown-mode, transport and recovery tests remain.

## Development checks

From this project root in a development virtual environment:

```sh
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
python -m ruff check custom_components tests
python -m ruff format --check custom_components tests
```

95 tests and Ruff checks passed at this checkpoint. Dependencies are development
only. Tests cover packets, command bounds, HCI filtering/fragmentation, ATT errors,
confirmation, queueing, non-replay, cancellation and cleanup. Fake clients and
boundary stand-ins are not a full real-HA framework environment or real radio.

Remaining checks include actual loss during write/readback, adapter/range loss,
Pi reboot, active-command unload, file-version
rollback, at least 48 hours ordinary-use observation, full HA lifecycle/service
tests, independent review and Hassfest/Marketplace validation. Wider controller
and calibration claims need separate evidence. See [remaining work](../REMAINING_WORK.md).

Documentation/artwork changes do not trigger physical control tests. Future
heating tests need an observer, clear sequence and prior-settings restoration.

Personal dashboard customizations and their visual checks are outside integration release scope.
