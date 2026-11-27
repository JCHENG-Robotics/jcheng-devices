# Device registry rules

> Status: **Experimental** as of 2026-11-27, v0.1.0.
> These rules define identity, category, status and verification for every
> registered profile.

## 1. Identifier convention

Every device uses `<vendor>.<slug>`:

- lower-case ASCII;
- one dot separates the vendor namespace from the device slug;
- the vendor namespace is the legal or commonly used vendor name, not a
  product line;
- the slug is stable, hyphenated and does not encode a firmware version;
- the id never changes when a profile is revised. A different physical device
  family gets a new id.

Examples:

| Id | Meaning |
|---|---|
| `hiwonder.armpi-ultra` | Hiwonder ArmPi Ultra arm |
| `hiwonder.armpi-ultra-gripper` | the gripper bundled with that arm |
| `intel.realsense-d435i` | Intel RealSense D435i |
| `lslidar.m10` | LSLIDAR M10 |
| `agilex.piper-x` | AgileX PiPER X |

The file name must equal the id: `registry/devices/<id>.yaml`. Capability ids
use `<domain>.<capability>`, for example `arm.position_control`, and live in
`registry/capabilities/<id>.yaml`.

An id is unique across both sections. Registering the same id twice, or using a
device id for a capability, fails validation.

## 2. Categories

| Category | Meaning | Populated in v0.1.0 |
|---|---|---|
| `arm` | serial manipulator | ArmPi Ultra, PiPER X |
| `mobile_base` | wheeled or tracked base | ArmPi Ultra chassis |
| `end_effector` | gripper or tool | ArmPi Ultra gripper |
| `sensor` | camera, LiDAR, IMU, force sensor | D435i, M10 |
| `teleop_device` | operator input device | reserved, no profile |

The `teleop_device` category is reserved for the teleoperation input boundary.
It stays empty until the operator-side adapter exists and an input device is
actually registered; a reserved category is not a claim that a device exists.

## 3. Status values

| Status | Meaning |
|---|---|
| `reference` | in use on a reference robot and maintained |
| `candidate` | under evaluation; no adoption decision |
| `planned` | interface reserved; the device is not connected |

Status is independent of verification. A `reference` device can still have
`unverified` parameters, and the profile must say which ones.

## 4. Registration procedure

1. Choose the id and confirm it is not already registered.
2. Create `registry/devices/<id>.yaml` from an existing profile of the same
   category.
3. Fill every claimed value from a named source. If no source exists, omit the
   value and explain the gap in `verification.notes`.
4. Set `verification.status` honestly:
   - `verified`: evidence and date are mandatory;
   - `partially_verified`: evidence and date are mandatory, and the notes say
     what remains open;
   - `unverified`: notes are mandatory.
5. Reference only capability profiles whose `category` matches the device.
6. Add the entry to `registry/registry.yaml`; there is no auto-discovery.
7. Run `jcheng-devices validate` and `python3 -m pytest -q tests`.

A profile without a capability reference is invalid. A capability without a
constraint statement is invalid.

## 5. File and path rules

- All paths in the index are relative to `registry/`.
- Absolute paths and `..` escapes are rejected before the file is read.
- One profile per file. YAML anchors across files are not used.
- Comments may explain provenance, but they are not validation input.
- No device asset, recording, model weight or binary mesh enters the registry.
  Asset placement is defined in [ASSET_LAYOUT.md](ASSET_LAYOUT.md).

## 6. Devices that are deliberately not registered

| Device | Why not |
|---|---|
| Wrist Aurora 930 camera | The in-tree documentation records the model and calibration, but not a confirmed vendor identity. Registering it under a guessed vendor would violate the no-fabrication rule; it is added when the vendor is confirmed. |
| PiPER X gripper | The arm is a candidate; the prismatic gripper is described in the learning adapter profile and becomes a separate end-effector profile only when the device is adopted. |
| Vendor bus servo controller | It is an internal component of the ArmPi arm, not an independently addressable device in the ecosystem. The arm profile carries the bus description. |

## 7. Change control

- A new device or a status change is a profile change plus a registry change in
  the same pull request.
- Moving a profile to `reference` requires a recorded source review; moving it
  to `verified` requires per-parameter evidence.
- Removing a device keeps its history in git. A deprecated profile is marked in
  its notes before removal; the changelog records the removal.
- Renaming an id is a breaking change. Register the new id and retire the old
  one explicitly; never silently rewrite references.

## 8. Related

- [README](../README.md)
- [Profile schemas](PROFILE_SCHEMA.md)
- [Asset layout](ASSET_LAYOUT.md)
- [Safety model](SAFETY_MODEL.md)
- [Registry index](../registry/registry.yaml)
