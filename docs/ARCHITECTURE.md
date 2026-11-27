# Architecture

> Status: **Experimental** as of 2026-11-27, v0.1.0.
> Scope: the offline device library. There is no runtime, no device access and
> no motion authority.

## 1. Position in the ecosystem

`jcheng-devices` is an L3 repository (`.github/docs/repo-taxonomy.md`). It
describes devices for every other layer; it does not participate in a runtime
graph.

```text
jcheng-interfaces (L1)      contracts, schemas, contract hash
        ^
        |  pinned range + hash (declarative in v0.1.0)
jcheng-devices (L3)         device profiles, capability profiles, validator
        |
        |  profile data (future: reviewed adapter contract, v0.3.x)
        v
jcheng-system (L2)          hardware I/O, leases, safety, motion
jcheng-simulation (SIM)     offline plant on domain 43
```

Device I/O belongs to `jcheng-system`'s hardware bridge and the vendor stack.
This repository has no device handle, no bus, no topic and no service.

## 2. Data flow

```text
registry/registry.yaml
        |
        +--> devices/<id>.yaml ------------+
        |                                  |
        +--> capabilities/<id>.yaml -------+--> Registry.load()
                                                   |
                         bundled JSON Schemas -----+
                                                   |
                                      +------------+------------+
                                      |                         |
                                 validate (exit 0/1)      list / show / digest
                                      |                         |
                                 CI + repository gate     deterministic JSON
```

`Registry.load()` is the only entry point. It reads the index, resolves each
registered path inside `registry/`, loads YAML, validates against the bundled
schema and then performs cross-reference checks. Nothing is imported from ROS,
vendor packages or the network.

## 3. Modules

| Path | Responsibility |
|---|---|
| `src/jcheng_devices/registry.py` | index loading, path safety, cross-reference and kinematics checks, digest |
| `src/jcheng_devices/validation.py` | JSON Schema validators for both profile kinds |
| `src/jcheng_devices/loading.py` | YAML loading and canonical JSON |
| `src/jcheng_devices/errors.py` | fatal load errors and validation issues |
| `src/jcheng_devices/cli.py` | `list`, `show`, `validate`, `digest` |
| `src/jcheng_devices/schemas/` | `device-profile.v1`, `capability-profile.v1` |
| `registry/` | the data under validation |

## 4. Invariants

1. **No runtime.** No module imports a robot stack, opens a device, starts a
   process or touches the network. A static test enforces the import boundary.
2. **One identifier, one profile.** `id` is unique across devices and
   capabilities; the file name equals the id; the path stays inside
   `registry/`.
3. **Schema before semantics.** A profile must satisfy its schema before the
   cross-reference checks run. A malformed profile is never partially accepted.
4. **Verification is explicit.** `verified` and `partially_verified` require
   evidence and a date. `unverified` requires a note explaining what is unknown.
   An absent value is preferable to a guessed one.
5. **Descriptions are not authority.** A capability profile states what a
   device can do. It defines no command channel, no lease and no execution
   path.
6. **Deterministic output.** JSON output and the registry digest are sorted and
   independent of file order, so CI can compare bytes.

## 5. Failure semantics

- The gate and `validate` fail closed: any issue means exit 1, and CI fails.
- A missing registry index is a fatal load error (exit 2); a missing profile
  file is a validation issue on that entry.
- A path that escapes `registry/` is rejected before the file is read.
- Duplicate ids are reported even when the first entry fails to load.
- Invalid YAML is reported against the registered id, never silently skipped.

## 6. Future adapter boundary (v0.3.x)

The roadmap introduces a device adapter contract and an in-memory mock. That
work is contract-first:

1. Propose the adapter protocol in `jcheng-interfaces`; do not invent a second
   contract inside this repository.
2. The adapter may read profiles and expose a deterministic mock. It may not
   open a device, publish motion or hold a lease.
3. Real execution remains with `jcheng-system`; this repository never becomes a
   motion source.

## 7. Non-goals

- Device drivers, vendor SDKs, firmware and bus configuration.
- Runtime nodes, topics, services, actions or gateways.
- Hardware calibration execution. Calibration files may be registered as
  assets, but the measurement happens outside this repository.
- Replacing the learning robot-adapter profiles or the simulation robot
  catalog. This repository supplies descriptions; consumers keep their own
  runtime contracts.

## 8. Related

- [README](../README.md)
- [Device registry rules](DEVICE_REGISTRY.md)
- [Profile schemas](PROFILE_SCHEMA.md)
- [Safety model](SAFETY_MODEL.md)
- [Integration boundary](INTEGRATION.md)
- [`.github` repository taxonomy](https://github.com/JCHENG-Robotics/.github/blob/main/docs/repo-taxonomy.md)
