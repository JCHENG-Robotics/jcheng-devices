# jcheng-devices roadmap

> Status: **v0.1.0** as of 2026-11-27. The offline registry, schemas, validator
> and reference profiles are in place; no adapter, runtime or hardware
> integration exists.

## Current state

| Item | State | Evidence |
|---|---|---|
| Registry, nine device profiles, seven capability profiles | Complete | `registry/registry.yaml`; [evidence/20261127_scaffold/](evidence/20261127_scaffold/README.md) |
| `device-profile.v1` and `capability-profile.v1` schemas | Complete | `src/jcheng_devices/schemas/` |
| Offline validator, CLI and deterministic digest | Complete | `src/jcheng_devices/`; `tests/` |
| Repository gate and CI | Complete | `scripts/check_repo_gate.sh`; `.github/workflows/ci.yml` |
| ArmPi Ultra reference profiles (arm, gripper, chassis, D435i) | In progress — partially verified facts only | `registry/devices/hiwonder.*`, `registry/devices/intel.realsense-d435i.yaml` |
| PiPER X candidate profile | Planned — unverified, no hardware | `registry/devices/agilex.piper-x.yaml` |
| M10 LiDAR profile | Planned — device not connected | `registry/devices/lslidar.m10.yaml` |
| URDF/Xacro, calibration, hardware and simulation assets | Planned — layout defined, nothing copied | [docs/ASSET_LAYOUT.md](docs/ASSET_LAYOUT.md) |
| Capability matching and compatibility validation | Not started | — |
| Device adapter contract and mock | Not started | — |
| Controlled integration with system/simulation | Not started | — |
| Hardware validation of any profile | Not started | — |

## Milestones

| Milestone | Scope | State | Exit criterion | Evidence |
|---|---|---|---|---|
| M0 | Admission: L3 device library, offline boundary, taxonomy entry | Complete (2026-11-27) | Boundary approved with `hardware_access: none` and an empty runtime surface | `capability.yaml`; `.github/docs/repo-taxonomy.md` |
| M1 | Device registry, description, capability model and offline validation (v0.1.x) | Complete (2026-11-27) | Registry validates; schemas, CLI, tests, CI and reference profiles exist | [evidence/20261127_scaffold/](evidence/20261127_scaffold/README.md) |
| M2 | Multi-device description specification, capability matching and compatibility validation (v0.2.x) | Planned | A compatibility matrix rejects category, range and capability mismatches deterministically, reconciles joint overlap with the system `robot-profile.v1`, and passes for at least two arm vendors | — |
| M3 | Device adapter contract design and mock implementation (v0.3.x) | Planned | Adapter protocol reviewed and merged in `jcheng-interfaces`; an in-memory mock passes contract tests; no device access | — |
| M4 | Controlled integration with `jcheng-system` and `jcheng-simulation` (v0.4.x) | Planned | Profiles drive a simulated plant on domain 43 and a plan-only system path under a reviewed contract; no independent control channel | — |
| M5 | Cross-device task transfer and real-robot adaptation validation (v0.5.x) | Planned | One task recipe transfers between two device profiles with recorded, supervised evidence; failures stay failed | — |
| M6 | v1.0.0: hardware-verified device management and stable adapter contracts | Planned | Every reference profile has per-parameter evidence; adapter contracts are tagged; acceptance is signed | — |

## Next

1. **M2 — compatibility validation.** Add a deterministic compatibility matrix
   over registry entries: joint range containment, capability requirements,
   category agreement and sensor envelope checks. Prerequisites: agree whether
   the matrix schema is repository-local or a `jcheng-interfaces` proposal,
   and close the contract review before any cross-repository consumer appears.
2. **M3 — adapter contract and mock.** Define the adapter boundary as a
   contract-first proposal, never as a new control channel. Prerequisites: M2
   accepted; `jcheng-system` owner review; explicit statement that execution
   remains with the system layer.

## Out of scope

- Direct hardware access, device drivers, serial/CAN/GPIO/video ownership.
- Joining a runtime graph, starting a runtime node or publishing a topic.
- An independent control channel, a lease of its own, or any `ExecuteMotion`
  origin.
- Bypassing the system layer's execution authority, safety state machine,
  arbiter or stop latch.
- Duplicating perception, mobile, learning or teleoperation functionality.
- Copying, migrating, deleting or modifying assets that belong to another
  repository.
- Vendor code, vendor meshes and model weights inside this repository.
- Functional-safety certification. The platform has no e-stop, brake or
  independent encoder.

## Dependencies

- `jcheng-interfaces` `>=0.2,<0.3`; contract hash
  `sha256:afca22a42f7163e0351d185d5a8577b0b51f2f3da4b92278f161a4a7d2c35b1c`
  (v0.2.0).
- `jcheng-system` API `>=0.2,<0.4`. v0.1.0 uses none of it; the range is
  declarative.
- Any cross-repository interface change requires a contract review in
  `jcheng-interfaces` first. Device profile schemas stay repository-local until
  such a review promotes them.
- Real-robot work requires separate, explicit, per-session operator
  authorization. This repository does not authorize or schedule motion.
