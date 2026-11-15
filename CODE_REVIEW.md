# Focused code review

This is a manual pass by the developing assistant, not an independent human
audit or complete Home Assistant runtime coverage. Code checkpoint: beta.1.

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

107 offline tests and Ruff checks passed at the current checkpoint. Tests use
captured-format synthetic frames and boundary stand-ins rather than a full HA
framework/radio environment. See docs/TESTING.md for checks and remaining work.
GitHub Actions supplies separate packaging checks; assess its actual results.

A whole-integration review using GPT-6 Astra on 15 November identified an overly
broad timeout catch in alpha.17's optional zero-temperature confirmation. Beta.1
catches only notification-wait expiry; GATT write timeouts propagate through normal
failure/recovery handling. Fault-injection tests cover both paths and cancellation.

The review verified shutdown registration against HA Core 2026.11.1. Its polling
probe found that a released idle-event waiter may run during a new command burst;
the transport lock still serializes sessions. No incorrect final state was proven,
so the source comment was clarified without changing lock behaviour. Real-HA
lifecycle fixtures remain a test-coverage priority. A second-model review with
shared project context is not an independent human audit.

Beta.1 adds a narrow repeated-zero plausibility heuristic using the last valid
temperature and monotonic elapsed time. Rejected measurements become unknown,
not stale values. Cold-start and long-gap limitations are documented in
docs/BEHAVIOUR.md; live sensor behaviour still requires observation.
