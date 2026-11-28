# Device source of truth

> Status: **Experimental** as of 2026-11-28, repository version 0.1.0.
> Scope: the offline MIG-01 device declaration source. This document adds no
> runtime interface, no hardware access and no `jcheng-interfaces` contract.

`jcheng-devices` owns the **declarative** device source of truth: the stable
device id, the profile version, the declared capabilities and the catalog joint
limits. `jcheng-system` keeps the **deployed** robot instance and the system
safety overlay. Consumers read a generated snapshot file; they never import
this package or call the device library at runtime.

## 1. Authority model

```text
jcheng-devices registry (declaration truth)
  device_id + device_version + content_hash + capability declarations
        |
        |  generated snapshot file (offline, read-only)
        v
jcheng-system deployment instance + safety overlay (runtime truth)
        |
        +--> system motion, lease and stop authority
        +--> simulation plant configuration
        +--> learning adapter and studio display
        +--> applications capability matching
```

| Fact | Declared by | Runtime authority |
|---|---|---|
| Device id, profile version, capability ids and parameters | `jcheng-devices` | consumer copies the pinned values |
| Catalog joint names, roles and degree limits | `jcheng-devices` | `jcheng-system` `robot-profile.v1` for a deployed robot |
| Servo ids, direction, measured pulses, table plane, motion profiles | not in a device profile | `jcheng-system` |
| Safety overlay (tightened limits and joint-space workspace) | authored by `jcheng-system` | `jcheng-system` |
| Deployment snapshot | generated from `jcheng-devices` | read-only artifact |

Rules:

1. **`jcheng-devices` is the declaration source of truth.** It never opens a
   device, publishes motion, holds a lease or joins a runtime graph.
2. **`jcheng-system` keeps the deployed instance and the safety overlay.** The
   per-robot `robot-profile.v1` remains the runtime authority for servo mapping,
   measured limits, workspace, table plane and motion profiles.
3. **No online dependency.** A consumer reads a file and validates the pinned
   `content_hash`; it does not require this repository or its Python package to
   be installed.
4. **A mismatch is a release blocker.** Overlapping values must agree after the
   safety overlay is applied. They are never reconciled by a silent preference.
5. **No default deployable.** A missing, unknown or incompatible capability is
   an error. Only an explicit, complete requirement set can produce a
   deployable result.

## 2. Identity and content hash

| Field | Meaning |
|---|---|
| `device_id` | Stable registry id, for example `hiwonder.armpi-ultra` |
| `device_version` | The profile's `profile_version`, `MAJOR.MINOR.PATCH` |
| `source_hash` | `sha256:<64 lower-case hex>` over canonical YAML profile content |
| `source_path` | Registry-relative source file, for example `registry/devices/hiwonder.armpi-ultra.yaml` |

Canonical YAML is:

- mapping keys sorted at every level;
- encoded as UTF-8;
- rendered without a generated timestamp, file path or comment;
- independent of key order, comments and incidental formatting.

Changing a value changes the hash; reformatting a file does not. The hash is
the **content identity**, not a hash of the bytes on disk. It is computed from
the parsed profile, not from a timestamped export.

```bash
# The same command a consumer can use to verify a pinned snapshot.
python3 -c 'from jcheng_devices.hashing import content_hash; print(content_hash("registry/devices/hiwonder.armpi-ultra.yaml"))'
```

The content hash is repository-local data. It is not a `jcheng-interfaces`
contract until a reviewed proposal is accepted.

## 3. Deployment snapshot

A snapshot is a deterministic, read-only projection of one device profile and
its capability declarations. The format is `jcheng.device_snapshot.v1`:

| Field | Content |
|---|---|
| `schema` | `jcheng.device_snapshot.v1` |
| `source_device` | Device id |
| `device_version` | Source `profile_version` |
| `source_hash` | Content hash of the source profile |
| `content_hash` | Canonical self-hash of the snapshot document (excludes `content_hash`) |
| `generated_by` | `jcheng-devices <version>` |
| `source_path` | Registry-relative source path |
| `capabilities` | `[{id, parameters, feedback}]`, sorted by id |
| `joints` | `[{name, role, limits}]` in profile order |
| `attributes` | `{category, role, dof, control_modes, kinematics_declared}`; `dof` is null when undeclared |
| `safety_overlay` | `{applied, source, content_hash, stricter_wins}` |
| `notes` | Source notes, plus an overlay sentence when an overlay was applied |

Example (abbreviated):

