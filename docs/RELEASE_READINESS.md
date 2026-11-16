# Releases

The integration is distributed through a Marketplace custom repository.
No default-catalog submission has been made.

## Before publishing code

- [ ] Review the diff and update the changelog and manifest version.
- [ ] Run the [development checks](TESTING.md).
- [ ] Check public files, test fixtures and commit metadata for private information.
  Use synthetic device addresses and a GitHub noreply author email.
- [ ] Push the commit and wait for tests, Hassfest and Marketplace validation.
- [ ] Publish a release targeting that commit. Mark alpha/beta releases as prereleases.
- [ ] Refresh Marketplace information and check that it offers the expected version.

Release notes should describe the changes users will notice and any installation
steps. Keep implementation details in the supporting docs.

Documentation changes can be committed to the main branch without a new version.
Existing GitHub release descriptions can also be edited without changing the code.

## After installing

Check the loaded version, entity availability, settings, status reads and logs.
Keep a copy of the previous integration files before updating. Remaining
hardware and lifecycle tests are tracked in [remaining work](../REMAINING_WORK.md).

## Reference

- [Marketplace integration guide](https://contributors.home-assistant.io/marketplace/guides/integrations/)
- [Repository structure](https://contributors.home-assistant.io/marketplace/reference/repository-structure/)
- [Validation](https://contributors.home-assistant.io/marketplace/reference/validation/)
- [Branding](https://contributors.home-assistant.io/core/integrations/brands/)
