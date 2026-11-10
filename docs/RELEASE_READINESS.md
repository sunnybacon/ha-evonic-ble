# Publication and Marketplace status

Repository: https://github.com/sunnybacon/ha-evonic-ble

This is an early personal project, not a Home Assistant-certified integration.
Initial public code checkpoint: 0.1.0-alpha.16. Public visibility is separate
from default Marketplace catalog inclusion; no catalog submission has been made.

The repository follows the custom-integration layout, includes English
translations and local branding, and provides MIT-licensed source code with
separate manufacturer-artwork attribution. The author's personal dashboard and
optional wrapper patch are not part of this project.

GitHub Actions runs offline tests/lint, Hassfest and Marketplace validation.
Use the actual Actions results for current status; the presence of a workflow
file is not proof that a check passed. Tests/lint, Hassfest and Marketplace
validation passed for the initial public release. Adoption of an existing manual
installation through Marketplace was verified on HA 2026.11.1 with alpha.16;
the existing device/entities and area survived restart, and status polling resumed.
File-version rollback and broader installations still require their own trials.
Known device/runtime validation limits are in ../REMAINING_WORK.md.

Public packaging omits private configuration/history, APK/decompiled source,
phone bug reports and raw captures. Test identifiers are synthetic. Review any
diagnostics or logs before sharing them in an issue.

Official guidance:

- [Publishing integrations](https://contributors.home-assistant.io/marketplace/guides/integrations/)
- [Repository structure](https://contributors.home-assistant.io/marketplace/reference/repository-structure/)
- [Validation](https://contributors.home-assistant.io/marketplace/reference/validation/)
- [Branding](https://contributors.home-assistant.io/core/integrations/brands/)
