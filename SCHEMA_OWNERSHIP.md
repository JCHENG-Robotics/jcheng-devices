# Schema ownership and consumers

> Status: **repo-local v1.0** as of 2026-11-27. Both JSON Schemas in this
> repository are repository-local documents. Neither is a `jcheng-interfaces`
> contract, and no other repository may parse or depend on them until an
> interfaces proposal is accepted.

## Ownership table

| Schema file | Schema ID (`$id`) | Version | Status | Owner | Consumers | Promotion trigger |
|---|---|---|---|---|---|---|
| `src/jcheng_devices/schemas/device-profile.v1.schema.json` | `jcheng.device-profile.v1` | 1.0.0 | `repo-local` | `jcheng-devices` | none; planned `jcheng-simulation`, `jcheng-learning`, `jcheng-studio` | any consumer parses a device profile |
| `src/jcheng_devices/schemas/capability-profile.v1.schema.json` | `jcheng.capability-profile.v1` | 1.0.0 | `repo-local` | `jcheng-devices` | none; planned `jcheng-applications`, `jcheng-simulation` | any consumer matches capabilities from a profile |

## Rules

1. `Status` is `repo-local` or `contract`. `contract` is reserved for a Schema
   published by `jcheng-interfaces`; this repository has none.
2. A row's `Consumers` lists only repositories that actually parse the file.
   A planned consumer is not a consumer and grants no stability promise.
3. The first external consumer triggers an interfaces proposal. Until that
   proposal is accepted, the external repository must not parse the file.
4. A device profile describes a device model. It never becomes a deployment
   configuration: `jcheng-system/configs/robots/<robot>/profile.yaml` stays the
   runtime authority for a deployed robot.
5. Any new Schema file must be added to this table; the repository gate fails
   when a file under `src/jcheng_devices/schemas/` is undeclared.
6. Version bumps that change required fields are breaking; add a new `vN`
   Schema instead of editing a released one.

## Related

- [Profile schema](docs/PROFILE_SCHEMA.md)
- [Device registry](docs/DEVICE_REGISTRY.md)
- [Integration boundary](docs/INTEGRATION.md)
- [Boundary specification](https://github.com/JCHENG-Robotics/.github/blob/main/docs/repo-boundaries.md)
