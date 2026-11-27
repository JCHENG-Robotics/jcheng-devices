# Asset layout

> Status: **Experimental** as of 2026-11-27, v0.1.0.
> This document defines where device assets belong. No URDF, Xacro, calibration
> file or simulation asset is committed in v0.1.0.

## 1. Planned layout

```text
assets/
├── README.md
├── urdf/<vendor>.<device>/          # link and joint tree
├── xacro/<vendor>.<device>/         # parameterised description
├── calibration/<vendor>.<device>/   # measured intrinsics, extrinsics, hand-eye
├── hardware/<vendor>.<device>/      # wiring, bus map, udev rules, reviewed config
└── simulation/<vendor>.<device>/    # plant-side description for domain 43
```

`<vendor>.<device>` is the registry id. One directory per registered device.
A device that is not registered has no asset directory.

## 2. Naming

| Artifact | Pattern | Example |
|---|---|---|
| URDF | `<device>.urdf` | `armpi-ultra.urdf` |
| Xacro | `<device>.xacro` | `armpi-ultra.xacro` |
| Calibration | `calibration_<YYYYMMDD>.yaml` | `calibration_20261124.yaml` |
| Provenance | `provenance.yaml` | one per directory |
| Checksums | `SHA256SUMS` | one per directory |
| Simulation config | `sim_<device>.yaml` | `sim_armpi-ultra.yaml` |

Names are lower-case and hyphenated. A new measurement gets a new dated file;
an existing calibration file is never silently overwritten.

## 3. Provenance manifest

Every asset directory carries `provenance.yaml`:

```yaml
schema_version: 1
device: hiwonder.armpi-ultra
source:
  kind: vendor | measured | derived
  reference: "read-only vendor tree on the robot, or repository/commit, or session id"
  retrieved: "2026-11-27"
license: "pending review"
transformation: "none | diff summary | converter name and version"
sha256:
  armpi-ultra.urdf: "<sha256>"
reviewer: "pending"
```

Rules:

- The source is named precisely: a path, a repository and commit, or a session
  id. "The internet" is not a source.
- `transformation` records every modification. A vendor file is never edited in
  place and committed as if it were original.
- A vendor tree on the robot (for example `~/ArmPiUltra/`) is **read-only**.
  Assets are copied out and reviewed; the vendor tree is never modified.
- No asset enters the repository before the license review records its terms.

## 4. Text and binary assets

| Kind | Policy |
|---|---|
| URDF, Xacro, calibration YAML, simulation YAML | text; may be committed after review |
| STL, DAE, GLB, OBJ, textures | binary; stay outside the repository until an explicit review approves them |
| Recordings, point clouds, images, model weights | outside the repository; reference them by evidence path, never copy |
| Vendor source code | never copied; record a diff or a reference instead |

The repository gate rejects recordings, weights and common binary mesh formats.
A file over 5 MB is rejected before it enters history.

## 5. Calibration files

A calibration file is evidence, not configuration to be edited casually:

- it carries the date, method, residuals and the board or target used;
- it records whether the measurement used bus-measured joints or a command
  cache;
- a re-measurement produces a new dated file and a changelog entry;
- the device profile's `assets.calibration` points at the current accepted
  file only after review.

Camera intrinsics and hand-eye transforms stay in the owning capability
repository until they are explicitly registered here. This repository does not
redefine calibration that `jcheng-perception` or the frozen baseline already
owns.

## 6. Simulation assets

Simulation descriptions are derived from device profiles, not hand-written
duplicates:

- the plant is confined to domain 43;
- simulation assets never contain a hardware device node or a vendor SDK path;
- a simulation asset records the profile digest it was generated from;
- a mismatch between profile and simulation description fails the simulation
  check, rather than silently using stale geometry.

## 7. Registration and validation

In v0.1.0 the `assets` block exists in the device schema but no profile uses it.
From M2 the validator will:

1. require every referenced path to exist and stay inside the repository;
2. verify the `SHA256SUMS` entry;
3. require `provenance.yaml` with a non-pending license or an explicit
   `pending` marker that blocks release.

## 8. Related

- [README](../README.md)
- [Device registry rules](DEVICE_REGISTRY.md)
- [Profile schemas](PROFILE_SCHEMA.md)
- [Integration boundary](INTEGRATION.md)
- [`.github` hardware workflow](https://github.com/JCHENG-Robotics/.github/blob/main/docs/hardware-workflow.md)
