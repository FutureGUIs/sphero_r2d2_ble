# HACS submission checklist

Guidance checked on October 6, 2026. This prepares a HACS default-list submission;
users can already install the integration as a custom repository.

## Current guidance

- Keep one integration under `custom_components/sphero_r2d2_ble`. Include
  `domain`, `name`, `documentation`, `issue_tracker`, `codeowners`, and `version`
  in the integration manifest. Local brand assets are supported, with at least
  `brand/icon.png`. This repository already contains a 256x256 PNG icon.
  [HACS integration requirements](https://www.hacs.xyz/docs/publish/integration/)
- The public GitHub repository needs a description, topics, and a useful README.
  `hacs.json` belongs in the root. Country restrictions are appropriate only for
  integrations limited to particular countries; this integration has none.
  [General requirements](https://www.hacs.xyz/docs/publish/start/)
- Default-list inclusion requires both official HACS and Hassfest checks to pass,
  without ignored HACS checks, followed by a full GitHub release. A tag alone is
  insufficient. The owner or a major contributor must submit the request.
  [Default-list submission](https://www.hacs.xyz/docs/publish/include/)
- Keep the minimum dependency requirement `bleak-retry-connector>=3.9.0`. Current
  Hassfest checks reject exact pins that conflict with HA's shared dependencies;
  a minimum version lets HA's Bluetooth stack advance without being downgraded.
  [Current Hassfest dependency validator](https://github.com/home-assistant/core/blob/dev/script/hassfest/requirements.py)

## Prepared locally

- Version 0.3.0 and changelog.
- Manifest codeowner `@FutureGUIs`, issue tracker, and sorted manifest fields.
- Root HACS manifest with display name and minimum HA version 2026.3.0.
- Existing local brand icon verified as a 256x256 PNG.
- Tracked Python bytecode removed; generated caches are excluded from Git.
- Validate workflow: regression suite, local checks, official Hassfest and HACS.
  It runs on pushes, pull requests, manual dispatch, and a weekly schedule. The
  HACS job has no ignored checks and does not post PR comments.
- 39 simulated regression tests, Python syntax, JSON, and local metadata checks
  passed. The user reported successful real-device testing of the integration.

Official HACS and Hassfest jobs have **not** run for these unpublished changes.
Their Docker actions cannot be run in the available local Windows environment.
Local checks are deliberately narrower and do not establish submission approval.
The checkout's baseline is commit `94036ac`; a fresh remote fetch could not be
completed during preparation, so sync the branch before publishing.

## Remaining GitHub steps

1. Set the repository's About description, for example:
   `Native Home Assistant Bluetooth integration for Sphero R2-D2.`
2. Add topics such as `home-assistant`, `hacs`, `custom-integration`, `bluetooth`,
   `sphero`, and `r2d2`. Keep the repository public, active, and issues enabled.
3. Commit/push the prepared changes. Wait for every Validate job to pass and fix
   any official-validator failures; do not ignore checks to obtain a green run.
4. Publish a full GitHub release with tag `v0.3.0`, title `0.3.0`, and the 0.3.0
   changelog as its notes. HACS can download the repository contents directly;
   no `zip_release` configuration or specially named release asset is needed.
5. Verify custom-repository installation of the release in HACS and confirm the
   installed integration reports version 0.3.0.
6. From your personal account, fork `hacs/default`, create a new branch from its
   current `master`, and add `FutureGUIs/sphero_r2d2_ble` alphabetically to the
   `integration` list. Keep the PR editable by maintainers.
7. Fill out the current PR template truthfully, including ownership, working
   installation, passing validations, and the published release. Submit only
   once these prerequisites are complete.

No repository settings, GitHub release, or HACS submission were changed by the
local preparation. This checklist records the actions still needed online.
