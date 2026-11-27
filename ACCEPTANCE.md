# Acceptance report

> Status: **pass** as of 2026-11-27 for v0.1.0.
> Operator: Kewei (Jericho) Cheng. Reviewer: pending.
> Scope: the offline registry, both profile schemas, the validator/CLI and the
> repository gate. This report covers L0 and L1 only.
> No motion command was sent and no device was opened.

## 1. Gates

| Gate | Command | Level | Result | Evidence |
|---|---|---|---|---|
| Contract / static | `bash scripts/check_repo_gate.sh` | L0 | pass | [evidence/20261127_scaffold/gate.txt](evidence/20261127_scaffold/gate.txt) |
| Unit / integration (offline) | `python3 -m pytest -q tests` | L1 | pass | [evidence/20261127_scaffold/pytest.txt](evidence/20261127_scaffold/pytest.txt) |
| Registry validation | `jcheng-devices validate` | L0 | pass | [evidence/20261127_scaffold/gate.txt](evidence/20261127_scaffold/gate.txt) |
| Mock integration | — | L2 | not applicable | No mock runtime or adapter exists in v0.1.0. |
| Mock end-to-end | — | L3 | not applicable | No runtime graph or plant integration exists. |
| Replay | — | L4 | not applicable | No recorded device data is consumed. |
| Hardware | — | L5 | not run | No device was opened; no operator session was requested. |

## 2. Verified claims

| Claim | Level | Evidence |
|---|---|---|
| Every registered profile loads, matches its schema and resolves its capability references | L1 | [evidence/20261127_scaffold/pytest.txt](evidence/20261127_scaffold/pytest.txt) |
| The registry contains six device profiles and seven capability profiles | L1 | `tests/test_registry.py`; `tests/test_profiles.py` |
| Duplicate identifiers, path escapes, unknown capabilities, category mismatches and inconsistent verification statements are rejected | L1 | `tests/test_registry.py` |
| All five device categories are reserved; four are populated | L0 | `tests/test_registry.py`; `docs/DEVICE_REGISTRY.md` |
| Code and data contain no device-opening, runtime-graph or motion tokens | L0 | `tests/test_no_hardware.py` |
| The CLI exits 0/1/2 as declared and emits deterministic output | L1 | `tests/test_cli.py` |
| The registry digest is deterministic and independent of file order | L1 | `tests/test_registry.py`; `tests/test_cli.py` |
| The ArmPi Ultra reference facts match the recorded system and learning sources | L1 | `tests/test_reference_devices.py` |

## 3. Not verified

| Item | Reason | Risk |
|---|---|---|
| Any device parameter measured on hardware | No L5 session; the repository never opens a device | A profile value could be copied from a stale or wrong source |
| ArmPi Ultra payload, repeatability, absolute accuracy and workspace | Not measured by this repository | Planning may assume an envelope the arm does not have |
| PiPER X joint limits, velocity and bus configuration | No hardware or datasheet review | A candidate profile may be wrong; it is marked unverified |
| M10 range, field of view and scan rate | Device not connected | The planned envelope may not match the delivered unit |
| URDF/Xacro and calibration assets | Not copied in v0.1.0 | Simulation and back-projection cannot use this repository yet |
| Capability matching and compatibility validation | M2 not started | Cross-device reuse is not validated |
| Adapter contract and mock | M3 not started | No executable boundary exists yet |
| Integration with system or simulation | M4 not started | Profiles are documentation only |

## 4. Limitations

- This repository describes devices; it does not prove that a device behaves as
  described. Synthetic, mock and offline checks are never reported as hardware
  validation.
- The ArmPi Ultra profile inherits joint limits from the learning adapter
  profile and bus IDs from the system documentation. Those values are marked
  `verified: false` per joint and the profile overall is only
  `partially verified`.
- The D435i deployment is split into a UVC colour stream and a depth-only
  stream; colour and depth are not aligned. The profile states this and makes
  no aligned-depth claim.
- The chassis speed value is an intent limit from `jcheng-mobile`, not a
  measured chassis limit.
- No profile grants motion authority. The system layer remains the only origin
  of motion.
- The device profile schemas are repository-local. They are not contracts until
  a reviewed proposal is accepted in `jcheng-interfaces`.

## 5. Sign-off

| Role | Name | Date |
|---|---|---|
| Operator | Kewei (Jericho) Cheng | 2026-11-27 |
| Reviewer | pending | — |

## 6. Machine-readable report

None. The evidence directory contains the raw gate and test output; no JSON
acceptance report was produced for v0.1.0.
