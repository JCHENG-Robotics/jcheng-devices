# License review — jcheng-devices

> Status: **pending** as of 2026-11-27.
> No `LICENSE` file exists. This repository follows the organization rule that
> no license is added before the review is signed off
> (`.github/docs/license-review.md`).

## 1. Current facts

| Item | Fact |
|---|---|
| `LICENSE` file | none |
| Code in v0.1.0 | offline Python package, JSON Schemas, YAML profiles, shell gate and tests; no runtime node |
| Runtime dependencies | `PyYAML==6.0.2`, `jsonschema==4.26.0` and its transitive packages |
| Test dependencies | `pytest==8.3.4` — CI and development only |
| Device assets | none copied; no URDF, mesh, calibration file or vendor code |
| Measured data | none copied; profiles cite evidence in other repositories |
| Robot access | none |

## 2. Decision recorded on 2026-11-27

The repository is created **without** a `LICENSE` file until the ecosystem
review closes. Adding MIT now would pre-empt the organization decision and
would suggest the eventual license covers device assets and vendor-derived
descriptions, which it will not.

The review must decide before the ecosystem reaches v1.0:

1. The copyright holder and year for new repositories.
2. Whether MIT is the intended license for capability repositories.
3. How device assets and vendor-derived descriptions are licensed and
   attributed.
4. Whether a `THIRD_PARTY_NOTICES.md` is required once URDF, meshes or
   calibration files are adopted.

## 3. Third-party inventory

| Dependency | Use | Known/probable license | Risk |
|---|---|---|---|
| Python standard library | code | PSF | Low |
| PyYAML 6.0.2 | profile and registry parsing | MIT | Low |
| jsonschema 4.26.0 | schema validation | MIT | Low |
| attrs (jsonschema dependency) | schema validation | MIT | Low |
| jsonschema-specifications (dependency) | schema validation | MIT | Low |
| referencing (dependency) | schema validation | MIT | Low |
| rpds-py (dependency) | schema validation | MIT | Low |
| pytest 8.3.4 | tests only | MIT | Low |
| Device profile facts | YAML descriptions | derived from in-tree documentation; no vendor code copied | Review wording and attribution before v1.0 |
| URDF/Xacro assets (future) | simulation and description | per vendor; not yet adopted | Must be reviewed before the first copy |
| Meshes and simulation assets (future) | simulation | per vendor; not yet adopted | Binary assets stay outside the repository until reviewed |

## 4. Open questions

- [ ] Confirm the copyright holder and year.
- [ ] Confirm MIT for this capability repository.
- [ ] Define the record for vendor-derived device descriptions.
- [ ] Define the review process for URDF/Xacro and mesh provenance.
- [ ] Decide whether a `THIRD_PARTY_NOTICES.md` is required.
- [ ] Record the ecosystem-wide decision in `.github/docs/license-review.md`.

## 5. Related

- [`.github/docs/license-review.md`](https://github.com/JCHENG-Robotics/.github/blob/main/docs/license-review.md)
- [Acceptance report](ACCEPTANCE.md)
- [README](README.md)
