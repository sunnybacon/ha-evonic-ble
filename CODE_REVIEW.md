# Focused code review

This is a manual pass by the developing assistant, not an independent human
audit or complete Home Assistant runtime coverage. Code checkpoint: alpha.16.

| Area | Reviewed | Remaining limits |
| --- | --- | --- |
| Protocol | Packet size, control bounds, separate measured/target temperature | One controller; defensive room-temperature bounds, no calibration claim |
| Transport | Local route, valid readback despite ATT errors, bounded sessions, one mutation per operation, query-only recovery | Radio loss after mutation needs a specific live trial; protocol has no sequence ID |
| HCI | Adapter/peer/connection/value-handle filtering, fragmentation, RX-only, close-on-error | Protected/OS interfaces need upgrade checks; proxies unsupported |
| Scheduler | Coalescing, Off priority, deadlines, cancellation, no write replay | Full HA runtime and broader radio failures are not established by fake clients |
| Lifecycle | Shutdown registration, idle unload/re-enable and startup recovery | Mid-command unload, file-version rollback and full HA lifecycle fixtures remain |
| Diagnostics | Cached allowlist, no arbitrary entry data/address/exception text | Review separately collected logs before sharing |

The review reproduced cancellation masking during rejected-backend disconnect
cleanup. Alpha.15 corrected it with failing-before/passing-after tests.
Alpha.16 makes target temperature and Low/High standard controls while retaining
Off/unknown-mode guards and confirmed-state semantics.

95 offline tests and Ruff checks passed at the publication checkpoint. Tests use
captured-format synthetic frames and boundary stand-ins rather than a full HA
framework/radio environment. See docs/TESTING.md for checks and remaining work.
GitHub Actions supplies separate packaging checks; assess its actual results.