```yaml
schema: jcheng.device_snapshot.v1
source_device: hiwonder.armpi-ultra
device_version: 0.1.0
source_hash: sha256:f3c0c1b5373066599e46f85a63055a7a0cd3cd53f96c939bd4e101413551aeb9
content_hash: sha256:602e211ed6be27823154c1cd7ac06a97af9db95c45c844531408cfc0f729dbeb
generated_by: jcheng-devices 0.1.0
source_path: registry/devices/hiwonder.armpi-ultra.yaml
capabilities:
  - id: arm.joint_feedback
    parameters:
      - {name: joint_names, type: list, required: true}
    feedback:
      - {name: position_deg, type: list, unit: deg}
  - id: arm.position_control
    parameters:
      - {name: joint_names, type: list, required: true}
      - {name: target_deg, type: list, required: true}
      - {name: duration_s, type: duration, required: false}
    feedback:
      - {name: position_deg, type: list, unit: deg}
joints:
  - name: joint1
    role: shoulder_pan
    limits: {min_deg: -103.2, max_deg: 103.2}
safety_overlay:
  applied: false
  source: null
  content_hash: null
  stricter_wins: true
notes: >
  The gripper is registered separately as hiwonder.armpi-ultra-gripper.
```

Deterministic ordering:

- top-level fields use the order above;
- capabilities are sorted by capability id;
- joints keep the profile order, because that order defines the target vector;
- parameter and feedback entries keep the capability profile order;
- paths are registry-relative POSIX paths.

**No timestamp is embedded.** A timestamp would make two snapshots of identical
content differ. Provenance is carried by `source_hash`, `content_hash`, `device_version`,
`generated_by` and the source path; the consumer records the repository commit
and date in its own evidence. This is a deliberate deviation from the Phase 2
design draft, which listed a timestamp.

Generate a snapshot:

```bash
jcheng-devices snapshot hiwonder.armpi-ultra --output /tmp/armpi-ultra.snapshot.yaml
jcheng-devices snapshot hiwonder.armpi-ultra --json
jcheng-devices snapshot hiwonder.armpi-ultra --overlay /path/to/overlay.yaml
```

### File-only consumption

The snapshot is data, not an API:

- it is plain YAML or JSON and is parsed with a standard YAML/JSON reader;
- the consumer does not import `jcheng_devices`, open a device or join a graph;
- the consumer checks `schema`, `source_device`, `device_version` and
  `source_hash` against its pinned reference and recomputes `content_hash`;
- a missing, unknown or mismatched value is rejected, never replaced by a
  default profile.

An applications reference harness can therefore consume a snapshot as a pinned
fixture: read the file, record its provenance and run its own offline plan or
capability check. The file format is repository-local; it becomes a contract
only through a reviewed `jcheng-interfaces` proposal.

## 4. Safety overlay

The system layer owns the safety overlay. This repository validates an overlay
and records it in the snapshot; it never activates one at runtime.

Format `jcheng.device_safety_overlay.v1`:

```yaml
schema: jcheng.device_safety_overlay.v1
source: jcheng-system/configs/robots/armpi_ultra/profile.yaml
joint_limits:
  joint1: {min_deg: -100.0, max_deg: 100.0}
workspace:
  min_deg: [-90.0, -30.0, -90.0, -80.0, -80.0]
  max_deg: [90.0, 60.0, 0.0, 80.0, 80.0]
notes: Narrowed for the current cell.
```

Rules:

1. `joint_limits` may provide `min_deg`, `max_deg` or both for a named joint.
2. `workspace` is a **joint-space envelope**, one value per snapshot joint in
   snapshot order. A Cartesian workspace envelope is not machine-checkable from
   the current device profiles and is rejected as an unknown field.
3. Every provided bound must lie inside the declared device bound. A bound that
   exceeds the device bound is `OVERLAY_LOOSENS_LIMIT` or
   `OVERLAY_LOOSENS_WORKSPACE`.
4. The effective limit is the intersection of the device bound, the per-joint
   override and the workspace box. **The stricter bound wins**; the snapshot
   records `stricter_wins: true`.
5. An unknown joint, an unknown field, a wrong schema, a missing source, an
   empty overlay or an empty tightened range is an explicit error. The CLI
   exits `1` and writes no snapshot.
6. `content_hash` is the canonical hash of the overlay data. It is recorded in
   `safety_overlay.content_hash` together with the overlay `source`.

The snapshot with an overlay is still a declaration-shaped artifact. It does
not replace the system robot profile, and it grants no motion authority.

## 5. Compatibility

A requirement set is `jcheng.device_requirements.v1`:

```yaml
schema: jcheng.device_requirements.v1
device: hiwonder.armpi-ultra
device_version: 0.1.0
source_hash: sha256:f3c0c1b5373066599e46f85a63055a7a0cd3cd53f96c939bd4e101413551aeb9
capabilities:
  - id: arm.position_control
    required: true
    parameters:
      joint_names: [joint1, joint2, joint3, joint4, joint5]
  - id: sensor.depth_stream
    required: false
notes: Offline reference requirement.
```

