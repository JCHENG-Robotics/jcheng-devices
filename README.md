# jcheng-devices

**English** | [简体中文](README.zh-CN.md)

`jcheng-devices` is the L3 device library of the JCHENG Robotics ecosystem: one
explicit registry of declarative device and capability profiles, plus an
offline validator that checks identity, schema, cross-references and
verification markers. It describes devices; it never opens one, joins a
runtime graph, commands motion or bypasses `jcheng-system`.

> Status: **Experimental** as of 2026-11-27. Version 0.1.0. Offline validation
> only: no device has been opened by this repository and no profile is
> hardware-verified.
> English canonical; the Chinese README is a translation.

## Scope and boundary

| Item | This repository |
|---|---|
| Layer | L3 |
| Inputs | `registry/registry.yaml`; device and capability profile YAML; two bundled JSON schemas |
| Outputs | validated profile data, deterministic listings, a registry digest |
| Hardware access | `none` (`capability.yaml`) |
| Owned devices | none — device I/O stays with `jcheng-system` |
| Forbidden | device access, runtime-graph participation, motion or lease authority, vendor code, an independent control channel |

What v0.1.0 provides:

- A device registry with six profiles: the ArmPi Ultra arm, gripper and
  chassis, the front D435i camera, the planned M10 LiDAR and the PiPER X
  candidate.
- Seven device capability profiles covering arm position control and feedback,
  gripper position control, chassis velocity intent, and RGB, depth and laser
  scan streams.
- `device-profile.v1` and `capability-profile.v1` JSON Schemas, an offline
  validator, a four-command CLI and a fail-closed repository gate.
- An asset organisation standard for URDF/Xacro, calibration, hardware
  configuration and simulation assets. No asset is copied in v0.1.0.

What it deliberately does not do:

- It opens no serial, USB, CAN, GPIO or video device.
- It publishes and subscribes to nothing and starts no runtime node.
- It defines no command path and holds no lease. The system layer remains the
  only origin of motion.
- It does not copy vendor code, vendor meshes or measurement data.
- It does not guess an unverified parameter. Unverified values are marked, or
  absent.

Device profiles describe device models and capabilities. The per-robot
`robot-profile.v1` in `jcheng-system` remains the runtime authority for servo
mapping, joint limits, workspace and table plane; this repository never
replaces or exports runtime configuration.

## Repository layout

```text
jcheng-devices/
├── capability.yaml
├── VERSION
├── README.md / README.zh-CN.md
├── ROADMAP.md / CHANGELOG.md / ACCEPTANCE.md
├── SCHEMA_OWNERSHIP.md        # schema owner, status, consumers, promotion triggers
├── registry/
│   ├── registry.yaml          # explicit index
│   ├── devices/               # six device profiles
│   └── capabilities/          # seven capability profiles
├── src/jcheng_devices/
│   ├── schemas/               # device-profile.v1, capability-profile.v1
│   ├── registry.py            # loading and cross-reference checks
│   └── cli.py                 # list / show / validate / digest
├── tests/
├── docs/
├── assets/                    # layout only; no asset committed
├── scripts/check_repo_gate.sh
└── evidence/
```

## Requirements

- Python 3.10 or newer (the host toolchain is tested on 3.12).
- `PyYAML==6.0.2` and `jsonschema==4.26.0`; `pytest==8.3.4` for the tests.
- No ROS distribution and no robot are required.
- No hardware access is used at any point.

## Quick start

```bash
python3 -m pip install -e '.[test]'

# Validate the registry and every profile.
jcheng-devices validate

# Inspect the registry.
jcheng-devices list
jcheng-devices show hiwonder.armpi-ultra --json
jcheng-devices digest

# Run the tests and the repository gate without installing the package.
python3 -m pytest -q tests
bash scripts/check_repo_gate.sh
```

`validate` exits `0` only when every profile loads, matches its schema, resolves
its capability references and carries a consistent verification statement. It
exits `1` on any issue and `2` when the registry cannot be read at all.

## Validation status

| Claim | Status | Evidence |
|---|---|---|
| Registry, schemas, CLI and cross-reference checks validate offline | Verified (L0/L1, 2026-11-27) | [evidence/20261127_scaffold/](evidence/20261127_scaffold/README.md) |
| ArmPi Ultra reference device facts | Partially verified (2026-11-25) | `registry/devices/hiwonder.armpi-ultra.yaml`; system acceptance and safety documents |
| PiPER X candidate profile | Unverified | `registry/devices/agilex.piper-x.yaml`; no hardware present |
| M10 LiDAR planned profile | Unverified | `registry/devices/lslidar.m10.yaml`; device not connected |
| Any profile parameter measured on hardware by this repository | Unverified | No hardware session; no measurement recorded here |

Full report: [ACCEPTANCE.md](ACCEPTANCE.md).

## Related repositories

- [`jcheng-interfaces`](https://github.com/JCHENG-Robotics/jcheng-interfaces) — contract source, schemas and contract hash.
- [`jcheng-system`](https://github.com/JCHENG-Robotics/jcheng-system) — privileged runtime; sole owner of hardware I/O and motion.
- [`jcheng-simulation`](https://github.com/JCHENG-Robotics/jcheng-simulation) — offline plant on domain 43; future consumer of device profiles.
- [`jcheng-learning`](https://github.com/JCHENG-Robotics/jcheng-learning) — robot adapter profiles; this repository does not replace them.
- [`jcheng-perception`](https://github.com/JCHENG-Robotics/jcheng-perception) — camera deployment and calibration evidence.
- [`jcheng-mobile`](https://github.com/JCHENG-Robotics/jcheng-mobile) — chassis intent and LiDAR interface expectations.
- [`jcheng-teleop`](https://github.com/JCHENG-Robotics/jcheng-teleop) — future teleoperation-device category consumer.
- [`jcheng-ops`](https://github.com/JCHENG-Robotics/jcheng-ops) — unattended health and watchdogs.
- [`.github`](https://github.com/JCHENG-Robotics/.github) — taxonomy, documentation standard, ecosystem roadmap and the [boundary specification](https://github.com/JCHENG-Robotics/.github/blob/main/docs/repo-boundaries.md).

## License

Pending third-party and copyright review; no `LICENSE` file has been added.
See [LICENSE-REVIEW.md](LICENSE-REVIEW.md).
