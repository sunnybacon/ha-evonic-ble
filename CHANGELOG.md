# Changes

## 0.1.0-alpha.16 — 2026-11-08

- Make target temperature and Low/High standard climate controls for new and
  existing entries. Remove the experimental checkbox/options flow and obsolete
  entity/diagnostic flags. Legacy saved opt-in values are harmless and ignored;
  no entry recreation or registry change is needed.
- Preserve Off-state, unknown-mode and command validation guards, confirmation,
  serialization and recovery behaviour. Setup/restart remains status-only.
- Update user docs/translations. 95 offline tests pass; three obsolete opt-in
  tests retired and climate coverage now checks standard controls and legacy
  disabled-entry compatibility. Ruff lint/format checks pass.

## Documentation and branding preparation — 2026-11-08

- Explain the personal-project origins, owner's Home Assistant/coding experience
  and iterative Codex-assisted development, without equating AI assistance with
  correctness or broad compatibility.
- Reorganize installation, behaviour, troubleshooting, testing and release docs;
  correct stale pending-test claims and mark historical manual scripts.
- Bundle official Evonic wordmark/site icon with attribution and reproducible
  PNG packaging, plus conservative Marketplace metadata. Runtime Python and
  manifest version remained alpha.15 at that preparation checkpoint.

## 0.1.0-alpha.15 — 2026-11-08

- Preserve cancellation when cleaning up a rejected non-BlueZ backend, and chain
  other cleanup failures without hiding the routing refusal. New regression
  reproduced the cancellation-masking defect before the correction.
- Add cached-state-only diagnostics with an explicit data allowlist; omit device
  addresses, arbitrary entry data and exception text. No Bluetooth write/read is
  initiated by downloading diagnostics.
- 98 offline regressions, Ruff checks and formatting verification pass. Formatting
  preserved production AST apart from import ordering. Real-HA lifecycle tests,
  packaging checks and independent review remain outstanding.

## 0.1.0-alpha.14 — 2026-11-08

- Expose measured room temperature on the climate entity, including while Off.
  Status bytes5–6 are distinct from the target bytes3–4; passive readings20.4–20.5C
  compared plausibly with the nearby downstairs thermostat20.7C. Sensor placement
  and calibration remain unverified. Out-of-range measurements become unknown.
- Natural room-temperature drift cannot fail command confirmation. All controlled
  settings remain checked, and measurement-only changes still notify HA.
- 93 offline regressions pass, including changing measurements during all command
  types, invalid measurement fallback and Off-state room-temperature presentation.

## 0.1.0-alpha.13 — 2026-11-08

- Integration translations display Low/High without changing raw preset IDs.
  Frontend translation API verified both labels after restart.

## 0.1.0-alpha.12 — 2026-11-08

- Keep queue-status changes internal instead of publishing pending attributes
  or changing the brightness icon. Confirmed states/errors still publish normally.
- 88 offline regressions pass. This avoids one control reset cause; the installed
  Custom Card Features slider has a separate unawaited-service reset issue.

## 0.1.0-alpha.11 — 2026-11-08

- Preserve cancellation if disconnect cleanup itself fails. Log disconnect
  failures instead of silently swallowing them or masking the original error.
- Still attempt disconnect if receiver close fails. Always close the monitor
  socket and clear peer/fragment state even when reader removal raises; report
  read failures to the transport even if receiver cleanup also fails.
- 85 tests pass. Eight new regressions cover cleanup failures, link loss before
  mutation, applied-but-unconfirmed mutation, query-only recovery, queued
  brightness discard and explicit queued Off. No live mains interruption yet.

## 0.1.0-alpha.10 — 2026-11-08

- Request resolved services instead of the retry connector's service-cache
  shortcut. A touchscreen release trial left client service discovery incomplete
  despite the expected FFF0/FFF1/FFF2 objects existing in BlueZ diagnostics.
- Log each status failure's type/reason at DEBUG, including repeated failures.
- 77 tests pass, including connection-option forwarding and missing-service
  cleanup before GATT writes. One actual idle/off touchscreen release trial
  recovered automatically without refresh/reload/restart; other concurrency
  scenarios remain untested. README documents limitations and observations.

## 0.1.0-alpha.9 — 2026-11-08

- Match APK gear-only changes by preserving the current controller mode in the
  command and required confirmation. Temperature changes explicitly select manual
  mode 0, as in the native app (which warns that timing is turned off).
