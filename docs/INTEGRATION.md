# Integration boundary

> Status: **Experimental** as of 2026-11-27, v0.1.0.
> There is no runtime interface in v0.1.0. This document records who may consume
> device profiles and under which conditions.

## 1. Boundary table

| Repository | Relationship | Allowed | Forbidden |
|---|---|---|---|
| `jcheng-interfaces` | contract source | pin version and hash; propose schemas; `robot-profile.v1` stays the deployment contract | redefining a contract or the robot profile here |
| `jcheng-system` | hardware and motion owner; robot-profile runtime authority | cite or compare profile data | opening a device, publishing motion, holding a lease, replacing `robot-profile.v1` |
| `jcheng-simulation` | future consumer | read profiles to build the domain-43 plant | joining domains 0/41/42, driving hardware |
| `jcheng-learning` | description overlap | reference device identity | replacing robot-adapter profiles or duplicating datasets |
| `jcheng-perception` | evidence source | cite camera deployment and calibration evidence | opening a camera or redefining calibration |
| `jcheng-mobile` | evidence source | cite chassis and LiDAR interface expectations | publishing chassis intent or owning a driver |
| `jcheng-teleop` | future consumer | register teleoperation devices in the reserved category | becoming an input adapter or motion source |
| `jcheng-ops` | observer | read the registry and digest | writing profiles or touching hardware |

## 2. No runtime interface in v0.1.0

- No topic, service, action, HTTP endpoint or WebSocket message is produced.
- No ROS distribution is imported. The package runs on a plain Python host.
- No DDS domain is joined. The manifest declares an empty runtime surface.
- No device node, bus or vendor SDK is opened.

The only integration surfaces are files:

1. `registry/registry.yaml` and the profiles it indexes;
2. the two JSON Schemas;
3. the CLI and its deterministic JSON output;
4. the registry digest.

## 3. Contract ownership

Cross-repository contracts live only in `jcheng-interfaces`. The device and
capability profile schemas are repository-local descriptions in v0.1.0. They
become contracts only through a reviewed proposal:

1. open a proposal in `jcheng-interfaces` with the schema, compatibility rules
   and migration path;
2. get owner review from the system and capability layers;
3. tag a contract version and update the pinned hash here.

Until then, no other repository may parse or depend on these files as a
contract. Citing a profile in documentation is not a contract dependency.

### 3.1 Deployment profile versus device profile

`jcheng-system` keeps one `robot-profile.v1` instance per robot in
`configs/robots/<robot>/profile.yaml` (servo ids, radians, direction, measured
pulses, workspace, table plane, motion profiles). That file is the runtime
authority for a deployed robot.

A device profile describes the device model and its capabilities for planning,
capability matching and simulation configuration. It never replaces the system
profile and is never exported as runtime configuration. Overlapping joint
ranges are reconciled by the M2 compatibility check; a mismatch is an error,
not a silent preference.

## 4. Future adapter boundary (v0.3.x)

An adapter is a reviewed boundary, not a second control path:

- it reads a validated profile and exposes a deterministic, in-memory mock;
- it has no device handle and no network access;
- it does not publish motion, hold a lease or bypass the system arbiter;
- execution is requested only through `jcheng-system`, which remains the sole
  origin of motion.

The adapter protocol is proposed to `jcheng-interfaces` before any code lands.
The mock is tested offline; it is never reported as hardware evidence.

## 5. Controlled integration (v0.4.x)

Integration with `jcheng-system` and `jcheng-simulation` requires all of:

1. an accepted adapter contract with a tagged version;
2. a profile digest pinned by the consumer;
3. a simulation check on domain 43;
4. a plan-only system path with no motion;
5. a separate, explicit authorization for any later hardware session.

A failed bound stays failed. A simulated result is never reported as a hardware
result.

## 6. Failure semantics

| Condition | Behaviour |
|---|---|
| Unknown or duplicate id | validation error; CI fails |
| Schema violation | validation error; no consumer sees the profile |
| Unresolved capability reference | validation error |
| Category mismatch | validation error |
| `verified` without evidence or date | validation error |
| `unverified` without an explanation | validation error |
| Missing profile file | validation error on that registry entry |
| Unreadable registry index | fatal load error, exit 2 |
| Path escape | rejected before the file is read |

Consumers must fail closed: an invalid or missing profile is never replaced by
a default device description.

## 7. Related

- [README](../README.md)
- [Architecture](ARCHITECTURE.md)
- [Safety model](SAFETY_MODEL.md)
- [Profile schemas](PROFILE_SCHEMA.md)
- [`jcheng-interfaces`](https://github.com/JCHENG-Robotics/jcheng-interfaces)
- [`jcheng-system`](https://github.com/JCHENG-Robotics/jcheng-system)
