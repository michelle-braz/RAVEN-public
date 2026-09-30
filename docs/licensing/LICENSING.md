# Licensing and ownership

> Classification: Licensing. Not legal advice; counsel should confirm the points marked *confirm*.

## Status

RAVEN's own code and documentation are **proprietary, all rights reserved** by Michelle Braz
([LICENSE](../../LICENSE)). Package metadata says `LicenseRef-Proprietary` and carries the
`Private :: Do Not Upload` classifier so the package cannot be published to PyPI by accident.

## History

| Period | Licence |
|---|---|
| First public release (2026-07-29) up to and including commit `0f66b49` (2026-09-28) | MIT |
| Later commits | Proprietary |

Why the change is possible: git history shows one human author (the owner) plus commits authored by an AI
assistant on the owner's behalf; no external contributions were merged and the previous CONTRIBUTING invited none
without prior discussion. A sole copyright holder can license future versions differently.

What it does not do: MIT grants are not withdrawn for copies of the earlier versions anyone already obtained;
those copies stay usable under MIT. The public history remains public unless the repository is made private
(and even then, existing forks or clones are unaffected). *Confirm* this reading, and the position on
AI-assisted authorship (ownership of generated code varies by jurisdiction), with counsel.

## Contributions

No external contribution should be accepted without a signed assignment or licence from the contributor.
CONTRIBUTING says so.

## Third-party material

| Category | Result |
|---|---|
| Python dependencies (runtime and test) | Fully inventoried with licences and texts: [THIRD_PARTY.md](THIRD_PARTY.md), [THIRD_PARTY_LICENSES.txt](THIRD_PARTY_LICENSES.txt). All permissive (MIT, BSD, Apache-2.0, PSF-2.0) except `certifi` (MPL-2.0, file-level copyleft, used unmodified) |
| Front-end libraries | None: Cyber Missions is plain HTML, CSS and JavaScript |
| Fonts | None bundled: the system font stack is used |
| Icons and images | One inline SVG favicon written for the project; no image assets |
| Datasets and examples | All synthetic, written for this repository (a test checks the log examples for forbidden identifiers) |
| Mission content (33 missions, rubrics) | Original text by the owner; no third-party text was identified. Tooling cannot prove provenance of prose |
| Third-party APIs and external content | None consumed at runtime. Development-only browser tests use Playwright and axe-core, installed by the tester, not distributed |
| Container base images | `python:3.11-slim` (Debian and Python licences) and `caddy:2` (Apache-2.0); pulled at build time, not redistributed by this repository |

An automated check (`tools/license_inventory.py --check`, run in CI) fails if the inventory is stale or a dependency
appears with a licence outside the allow-list.

## Obligations when distributing

* Keep copyright notices and licence texts with copies of third-party software: the image includes
  `/usr/share/doc/raven/THIRD_PARTY_LICENSES.txt`.
* MPL-2.0 (`certifi`): if its files are ever modified, the modified files must be published under MPL-2.0.
* This repository names no third-party trademarks as endorsement; the README states that RAVEN is unaffiliated
  with any observability provider.
* The names RAVEN and FOXHUMAN have not been cleared as trademarks (see [legal](../legal/README.md)).

## Repository visibility

The repository is public today. A proprietary notice on a public repository stops reuse but not reading. If the
source is a commercial asset, make the repository private before selling. That is the owner's decision; nothing
in the software depends on it.