Matching rules:

1. `device`, `device_version` and `source_hash` are optional exact pins. A
   mismatch is `DEVICE_ID_MISMATCH`, `DEVICE_VERSION_MISMATCH` or
   `SOURCE_HASH_MISMATCH`.
2. A capability requirement is required unless it explicitly says
   `required: false`. There is no default "assume deployable".
3. A required capability that the snapshot does not declare is reported as both
   `UNKNOWN_CAPABILITY` and `MISSING_REQUIRED_CAPABILITY`.
4. An absent optional capability is a `MISSING_OPTIONAL_CAPABILITY` warning.
5. A requirement parameter that the capability does not declare, or whose value
   does not match the declared type, is `INCOMPATIBLE_PARAMETER`.
6. A requirements set with no required capability is
   `NO_REQUIRED_CAPABILITY` and is not deployable.
7. `deployable` is true only when there is no error and every required
   capability is `satisfied`. Warnings do not make a result deployable on their
   own; an absent required capability always prevents it.

Run the matcher:

```bash
jcheng-devices compatibility \
  --requirements /tmp/armpi-requirements.yaml \
  --snapshot /tmp/armpi-ultra.snapshot.yaml \
  --json
```

Exit codes: `0` deployable, `1` not deployable or an invalid requirement /
snapshot, `2` the snapshot or requirements file cannot be read.

The report is `jcheng.device_compatibility.v1` with `ok`, `deployable`,
`errors`, `warnings` and one row per capability (`satisfied`, `missing` or
`incompatible`). A report is evidence of a declaration match only; it is not a
hardware validation or a safety certification.

### Error codes

| Code | Meaning |
|---|---|
| `UNKNOWN_CAPABILITY` | The snapshot does not declare the requested capability |
| `MISSING_REQUIRED_CAPABILITY` | A required capability is absent |
| `MISSING_OPTIONAL_CAPABILITY` | Warning: an optional capability is absent |
| `INCOMPATIBLE_PARAMETER` | A parameter name or value type does not match the declaration |
| `DEVICE_ID_MISMATCH` | The pinned device id differs from the snapshot |
| `DEVICE_VERSION_MISMATCH` | The pinned version differs from the snapshot |
| `CONTENT_HASH_MISMATCH` | The pinned content hash differs from the snapshot |
| `NO_REQUIRED_CAPABILITY` | The requirements declare no required capability |
| `INVALID_REQUIREMENTS` | The requirements document is malformed |
| `INVALID_SNAPSHOT` | The snapshot document is malformed |
| `SNAPSHOT_SCHEMA_MISMATCH` | The snapshot is not `jcheng.device_snapshot.v1` |
| `OVERLAY_LOOSENS_LIMIT` | A joint limit is outside the declared device range |
| `OVERLAY_LOOSENS_WORKSPACE` | A workspace bound is outside the declared device range |
| `OVERLAY_UNKNOWN_JOINT` | The overlay names a joint the device does not declare |
| `OVERLAY_UNKNOWN_FIELD` | The overlay has an unknown section |
| `OVERLAY_EMPTY` | The overlay narrows nothing |
| `OVERLAY_EMPTY_RANGE` | The tightened range is empty |

## 6. Non-goals

- No device access, driver, bus, firmware, calibration session or motion path.
- No runtime node, topic, service, action, endpoint or graph participation.
- No activation of a safety overlay; the system layer owns its deployment.
- No contract or JSON Schema promotion; the snapshot and requirements formats
  are repository-local data documents.
- No deletion or rewrite of the existing profiles, schemas or registry
  semantics. The old profiles remain until equivalence is proven.
- No timestamp inside a snapshot; provenance is content hash plus generator
  version and consumer-recorded commit.
- No Cartesian workspace claim. Device profiles do not measure one, so an
  overlay cannot prove a Cartesian bound.
- No new third-party dependency and no online lookup.

## 7. Related

- [Architecture](ARCHITECTURE.md)
- [Profile schemas](PROFILE_SCHEMA.md)
- [Integration boundary](INTEGRATION.md)
- [Device registry rules](DEVICE_REGISTRY.md)
- [Safety model](SAFETY_MODEL.md)
- [ArmPi Ultra profile](../registry/devices/hiwonder.armpi-ultra.yaml)
- [Phase 2 design](https://github.com/JCHENG-Robotics/.github/blob/main/docs/boundary-consolidation/24-phase2-source-of-truth-design.md)
- [`jcheng-interfaces`](https://github.com/JCHENG-Robotics/jcheng-interfaces)
- [`jcheng-system`](https://github.com/JCHENG-Robotics/jcheng-system)