- Unknown-mode and off-state heater guards remain; no implicit power-on added.
- 75 tests pass, including week/holiday preservation, manual target changes and
  failure without mutation replay if the returned mode unexpectedly changes.
- Actual week/holiday-mode gear writes remain untested on hardware; no schedules
  were enabled or edited to exercise this path.

## 0.1.0-alpha.8 — 2026-11-08

- Preserve unknown controller-mode bytes in otherwise valid status replies;
  touchscreen use produced mode 182, previously causing the entire reply to be
  discarded. Expose controller_mode_raw without inventing its meaning.
- Temperature/heat-level writes reject unknown controller modes with fresh
  status, avoiding an implicit mode change. Standard power/brightness commands
  preserve the mode and continue to require confirmed full control-state readback.
- 72 tests pass, including unknown-mode status/control preservation and rejection.

## 0.1.0-alpha.7 — 2026-11-08

- Distinguish unsupported full status replies from a missing reply. Debug logs
  include only parsed control fields from this fire's filtered status packets.
- Keep strict decoding unchanged while investigating touchscreen recovery.
- Add regression coverage for unsupported mode 182: no control write, cleanup,
  diagnostic error. 70 integration tests pass.

## 0.1.0-alpha.6 — 2026-11-08

- Reject temperature/heat-level requests while off with fresh confirmed status,
  without control writes or loss of availability. Matches the native app guard.
- The first live off-state target change was not applied. Corrected the fake
  transport test's unsupported assumption that heating commands work while off.
- On-state heater writes and physical heat output remain unvalidated.

## 0.1.0-alpha.5 — 2026-11-08

- Add an options flow to enable/disable experimental heating controls on the
  existing entry. Uses HA's OptionsFlowWithReload; changing the flag only reloads
  the entry and queries status. Entity identity and saved power are preserved.
- Explicit options override the original setup flag in either direction.
- Ten climate-action/option precedence boundary tests; 68 integration tests pass.
- Off/Low/High combined presentation is a recorded design preference, not yet
  implemented. Actual heating writes and physical output remain separate tests.

## 0.1.0-alpha.4 — 2026-11-08

- Fix HA reselecting an ESPHome proxy despite initially selecting a local device.
  A per-integration client pins the selected BlueZ device path, retains HA's
  connection-slot handling, and never invokes the remote-capable selector.
- Check backend identity and require a matching HCI connection event before
  any GATT query/control. Unsupported routes fail without commands.
- Uses protected HA wrapper interfaces in one isolated adapter, with compatibility
  checks that fail closed. No global patches, scanner/proxy or permission changes.
- Ten additional routing/HCI-gate regression tests; 58 integration tests pass.

## 0.1.0-alpha.3 — 2026-11-08

- One active control and at most one pending control. Intermediate waiting
  brightness values are replaced by the latest, rather than building a backlog.
- Explicit Off discards waiting brightness and blocks new brightness work until
  finished. An active write is allowed to finish/clean up; it is not interrupted
  blindly. Off remains a separate explicit request even if active brightness fails.
- Other overlapping control types return a validation message instead of queuing.
- Pending attributes and brightness hourglass icon; confirmed values remain
  separate from desired values. Custom dashboard presentation remains separate work.
- Cancelled/expired unsent requests do not execute later. Pending brightness is
  discarded after failure; control writes are never automatically replayed.
- Request deadlines include waiting; per-operation and transport-lock waits are
  bounded. Polling waits until the control burst ends before querying/publishing.
- 16 new scheduler/wiring tests: 48 integration tests now pass. Live rapid-slider
  observation is still required.

## 0.1.0-alpha.2 — 2026-11-08

- Distinguish rejected requests from device/transport failures. Brightness while
  off now returns a validation message and retains fresh confirmed availability,
  rather than taking the entire device unavailable.
- Invalid command values do not invalidate previously confirmed device status.
- Request a coalesced, entry-owned status refresh after genuine command failure;
  never replay the failed control write.
- Seven new command-policy boundary tests, plus stronger transport assertions
  for the off-brightness rejection. 32 integration tests pass; these do not replace
  real HA runtime verification.
- Includes the previously saved native climate API naming cleanup.

## 0.1.0-alpha.1

- Initial local climate/brightness integration, with filtered local HCI replies.
- Corrected BlueZ declaration/value handle selection using the discovered CCCD.
- Status/setup/reload verified in HA Core; heating setters disabled by default.
