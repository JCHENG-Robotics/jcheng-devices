# Profile schemas

> Status: **Experimental** as of 2026-11-27, v0.1.0.
> The schemas are repository-local. They are not ecosystem contracts until a
> reviewed proposal is accepted in `jcheng-interfaces`.

Two schema files describe the registry:

| Schema | File | Purpose |
|---|---|---|
| `jcheng.device-profile.v1` | `src/jcheng_devices/schemas/device-profile.v1.schema.json` | one physical device |
| `jcheng.capability-profile.v1` | `src/jcheng_devices/schemas/capability-profile.v1.schema.json` | what a device class can do |

Both use JSON Schema draft 2020-12 and reject unknown properties. Schema
validation runs before any semantic check.

## 1. Device profile

Required common fields:

| Field | Type | Rule |
|---|---|---|
| `schema_version` | integer | `1` |
| `kind` | string | `device-profile` |
| `id` | string | `<vendor>.<slug>`, unique |
| `display_name` | string | 1–120 characters |
| `category` | enum | `arm`, `mobile_base`, `end_effector`, `sensor`, `teleop_device` |
| `status` | enum | `reference`, `candidate`, `planned` |
| `description` | string | at least 10 characters |
| `profile_version` | string | `MAJOR.MINOR.PATCH` |
| `vendor` | object | `name`, `product`, `source`, `verification`; `url` optional |
| `verification` | object | `status`, `evidence`, `date`, `notes` |
| `hardware` | object | `interfaces` required; `compute`, `bus`, `power`, `notes` optional |
| `capabilities` | array | at least one registered capability id |

Category-specific block, enforced by `if/then`:

| Category | Required block | Key fields |
|---|---|---|
| `arm` | `kinematics` | `dof`, `joints`, `control_modes`, `feedback`, `workspace` |
| `mobile_base` | `chassis` | `drive_type`, `wheel_count`, `source`, `verified`; speed limits optional |
| `end_effector` | `end_effector` | `kind`, `source`, `verified`; stroke, canonical range and pulse range optional |
| `sensor` | `sensor` | `sensor_type`, `model`, `interface`, `source`, `verified`; rate, range and field of view optional |
| `teleop_device` | `teleop` | `device_type`, `interface`, `source`, `verified` |

Optional `assets` maps `urdf`, `xacro`, `calibration` and `simulation` to
repository-relative paths. Absolute paths and `..` are rejected by the schema.
v0.1.0 registers no asset; see [ASSET_LAYOUT.md](ASSET_LAYOUT.md).

## 2. Joint convention

- Joint limits are stored in **degrees** (`limits.min_deg`, `limits.max_deg`).
  Profiles are human-maintained description data; degrees keep review readable.
- Cross-repository contracts express radians. Conversion belongs to the
  adapter/contract layer, not to the profile reader.
- Every joint carries `source` and `verified`. A value copied from another
  repository keeps `verified: false` until it is checked against the device.
- Raw servo pulses are **not** a joint unit. The only pulse field is
  `end_effector.pulse_range`, recorded as a hardware mapping fact and never as
  an ecosystem contract.
- `dof` must equal the number of joints; names are unique; a movable joint has
  a non-zero range; `min_deg < max_deg`.

## 3. Capability profile

| Field | Type | Rule |
|---|---|---|
| `schema_version` | integer | `1` |
| `kind` | string | `capability-profile` |
| `id` | string | `<domain>.<capability>` |
| `display_name` | string | 1–120 characters |
| `category` | enum | same five categories |
| `description` | string | at least 10 characters |
| `parameters` | array | `name`, `type`, `description`, `required`; `unit` optional |
| `feedback` | array | `name`, `type`, `description`; `unit` and `rate_hz` optional |
| `constraints` | array | at least one binding statement |
| `requires` | array | optional capability ids; must resolve |
| `verification` | object | same verification shape |

A capability profile is a **description**, never an execution API:

- it defines no topic, service, action, endpoint or transport;
- it grants no lease and no authority;
- it cannot override a device profile limit;
- its constraints must state the execution boundary, for example that execution
  is requested through `jcheng-system`.

## 4. Verification markers

| Status | Evidence | Date | Notes |
|---|---|---|---|
| `verified` | at least one link | required | what was measured |
| `partially_verified` | at least one link | required | what remains open |
| `unverified` | may be empty | may be empty | required: what is unknown and why |

The validator rejects an inconsistent combination. A profile with status
`verified` cannot point at an empty evidence list, and an `unverified` profile
cannot omit its explanation. Evidence is a repository path or an absolute URL;
it is not prose.

## 5. Checks beyond JSON Schema

`Registry.load()` additionally enforces:

1. registry ids are unique and match their file names;
2. paths stay inside `registry/`;
3. `kind` and `id` agree with the index entry;
4. every device capability exists and has the same category;
5. `requires` targets exist and a capability does not require itself;
6. `dof` matches the joint count, names are unique and ranges are ordered;
7. `profile_version` is semantic;
8. descriptions and verification notes are non-empty where required.

## 6. Relationship to `robot-profile.v1`

`jcheng-interfaces` already owns `robot-profile.v1`, and `jcheng-system` keeps
one instance per robot in `configs/robots/<robot>/profile.yaml`. The two
profile kinds answer different questions and must not be merged:

| Question | `robot-profile.v1` (interfaces + system) | `device-profile.v1` (this repository) |
|---|---|---|
| What is it for? | deploy and run one robot instance | describe a device model and its capabilities |
| Owner | system layer and deployment | device library |
| Joint limits | authoritative runtime values in radians | catalog values in degrees, cited from the system profile |
| Servo mapping, direction, measured pulses | present | absent |
| Workspace, table plane, named motion profiles | present | workspace only as an unmeasured description |
| Capabilities and verification | not described | required |
| Consumers | safety, MoveIt, gateway, arbitration | planning, capability matching, simulation configuration |

Rules:

- The system robot profile remains the **runtime authority** for a deployed
  robot. A device profile never replaces it and is never copied into runtime
  configuration.
- Overlapping values (joint names and ranges) must be reconciled, not
  duplicated silently. M2 adds a compatibility check that fails on a mismatch.
- Fields that only make sense for an instance (servo id, direction, measured
  pulses, table plane, motion profiles, source hashes) stay out of a device
  profile.
- Fields that describe a device model (vendor, category, joint roles,
  capabilities, verification) stay out of the system robot profile.

## 7. Schema change policy

- Additive, backward-compatible fields may land in `v1` with a
  `profile_version` bump.
- A breaking change creates `device-profile.v2` / `capability-profile.v2` and
  a migration note in the changelog. A v1 file is never silently reinterpreted.
- Promoting a profile schema to `jcheng-interfaces` requires a contract review,
  a schema review and a versioned tag. Until then, no other repository may
  depend on these files as a contract.

## 8. Related

- [README](../README.md)
- [Device registry rules](DEVICE_REGISTRY.md)
- [Asset layout](ASSET_LAYOUT.md)
- [Safety model](SAFETY_MODEL.md)
- [`jcheng-interfaces`](https://github.com/JCHENG-Robotics/jcheng-interfaces)
