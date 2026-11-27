# M1 plan — offline device library (v0.1.x)

> Status: **Complete** as of 2026-11-27 for v0.1.0.
> Scope: registry, schemas, validator, CLI, reference profiles, tests and CI.
> No device, runtime node or motion path is in scope.

## 1. Goal

Establish one explicit, reviewable description of the ecosystem's devices and
device capabilities, with a fail-closed offline validator, so that later
adapters, simulation configuration and capability matching have a single
source of device facts instead of copies in several repositories.

## 2. In scope

- [x] L3 admission with `hardware_access: none` and an empty runtime surface.
- [x] Explicit `registry/registry.yaml`; no filesystem auto-discovery.
- [x] Device identifier convention `<vendor>.<slug>`, unique across devices and
  capabilities, with the file name equal to the id.
- [x] Five device categories: `arm`, `mobile_base`, `end_effector`, `sensor`,
  `teleop_device` (reserved).
- [x] Device profile schema: vendor, hardware, kinematics, chassis,
  end-effector, sensor and teleop blocks, per-parameter source and verification.
- [x] Capability profile schema: parameters, feedback, constraints, required
  capabilities and verification.
- [x] ArmPi Ultra reference profiles: arm, gripper, chassis and front camera.
- [x] PiPER X candidate profile and M10 planned profile, both explicitly
  unverified.
- [x] Offline validator with identity, schema, path, cross-reference,
  kinematics and verification checks.
- [x] `list`, `show`, `validate` and `digest` CLI commands; deterministic JSON.
- [x] Tests: contract, registry failure paths, profile invariants, CLI, static
  hardware boundary and reference-device facts.
- [x] Repository gate and CI.
- [x] Asset organisation standard for URDF/Xacro, calibration, hardware
  configuration and simulation assets.

## 3. Out of scope

- Copying URDF, Xacro, meshes or calibration files (M2).
- Capability matching and compatibility validation (M2).
- Adapter contract and mock (M3).
- Integration with `jcheng-system` or `jcheng-simulation` (M4).
- Any hardware session or measured parameter (M5).
- Promoting the profile schemas to `jcheng-interfaces` without a contract
  review.

## 4. Exit criteria

| Criterion | Result |
|---|---|
| `jcheng-devices validate` exits 0 on the repository | pass |
| `python3 -m pytest -q tests` passes | pass |
| `bash scripts/check_repo_gate.sh` passes | pass |
| Every registered profile has a source and a verification statement | pass |
| No code or data contains a device, runtime-graph or motion token | pass |
| The manifest declares `hardware_access: none` and an empty runtime | pass |
| The document set and status vocabulary match the organization standard | pass |

## 5. Evidence

- [evidence/20261127_scaffold/README.md](../evidence/20261127_scaffold/README.md)
- `evidence/20261127_scaffold/gate.txt` — repository gate output
- `evidence/20261127_scaffold/pytest.txt` — test output
- [ACCEPTANCE.md](../ACCEPTANCE.md) — L0/L1 gate results and limitations

## 6. Open questions carried forward

| Question | Owner | Target |
|---|---|---|
| Wrist Aurora 930 vendor identity and registration | device library | M2 |
| PiPER X datasheet review and joint-limit confirmation | device library | M2 |
| Whether capability matching needs a `jcheng-interfaces` schema | interfaces + devices | M2 |
| Adapter protocol shape and mock semantics | devices + system | M3 |
| Asset provenance and licensing for URDF/meshes | licensing review | M2 |

## 7. Review checklist

- [ ] No profile claims `verified` without evidence and a date.
- [ ] No unverified parameter is stated as a fact.
- [ ] No prohibited import, device token or motion token is present.
- [ ] Every capability reference resolves and matches the device category.
- [ ] Every path is relative and stays inside `registry/`.
- [ ] The changelog and roadmap match the delivered scope.

## 8. Related

- [README](../README.md)
- [ROADMAP](../ROADMAP.md)
- [ACCEPTANCE](../ACCEPTANCE.md)
- [Architecture](ARCHITECTURE.md)
- [Safety model](SAFETY_MODEL.md)
